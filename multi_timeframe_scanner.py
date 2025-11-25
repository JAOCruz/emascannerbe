"""
Enhanced Crypto EMA Scanner with Multi-Timeframe Analysis
Supports: 15m, 30m, 1h, 4h, 12h, 1D, 1W
"""

import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import json
import os
import glob

class MultiTimeframeEMAScanner:
    def __init__(self, cmc_api_key=None, top_n=200, cache_duration_minutes=60):
        self.coingecko_base = "https://api.coingecko.com/api/v3"
        self.binance_base = "https://api.binance.com/api/v3"
        self.binance_futures_base = "https://fapi.binance.com/fapi/v1"
        self.cmc_api_key = cmc_api_key
        self.cmc_base = "https://pro-api.coinmarketcap.com/v1"
        self.top_n = top_n
        self.cache_duration_minutes = cache_duration_minutes
        self.cache_file_pattern = f'crypto_ema_multi_scan_top{top_n}_*.json'
        
        # All timeframes we support
        self.timeframes = {
            '15m': {'binance': '15m', 'limit': 200, 'label': '15-Min'},
            '30m': {'binance': '30m', 'limit': 200, 'label': '30-Min'},
            '1h': {'binance': '1h', 'limit': 200, 'label': '1-Hour'},
            '4h': {'binance': '4h', 'limit': 60, 'label': '4-Hour'},
            '12h': {'binance': '12h', 'limit': 60, 'label': '12-Hour'},
            '1d': {'binance': '1d', 'limit': 60, 'label': 'Daily'},
            '1w': {'binance': '1w', 'limit': 60, 'label': 'Weekly'}
        }
    
    def get_recent_scan(self):
        """Check if there's a recent scan within the cache duration"""
        try:
            scan_files = glob.glob(self.cache_file_pattern)
            
            if not scan_files:
                return None
            
            most_recent_file = max(scan_files, key=os.path.getctime)
            file_time = datetime.fromtimestamp(os.path.getctime(most_recent_file))
            time_diff = datetime.now() - file_time
            
            if time_diff < timedelta(minutes=self.cache_duration_minutes):
                print(f"\n🔄 Found recent scan from {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   ({int(time_diff.total_seconds() / 60)} minutes ago)")
                print(f"   Loading cached data: {most_recent_file}")
                
                with open(most_recent_file, 'r') as f:
                    data = json.load(f)
                return data
            else:
                print(f"\n⏰ Last scan was {int(time_diff.total_seconds() / 60)} minutes ago")
                print(f"   Cache expired (>{self.cache_duration_minutes} minutes), running new scan...")
                return None
                
        except Exception as e:
            print(f"Error checking cache: {e}")
            return None
    
    def get_top_n_coins(self):
        """Fetch top N cryptocurrencies by market cap from CoinGecko"""
        print(f"Fetching top {self.top_n} coins by market cap...")
        url = f"{self.coingecko_base}/coins/markets"
        
        all_coins = []
        pages_needed = (self.top_n + 49) // 50
        
        for page in range(1, pages_needed + 1):
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
                print(f"  Fetched page {page}/{pages_needed}...")
                time.sleep(1)
                
            except Exception as e:
                print(f"Error fetching page {page}: {e}")
                continue
        
        all_coins = all_coins[:self.top_n]
        print(f"Successfully fetched {len(all_coins)} coins")
        return all_coins
    
    def get_binance_data(self, symbol, interval='1h', limit=200, use_futures=False):
        """Fetch candlestick data from Binance"""
        base_url = self.binance_futures_base if use_futures else self.binance_base
        url = f"{base_url}/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data
        except:
            return None
    
    def calculate_ema(self, prices, period=50):
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return None
        
        df = pd.DataFrame({'price': prices})
        ema = df['price'].ewm(span=period, adjust=False).mean()
        return ema.tolist()
    
    def analyze_timeframe(self, coin_data, timeframe_key, verbose=False):
        """Analyze a single timeframe for a coin"""
        symbol = coin_data['symbol'].upper()
        tf_config = self.timeframes[timeframe_key]
        
        symbol_formats = [
            f"{symbol}USDT",
            f"{symbol}BUSD",
            f"{symbol}FDUSD",
            f"{symbol}USDC"
        ]
        
        for base_symbol in symbol_formats:
            # Try spot first
            klines = self.get_binance_data(
                base_symbol, 
                interval=tf_config['binance'],
                limit=tf_config['limit'],
                use_futures=False
            )
            
            if klines and len(klines) >= 50:
                closes = [float(candle[4]) for candle in klines]
                ema_values = self.calculate_ema(closes, period=50)
                
                if not ema_values:
                    continue
                
                current_price = closes[-1]
                current_ema50 = ema_values[-1]
                pct_diff = ((current_price - current_ema50) / current_ema50) * 100
                
                return {
                    'timeframe': timeframe_key,
                    'timeframe_label': tf_config['label'],
                    'rank': coin_data['market_cap_rank'],
                    'name': coin_data['name'],
                    'symbol': symbol,
                    'binance_symbol': base_symbol,
                    'current_price': current_price,
                    'ema50': current_ema50,
                    'above_ema50': current_price > current_ema50,
                    'pct_from_ema50': pct_diff,
                    'market_cap': coin_data.get('market_cap', 0),
                    'data_source': 'Binance Spot',
                    'candle_count': len(klines)
                }
            
            # Try futures
            klines = self.get_binance_data(
                base_symbol,
                interval=tf_config['binance'],
                limit=tf_config['limit'],
                use_futures=True
            )
            
            if klines and len(klines) >= 50:
                closes = [float(candle[4]) for candle in klines]
                ema_values = self.calculate_ema(closes, period=50)
                
                if not ema_values:
                    continue
                
                current_price = closes[-1]
                current_ema50 = ema_values[-1]
                pct_diff = ((current_price - current_ema50) / current_ema50) * 100
                
                return {
                    'timeframe': timeframe_key,
                    'timeframe_label': tf_config['label'],
                    'rank': coin_data['market_cap_rank'],
                    'name': coin_data['name'],
                    'symbol': symbol,
                    'binance_symbol': base_symbol,
                    'current_price': current_price,
                    'ema50': current_ema50,
                    'above_ema50': current_price > current_ema50,
                    'pct_from_ema50': pct_diff,
                    'market_cap': coin_data.get('market_cap', 0),
                    'data_source': 'Binance Futures',
                    'candle_count': len(klines)
                }
        
        return None
    
    def analyze_coin_all_timeframes(self, coin_data, verbose=False):
        """Analyze a coin across all 7 timeframes"""
        results = {}
        
        for tf_key in self.timeframes.keys():
            result = self.analyze_timeframe(coin_data, tf_key, verbose)
            results[tf_key] = result
        
        return results
    
    def get_timeframe_trend(self, pct_from_ema):
        """Get trend strength based on % from EMA"""
        if pct_from_ema is None:
            return 'N/A'
        
        if pct_from_ema > 20:
            return 'Very Bullish'
        elif pct_from_ema > 10:
            return 'Bullish'
        elif pct_from_ema > 5:
            return 'Slightly Bullish'
        elif pct_from_ema > -5:
            return 'Neutral'
        elif pct_from_ema > -10:
            return 'Slightly Bearish'
        elif pct_from_ema > -20:
            return 'Bearish'
        else:
            return 'Very Bearish'
    
    def scan_all_coins(self, verbose=False):
        """Main function to scan all top N coins across all timeframes"""
        coins = self.get_top_n_coins()
        
        all_coin_results = []
        
        print(f"\nAnalyzing coins across 7 timeframes (15m, 30m, 1h, 4h, 12h, 1D, 1W)...")
        print("-" * 100)
        
        total_coins = len(coins)
        for i, coin in enumerate(coins, 1):
            symbol = coin['symbol'].upper()
            name = coin['name']
            
            print(f"[{i}/{total_coins}] Analyzing {name} ({symbol})...")
            
            results = self.analyze_coin_all_timeframes(coin, verbose=verbose)
            
            # Store complete result
            coin_result = {
                'coin_info': coin,
                'timeframes': results
            }
            all_coin_results.append(coin_result)
            
            # Display summary (compact)
            summary_parts = []
            for tf in ['15m', '30m', '1h', '4h', '12h', '1d', '1w']:
                if results[tf]:
                    pct = results[tf]['pct_from_ema50']
                    summary_parts.append(f"{tf}: {pct:+.1f}%")
                else:
                    summary_parts.append(f"{tf}: N/A")
            
            print(f"   {' | '.join(summary_parts)}")
            
            time.sleep(0.3)  # Slightly faster for more timeframes
        
        return all_coin_results
    
    def generate_timeframe_analysis(self, all_coin_results):
        """Generate analysis showing trend alignment across timeframes"""
        analysis = []
        
        for coin_result in all_coin_results:
            coin_info = coin_result['coin_info']
            timeframes = coin_result['timeframes']
            
            # Count how many timeframes are bullish
            bullish_count = 0
            bearish_count = 0
            total_count = 0
            
            tf_data = {}
            for tf_key, tf_result in timeframes.items():
                if tf_result:
                    total_count += 1
                    if tf_result['above_ema50']:
                        bullish_count += 1
                    else:
                        bearish_count += 1
                    
                    tf_data[tf_key] = {
                        'pct': tf_result['pct_from_ema50'],
                        'trend': self.get_timeframe_trend(tf_result['pct_from_ema50']),
                        'above': tf_result['above_ema50']
                    }
            
            if total_count == 0:
                continue
            
            # Calculate alignment score (% of timeframes that agree)
            alignment_score = max(bullish_count, bearish_count) / total_count * 100
            primary_trend = 'Bullish' if bullish_count > bearish_count else 'Bearish'
            
            analysis.append({
                'rank': coin_info['market_cap_rank'],
                'name': coin_info['name'],
                'symbol': coin_info['symbol'].upper(),
                'bullish_timeframes': bullish_count,
                'bearish_timeframes': bearish_count,
                'total_timeframes': total_count,
                'alignment_score': alignment_score,
                'primary_trend': primary_trend,
                'timeframe_data': tf_data
            })
        
        # Sort by alignment score (highest first)
        analysis.sort(key=lambda x: x['alignment_score'], reverse=True)
        
        return analysis
    
    def display_results(self, all_coin_results):
        """Display formatted multi-timeframe results"""
        print("\n" + "=" * 120)
        print(f"MULTI-TIMEFRAME EMA SCAN COMPLETED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 120)
        
        analysis = self.generate_timeframe_analysis(all_coin_results)
        
        # Display top aligned coins
        print("\n" + "=" * 120)
        print(f"🎯 TOP 20 COINS WITH STRONGEST TIMEFRAME ALIGNMENT")
        print("=" * 120)
        print(f"{'Rank':<6} {'Name':<20} {'Symbol':<8} {'Trend':<10} {'Alignment':<12} {'Bull TF':<10} {'Bear TF':<10}")
        print("-" * 120)
        
        for coin in analysis[:20]:
            print(f"{coin['rank']:<6} {coin['name']:<20} {coin['symbol']:<8} "
                  f"{coin['primary_trend']:<10} {coin['alignment_score']:<11.1f}% "
                  f"{coin['bullish_timeframes']:<10} {coin['bearish_timeframes']:<10}")
        
        # Display detailed timeframe breakdown for top 10
        print("\n" + "=" * 120)
        print(f"📊 DETAILED TIMEFRAME BREAKDOWN - TOP 10 COINS")
        print("=" * 120)
        
        for i, coin in enumerate(analysis[:10], 1):
            print(f"\n#{coin['rank']} {coin['name']} ({coin['symbol']})")
            print(f"Overall: {coin['primary_trend']} with {coin['alignment_score']:.1f}% alignment")
            print(f"{'Timeframe':<12} {'% from EMA':<15} {'Trend':<20} {'Position':<15}")
            print("-" * 70)
            
            for tf in ['15m', '30m', '1h', '4h', '12h', '1d', '1w']:
                if tf in coin['timeframe_data']:
                    data = coin['timeframe_data'][tf]
                    position = "ABOVE EMA ▲" if data['above'] else "BELOW EMA ▼"
                    print(f"{tf:<12} {data['pct']:>+13.2f}% {data['trend']:<20} {position:<15}")
                else:
                    print(f"{tf:<12} {'N/A':<15} {'No Data':<20} {'N/A':<15}")
    
    def save_results(self, all_coin_results):
        """Save results to JSON"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        analysis = self.generate_timeframe_analysis(all_coin_results)
        
        output = {
            'scan_date': datetime.now().isoformat(),
            'top_n': self.top_n,
            'timeframes_analyzed': list(self.timeframes.keys()),
            'coins': all_coin_results,
            'analysis': analysis,
            'summary': {
                'total_scanned': self.top_n,
                'coins_analyzed': len(analysis)
            }
        }
        
        json_filename = f'crypto_ema_multi_scan_top{self.top_n}_{timestamp}.json'
        with open(json_filename, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"\n💾 Results saved to: {json_filename}")
        
        # Save CSV with alignment analysis
        if analysis:
            df = pd.DataFrame(analysis)
            csv_filename = f'crypto_multi_timeframe_top{self.top_n}_{timestamp}.csv'
            
            # Flatten timeframe data for CSV
            rows = []
            for coin in analysis:
                row = {
                    'rank': coin['rank'],
                    'name': coin['name'],
                    'symbol': coin['symbol'],
                    'primary_trend': coin['primary_trend'],
                    'alignment_score': coin['alignment_score'],
                    'bullish_timeframes': coin['bullish_timeframes'],
                    'bearish_timeframes': coin['bearish_timeframes']
                }
                
                # Add each timeframe's data
                for tf in ['15m', '30m', '1h', '4h', '12h', '1d', '1w']:
                    if tf in coin['timeframe_data']:
                        row[f'{tf}_pct'] = coin['timeframe_data'][tf]['pct']
                        row[f'{tf}_trend'] = coin['timeframe_data'][tf]['trend']
                    else:
                        row[f'{tf}_pct'] = None
                        row[f'{tf}_trend'] = 'N/A'
                
                rows.append(row)
            
            df_export = pd.DataFrame(rows)
            df_export.to_csv(csv_filename, index=False)
            print(f"💾 CSV analysis saved to: {csv_filename}")
        
        return json_filename
    
    def run(self):
        """Run the complete multi-timeframe scan"""
        print("=" * 120)
        print(f"CRYPTOCURRENCY MULTI-TIMEFRAME EMA50 SCANNER - TOP {self.top_n}")
        print("Timeframes: 15m, 30m, 1h, 4h, 12h, 1D, 1W")
        print("Sources: Binance Spot + Binance Futures")
        print(f"Cache Duration: {self.cache_duration_minutes} minutes")
        print("=" * 120)
        
        cached_data = self.get_recent_scan()
        
        if cached_data:
            analysis = cached_data.get('analysis', [])
            all_coin_results = cached_data.get('coins', [])
            
            print("\n✅ Using cached scan data")
            self.display_results(all_coin_results)
            
            print(f"\n💡 To force a new scan, delete the cache file or wait {self.cache_duration_minutes} minutes")
            return
        
        start_time = time.time()
        
        all_coin_results = self.scan_all_coins()
        
        self.display_results(all_coin_results)
        self.save_results(all_coin_results)
        
        elapsed_time = time.time() - start_time
        print(f"\n⏱️  Scan completed in {elapsed_time/60:.2f} minutes ({elapsed_time:.1f} seconds)")
        print(f"✅ Results cached for {self.cache_duration_minutes} minutes")

# Main execution
if __name__ == "__main__":
    CMC_API_KEY = None  # Optional
    TOP_N_COINS = 10  # Start small for testing
    CACHE_DURATION_MINUTES = 60
    
    scanner = MultiTimeframeEMAScanner(
        cmc_api_key=CMC_API_KEY,
        top_n=TOP_N_COINS,
        cache_duration_minutes=CACHE_DURATION_MINUTES
    )
    scanner.run()