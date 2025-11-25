import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import json
import os
import glob

class CryptoEMAScanner:
    def __init__(self, cmc_api_key=None, top_n=200, cache_duration_minutes=60):
        self.coingecko_base = "https://api.coingecko.com/api/v3"
        self.binance_base = "https://api.binance.com/api/v3"
        self.binance_futures_base = "https://fapi.binance.com/fapi/v1"
        self.cmc_api_key = cmc_api_key
        self.cmc_base = "https://pro-api.coinmarketcap.com/v1"
        self.top_n = top_n
        self.cache_duration_minutes = cache_duration_minutes
        self.cache_file_pattern = f'crypto_ema_scan_top{top_n}_*.json'
        
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
    
    def get_binance_spot_data(self, symbol, interval='1w', limit=60):
        """Fetch SPOT candlestick data from Binance"""
        url = f"{self.binance_base}/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data, 'spot'
        except:
            return None, None
    
    def get_binance_futures_data(self, symbol, interval='1w', limit=60):
        """Fetch FUTURES candlestick data from Binance"""
        url = f"{self.binance_futures_base}/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data, 'futures'
        except:
            return None, None
    
    def get_cmc_data(self, symbol, interval='weekly', limit=60):
        """Fetch OHLCV data from CoinMarketCap"""
        if not self.cmc_api_key:
            return None
        
        url = f"{self.cmc_base}/cryptocurrency/map"
        headers = {
            'X-CMC_PRO_API_KEY': self.cmc_api_key,
            'Accept': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers, params={'symbol': symbol}, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('data') or len(data['data']) == 0:
                return None
            
            coin_id = data['data'][0]['id']
            ohlcv_url = f"{self.cmc_base}/cryptocurrency/ohlcv/historical"
            
            if interval == 'weekly':
                days_back = limit * 7
                time_period = 'weekly'
            elif interval == 'daily':
                days_back = limit
                time_period = 'daily'
            else:  # hourly
                days_back = int(limit / 24 * 4)  # Approximate for 4h intervals
                time_period = 'hourly'
            
            time_start = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            
            params = {
                'id': coin_id,
                'time_start': time_start,
                'time_period': time_period,
                'count': limit,
                'convert': 'USD'
            }
            
            response = requests.get(ohlcv_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            ohlcv_data = response.json()
            
            if ohlcv_data.get('data') and ohlcv_data['data'].get('quotes'):
                quotes = ohlcv_data['data']['quotes']
                candles = []
                for quote in quotes:
                    q = quote['quote']['USD']
                    candles.append([
                        quote['time_open'],
                        q['open'],
                        q['high'],
                        q['low'],
                        q['close'],
                        q['volume']
                    ])
                return candles
            
            return None
            
        except Exception as e:
            return None
    
    def calculate_ema(self, prices, period=50):
        """Calculate Exponential Moving Average"""
        df = pd.DataFrame({'price': prices})
        ema = df['price'].ewm(span=period, adjust=False).mean()
        return ema.tolist()
    
    def analyze_coin_binance(self, coin_data, interval='1w', limit=60, verbose=False):
        """Analyze a coin using Binance data (SPOT + FUTURES)"""
        symbol = coin_data['symbol'].upper()
        
        symbol_formats = [
            f"{symbol}USDT",
            f"{symbol}BUSD",
            f"{symbol}FDUSD",
            f"{symbol}USDC",
            f"{symbol}USD",
            f"{symbol}BTC",
            f"{symbol}ETH"
        ]
        
        for base_symbol in symbol_formats:
            klines, market_type = self.get_binance_spot_data(base_symbol, interval=interval, limit=limit)
            
            if klines and len(klines) >= 50:
                closes = [float(candle[4]) for candle in klines]
                ema_values = self.calculate_ema(closes, period=50)
                
                current_price = closes[-1]
                current_ema50 = ema_values[-1]
                pct_diff = ((current_price - current_ema50) / current_ema50) * 100
                
                timeframe_label = "Weekly" if interval == '1w' else "Daily" if interval == '1d' else "4-Hour"
                
                return {
                    'rank': coin_data['market_cap_rank'],
                    'name': coin_data['name'],
                    'symbol': symbol,
                    'binance_symbol': base_symbol,
                    'current_price': current_price,
                    'ema50': current_ema50,
                    'above_ema50': current_price > current_ema50,
                    'pct_from_ema50': pct_diff,
                    'market_cap': coin_data.get('market_cap', 0),
                    'timeframe': timeframe_label,
                    'data_source': 'Binance Spot',
                    'candle_count': len(klines)
                }
            
            if klines and verbose:
                print(f"      → {base_symbol} (Spot): Only {len(klines)} candles")
            
            klines, market_type = self.get_binance_futures_data(base_symbol, interval=interval, limit=limit)
            
            if klines and len(klines) >= 50:
                closes = [float(candle[4]) for candle in klines]
                ema_values = self.calculate_ema(closes, period=50)
                
                current_price = closes[-1]
                current_ema50 = ema_values[-1]
                pct_diff = ((current_price - current_ema50) / current_ema50) * 100
                
                timeframe_label = "Weekly" if interval == '1w' else "Daily" if interval == '1d' else "4-Hour"
                
                return {
                    'rank': coin_data['market_cap_rank'],
                    'name': coin_data['name'],
                    'symbol': symbol,
                    'binance_symbol': base_symbol,
                    'current_price': current_price,
                    'ema50': current_ema50,
                    'above_ema50': current_price > current_ema50,
                    'pct_from_ema50': pct_diff,
                    'market_cap': coin_data.get('market_cap', 0),
                    'timeframe': timeframe_label,
                    'data_source': 'Binance Futures',
                    'candle_count': len(klines)
                }
            
            if klines and verbose:
                print(f"      → {base_symbol} (Futures): Only {len(klines)} candles")
        
        return None
    
    def analyze_coin_cmc(self, coin_data, interval='weekly', limit=60):
        """Analyze a coin using CoinMarketCap data"""
        if not self.cmc_api_key:
            return None
        
        symbol = coin_data['symbol'].upper()
        klines = self.get_cmc_data(symbol, interval=interval, limit=limit)
        
        if klines and len(klines) >= 50:
            closes = [float(candle[4]) for candle in klines]
            ema_values = self.calculate_ema(closes, period=50)
            
            current_price = closes[-1]
            current_ema50 = ema_values[-1]
            pct_diff = ((current_price - current_ema50) / current_ema50) * 100
            
            timeframe_label = "Weekly" if interval == 'weekly' else "Daily" if interval == 'daily' else "4-Hour"
            
            return {
                'rank': coin_data['market_cap_rank'],
                'name': coin_data['name'],
                'symbol': symbol,
                'binance_symbol': 'N/A',
                'current_price': current_price,
                'ema50': current_ema50,
                'above_ema50': current_price > current_ema50,
                'pct_from_ema50': pct_diff,
                'market_cap': coin_data.get('market_cap', 0),
                'timeframe': timeframe_label,
                'data_source': 'CoinMarketCap',
                'candle_count': len(klines)
            }
        
        return None
    
    def analyze_coin_all_timeframes(self, coin_data, verbose=False):
        """Analyze a coin across all timeframes: Weekly, Daily, and 4-Hour"""
        results = {}
        
        # Weekly analysis
        result = self.analyze_coin_binance(coin_data, interval='1w', limit=60, verbose=verbose)
        if not result and self.cmc_api_key:
            result = self.analyze_coin_cmc(coin_data, interval='weekly', limit=60)
        results['weekly'] = result
        
        # Daily analysis
        result = self.analyze_coin_binance(coin_data, interval='1d', limit=60, verbose=verbose)
        if not result and self.cmc_api_key:
            result = self.analyze_coin_cmc(coin_data, interval='daily', limit=60)
        results['daily'] = result
        
        # 4-Hour analysis
        result = self.analyze_coin_binance(coin_data, interval='4h', limit=60, verbose=verbose)
        if not result and self.cmc_api_key:
            result = self.analyze_coin_cmc(coin_data, interval='hourly', limit=60)
        results['4h'] = result
        
        return results
    
    def scan_all_coins(self, verbose=False):
        """Main function to scan all top N coins across all timeframes"""
        coins = self.get_top_n_coins()
        
        all_coin_results = []
        
        print(f"\nAnalyzing coins across all timeframes (Weekly, Daily, 4H)...")
        print("-" * 80)
        
        total_coins = len(coins)
        for i, coin in enumerate(coins, 1):
            symbol = coin['symbol'].upper()
            name = coin['name']
            
            print(f"[{i}/{total_coins}] Analyzing {name} ({symbol})...")
            
            results = self.analyze_coin_all_timeframes(coin, verbose=verbose)
            
            # Store complete result
            coin_result = {
                'coin_info': coin,
                'weekly': results['weekly'],
                'daily': results['daily'],
                '4h': results['4h']
            }
            all_coin_results.append(coin_result)
            
            # Display summary
            weekly_status = f"Weekly: {results['weekly']['pct_from_ema50']:+.2f}%" if results['weekly'] else "Weekly: N/A"
            daily_status = f"Daily: {results['daily']['pct_from_ema50']:+.2f}%" if results['daily'] else "Daily: N/A"
            four_h_status = f"4H: {results['4h']['pct_from_ema50']:+.2f}%" if results['4h'] else "4H: N/A"
            
            print(f"   {weekly_status} | {daily_status} | {four_h_status}")
            
            time.sleep(0.5)
        
        return all_coin_results
    
    def categorize_results(self, all_coin_results):
        """Categorize coins into different lists based on EMA analysis"""
        results_above_weekly = []
        results_below_weekly = []
        results_above_daily = []
        results_below_daily = []
        results_4h = []
        failed_coins = []
        
        for coin_result in all_coin_results:
            coin_info = coin_result['coin_info']
            weekly = coin_result['weekly']
            daily = coin_result['daily']
            four_h = coin_result['4h']
            
            # Categorize by primary timeframe (Weekly/Daily)
            if weekly:
                if weekly['above_ema50']:
                    results_above_weekly.append(weekly)
                else:
                    results_below_weekly.append(weekly)
            elif daily:
                if daily['above_ema50']:
                    results_above_daily.append(daily)
                else:
                    results_below_daily.append(daily)
            else:
                failed_coins.append({
                    'rank': coin_info['market_cap_rank'],
                    'name': coin_info['name'],
                    'symbol': coin_info['symbol'].upper()
                })
            
            # Store 4H data if available
            if four_h:
                results_4h.append(four_h)
        
        return results_above_weekly, results_below_weekly, results_above_daily, results_below_daily, results_4h, failed_coins
    
    def generate_strategic_summary(self, results_above_weekly, results_below_weekly,
                                   results_above_daily, results_below_daily, results_4h):
        """Generate strategic investment summary"""
        
        # COINS TO EVALUATE (Long-term)
        coins_to_evaluate = []
        
        # 1. All coins above weekly EMA50
        coins_to_evaluate.extend(results_above_weekly)
        
        # 2. If weekly not available, use daily above EMA50
        coins_to_evaluate.extend(results_above_daily)
        
        # 3. Coins below weekly EMA50 by 10% or less
        close_to_weekly_ema = [r for r in results_below_weekly if r['pct_from_ema50'] >= -10]
        coins_to_evaluate.extend(close_to_weekly_ema)
        
        # 4. Coins below daily EMA50 by 10% or less (where weekly not available)
        close_to_daily_ema = [r for r in results_below_daily if r['pct_from_ema50'] >= -10]
        coins_to_evaluate.extend(close_to_daily_ema)
        
        # Remove duplicates
        seen = set()
        unique_evaluate = []
        for coin in coins_to_evaluate:
            if coin['symbol'] not in seen:
                seen.add(coin['symbol'])
                unique_evaluate.append(coin)
        unique_evaluate.sort(key=lambda x: x['rank'])
        
        # COINS TO AVOID
        all_coins_dict = {}
        for coin in results_above_weekly + results_below_weekly + results_above_daily + results_below_daily:
            all_coins_dict[coin['symbol']] = coin
        
        coins_to_avoid = []
        for symbol, coin in all_coins_dict.items():
            if symbol not in seen:
                coins_to_avoid.append(coin)
        coins_to_avoid.sort(key=lambda x: x['rank'])
        
        # POSSIBLE TO TRADE NOW (4H within 5% of EMA50)
        coins_to_trade_now = []
        for coin in results_4h:
            # Within 5% (either above or below)
            if abs(coin['pct_from_ema50']) <= 5:
                coins_to_trade_now.append(coin)
        coins_to_trade_now.sort(key=lambda x: abs(x['pct_from_ema50']))  # Sort by proximity to EMA
        
        return unique_evaluate, coins_to_avoid, coins_to_trade_now
    
    def display_results(self, results_above_weekly, results_below_weekly,
                       results_above_daily, results_below_daily, results_4h, failed_coins):
        """Display formatted results"""
        print("\n" + "=" * 100)
        print(f"SCAN COMPLETED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)
        
        print(f"\n📊 SUMMARY:")
        print(f"   • Coins ABOVE Weekly EMA50: {len(results_above_weekly)}")
        print(f"   • Coins BELOW Weekly EMA50: {len(results_below_weekly)}")
        print(f"   • Coins ABOVE Daily EMA50: {len(results_above_daily)}")
        print(f"   • Coins BELOW Daily EMA50: {len(results_below_daily)}")
        print(f"   • Coins with 4H Data: {len(results_4h)}")
        print(f"   • Complete Data Not Available: {len(failed_coins)}")
        print(f"\n   📈 TOTAL ABOVE EMA50: {len(results_above_weekly) + len(results_above_daily)}")
        print(f"   📉 TOTAL BELOW EMA50: {len(results_below_weekly) + len(results_below_daily)}")
        
        all_results = results_above_weekly + results_below_weekly + results_above_daily + results_below_daily
        spot_count = sum(1 for r in all_results if r['data_source'] == 'Binance Spot')
        futures_count = sum(1 for r in all_results if r['data_source'] == 'Binance Futures')
        cmc_count = sum(1 for r in all_results if r['data_source'] == 'CoinMarketCap')
        
        print(f"\n   📡 Data Sources:")
        print(f"      - Binance Spot: {spot_count} coins")
        print(f"      - Binance Futures: {futures_count} coins")
        if cmc_count > 0:
            print(f"      - CoinMarketCap: {cmc_count} coins")
        
        if results_above_weekly:
            print("\n" + "=" * 100)
            print(f"🟢 COINS ABOVE WEEKLY EMA50 ({len(results_above_weekly)} coins)")
            print("=" * 100)
            print(f"{'Rank':<6} {'Name':<20} {'Symbol':<10} {'Price':<15} {'EMA50':<15} {'% Diff':<10} {'Source':<20}")
            print("-" * 100)
            
            results_above_weekly.sort(key=lambda x: x['rank'])
            for r in results_above_weekly:
                print(f"{r['rank']:<6} {r['name']:<20} {r['symbol']:<10} "
                      f"${r['current_price']:<14,.2f} ${r['ema50']:<14,.2f} "
                      f"+{r['pct_from_ema50']:<9.2f}% {r['data_source']:<20}")
        
        if results_above_daily:
            print("\n" + "=" * 100)
            print(f"🟢 COINS ABOVE DAILY EMA50 ({len(results_above_daily)} coins - Weekly data insufficient)")
            print("=" * 100)
            print(f"{'Rank':<6} {'Name':<20} {'Symbol':<10} {'Price':<15} {'EMA50':<15} {'% Diff':<10} {'Source':<20}")
            print("-" * 100)
            
            results_above_daily.sort(key=lambda x: x['rank'])
            for r in results_above_daily:
                print(f"{r['rank']:<6} {r['name']:<20} {r['symbol']:<10} "
                      f"${r['current_price']:<14,.2f} ${r['ema50']:<14,.2f} "
                      f"+{r['pct_from_ema50']:<9.2f}% {r['data_source']:<20}")
        
        if results_below_weekly:
            print("\n" + "=" * 100)
            print(f"🔴 COINS BELOW WEEKLY EMA50 ({len(results_below_weekly)} coins)")
            print("=" * 100)
            print(f"{'Rank':<6} {'Name':<20} {'Symbol':<10} {'Price':<15} {'EMA50':<15} {'% Diff':<10} {'Source':<20}")
            print("-" * 100)
            
            results_below_weekly.sort(key=lambda x: x['rank'])
            for r in results_below_weekly:
                print(f"{r['rank']:<6} {r['name']:<20} {r['symbol']:<10} "
                      f"${r['current_price']:<14,.2f} ${r['ema50']:<14,.2f} "
                      f"{r['pct_from_ema50']:<9.2f}% {r['data_source']:<20}")
        
        if results_below_daily:
            print("\n" + "=" * 100)
            print(f"🔴 COINS BELOW DAILY EMA50 ({len(results_below_daily)} coins - Weekly data insufficient)")
            print("=" * 100)
            print(f"{'Rank':<6} {'Name':<20} {'Symbol':<10} {'Price':<15} {'EMA50':<15} {'% Diff':<10} {'Source':<20}")
            print("-" * 100)
            
            results_below_daily.sort(key=lambda x: x['rank'])
            for r in results_below_daily:
                print(f"{r['rank']:<6} {r['name']:<20} {r['symbol']:<10} "
                      f"${r['current_price']:<14,.2f} ${r['ema50']:<14,.2f} "
                      f"{r['pct_from_ema50']:<9.2f}% {r['data_source']:<20}")
        
        if failed_coins:
            print("\n" + "=" * 100)
            print(f"⚠️  COINS WITH NO DATA AVAILABLE ({len(failed_coins)} coins)")
            print("=" * 100)
            for coin in failed_coins:
                print(f"   Rank {coin['rank']}: {coin['name']} ({coin['symbol']})")
        
        # STRATEGIC SUMMARY
        coins_to_evaluate, coins_to_avoid, coins_to_trade_now = self.generate_strategic_summary(
            results_above_weekly, results_below_weekly,
            results_above_daily, results_below_daily, results_4h
        )
        
        print("\n" + "=" * 100)
        print("🎯 STRATEGIC INVESTMENT SUMMARY")
        print("=" * 100)
        
        print("\n" + "=" * 100)
        print(f"✅ COINS TO EVALUATE - LONG TERM ({len(coins_to_evaluate)} coins)")
        print("=" * 100)
        print("Criteria: Price ABOVE Weekly EMA50 OR (if weekly N/A) ABOVE Daily EMA50")
        print("          OR within 10% BELOW EMA50 (Weekly preferred, Daily if weekly N/A)")
        print("-" * 100)
        print(f"{'Rank':<6} {'Name':<20} {'Symbol':<10} {'Price':<15} {'EMA50':<15} {'% Diff':<10} {'Timeframe':<10}")
        print("-" * 100)
        
        for coin in coins_to_evaluate:
            print(f"{coin['rank']:<6} {coin['name']:<20} {coin['symbol']:<10} "
                  f"${coin['current_price']:<14,.2f} ${coin['ema50']:<14,.2f} "
                  f"{coin['pct_from_ema50']:>+9.2f}% {coin['timeframe']:<10}")
        
        print("\n" + "=" * 100)
        print(f"🔥 POSSIBLE TO TRADE NOW - SHORT TERM ({len(coins_to_trade_now)} coins)")
        print("=" * 100)
        print("Criteria: 4H chart within 5% of EMA50 (above or below)")
        print("          These coins are at critical support/resistance levels")
        print("-" * 100)
        print(f"{'Rank':<6} {'Name':<20} {'Symbol':<10} {'Price':<15} {'EMA50 4H':<15} {'% Diff':<10} {'Position':<12}")
        print("-" * 100)
        
        for coin in coins_to_trade_now:
            position = "ABOVE EMA" if coin['above_ema50'] else "BELOW EMA"
            print(f"{coin['rank']:<6} {coin['name']:<20} {coin['symbol']:<10} "
                  f"${coin['current_price']:<14,.2f} ${coin['ema50']:<14,.2f} "
                  f"{coin['pct_from_ema50']:>+9.2f}% {position:<12}")
        
        print("\n" + "=" * 100)
        print(f"❌ COINS TO AVOID ({len(coins_to_avoid)} coins)")
        print("=" * 100)
        print("Criteria: Price MORE than 10% below EMA50")
        print("-" * 100)
        print(f"{'Rank':<6} {'Name':<20} {'Symbol':<10} {'Price':<15} {'EMA50':<15} {'% Diff':<10} {'Timeframe':<10}")
        print("-" * 100)
        
        for coin in coins_to_avoid:
            print(f"{coin['rank']:<6} {coin['name']:<20} {coin['symbol']:<10} "
                  f"${coin['current_price']:<14,.2f} ${coin['ema50']:<14,.2f} "
                  f"{coin['pct_from_ema50']:>9.2f}% {coin['timeframe']:<10}")
        
        print("\n" + "=" * 100)
        print("📝 INVESTMENT STRATEGY NOTES:")
        print("=" * 100)
        print(f"• LONG TERM: {len(coins_to_evaluate)} coins with strong technicals (Weekly/Daily above or near EMA50)")
        print(f"• SHORT TERM: {len(coins_to_trade_now)} coins at critical 4H EMA50 levels (±5%) - IMMEDIATE trading opportunities")
        print(f"• AVOID: {len(coins_to_avoid)} coins with weak technicals (>10% below EMA50)")
        print(f"• 4H Trading Strategy: Watch for bounces at EMA50 or breakouts above/below")
        print(f"• Weekly/Daily timeframe for trend, 4H timeframe for precise entry/exit")
        print("=" * 100)
    
    def save_results(self, results_above_weekly, results_below_weekly,
                    results_above_daily, results_below_daily, results_4h, failed_coins):
        """Save results to JSON and CSV files"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Generate strategic summary
        coins_to_evaluate, coins_to_avoid, coins_to_trade_now = self.generate_strategic_summary(
            results_above_weekly, results_below_weekly,
            results_above_daily, results_below_daily, results_4h
        )
        
        output = {
            'scan_date': datetime.now().isoformat(),
            'top_n': self.top_n,
            'coins_above_weekly_ema50': results_above_weekly,
            'coins_below_weekly_ema50': results_below_weekly,
            'coins_above_daily_ema50': results_above_daily,
            'coins_below_daily_ema50': results_below_daily,
            'coins_4h_ema50': results_4h,
            'failed_coins': failed_coins,
            'strategic_summary': {
                'coins_to_evaluate_long_term': coins_to_evaluate,
                'coins_to_trade_now_short_term': coins_to_trade_now,
                'coins_to_avoid': coins_to_avoid
            },
            'summary': {
                'total_scanned': self.top_n,
                'total_above_weekly': len(results_above_weekly),
                'total_below_weekly': len(results_below_weekly),
                'total_above_daily': len(results_above_daily),
                'total_below_daily': len(results_below_daily),
                'total_4h_analyzed': len(results_4h),
                'total_above': len(results_above_weekly) + len(results_above_daily),
                'total_below': len(results_below_weekly) + len(results_below_daily),
                'total_failed': len(failed_coins),
                'total_to_evaluate': len(coins_to_evaluate),
                'total_to_trade_now': len(coins_to_trade_now),
                'total_to_avoid': len(coins_to_avoid)
            }
        }
        
        json_filename = f'crypto_ema_scan_top{self.top_n}_{timestamp}.json'
        with open(json_filename, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"\n💾 Results saved to: {json_filename}")
        
        # Save strategic lists to CSV
        if coins_to_evaluate:
            df_evaluate = pd.DataFrame(coins_to_evaluate)
            csv_evaluate = f'coins_LONGTERM_top{self.top_n}_{timestamp}.csv'
            df_evaluate.to_csv(csv_evaluate, index=False)
            print(f"💾 Long-term coins saved to: {csv_evaluate}")
        
        if coins_to_trade_now:
            df_trade = pd.DataFrame(coins_to_trade_now)
            csv_trade = f'coins_TRADE_NOW_top{self.top_n}_{timestamp}.csv'
            df_trade.to_csv(csv_trade, index=False)
            print(f"💾 Trade NOW coins (4H) saved to: {csv_trade}")
        
        if coins_to_avoid:
            df_avoid = pd.DataFrame(coins_to_avoid)
            csv_avoid = f'coins_AVOID_top{self.top_n}_{timestamp}.csv'
            df_avoid.to_csv(csv_avoid, index=False)
            print(f"💾 Coins to AVOID saved to: {csv_avoid}")
        
        return json_filename
    
    def run(self):
        """Run the complete scan with caching"""
        print("=" * 100)
        print(f"CRYPTOCURRENCY EMA50 SCANNER - TOP {self.top_n}")
        print("Timeframes: Weekly + Daily + 4-Hour")
        print("Sources: Binance Spot + Binance Futures + CoinMarketCap")
        print(f"Cache Duration: {self.cache_duration_minutes} minutes")
        print("=" * 100)
        
        cached_data = self.get_recent_scan()
        
        if cached_data:
            results_above_weekly = cached_data.get('coins_above_weekly_ema50', [])
            results_below_weekly = cached_data.get('coins_below_weekly_ema50', [])
            results_above_daily = cached_data.get('coins_above_daily_ema50', [])
            results_below_daily = cached_data.get('coins_below_daily_ema50', [])
            results_4h = cached_data.get('coins_4h_ema50', [])
            failed_coins = cached_data.get('failed_coins', [])
            
            print("\n✅ Using cached scan data")
            self.display_results(results_above_weekly, results_below_weekly,
                               results_above_daily, results_below_daily, results_4h, failed_coins)
            
            print(f"\n💡 To force a new scan, delete the cache file or wait {self.cache_duration_minutes} minutes")
            return
        
        if self.cmc_api_key:
            print("✓ CoinMarketCap API enabled")
        else:
            print("⚠ CoinMarketCap API not configured (Binance only)")
        
        start_time = time.time()
        
        all_coin_results = self.scan_all_coins()
        results_above_weekly, results_below_weekly, results_above_daily, results_below_daily, results_4h, failed_coins = self.categorize_results(all_coin_results)
        
        self.display_results(results_above_weekly, results_below_weekly,
                           results_above_daily, results_below_daily, results_4h, failed_coins)
        self.save_results(results_above_weekly, results_below_weekly,
                         results_above_daily, results_below_daily, results_4h, failed_coins)
        
        elapsed_time = time.time() - start_time
        print(f"\n⏱️  Scan completed in {elapsed_time/60:.2f} minutes ({elapsed_time:.1f} seconds)")
        print(f"✅ Results cached for {self.cache_duration_minutes} minutes")

# Main execution
if __name__ == "__main__":
    CMC_API_KEY = ""  # Replace with your actual key or None
    TOP_N_COINS = 200
    CACHE_DURATION_MINUTES = 60
    
    scanner = CryptoEMAScanner(
        cmc_api_key=CMC_API_KEY,
        top_n=TOP_N_COINS,
        cache_duration_minutes=CACHE_DURATION_MINUTES
    )
    scanner.run()
