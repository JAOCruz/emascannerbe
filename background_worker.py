"""
Background Worker to Fetch and Store Candle Data
Runs continuously to keep database updated
"""

import psycopg
from psycopg import sql
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import os
import sys

DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    """Get database connection"""
    return psycopg.connect(DATABASE_URL)

def get_top_coins(limit=200):
    """Fetch top N coins from CoinGecko"""
    print(f"📊 Fetching top {limit} coins...")
    
    url = "https://api.coingecko.com/api/v3/coins/markets"
    all_coins = []
    
    pages = (limit + 49) // 50
    
    for page in range(1, pages + 1):
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 50,
            'page': page,
            'sparkline': False
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            coins = response.json()
            all_coins.extend(coins)
            time.sleep(1)
        except Exception as e:
            print(f"   ⚠️  Error fetching page {page}: {e}")
            continue
    
    print(f"   ✅ Got {len(all_coins)} coins")
    return all_coins[:limit]

def store_coins(coins):
    """Store coin metadata in database"""
    print("💾 Storing coin metadata...")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    for coin in coins:
        try:
            cur.execute("""
                INSERT INTO coins (symbol, name, market_cap_rank, market_cap, current_price, last_updated)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol) 
                DO UPDATE SET
                    name = EXCLUDED.name,
                    market_cap_rank = EXCLUDED.market_cap_rank,
                    market_cap = EXCLUDED.market_cap,
                    current_price = EXCLUDED.current_price,
                    last_updated = EXCLUDED.last_updated
            """, (
                coin['symbol'].upper(),
                coin['name'],
                coin.get('market_cap_rank', 0),
                coin.get('market_cap', 0),
                coin.get('current_price', 0),
                datetime.now()
            ))
        except Exception as e:
            print(f"   ⚠️  Error storing {coin['symbol']}: {e}")
            continue
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"   ✅ Stored {len(coins)} coins")

def get_binance_candles(symbol, interval='1d', limit=100):
    """Fetch candles from Binance"""
    base_url = "https://api.binance.com/api/v3/klines"
    
    symbol_formats = [
        f"{symbol}USDT",
        f"{symbol}BUSD",
        f"{symbol}FDUSD"
    ]
    
    for binance_symbol in symbol_formats:
        try:
            params = {
                'symbol': binance_symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) >= 50:
                return data, binance_symbol, 'Binance Spot'
                
        except:
            continue
    
    # Try futures
    futures_url = "https://fapi.binance.com/fapi/v1/klines"
    
    for binance_symbol in symbol_formats:
        try:
            params = {
                'symbol': binance_symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = requests.get(futures_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) >= 50:
                return data, binance_symbol, 'Binance Futures'
                
        except:
            continue
    
    return None, None, None

def calculate_ema(prices, period=50):
    """Calculate EMA"""
    if len(prices) < period:
        return None
    
    df = pd.DataFrame({'price': prices})
    ema = df['price'].ewm(span=period, adjust=False).mean()
    return ema.tolist()

def store_candles(symbol, timeframe, candles, ema_values, binance_symbol, data_source):
    """Store candles in database"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    rows = []
    for i, candle in enumerate(candles):
        timestamp = datetime.fromtimestamp(candle[0] / 1000)
        ema50 = ema_values[i] if ema_values and i < len(ema_values) else None
        
        rows.append((
            timestamp,
            symbol,
            timeframe,
            float(candle[1]),  # open
            float(candle[2]),  # high
            float(candle[3]),  # low
            float(candle[4]),  # close
            float(candle[5]),  # volume
            ema50
        ))
    
    # Batch insert using executemany
    cur.executemany(
        """
        INSERT INTO candles (time, symbol, timeframe, open, high, low, close, volume, ema50)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (time, symbol, timeframe) DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume,
            ema50 = EXCLUDED.ema50
        """,
        rows
    )
    
    # Update coin with binance symbol
    cur.execute("""
        UPDATE coins 
        SET binance_symbol = %s, data_source = %s
        WHERE symbol = %s
    """, (binance_symbol, data_source, symbol))
    
    conn.commit()
    cur.close()
    conn.close()

def store_ema_analysis(symbol, timeframe, current_price, ema50):
    """Store EMA analysis"""
    pct_from_ema = ((current_price - ema50) / ema50) * 100
    above_ema = current_price > ema50
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO ema_analysis 
        (symbol, timeframe, current_price, ema50, pct_from_ema50, above_ema50, analysis_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (symbol, timeframe, analysis_date) DO UPDATE SET
            current_price = EXCLUDED.current_price,
            ema50 = EXCLUDED.ema50,
            pct_from_ema50 = EXCLUDED.pct_from_ema50,
            above_ema50 = EXCLUDED.above_ema50
    """, (
        symbol,
        timeframe,
        current_price,
        ema50,
        pct_from_ema,
        above_ema,
        datetime.now().date()
    ))
    
    conn.commit()
    cur.close()
    conn.close()

def process_coin(coin, timeframes):
    """Process a single coin across multiple timeframes"""
    symbol = coin['symbol'].upper()
    success_count = 0
    
    for tf_key, tf_config in timeframes.items():
        try:
            candles, binance_symbol, data_source = get_binance_candles(
                symbol,
                interval=tf_config['binance'],
                limit=tf_config['limit']
            )
            
            if not candles:
                continue
            
            # Calculate EMA
            closes = [float(c[4]) for c in candles]
            ema_values = calculate_ema(closes, period=50)
            
            if not ema_values:
                continue
            
            # Store candles
            store_candles(symbol, tf_key, candles, ema_values, binance_symbol, data_source)
            
            # Store EMA analysis
            current_price = closes[-1]
            current_ema = ema_values[-1]
            store_ema_analysis(symbol, tf_key, current_price, current_ema)
            
            success_count += 1
            
        except Exception as e:
            print(f"      ⚠️  Error processing {symbol} {tf_key}: {e}")
            continue
    
    return success_count > 0  # Return True if at least one timeframe succeeded

def run_full_scan(top_n=200):
    """Run a complete scan and update database"""
    print("\n" + "=" * 60)
    print(f"🔄 STARTING FULL SCAN - TOP {top_n} COINS")
    print("=" * 60)
    
    start_time = time.time()
    
    # Timeframes to scan
    timeframes = {
        '15m': {'binance': '15m', 'limit': 200},
        '1h': {'binance': '1h', 'limit': 200},
        '4h': {'binance': '4h', 'limit': 60},
        '1d': {'binance': '1d', 'limit': 60},
        '1w': {'binance': '1w', 'limit': 60}
    }
    
    # Get top coins
    coins = get_top_coins(limit=top_n)
    
    # Store coin metadata
    store_coins(coins)
    
    # Process each coin
    print(f"\n📈 Processing {len(coins)} coins across {len(timeframes)} timeframes...")
    
    success_count = 0
    for i, coin in enumerate(coins, 1):
        print(f"[{i}/{len(coins)}] Processing {coin['name']} ({coin['symbol'].upper()})...")
        
        if process_coin(coin, timeframes):
            success_count += 1
        
        time.sleep(0.5)  # Rate limiting
    
    # Store scan history
    duration = int(time.time() - start_time)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO scan_history (scan_date, top_n, coins_scanned, scan_duration_seconds)
        VALUES (%s, %s, %s, %s)
    """, (datetime.now(), top_n, success_count, duration))
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print(f"✅ SCAN COMPLETE")
    print(f"   Processed: {success_count}/{len(coins)} coins")
    print(f"   Duration: {duration // 60}m {duration % 60}s")
    print("=" * 60)

def run_continuous(interval_minutes=60, top_n=200):
    """Run scans continuously"""
    print("\n🔄 STARTING CONTINUOUS WORKER")
    print(f"   Interval: Every {interval_minutes} minutes")
    print(f"   Top N coins: {top_n}")
    print(f"   Press Ctrl+C to stop\n")
    
    while True:
        try:
            run_full_scan(top_n=top_n)
            
            print(f"\n⏰ Waiting {interval_minutes} minutes until next scan...")
            time.sleep(interval_minutes * 60)
            
        except KeyboardInterrupt:
            print("\n\n👋 Stopping worker...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("   Retrying in 5 minutes...")
            time.sleep(300)

if __name__ == "__main__":
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in environment")
        sys.exit(1)
    
    # Default: scan top 200 coins every 60 minutes
    TOP_N = int(os.getenv('TOP_N_COINS', 200))
    INTERVAL_MINUTES = int(os.getenv('SCAN_INTERVAL_MINUTES', 60))
    
    run_continuous(interval_minutes=INTERVAL_MINUTES, top_n=TOP_N)