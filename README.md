# 🚀 Crypto EMA50 Scanner Bot

A powerful cryptocurrency scanner that analyzes the top coins by market cap across multiple timeframes (Weekly, Daily, 4-Hour) to identify trading opportunities based on the 50-period Exponential Moving Average (EMA50).

## 📊 Features

### Multi-Timeframe Analysis
- **Weekly**: Long-term trend identification
- **Daily**: Medium-term trend confirmation  
- **4-Hour**: Short-term entry/exit timing

### Data Sources
- **Binance Spot**: Primary data source
- **Binance Futures**: Fallback for spot data
- **CoinMarketCap** (Optional): Additional coverage with API key

### Strategic Categorization
The scanner automatically categorizes coins into three actionable lists:

1. **✅ LONG TERM**: Coins with strong technicals (above or near EMA50)
2. **🔥 TRADE NOW**: Coins at critical 4H EMA50 levels (±5%) for immediate trading
3. **❌ AVOID**: Coins with weak technicals (>10% below EMA50)

### Smart Caching
- Caches scan results for configurable duration (default: 60 minutes)
- Saves API calls and speeds up repeated queries
- Auto-expires and refreshes when data gets stale

## 🛠️ Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt --break-system-packages
```

Or install manually:
```bash
pip install requests pandas --break-system-packages
```

### 2. Optional: Get CoinMarketCap API Key

For maximum coin coverage, sign up for a free API key at:
https://coinmarketcap.com/api/

## 🎯 Quick Start

### Test Run (Top 10 Coins)
```bash
python test_scanner.py
```

This will:
- Scan only the top 10 coins by market cap
- Test all features quickly (takes ~2-3 minutes)
- Verify everything is working correctly

### Full Scan (Top 200 Coins)
```bash
python crypto_ema_scanner.py
```

This will:
- Scan the top 200 coins by market cap
- Analyze across all 3 timeframes
- Take approximately 15-20 minutes
- Generate comprehensive reports

## ⚙️ Configuration

Edit the settings at the bottom of `crypto_ema_scanner.py`:

```python
if __name__ == "__main__":
    CMC_API_KEY = ""  # Your CoinMarketCap API key (optional)
    TOP_N_COINS = 200  # Number of coins to scan (10, 50, 100, 200, etc.)
    CACHE_DURATION_MINUTES = 60  # How long to cache results
    
    scanner = CryptoEMAScanner(
        cmc_api_key=CMC_API_KEY,
        top_n=TOP_N_COINS,
        cache_duration_minutes=CACHE_DURATION_MINUTES
    )
    scanner.run()
```

### Configuration Options

| Parameter | Description | Default | Recommended |
|-----------|-------------|---------|-------------|
| `CMC_API_KEY` | CoinMarketCap API key | `None` | Get free key for better coverage |
| `TOP_N_COINS` | Number of coins to scan | `200` | Start with 50 for testing |
| `CACHE_DURATION_MINUTES` | Cache expiration time | `60` | 60 for live trading, 1440 for daily checks |

## 📈 Output Files

The scanner generates four types of output files:

### 1. Main JSON Report
`crypto_ema_scan_top200_YYYYMMDD_HHMMSS.json`
- Complete scan data with all analysis
- Includes raw data for each coin
- Used for caching and programmatic access

### 2. Long-Term CSV
`coins_LONGTERM_top200_YYYYMMDD_HHMMSS.csv`
- Coins for position trading (days to weeks)
- Above EMA50 or within 10% below
- Best for swing trading strategies

### 3. Trade Now CSV  
`coins_TRADE_NOW_top200_YYYYMMDD_HHMMSS.csv`
- Coins at critical 4H EMA50 levels
- Within ±5% of EMA50
- Immediate trading opportunities

### 4. Avoid CSV
`coins_AVOID_top200_YYYYMMDD_HHMMSS.csv`
- Coins >10% below EMA50
- Weak technical position
- Stay away until trend improves

## 📊 Understanding the Results

### Console Output

```
====================================================================================================
SCAN COMPLETED - 2025-11-23 15:30:45
====================================================================================================

📊 SUMMARY:
   • Coins ABOVE Weekly EMA50: 67
   • Coins BELOW Weekly EMA50: 89
   • Coins ABOVE Daily EMA50: 12
   • Coins BELOW Daily EMA50: 18
   • Coins with 4H Data: 186
   • Complete Data Not Available: 14

   📈 TOTAL ABOVE EMA50: 79
   📉 TOTAL BELOW EMA50: 107

   📡 Data Sources:
      - Binance Spot: 142 coins
      - Binance Futures: 44 coins
```

### Strategic Summary

```
====================================================================================================
🎯 STRATEGIC INVESTMENT SUMMARY
====================================================================================================

✅ COINS TO EVALUATE - LONG TERM (87 coins)
Criteria: Price ABOVE Weekly EMA50 OR within 10% BELOW EMA50

🔥 POSSIBLE TO TRADE NOW - SHORT TERM (23 coins)  
Criteria: 4H chart within 5% of EMA50 (above or below)
          These coins are at critical support/resistance levels

❌ COINS TO AVOID (90 coins)
Criteria: Price MORE than 10% below EMA50
```

## 🎯 Trading Strategies

### Strategy 1: Long-Term Position Trading
**Use**: Weekly/Daily timeframe coins

**Setup**:
1. Look at `coins_LONGTERM_*.csv`
2. Find coins above Weekly EMA50
3. Wait for pullback to EMA50 on Daily chart
4. Enter position
5. Hold until price breaks below Weekly EMA50

**Example**:
```
Bitcoin (BTC):
Weekly: +14.5% (strong uptrend)
Daily: +3.2% (confirmed)
4H: -2.1% (minor pullback)
→ STRATEGY: Watch for 4H bounce at EMA, then buy
```

### Strategy 2: Day Trading (4H Timeframe)
**Use**: Coins from `coins_TRADE_NOW_*.csv`

**Setup**:
1. Coin must be within ±5% of 4H EMA50
2. Check Weekly/Daily for overall trend
3. If trend is up: Buy near 4H EMA support
4. If trend is down: Short near 4H EMA resistance
5. Exit when price moves 5% in your favor

**Example**:
```
Solana (SOL):
Weekly: +8.5% (uptrend)
Daily: +4.2% (confirmed)
4H: -1.8% (at EMA support)
→ STRATEGY: BUY at 4H EMA, target +5%, stop -3%
```

### Strategy 3: Breakout Trading
**Use**: Coins transitioning from AVOID to EVALUATE

**Setup**:
1. Monitor coins in AVOID list that are approaching -10%
2. Watch for breakout above EMA50
3. Enter on confirmed breakout with volume
4. Move to EVALUATE list mentally

**Example**:
```
Polygon (MATIC):
Weekly: -12.5% (was in AVOID)
Daily: -8.3% (improving)
4H: -2.1% (near EMA)
→ STRATEGY: Watch for break above Weekly EMA50
```

## 🔧 Troubleshooting

### Problem: "Module not found" error
**Solution**: Install dependencies
```bash
pip install requests pandas --break-system-packages
```

### Problem: Connection timeout or API errors
**Solution**: 
1. Check internet connection
2. Try again in a few minutes (rate limits)
3. Reduce `TOP_N_COINS` to scan fewer coins

### Problem: No data for many coins
**Solution**: 
1. Add CoinMarketCap API key for better coverage
2. Some new/small coins may not have 50 weeks of data

### Problem: Scan takes too long
**Solution**:
1. Reduce `TOP_N_COINS` (try 50 or 100 instead of 200)
2. Use cached results (wait less than cache duration)

## 📝 Advanced Usage

### Custom Analysis

You can import and use the scanner programmatically:

```python
from crypto_ema_scanner import CryptoEMAScanner

# Create scanner
scanner = CryptoEMAScanner(top_n=50)

# Get top coins
coins = scanner.get_top_n_coins()

# Analyze specific coin
result = scanner.analyze_coin_all_timeframes(coins[0])

# Print results
print(f"Weekly: {result['weekly']}")
print(f"Daily: {result['daily']}")
print(f"4H: {result['4h']}")
```

### Scheduled Scans

Set up a cron job to run daily:

```bash
# Edit crontab
crontab -e

# Add this line to run at 8 AM daily
0 8 * * * cd /path/to/scanner && python crypto_ema_scanner.py
```

## 📚 How EMA50 Works

The 50-period Exponential Moving Average (EMA50) is a key technical indicator:

- **Above EMA50**: Bullish trend, buying pressure
- **Below EMA50**: Bearish trend, selling pressure
- **At EMA50**: Support/resistance level, decision point

**Why 50 periods?**
- Long enough to filter noise
- Short enough to be responsive
- Widely used by traders (self-fulfilling)

**Multiple Timeframes:**
- **Weekly EMA50**: Overall trend (months)
- **Daily EMA50**: Intermediate trend (weeks)
- **4H EMA50**: Short-term trend (days)

## 🎓 Best Practices

1. **Always check multiple timeframes** - Don't trade based on 4H alone
2. **Respect the cache** - Don't spam API calls, use cached data
3. **Start small** - Test with 10-50 coins first
4. **Combine with other indicators** - EMA50 is powerful but not perfect
5. **Paper trade first** - Test strategies before using real money
6. **Set stop losses** - EMA50 can break, protect your capital

## ⚠️ Disclaimer

This bot is for educational and informational purposes only. It is NOT financial advice. 

- Cryptocurrency trading carries significant risk
- Past performance does not guarantee future results
- Always do your own research (DYOR)
- Never invest more than you can afford to lose
- Consider consulting a financial advisor

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the code comments for detailed explanations
3. Test with small samples first (top 10 coins)

## 🔄 Updates

To get the latest market data:
- Just run the scanner again after cache expires
- Or delete the cache JSON files to force a fresh scan

## 📄 License

Free to use for personal and educational purposes.

---

**Happy Trading! 🚀📈**

Remember: The best trade is often no trade. Wait for high-probability setups!
# emascannerbe
