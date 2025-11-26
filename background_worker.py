"""
Incremental Background Worker - Smart Candle Updates
Only fetches NEW data, not duplicates
"""

import psycopg
from psycopg import sql
import requests
import pandas as pd
import time
from datetime import datetime, timedelta, timezone
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
                datetime.now(timezone.utc)
            ))
        except Exception as e:
            print(f"   ⚠️  Error storing {coin['symbol']}: {e}")
            continue
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"   ✅ Stored {len(coins)} coins")

def get_last_candle_time(symbol, timeframe):
    """Get the timestamp of the most recent candle for this symbol/timeframe"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT MAX(time) FROM candles 
            WHERE symbol = %s AND timeframe = %s
        """, (symbol, timeframe))
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        return result[0] if result and result[0] else None
    except:
        return None

def calculate_candles_needed(timeframe, last_time=None):
    """
    Calculate how many candles to fetch
    - If no last_time: fetch 5 years of history (initial population)
    - If last_time exists: fetch only missing candles
    """
    if last_time is None:
        return {
            '15m': 175200,
            '1h': 43800,
            '4h': 10950,
            '1d': 1825,
            '1w': 260
        }.get(timeframe, 1000)

    # -----------------------------
    # ✅ FIX: Ensure last_time is timezone-aware
    # -----------------------------
    if last_time.tzinfo is None:
        last_time = last_time.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    time_diff = now - last_time

    timeframe_minutes = {
        '15m': 15,
        '1h': 60,
        '4h': 240,
        '1d': 1440,
        '1w': 10080
    }
    
    minutes_elapsed = time_diff.total_seconds() / 60
    candles_behind = int(minutes_elapsed / timeframe_minutes.get(timeframe, 60))
    
    return max(candles_behind + 2, 2)


def get_binance_candles(symbol, interval='1d', limit=100, start_time=None, end_time=None):
    """
    Fetch candles from Binance
    If start_time provided, only fetch candles after that time
    If end_time provided, fetch candles before that time (for historical batching)
    """
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
                'limit': min(limit, 1000)  # Binance max is 1000
            }
            
            if start_time:
                # Convert to milliseconds timestamp
                params['startTime'] = int(start_time.timestamp() * 1000)
            
            if end_time:
                params['endTime'] = int(end_time.timestamp() * 1000)
            
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) >= 10:  # Need at least 10 candles
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
                'limit': min(limit, 1000)
            }
            
            if start_time:
                params['startTime'] = int(start_time.timestamp() * 1000)
                
            if end_time:
                params['endTime'] = int(end_time.timestamp() * 1000)
            
            response = requests.get(futures_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) >= 10:
                return data, binance_symbol, 'Binance Futures'
                
        except:
            continue
    
    return None, None, None

def fetch_historical_batches(symbol, timeframe_config, total_candles_needed):
    """
    Fetch historical data in batches of 1000 (Binance limit)
    Works backwards from current time
    """
    all_candles = []
    binance_symbol = None
    data_source = None
    
    end_time = datetime.now(timezone.utc)
    batches_needed = (total_candles_needed + 999) // 1000  # Round up
    
    print(f"         📦 Fetching {batches_needed} batches ({total_candles_needed} candles total)")
    
    for batch_num in range(batches_needed):
        try:
            candles, bs, ds = get_binance_candles(
                symbol,
                interval=timeframe_config['binance'],
                limit=1000,
                end_time=end_time
            )
            
            if not candles:
                print(f"         ⚠️  No more data available after {len(all_candles)} candles")
                break
            
            # Store binance_symbol and data_source from first successful fetch
            if binance_symbol is None:
                binance_symbol = bs
                data_source = ds
            
            all_candles.extend(candles)
            
            # Move end_time to the oldest candle from this batch (go further back)
            oldest_candle_time = candles[0][0]  # First candle is oldest
            end_time = datetime.fromtimestamp(oldest_candle_time / 1000) - timedelta(seconds=1)
            
            print(f"         ✓ Batch {batch_num + 1}/{batches_needed}: {len(candles)} candles (total: {len(all_candles)})")
            
            # Rate limiting - be nice to Binance
            time.sleep(0.5)
            
            # Stop if we got fewer candles than requested (reached the beginning of available data)
            if len(candles) < 1000:
                print(f"         ℹ️  Reached earliest available data")
                break
                
        except Exception as e:
            print(f"         ❌ Batch {batch_num + 1} failed: {e}")
            break
    
    # Remove any duplicate candles (can happen at batch boundaries)
    seen_times = set()
    unique_candles = []
    for candle in all_candles:
        candle_time = candle[0]
        if candle_time not in seen_times:
            seen_times.add(candle_time)
            unique_candles.append(candle)
    
    if len(unique_candles) < len(all_candles):
        print(f"         🔧 Removed {len(all_candles) - len(unique_candles)} duplicate candles")
    
    return unique_candles, binance_symbol, data_source

def calculate_ema(prices, period=50):
    """Calculate EMA"""
    if len(prices) < period:
        return None
    
    df = pd.DataFrame({'price': prices})
    ema = df['price'].ewm(span=period, adjust=False).mean()
    return ema.tolist()

def recalculate_ema_for_symbol(symbol, timeframe):
    """
    Recalculate EMA for all existing candles
    Needed when adding new candles to maintain accurate EMA
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get all candles for this symbol/timeframe, ordered by time
        cur.execute("""
            SELECT time, close FROM candles
            WHERE symbol = %s AND timeframe = %s
            ORDER BY time ASC
        """, (symbol, timeframe))
        
        rows = cur.fetchall()
        
        if len(rows) < 50:
            cur.close()
            conn.close()
            return
        
        # Calculate EMA for all closes
        closes = [float(row[1]) for row in rows]
        ema_values = calculate_ema(closes, period=50)
        
        if not ema_values:
            cur.close()
            conn.close()
            return
        
        # Update each candle with its EMA
        for i, row in enumerate(rows):
            if i < len(ema_values) and ema_values[i]:
                cur.execute("""
                    UPDATE candles SET ema50 = %s
                    WHERE time = %s AND symbol = %s AND timeframe = %s
                """, (ema_values[i], row[0], symbol, timeframe))
        
        conn.commit()
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"      ⚠️  Error recalculating EMA: {e}")

def store_candles(symbol, timeframe, candles, binance_symbol, data_source):
    """Store candles in database (without EMA initially) - optimized for large batches"""
    if not candles:
        return
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Prepare all rows
    rows = []
    for candle in candles:
        timestamp = datetime.fromtimestamp(candle[0] / 1000)
        
        rows.append((
            timestamp,
            symbol,
            timeframe,
            float(candle[1]),  # open
            float(candle[2]),  # high
            float(candle[3]),  # low
            float(candle[4]),  # close
            float(candle[5]),  # volume
            None  # EMA will be calculated after
        ))
    
    # Batch insert in chunks of 1000 for efficiency
    chunk_size = 1000
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]
        
        cur.executemany(
            """
            INSERT INTO candles (time, symbol, timeframe, open, high, low, close, volume, ema50)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (time, symbol, timeframe) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume
            """,
            chunk
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
    
    # Recalculate EMA for all candles
    recalculate_ema_for_symbol(symbol, timeframe)

def update_ema_analysis(symbol, timeframe):
    """Update EMA analysis table with latest data"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get latest candle with EMA
        cur.execute("""
            SELECT close, ema50 FROM candles
            WHERE symbol = %s AND timeframe = %s AND ema50 IS NOT NULL
            ORDER BY time DESC LIMIT 1
        """, (symbol, timeframe))
        
        result = cur.fetchone()
        
        if not result:
            cur.close()
            conn.close()
            return
        
        current_price = float(result[0])
        ema50 = float(result[1])
        
        pct_from_ema = ((current_price - ema50) / ema50) * 100
        above_ema = current_price > ema50
        
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
            datetime.now(timezone.utc).date()
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"      ⚠️  Error updating EMA analysis: {e}")

def process_coin_incremental(coin, timeframe_config):
    """Process a single coin for a single timeframe (incremental update)"""
    symbol = coin['symbol'].upper()
    tf_key = timeframe_config['key']
    
    try:
        # Check when we last updated this coin/timeframe
        last_time = get_last_candle_time(symbol, tf_key)
        
        # Calculate how many candles we need
        candles_needed = calculate_candles_needed(tf_key, last_time)
        
        is_initial = last_time is None
        
        if is_initial:
            print(f"      🆕 Initial population: fetching {candles_needed:,} candles")
            
            # For initial population, use batched fetching
            candles, binance_symbol, data_source = fetch_historical_batches(
                symbol,
                timeframe_config,
                candles_needed
            )
        else:
            print(f"      ➕ Incremental update: fetching {candles_needed} new candles")
            
            # For incremental updates, single fetch is enough
            candles, binance_symbol, data_source = get_binance_candles(
                symbol,
                interval=timeframe_config['binance'],
                limit=candles_needed,
                start_time=last_time
            )
        
        if not candles or len(candles) == 0:
            print(f"      ⚠️  No data available")
            return False
        
        # Store new candles
        store_candles(symbol, tf_key, candles, binance_symbol, data_source)
        
        # Update EMA analysis
        update_ema_analysis(symbol, tf_key)
        
        print(f"      ✅ Stored {len(candles):,} candles")
        return True
        
    except Exception as e:
        print(f"      ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def should_update_timeframe(timeframe, current_time):
    """
    Smart scheduling: only update timeframes when new candles are available
    """
    minute = current_time.minute
    hour = current_time.hour
    weekday = current_time.weekday()
    
    if timeframe == '15m':
        # Update every 15 minutes
        return minute % 15 == 0
    elif timeframe == '1h':
        # Update every hour (at minute 1 to ensure candle is complete)
        return minute == 1
    elif timeframe == '4h':
        # Update every 4 hours (at 00:01, 04:01, 08:01, etc.)
        return hour % 4 == 0 and minute == 1
    elif timeframe == '1d':
        # Update once per day at 00:05
        return hour == 0 and minute == 5
    elif timeframe == '1w':
        # Update once per week (Monday at 00:10)
        return weekday == 0 and hour == 0 and minute == 10
    
    return False

def run_smart_update(coins, force_all=False):
    """
    Run smart incremental update
    Only updates timeframes that need updating based on current time
    """
    current_time = datetime.now(timezone.utc)
    
    timeframes = {
        '15m': {'key': '15m', 'binance': '15m'},
        '1h': {'key': '1h', 'binance': '1h'},
        '4h': {'key': '4h', 'binance': '4h'},
        '1d': {'key': '1d', 'binance': '1d'},
        '1w': {'key': '1w', 'binance': '1w'}
    }
    
    # Determine which timeframes to update
    timeframes_to_update = []
    
    if force_all:
        timeframes_to_update = list(timeframes.keys())
        print(f"\n📈 FORCED UPDATE: Processing all {len(timeframes)} timeframes")
    else:
        for tf in timeframes.keys():
            if should_update_timeframe(tf, current_time):
                timeframes_to_update.append(tf)
        
        if not timeframes_to_update:
            print(f"\n⏭️  No timeframes need updating at {current_time.strftime('%H:%M')}")
            return 0, 0
        
        print(f"\n📈 Updating timeframes: {', '.join(timeframes_to_update)}")
    
    # Process coins
    total_success = 0
    
    for i, coin in enumerate(coins, 1):
        symbol = coin['symbol'].upper()
        print(f"[{i}/{len(coins)}] {coin['name']} ({symbol})")
        
        coin_success = 0
        for tf_key in timeframes_to_update:
            if process_coin_incremental(coin, timeframes[tf_key]):
                coin_success += 1
            
            time.sleep(0.3)  # Rate limiting
        
        if coin_success > 0:
            total_success += 1
        
        time.sleep(0.5)
    
    return total_success, len(timeframes_to_update)

def run_continuous_smart(top_n=200, check_interval_seconds=60):
    """
    Run smart continuous worker
    Checks every minute if any timeframe needs updating
    """
    print("\n🔄 STARTING SMART INCREMENTAL WORKER")
    print(f"   Check interval: Every {check_interval_seconds} seconds")
    print(f"   Top N coins: {top_n}")
    print(f"   Mode: Incremental updates only")
    print(f"   Press Ctrl+C to stop\n")
    
    # Get coins once at startup
    coins = get_top_coins(limit=top_n)
    store_coins(coins)
    
    # Force initial update on first run
    print("\n🆕 INITIAL POPULATION - Fetching 5 YEARS of data")
    print("   This will take 2-4 hours but only needs to run ONCE")
    print("   Progress will be shown below...\n")
    
    start_time = time.time()
    success, tf_count = run_smart_update(coins, force_all=True)
    duration = int(time.time() - start_time)
    
    print(f"\n✅ Initial population complete!")
    print(f"   Coins processed: {success}/{len(coins)}")
    print(f"   Timeframes: {tf_count}")
    print(f"   Duration: {duration // 3600}h {(duration % 3600) // 60}m {duration % 60}s")
    print(f"   Future updates will take only 5-30 seconds!")
    print()
    
    while True:
        try:
            # Wait until next check
            time.sleep(check_interval_seconds)
            
            # Check if any timeframe needs updating
            current_time = datetime.now(timezone.utc)
            print(f"\n⏰ Check at {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            start_time = time.time()
            success, tf_count = run_smart_update(coins, force_all=False)
            
            if success > 0:
                duration = int(time.time() - start_time)
                print(f"✅ Update complete: {success}/{len(coins)} coins, {tf_count} timeframes ({duration}s)")
            
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
    
    TOP_N = int(os.getenv('TOP_N_COINS', 200))
    
    # Run smart worker (checks every 60 seconds)
    run_continuous_smart(top_n=TOP_N, check_interval_seconds=60)