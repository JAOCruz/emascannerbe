"""
Enhanced Flask API Server with PostgreSQL Database
Serves candle data instantly from database
"""

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from flask_cors import CORS
import psycopg
from psycopg.rows import dict_row
import os
import json
from datetime import datetime, timedelta
import threading
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
CORS(app)

# Database connection pool
DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    """Get database connection"""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

# Global scan status
scan_status = {
    'running': False,
    'progress': 0,
    'total': 0,
    'current_coin': '',
    'status_message': 'Ready',
    'start_time': None,
    'error': None
}

@app.route('/health')
def health():
    """Health check endpoint"""
    print("🔍 Health check called")
    print(f"DATABASE_URL present: {DATABASE_URL is not None}")
    
    try:
        print("Attempting database connection...")
        conn = get_db_connection()
        print("Connection successful, executing query...")
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()
        print(f"Query result: {result}")
        cur.close()
        conn.close()
        print("✅ Health check passed")
        
        return jsonify({
            'status': 'ok',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/coins')
def get_coins():
    """Get all coins from database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT * FROM coins 
            ORDER BY market_cap_rank ASC
        """)
        
        coins = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'coins': coins,
            'total': len(coins)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/coins/<symbol>')
def get_coin(symbol):
    """Get specific coin data"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get coin info
        cur.execute("""
            SELECT * FROM coins WHERE symbol = %s
        """, (symbol.upper(),))
        
        coin = cur.fetchone()
        
        if not coin:
            return jsonify({'error': 'Coin not found'}), 404
        
        cur.close()
        conn.close()
        
        return jsonify(coin)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ema-analysis/<symbol>')
def get_ema_analysis(symbol):
    """Get latest EMA analysis for a coin across all timeframes"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get latest analysis for each timeframe
        cur.execute("""
            SELECT DISTINCT ON (timeframe)
                symbol,
                timeframe,
                current_price,
                ema50,
                pct_from_ema50,
                above_ema50,
                analysis_date
            FROM ema_analysis
            WHERE symbol = %s
            ORDER BY timeframe, analysis_date DESC
        """, (symbol.upper(),))
        
        results = cur.fetchall()
        
        if not results:
            return jsonify({'error': 'No analysis data found'}), 404
        
        # Organize by timeframe
        analysis = {}
        for row in results:
            analysis[row['timeframe']] = {
                'current_price': row['current_price'],
                'ema50': row['ema50'],
                'pct_from_ema50': row['pct_from_ema50'],
                'above_ema50': row['above_ema50'],
                'analysis_date': row['analysis_date'].isoformat()
            }
        
        cur.close()
        conn.close()
        
        return jsonify({
            'symbol': symbol.upper(),
            'analysis': analysis
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ema-analysis/all')
def get_all_ema_analysis():
    """Get latest EMA analysis for all coins"""
    try:
        timeframe = request.args.get('timeframe', '1w')  # default to weekly
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT DISTINCT ON (symbol)
                ea.symbol,
                c.name,
                c.market_cap_rank,
                ea.timeframe,
                ea.current_price,
                ea.ema50,
                ea.pct_from_ema50,
                ea.above_ema50,
                ea.analysis_date
            FROM ema_analysis ea
            JOIN coins c ON ea.symbol = c.symbol
            WHERE ea.timeframe = %s
            ORDER BY ea.symbol, ea.analysis_date DESC
        """, (timeframe,))
        
        results = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Categorize results
        above_ema = [r for r in results if r['above_ema50']]
        below_ema = [r for r in results if not r['above_ema50']]
        
        return jsonify({
            'timeframe': timeframe,
            'total': len(results),
            'above_ema50': {
                'count': len(above_ema),
                'coins': above_ema
            },
            'below_ema50': {
                'count': len(below_ema),
                'coins': below_ema
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/coins/<symbol>/details')
def get_coin_details(symbol):
    """
    Get comprehensive coin details including:
    - Data coverage (candles per timeframe)
    - EMA analysis across all timeframes
    - Historical price range (5-year high/low)
    - Data quality score
    - Last update timestamp
    """
    try:
        symbol = symbol.upper()
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Get coin basic info
        cur.execute("""
            SELECT symbol, name, market_cap_rank, current_price, 
                   market_cap, binance_symbol, data_source, last_updated
            FROM coins
            WHERE symbol = %s
        """, (symbol,))
        
        coin_info = cur.fetchone()
        
        if not coin_info:
            cur.close()
            conn.close()
            return jsonify({'error': 'Coin not found'}), 404
        
        # 2. Get data coverage per timeframe
        cur.execute("""
            SELECT 
                timeframe,
                COUNT(*) as candle_count,
                MIN(time) as earliest_candle,
                MAX(time) as latest_candle
            FROM candles
            WHERE symbol = %s
            GROUP BY timeframe
            ORDER BY 
                CASE timeframe
                    WHEN '15m' THEN 1
                    WHEN '1h' THEN 2
                    WHEN '4h' THEN 3
                    WHEN '1d' THEN 4
                    WHEN '1w' THEN 5
                END
        """, (symbol,))
        
        coverage = cur.fetchall()
        
        # Calculate years of coverage and quality for each timeframe
        coverage_data = []
        total_quality = 0
        
        for tf in coverage:
            earliest = tf['earliest_candle']
            latest = tf['latest_candle']
            candle_count = tf['candle_count']
            
            # Calculate years of data
            if earliest and latest:
                time_span = latest - earliest
                years = time_span.days / 365.25
            else:
                years = 0
            
            # Calculate quality score (0-100)
            # Based on how close to 5 years of data we have
            expected_candles = {
                '15m': 175200,  # 5 years
                '1h': 43800,
                '4h': 10950,
                '1d': 1825,
                '1w': 260
            }
            
            expected = expected_candles.get(tf['timeframe'], 1000)
            quality = min(100, int((candle_count / expected) * 100))
            total_quality += quality
            
            # Quality label
            if quality >= 90:
                quality_label = "Excellent"
                quality_color = "green"
            elif quality >= 70:
                quality_label = "Good"
                quality_color = "cyan"
            elif quality >= 50:
                quality_label = "Fair"
                quality_color = "yellow"
            else:
                quality_label = "Limited"
                quality_color = "orange"
            
            coverage_data.append({
                'timeframe': tf['timeframe'],
                'candle_count': candle_count,
                'earliest_candle': earliest.isoformat() if earliest else None,
                'latest_candle': latest.isoformat() if latest else None,
                'years_of_data': round(years, 2),
                'quality_score': quality,
                'quality_label': quality_label,
                'quality_color': quality_color
            })
        
        # Overall data quality score
        overall_quality = int(total_quality / len(coverage)) if coverage else 0
        
        # 3. Get EMA analysis for all timeframes
        cur.execute("""
            SELECT DISTINCT ON (timeframe)
                timeframe,
                current_price,
                ema50,
                pct_from_ema50,
                above_ema50,
                analysis_date
            FROM ema_analysis
            WHERE symbol = %s
            ORDER BY timeframe, analysis_date DESC
        """, (symbol,))
        
        ema_analysis = cur.fetchall()
        
        # 4. Get historical price range (all-time or 5 years)
        cur.execute("""
            SELECT 
                MIN(low) as all_time_low,
                MAX(high) as all_time_high,
                MIN(CASE WHEN time >= NOW() - INTERVAL '5 years' THEN low END) as five_year_low,
                MAX(CASE WHEN time >= NOW() - INTERVAL '5 years' THEN high END) as five_year_high,
                MIN(CASE WHEN time >= NOW() - INTERVAL '1 year' THEN low END) as one_year_low,
                MAX(CASE WHEN time >= NOW() - INTERVAL '1 year' THEN high END) as one_year_high
            FROM candles
            WHERE symbol = %s AND timeframe = '1d'
        """, (symbol,))
        
        price_range = cur.fetchone()
        
        # Calculate current price position
        current_price = float(coin_info['current_price']) if coin_info['current_price'] else 0
        
        if price_range and price_range['five_year_low'] and price_range['five_year_high']:
            five_year_range = float(price_range['five_year_high']) - float(price_range['five_year_low'])
            if five_year_range > 0:
                price_position = ((current_price - float(price_range['five_year_low'])) / five_year_range) * 100
            else:
                price_position = 50
        else:
            price_position = None
        
        # 5. Trading confidence score
        # Based on: data quality + EMA trend alignment + price position
        confidence_factors = []
        
        if overall_quality >= 80:
            confidence_factors.append("Excellent data coverage")
        elif overall_quality >= 60:
            confidence_factors.append("Good data coverage")
        else:
            confidence_factors.append("Limited historical data")
        
        # Check EMA alignment across timeframes
        if ema_analysis:
            above_count = sum(1 for e in ema_analysis if e['above_ema50'])
            ema_alignment = (above_count / len(ema_analysis)) * 100
            
            if ema_alignment >= 80:
                confidence_factors.append("Strong bullish trend")
            elif ema_alignment >= 60:
                confidence_factors.append("Bullish momentum")
            elif ema_alignment <= 20:
                confidence_factors.append("Strong bearish trend")
            elif ema_alignment <= 40:
                confidence_factors.append("Bearish momentum")
            else:
                confidence_factors.append("Mixed signals")
        
        # Overall confidence
        if overall_quality >= 80 and len(ema_analysis) >= 4:
            confidence = "HIGH"
            confidence_color = "green"
        elif overall_quality >= 60 and len(ema_analysis) >= 3:
            confidence = "MEDIUM"
            confidence_color = "cyan"
        else:
            confidence = "LOW"
            confidence_color = "orange"
        
        cur.close()
        conn.close()
        
        return jsonify({
            'coin_info': coin_info,
            'data_coverage': coverage_data,
            'overall_quality': overall_quality,
            'ema_analysis': ema_analysis,
            'price_range': {
                'all_time_low': float(price_range['all_time_low']) if price_range and price_range['all_time_low'] else None,
                'all_time_high': float(price_range['all_time_high']) if price_range and price_range['all_time_high'] else None,
                'five_year_low': float(price_range['five_year_low']) if price_range and price_range['five_year_low'] else None,
                'five_year_high': float(price_range['five_year_high']) if price_range and price_range['five_year_high'] else None,
                'one_year_low': float(price_range['one_year_low']) if price_range and price_range['one_year_low'] else None,
                'one_year_high': float(price_range['one_year_high']) if price_range and price_range['one_year_high'] else None,
                'current_price': current_price,
                'price_position_5y': round(price_position, 1) if price_position else None
            },
            'trading_confidence': {
                'level': confidence,
                'color': confidence_color,
                'factors': confidence_factors
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/candles/<symbol>')
def get_candles(symbol):
    """Get candle data for a symbol"""
    try:
        timeframe = request.args.get('timeframe', '1d')
        limit = int(request.args.get('limit', 100))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                time,
                open,
                high,
                low,
                close,
                volume,
                ema50
            FROM candles
            WHERE symbol = %s AND timeframe = %s
            ORDER BY time DESC
            LIMIT %s
        """, (symbol.upper(), timeframe, limit))
        
        candles = cur.fetchall()
        
        cur.close()
        conn.close()
        
        if not candles:
            return jsonify({'error': 'No candle data found'}), 404
        
        # Reverse to get chronological order
        candles = list(reversed(candles))
        
        return jsonify({
            'symbol': symbol.upper(),
            'timeframe': timeframe,
            'candles': candles,
            'count': len(candles)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/strategic-summary')
def get_strategic_summary():
    """Get strategic investment summary (EVALUATE, TRADE NOW, AVOID)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get latest weekly analysis
        cur.execute("""
            SELECT DISTINCT ON (symbol)
                ea.symbol,
                c.name,
                c.market_cap_rank,
                ea.current_price,
                ea.ema50,
                ea.pct_from_ema50,
                ea.above_ema50
            FROM ema_analysis ea
            JOIN coins c ON ea.symbol = c.symbol
            WHERE ea.timeframe = '1w'
            ORDER BY ea.symbol, ea.analysis_date DESC
        """)
        
        weekly_results = cur.fetchall()
        
        # Get 4H analysis for "trade now" opportunities
        cur.execute("""
            SELECT DISTINCT ON (symbol)
                ea.symbol,
                c.name,
                ea.pct_from_ema50
            FROM ema_analysis ea
            JOIN coins c ON ea.symbol = c.symbol
            WHERE ea.timeframe = '4h'
            ORDER BY ea.symbol, ea.analysis_date DESC
        """)
        
        four_h_results = {r['symbol']: r for r in cur.fetchall()}
        
        cur.close()
        conn.close()
        
        # Categorize coins
        coins_to_evaluate = []  # Above EMA or within 10% below
        coins_to_avoid = []     # More than 10% below EMA
        coins_to_trade_now = [] # 4H within ±5% of EMA
        
        for coin in weekly_results:
            symbol = coin['symbol']
            pct = coin['pct_from_ema50']
            
            # EVALUATE: Above EMA OR within 10% below
            if pct >= -10:
                coins_to_evaluate.append(coin)
            else:
                coins_to_avoid.append(coin)
            
            # TRADE NOW: 4H within ±5% of EMA
            if symbol in four_h_results:
                four_h_pct = four_h_results[symbol]['pct_from_ema50']
                if -5 <= four_h_pct <= 5:
                    coins_to_trade_now.append({
                        **coin,
                        'four_h_pct_from_ema': four_h_pct
                    })
        
        return jsonify({
            'evaluate_long_term': {
                'count': len(coins_to_evaluate),
                'coins': coins_to_evaluate,
                'description': 'Above Weekly EMA50 OR within 10% below'
            },
            'trade_now_short_term': {
                'count': len(coins_to_trade_now),
                'coins': coins_to_trade_now,
                'description': '4H chart within ±5% of EMA50'
            },
            'avoid': {
                'count': len(coins_to_avoid),
                'coins': coins_to_avoid,
                'description': 'More than 10% below Weekly EMA50'
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scan-history')
def get_scan_history():
    """Get scan history"""
    try:
        limit = int(request.args.get('limit', 10))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT * FROM scan_history
            ORDER BY scan_date DESC
            LIMIT %s
        """, (limit,))
        
        history = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'history': history,
            'count': len(history)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
def get_status():
    """Get current scan status"""
    return jsonify(scan_status)

@app.route('/api/current-prices')
def get_current_prices():
    """Get current prices from database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT * FROM current_prices
            ORDER BY last_updated DESC
        """)
        
        prices = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'prices': prices,
            'count': len(prices)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/database-stats')
def get_database_stats():
    """Get database statistics"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        stats = {}
        
        # Count candles
        cur.execute("SELECT COUNT(*) as count FROM candles")
        stats['candles'] = cur.fetchone()['count']
        
        # Count coins
        cur.execute("SELECT COUNT(*) as count FROM coins")
        stats['coins'] = cur.fetchone()['count']
        
        # Count EMA analysis
        cur.execute("SELECT COUNT(*) as count FROM ema_analysis")
        stats['ema_analysis'] = cur.fetchone()['count']
        
        # Count scans
        cur.execute("SELECT COUNT(*) as count FROM scan_history")
        stats['scans'] = cur.fetchone()['count']
        
        # Get latest scan date
        cur.execute("SELECT MAX(scan_date) as latest FROM scan_history")
        latest = cur.fetchone()
        stats['latest_scan'] = latest['latest'].isoformat() if latest['latest'] else None
        
        # Get oldest candle data
        cur.execute("SELECT MIN(time) as oldest FROM candles")
        oldest = cur.fetchone()
        stats['oldest_candle'] = oldest['oldest'].isoformat() if oldest['oldest'] else None
        
        cur.close()
        conn.close()
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 CRYPTO SCANNER API WITH DATABASE")
    print("=" * 60)
    print(f"📡 API Server: http://localhost:5001")
    print(f"🐘 Database: {'Connected' if DATABASE_URL else 'Not configured'}")
    print("=" * 60)
    print("\n📊 Endpoints:")
    print("  GET  /health                    - Health check + DB status")
    print("  GET  /api/coins                 - All coins")
    print("  GET  /api/coins/<symbol>        - Specific coin")
    print("  GET  /api/ema-analysis/<symbol> - EMA analysis for coin")
    print("  GET  /api/ema-analysis/all      - All EMA analysis")
    print("  GET  /api/candles/<symbol>      - Candle data")
    print("  GET  /api/strategic-summary     - EVALUATE/TRADE/AVOID lists")
    print("  GET  /api/scan-history          - Scan history")
    print("  GET  /api/current-prices        - Current prices")
    print("  GET  /api/database-stats        - Database statistics")
    print("  GET  /api/status                - Scan status")
    print("=" * 60)
    
    port = int(os.getenv('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port)