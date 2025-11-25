# 🚀 CRYPTO EMA SCANNER - QUICK START GUIDE

## What You've Got

Your crypto EMA scanner bot is ready! Here's what's included:

### 📁 Files

1. **crypto_ema_scanner.py** - Main bot (production-ready)
2. **demo_scanner.py** - Demo with simulated data (no internet needed)
3. **test_scanner.py** - Test with 10 real coins
4. **quick_test.py** - Quick 5-coin test
5. **requirements.txt** - Python dependencies
6. **README.md** - Full documentation

## 🎯 Quick Start (3 Steps)

### Step 1: Install Dependencies
```bash
pip install requests pandas --break-system-packages
```

### Step 2: Run Demo (No Internet Needed)
```bash
python demo_scanner.py
```
This shows how the bot works with simulated data.

### Step 3: Run Real Scan
```bash
# Test with 10 coins first (2-3 minutes)
python test_scanner.py

# Full scan with 200 coins (15-20 minutes)
python crypto_ema_scanner.py
```

## 📊 What The Bot Does

The scanner analyzes cryptocurrencies across 3 timeframes:

- **Weekly** - Long-term trend (months)
- **Daily** - Medium-term trend (weeks)  
- **4-Hour** - Short-term opportunities (days)

### It Tells You:

✅ **LONG TERM** - Which coins to consider for position trading
🔥 **TRADE NOW** - Which coins are at critical levels (±5% from EMA)
❌ **AVOID** - Which coins are in downtrends (>10% below EMA)

## 🎨 Example Output

```
====================================================================================================
🎯 STRATEGIC INVESTMENT SUMMARY
====================================================================================================

✅ COINS TO EVALUATE - LONG TERM (87 coins)
----------------------------------------------------------------------------------------------------
Rank   Name                 Symbol     Price           EMA50           % Diff    
----------------------------------------------------------------------------------------------------
1      Bitcoin              BTC        $112,450.00     $98,234.50      +14.47%
2      Ethereum             ETH        $4,234.00       $3,987.00       +6.20%
...

🔥 POSSIBLE TO TRADE NOW - SHORT TERM (23 coins)
----------------------------------------------------------------------------------------------------
Rank   Name                 Symbol     Price           EMA50 4H        % Diff     Position    
----------------------------------------------------------------------------------------------------
5      Solana               SOL        $204.80         $202.50         +1.14%     ABOVE EMA  
12     Chainlink            LINK       $18.20          $18.95          -3.96%     BELOW EMA  
...
```

## 🔧 Configuration

Edit settings in `crypto_ema_scanner.py` (bottom of file):

```python
CMC_API_KEY = ""  # Optional: Add CoinMarketCap API key
TOP_N_COINS = 200  # How many coins to scan
CACHE_DURATION_MINUTES = 60  # Cache results
```

### Recommended Settings:

- **Testing**: TOP_N_COINS = 10, CACHE = 5 minutes
- **Daily Check**: TOP_N_COINS = 50-100, CACHE = 60 minutes
- **Full Analysis**: TOP_N_COINS = 200, CACHE = 60 minutes

## 📂 Output Files

The bot creates 4 files:

1. **crypto_ema_scan_top200_YYYYMMDD_HHMMSS.json** - Full data
2. **coins_LONGTERM_top200_YYYYMMDD_HHMMSS.csv** - Position trades
3. **coins_TRADE_NOW_top200_YYYYMMDD_HHMMSS.csv** - Day trades
4. **coins_AVOID_top200_YYYYMMDD_HHMMSS.csv** - Skip these

## 📈 Trading Strategies

### Strategy 1: Long-Term (Weekly/Daily)
1. Open `coins_LONGTERM_*.csv`
2. Find coins above Weekly EMA50
3. Wait for pullback to EMA on Daily
4. Enter position, hold until break below Weekly EMA

### Strategy 2: Day Trading (4-Hour)
1. Open `coins_TRADE_NOW_*.csv`
2. Find coins within ±5% of 4H EMA50
3. Check Weekly/Daily for overall trend
4. Trade bounces or breakouts on 4H chart

### Strategy 3: Avoid Losers
1. Open `coins_AVOID_*.csv`
2. Skip these entirely
3. Wait for price to get back above EMA50

## 🎓 Understanding EMA50

**EMA50** = 50-period Exponential Moving Average

- **Above EMA50** = Bullish (buyers in control)
- **Below EMA50** = Bearish (sellers in control)
- **At EMA50** = Decision point (support/resistance)

**Why 3 Timeframes?**
- Weekly = See the forest (long-term trend)
- Daily = See the trees (medium-term)
- 4-Hour = See the leaves (entry/exit timing)

## ⚡ Pro Tips

1. **Start Small** - Test with 10 coins first
2. **Use Cache** - Don't spam APIs, use cached results
3. **Multiple Timeframes** - Weekly for direction, 4H for timing
4. **Combine Indicators** - EMA50 is powerful but not perfect
5. **Paper Trade First** - Test strategies before using real money

## 🐛 Troubleshooting

### "Module not found"
```bash
pip install requests pandas --break-system-packages
```

### "Connection error"
- Check internet connection
- Run demo_scanner.py instead (no internet needed)
- APIs may be rate-limited, try again in a few minutes

### "No data for coins"
- Some small coins don't have 50 weeks of history
- Add CoinMarketCap API key for better coverage

## 📞 Need Help?

1. Read the full README.md for detailed docs
2. Run demo_scanner.py to see how it works
3. Start with quick_test.py (5 coins) or test_scanner.py (10 coins)

## ⚠️ Important Warning

**This bot is for educational purposes only.**

- NOT financial advice
- Crypto trading is risky
- Never invest more than you can lose
- Always DYOR (Do Your Own Research)

## 🎉 You're Ready!

Run this command to start:
```bash
python demo_scanner.py
```

Then when ready for real data:
```bash
python crypto_ema_scanner.py
```

**Happy Trading! 🚀📈**
