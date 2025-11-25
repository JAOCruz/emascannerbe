#!/usr/bin/env python3
"""
DEMO MODE - Crypto EMA Scanner
Shows how the bot works with simulated data (no API calls needed)
"""

import pandas as pd
from datetime import datetime
import json
import random

class CryptoEMAScannerDemo:
    def __init__(self):
        self.demo_coins = [
            {'rank': 1, 'name': 'Bitcoin', 'symbol': 'BTC', 'market_cap': 1000000000000},
            {'rank': 2, 'name': 'Ethereum', 'symbol': 'ETH', 'market_cap': 500000000000},
            {'rank': 3, 'name': 'Tether', 'symbol': 'USDT', 'market_cap': 100000000000},
            {'rank': 4, 'name': 'BNB', 'symbol': 'BNB', 'market_cap': 90000000000},
            {'rank': 5, 'name': 'Solana', 'symbol': 'SOL', 'market_cap': 80000000000},
            {'rank': 6, 'name': 'XRP', 'symbol': 'XRP', 'market_cap': 70000000000},
            {'rank': 7, 'name': 'USD Coin', 'symbol': 'USDC', 'market_cap': 60000000000},
            {'rank': 8, 'name': 'Cardano', 'symbol': 'ADA', 'market_cap': 50000000000},
            {'rank': 9, 'name': 'Dogecoin', 'symbol': 'DOGE', 'market_cap': 40000000000},
            {'rank': 10, 'name': 'TRON', 'symbol': 'TRX', 'market_cap': 35000000000},
            {'rank': 11, 'name': 'Avalanche', 'symbol': 'AVAX', 'market_cap': 30000000000},
            {'rank': 12, 'name': 'Chainlink', 'symbol': 'LINK', 'market_cap': 25000000000},
            {'rank': 13, 'name': 'Polkadot', 'symbol': 'DOT', 'market_cap': 20000000000},
            {'rank': 14, 'name': 'Polygon', 'symbol': 'MATIC', 'market_cap': 18000000000},
            {'rank': 15, 'name': 'Litecoin', 'symbol': 'LTC', 'market_cap': 15000000000},
        ]
    
    def generate_demo_analysis(self, coin):
        """Generate realistic demo data for a coin"""
        random.seed(coin['rank'])  # Consistent results
        
        base_price = random.uniform(0.5, 100000)
        
        # Generate scenarios
        scenarios = ['strong_bull', 'bull', 'neutral', 'bear', 'strong_bear', 'trading_range']
        scenario = random.choice(scenarios)
        
        if scenario == 'strong_bull':
            weekly_pct = random.uniform(15, 40)
            daily_pct = random.uniform(8, 20)
            four_h_pct = random.uniform(-2, 10)
        elif scenario == 'bull':
            weekly_pct = random.uniform(5, 15)
            daily_pct = random.uniform(2, 10)
            four_h_pct = random.uniform(-3, 8)
        elif scenario == 'neutral':
            weekly_pct = random.uniform(-8, 8)
            daily_pct = random.uniform(-5, 5)
            four_h_pct = random.uniform(-4, 4)
        elif scenario == 'bear':
            weekly_pct = random.uniform(-15, -5)
            daily_pct = random.uniform(-12, -3)
            four_h_pct = random.uniform(-8, 3)
        elif scenario == 'strong_bear':
            weekly_pct = random.uniform(-40, -15)
            daily_pct = random.uniform(-25, -10)
            four_h_pct = random.uniform(-15, 0)
        else:  # trading_range
            weekly_pct = random.uniform(-3, 3)
            daily_pct = random.uniform(-2, 2)
            four_h_pct = random.uniform(-4, 4)
        
        results = {}
        
        # Weekly
        weekly_ema = base_price / (1 + weekly_pct/100)
        results['weekly'] = {
            'rank': coin['rank'],
            'name': coin['name'],
            'symbol': coin['symbol'],
            'binance_symbol': f"{coin['symbol']}USDT",
            'current_price': base_price,
            'ema50': weekly_ema,
            'above_ema50': weekly_pct > 0,
            'pct_from_ema50': weekly_pct,
            'market_cap': coin['market_cap'],
            'timeframe': 'Weekly',
            'data_source': 'Demo Data',
            'candle_count': 60
        }
        
        # Daily
        daily_ema = base_price / (1 + daily_pct/100)
        results['daily'] = {
            'rank': coin['rank'],
            'name': coin['name'],
            'symbol': coin['symbol'],
            'binance_symbol': f"{coin['symbol']}USDT",
            'current_price': base_price,
            'ema50': daily_ema,
            'above_ema50': daily_pct > 0,
            'pct_from_ema50': daily_pct,
            'market_cap': coin['market_cap'],
            'timeframe': 'Daily',
            'data_source': 'Demo Data',
            'candle_count': 60
        }
        
        # 4H
        four_h_ema = base_price / (1 + four_h_pct/100)
        results['4h'] = {
            'rank': coin['rank'],
            'name': coin['name'],
            'symbol': coin['symbol'],
            'binance_symbol': f"{coin['symbol']}USDT",
            'current_price': base_price,
            'ema50': four_h_ema,
            'above_ema50': four_h_pct > 0,
            'pct_from_ema50': four_h_pct,
            'market_cap': coin['market_cap'],
            'timeframe': '4-Hour',
            'data_source': 'Demo Data',
            'candle_count': 60
        }
        
        return results
    
    def categorize_results(self, all_coin_results):
        """Categorize coins into different lists"""
        results_above_weekly = []
        results_below_weekly = []
        results_4h = []
        
        for coin_result in all_coin_results:
            weekly = coin_result['weekly']
            four_h = coin_result['4h']
            
            if weekly['above_ema50']:
                results_above_weekly.append(weekly)
            else:
                results_below_weekly.append(weekly)
            
            if four_h:
                results_4h.append(four_h)
        
        return results_above_weekly, results_below_weekly, [], [], results_4h, []
    
    def generate_strategic_summary(self, results_above_weekly, results_below_weekly, results_4h):
        """Generate strategic summary"""
        coins_to_evaluate = []
        coins_to_evaluate.extend(results_above_weekly)
        close_to_weekly_ema = [r for r in results_below_weekly if r['pct_from_ema50'] >= -10]
        coins_to_evaluate.extend(close_to_weekly_ema)
        coins_to_evaluate.sort(key=lambda x: x['rank'])
        
        coins_to_avoid = [r for r in results_below_weekly if r['pct_from_ema50'] < -10]
        coins_to_avoid.sort(key=lambda x: x['rank'])
        
        coins_to_trade_now = [c for c in results_4h if abs(c['pct_from_ema50']) <= 5]
        coins_to_trade_now.sort(key=lambda x: abs(x['pct_from_ema50']))
        
        return coins_to_evaluate, coins_to_avoid, coins_to_trade_now
    
    def display_results(self, results_above_weekly, results_below_weekly, results_4h):
        """Display demo results"""
        print("\n" + "=" * 100)
        print(f"DEMO SCAN COMPLETED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)
        
        print(f"\n📊 SUMMARY:")
        print(f"   • Coins ABOVE Weekly EMA50: {len(results_above_weekly)}")
        print(f"   • Coins BELOW Weekly EMA50: {len(results_below_weekly)}")
        print(f"   • Coins with 4H Data: {len(results_4h)}")
        print(f"\n   📈 TOTAL ABOVE EMA50: {len(results_above_weekly)}")
        print(f"   📉 TOTAL BELOW EMA50: {len(results_below_weekly)}")
        
        if results_above_weekly:
            print("\n" + "=" * 100)
            print(f"🟢 COINS ABOVE WEEKLY EMA50 ({len(results_above_weekly)} coins)")
            print("=" * 100)
            print(f"{'Rank':<6} {'Name':<20} {'Symbol':<10} {'Price':<15} {'EMA50':<15} {'% Diff':<10}")
            print("-" * 100)
            
            for r in sorted(results_above_weekly, key=lambda x: x['rank']):
                print(f"{r['rank']:<6} {r['name']:<20} {r['symbol']:<10} "
                      f"${r['current_price']:<14,.2f} ${r['ema50']:<14,.2f} "
                      f"+{r['pct_from_ema50']:<9.2f}%")
        
        if results_below_weekly:
            print("\n" + "=" * 100)
            print(f"🔴 COINS BELOW WEEKLY EMA50 ({len(results_below_weekly)} coins)")
            print("=" * 100)
            print(f"{'Rank':<6} {'Name':<20} {'Symbol':<10} {'Price':<15} {'EMA50':<15} {'% Diff':<10}")
            print("-" * 100)
            
            for r in sorted(results_below_weekly, key=lambda x: x['rank']):
                print(f"{r['rank']:<6} {r['name']:<20} {r['symbol']:<10} "
                      f"${r['current_price']:<14,.2f} ${r['ema50']:<14,.2f} "
                      f"{r['pct_from_ema50']:<9.2f}%")
        
        # Strategic Summary
        coins_to_evaluate, coins_to_avoid, coins_to_trade_now = self.generate_strategic_summary(
            results_above_weekly, results_below_weekly, results_4h
        )
        
        print("\n" + "=" * 100)
        print("🎯 STRATEGIC INVESTMENT SUMMARY")
        print("=" * 100)
        
        print("\n" + "=" * 100)
        print(f"✅ COINS TO EVALUATE - LONG TERM ({len(coins_to_evaluate)} coins)")
        print("=" * 100)
        print("Criteria: Price ABOVE Weekly EMA50 OR within 10% BELOW EMA50")
        print("-" * 100)
        print(f"{'Rank':<6} {'Name':<20} {'Symbol':<10} {'Price':<15} {'EMA50':<15} {'% Diff':<10}")
        print("-" * 100)
        
        for coin in coins_to_evaluate:
            print(f"{coin['rank']:<6} {coin['name']:<20} {coin['symbol']:<10} "
                  f"${coin['current_price']:<14,.2f} ${coin['ema50']:<14,.2f} "
                  f"{coin['pct_from_ema50']:>+9.2f}%")
        
        print("\n" + "=" * 100)
        print(f"🔥 POSSIBLE TO TRADE NOW - SHORT TERM ({len(coins_to_trade_now)} coins)")
        print("=" * 100)
        print("Criteria: 4H chart within 5% of EMA50 (above or below)")
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
        print(f"{'Rank':<6} {'Name':<20} {'Symbol':<10} {'Price':<15} {'EMA50':<15} {'% Diff':<10}")
        print("-" * 100)
        
        for coin in coins_to_avoid:
            print(f"{coin['rank']:<6} {coin['name']:<20} {coin['symbol']:<10} "
                  f"${coin['current_price']:<14,.2f} ${coin['ema50']:<14,.2f} "
                  f"{coin['pct_from_ema50']:>9.2f}%")
        
        print("\n" + "=" * 100)
        print("📝 INVESTMENT STRATEGY NOTES:")
        print("=" * 100)
        print(f"• LONG TERM: {len(coins_to_evaluate)} coins with strong technicals")
        print(f"• SHORT TERM: {len(coins_to_trade_now)} coins at critical 4H EMA50 levels (±5%)")
        print(f"• AVOID: {len(coins_to_avoid)} coins with weak technicals (>10% below EMA50)")
        print(f"• 4H Trading Strategy: Watch for bounces at EMA50 or breakouts")
        print(f"• Weekly/Daily timeframe for trend, 4H timeframe for entry/exit")
        print("=" * 100)
    
    def run(self):
        """Run demo scan"""
        print("=" * 100)
        print("CRYPTOCURRENCY EMA50 SCANNER - DEMO MODE")
        print("Showing simulated data to demonstrate bot functionality")
        print("=" * 100)
        
        print(f"\nAnalyzing {len(self.demo_coins)} coins across all timeframes...")
        print("-" * 80)
        
        all_results = []
        for i, coin in enumerate(self.demo_coins, 1):
            print(f"[{i}/{len(self.demo_coins)}] Analyzing {coin['name']} ({coin['symbol']})...")
            
            results = self.generate_demo_analysis(coin)
            
            all_results.append({
                'coin_info': coin,
                'weekly': results['weekly'],
                'daily': results['daily'],
                '4h': results['4h']
            })
            
            weekly_status = f"Weekly: {results['weekly']['pct_from_ema50']:+.2f}%"
            daily_status = f"Daily: {results['daily']['pct_from_ema50']:+.2f}%"
            four_h_status = f"4H: {results['4h']['pct_from_ema50']:+.2f}%"
            
            print(f"   {weekly_status} | {daily_status} | {four_h_status}")
        
        results_above_weekly, results_below_weekly, _, _, results_4h, _ = self.categorize_results(all_results)
        
        self.display_results(results_above_weekly, results_below_weekly, results_4h)
        
        print("\n" + "=" * 100)
        print("✅ DEMO COMPLETED")
        print("=" * 100)
        print("\nThis is how the real bot works with live API data!")
        print("\nTo use with real data:")
        print("1. Ensure you have internet connectivity to crypto APIs")
        print("2. Run: python crypto_ema_scanner.py")
        print("3. Optional: Add CoinMarketCap API key for better coverage")

if __name__ == "__main__":
    demo = CryptoEMAScannerDemo()
    demo.run()
