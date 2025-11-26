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
    """Get top coins that are guaranteed to be on Binance"""
    print(f"📊 Using pre-validated list of top {limit} Binance coins...")
    
    # Hardcoded list of top 200 coins that exist on Binance
    # This avoids API rate limits and Binance IP blocking
    top_binance_coins = [
        # Top 50
        {'symbol': 'BTC', 'name': 'Bitcoin', 'market_cap_rank': 1},
        {'symbol': 'ETH', 'name': 'Ethereum', 'market_cap_rank': 2},
        {'symbol': 'USDT', 'name': 'Tether', 'market_cap_rank': 3},
        {'symbol': 'BNB', 'name': 'BNB', 'market_cap_rank': 4},
        {'symbol': 'SOL', 'name': 'Solana', 'market_cap_rank': 5},
        {'symbol': 'XRP', 'name': 'XRP', 'market_cap_rank': 6},
        {'symbol': 'ADA', 'name': 'Cardano', 'market_cap_rank': 7},
        {'symbol': 'DOGE', 'name': 'Dogecoin', 'market_cap_rank': 8},
        {'symbol': 'TRX', 'name': 'TRON', 'market_cap_rank': 9},
        {'symbol': 'AVAX', 'name': 'Avalanche', 'market_cap_rank': 10},
        {'symbol': 'SHIB', 'name': 'Shiba Inu', 'market_cap_rank': 11},
        {'symbol': 'DOT', 'name': 'Polkadot', 'market_cap_rank': 12},
        {'symbol': 'LINK', 'name': 'Chainlink', 'market_cap_rank': 13},
        {'symbol': 'BCH', 'name': 'Bitcoin Cash', 'market_cap_rank': 14},
        {'symbol': 'NEAR', 'name': 'NEAR Protocol', 'market_cap_rank': 15},
        {'symbol': 'UNI', 'name': 'Uniswap', 'market_cap_rank': 16},
        {'symbol': 'LTC', 'name': 'Litecoin', 'market_cap_rank': 17},
        {'symbol': 'MATIC', 'name': 'Polygon', 'market_cap_rank': 18},
        {'symbol': 'ICP', 'name': 'Internet Computer', 'market_cap_rank': 19},
        {'symbol': 'APT', 'name': 'Aptos', 'market_cap_rank': 20},
        {'symbol': 'ETC', 'name': 'Ethereum Classic', 'market_cap_rank': 21},
        {'symbol': 'XLM', 'name': 'Stellar', 'market_cap_rank': 22},
        {'symbol': 'ATOM', 'name': 'Cosmos', 'market_cap_rank': 23},
        {'symbol': 'FIL', 'name': 'Filecoin', 'market_cap_rank': 24},
        {'symbol': 'OP', 'name': 'Optimism', 'market_cap_rank': 25},
        {'symbol': 'ARB', 'name': 'Arbitrum', 'market_cap_rank': 26},
        {'symbol': 'VET', 'name': 'VeChain', 'market_cap_rank': 27},
        {'symbol': 'INJ', 'name': 'Injective', 'market_cap_rank': 28},
        {'symbol': 'HBAR', 'name': 'Hedera', 'market_cap_rank': 29},
        {'symbol': 'FTM', 'name': 'Fantom', 'market_cap_rank': 30},
        {'symbol': 'ALGO', 'name': 'Algorand', 'market_cap_rank': 31},
        {'symbol': 'RUNE', 'name': 'THORChain', 'market_cap_rank': 32},
        {'symbol': 'AAVE', 'name': 'Aave', 'market_cap_rank': 33},
        {'symbol': 'GRT', 'name': 'The Graph', 'market_cap_rank': 34},
        {'symbol': 'EGLD', 'name': 'MultiversX', 'market_cap_rank': 35},
        {'symbol': 'QNT', 'name': 'Quant', 'market_cap_rank': 36},
        {'symbol': 'THETA', 'name': 'Theta Network', 'market_cap_rank': 37},
        {'symbol': 'SAND', 'name': 'The Sandbox', 'market_cap_rank': 38},
        {'symbol': 'AXS', 'name': 'Axie Infinity', 'market_cap_rank': 39},
        {'symbol': 'MANA', 'name': 'Decentraland', 'market_cap_rank': 40},
        {'symbol': 'EOS', 'name': 'EOS', 'market_cap_rank': 41},
        {'symbol': 'XTZ', 'name': 'Tezos', 'market_cap_rank': 42},
        {'symbol': 'FLOW', 'name': 'Flow', 'market_cap_rank': 43},
        {'symbol': 'XMR', 'name': 'Monero', 'market_cap_rank': 44},
        {'symbol': 'KAVA', 'name': 'Kava', 'market_cap_rank': 45},
        {'symbol': 'NEO', 'name': 'NEO', 'market_cap_rank': 46},
        {'symbol': 'ZEC', 'name': 'Zcash', 'market_cap_rank': 47},
        {'symbol': 'DASH', 'name': 'Dash', 'market_cap_rank': 48},
        {'symbol': 'WAVES', 'name': 'Waves', 'market_cap_rank': 49},
        {'symbol': 'ZIL', 'name': 'Zilliqa', 'market_cap_rank': 50},
        # Top 51-100
        {'symbol': 'ENJ', 'name': 'Enjin Coin', 'market_cap_rank': 51},
        {'symbol': 'BAT', 'name': 'Basic Attention Token', 'market_cap_rank': 52},
        {'symbol': 'CHZ', 'name': 'Chiliz', 'market_cap_rank': 53},
        {'symbol': 'COMP', 'name': 'Compound', 'market_cap_rank': 54},
        {'symbol': 'SNX', 'name': 'Synthetix', 'market_cap_rank': 55},
        {'symbol': 'SUSHI', 'name': 'SushiSwap', 'market_cap_rank': 56},
        {'symbol': 'YFI', 'name': 'yearn.finance', 'market_cap_rank': 57},
        {'symbol': 'BAL', 'name': 'Balancer', 'market_cap_rank': 58},
        {'symbol': 'CRV', 'name': 'Curve DAO', 'market_cap_rank': 59},
        {'symbol': '1INCH', 'name': '1inch', 'market_cap_rank': 60},
        {'symbol': 'LUNA', 'name': 'Terra Classic', 'market_cap_rank': 61},
        {'symbol': 'CELO', 'name': 'Celo', 'market_cap_rank': 62},
        {'symbol': 'ZRX', 'name': '0x', 'market_cap_rank': 63},
        {'symbol': 'OMG', 'name': 'OMG Network', 'market_cap_rank': 64},
        {'symbol': 'REN', 'name': 'Ren', 'market_cap_rank': 65},
        {'symbol': 'LRC', 'name': 'Loopring', 'market_cap_rank': 66},
        {'symbol': 'BNT', 'name': 'Bancor', 'market_cap_rank': 67},
        {'symbol': 'KSM', 'name': 'Kusama', 'market_cap_rank': 68},
        {'symbol': 'RSR', 'name': 'Reserve Rights', 'market_cap_rank': 69},
        {'symbol': 'OCEAN', 'name': 'Ocean Protocol', 'market_cap_rank': 70},
        {'symbol': 'SXP', 'name': 'Solar', 'market_cap_rank': 71},
        {'symbol': 'BAND', 'name': 'Band Protocol', 'market_cap_rank': 72},
        {'symbol': 'STORJ', 'name': 'Storj', 'market_cap_rank': 73},
        {'symbol': 'ANKR', 'name': 'Ankr', 'market_cap_rank': 74},
        {'symbol': 'ICX', 'name': 'ICON', 'market_cap_rank': 75},
        {'symbol': 'IOST', 'name': 'IOST', 'market_cap_rank': 76},
        {'symbol': 'CELR', 'name': 'Celer Network', 'market_cap_rank': 77},
        {'symbol': 'DENT', 'name': 'Dent', 'market_cap_rank': 78},
        {'symbol': 'WAN', 'name': 'Wanchain', 'market_cap_rank': 79},
        {'symbol': 'HOT', 'name': 'Holo', 'market_cap_rank': 80},
        {'symbol': 'ONT', 'name': 'Ontology', 'market_cap_rank': 81},
        {'symbol': 'QTUM', 'name': 'Qtum', 'market_cap_rank': 82},
        {'symbol': 'SC', 'name': 'Siacoin', 'market_cap_rank': 83},
        {'symbol': 'DGB', 'name': 'DigiByte', 'market_cap_rank': 84},
        {'symbol': 'RVN', 'name': 'Ravencoin', 'market_cap_rank': 85},
        {'symbol': 'DCR', 'name': 'Decred', 'market_cap_rank': 86},
        {'symbol': 'LSK', 'name': 'Lisk', 'market_cap_rank': 87},
        {'symbol': 'STEEM', 'name': 'Steem', 'market_cap_rank': 88},
        {'symbol': 'ARDR', 'name': 'Ardor', 'market_cap_rank': 89},
        {'symbol': 'ARK', 'name': 'Ark', 'market_cap_rank': 90},
        {'symbol': 'STRAT', 'name': 'Stratis', 'market_cap_rank': 91},
        {'symbol': 'KMD', 'name': 'Komodo', 'market_cap_rank': 92},
        {'symbol': 'REP', 'name': 'Augur', 'market_cap_rank': 93},
        {'symbol': 'BTS', 'name': 'BitShares', 'market_cap_rank': 94},
        {'symbol': 'GAS', 'name': 'Gas', 'market_cap_rank': 95},
        {'symbol': 'DUSK', 'name': 'Dusk', 'market_cap_rank': 96},
        {'symbol': 'MTL', 'name': 'Metal', 'market_cap_rank': 97},
        {'symbol': 'FUN', 'name': 'FUNToken', 'market_cap_rank': 98},
        {'symbol': 'POWR', 'name': 'Power Ledger', 'market_cap_rank': 99},
        {'symbol': 'REQ', 'name': 'Request', 'market_cap_rank': 100},
        # Top 101-150
        {'symbol': 'PEPE', 'name': 'Pepe', 'market_cap_rank': 101},
        {'symbol': 'WIF', 'name': 'dogwifhat', 'market_cap_rank': 102},
        {'symbol': 'BONK', 'name': 'Bonk', 'market_cap_rank': 103},
        {'symbol': 'FLOKI', 'name': 'FLOKI', 'market_cap_rank': 104},
        {'symbol': 'SEI', 'name': 'Sei', 'market_cap_rank': 105},
        {'symbol': 'IMX', 'name': 'Immutable', 'market_cap_rank': 106},
        {'symbol': 'SUI', 'name': 'Sui', 'market_cap_rank': 107},
        {'symbol': 'TIA', 'name': 'Celestia', 'market_cap_rank': 108},
        {'symbol': 'FET', 'name': 'Fetch.ai', 'market_cap_rank': 109},
        {'symbol': 'RNDR', 'name': 'Render', 'market_cap_rank': 110},
        {'symbol': 'GALA', 'name': 'Gala', 'market_cap_rank': 111},
        {'symbol': 'ROSE', 'name': 'Oasis Network', 'market_cap_rank': 112},
        {'symbol': 'GMT', 'name': 'STEPN', 'market_cap_rank': 113},
        {'symbol': 'LDO', 'name': 'Lido DAO', 'market_cap_rank': 114},
        {'symbol': 'APE', 'name': 'ApeCoin', 'market_cap_rank': 115},
        {'symbol': 'BLUR', 'name': 'Blur', 'market_cap_rank': 116},
        {'symbol': 'DYDX', 'name': 'dYdX', 'market_cap_rank': 117},
        {'symbol': 'CFX', 'name': 'Conflux', 'market_cap_rank': 118},
        {'symbol': 'MASK', 'name': 'Mask Network', 'market_cap_rank': 119},
        {'symbol': '1000SATS', 'name': '1000SATS', 'market_cap_rank': 120},
        {'symbol': 'WLD', 'name': 'Worldcoin', 'market_cap_rank': 121},
        {'symbol': 'PENDLE', 'name': 'Pendle', 'market_cap_rank': 122},
        {'symbol': 'JUP', 'name': 'Jupiter', 'market_cap_rank': 123},
        {'symbol': 'ORDI', 'name': 'ORDI', 'market_cap_rank': 124},
        {'symbol': 'PYTH', 'name': 'Pyth Network', 'market_cap_rank': 125},
        {'symbol': 'MEME', 'name': 'Memecoin', 'market_cap_rank': 126},
        {'symbol': 'JTO', 'name': 'Jito', 'market_cap_rank': 127},
        {'symbol': 'DYM', 'name': 'Dymension', 'market_cap_rank': 128},
        {'symbol': 'ALT', 'name': 'AltLayer', 'market_cap_rank': 129},
        {'symbol': 'STRK', 'name': 'Starknet', 'market_cap_rank': 130},
        {'symbol': 'AXL', 'name': 'Axelar', 'market_cap_rank': 131},
        {'symbol': 'METIS', 'name': 'Metis', 'market_cap_rank': 132},
        {'symbol': 'MAGIC', 'name': 'Magic', 'market_cap_rank': 133},
        {'symbol': 'AI', 'name': 'Sleepless AI', 'market_cap_rank': 134},
        {'symbol': 'ACE', 'name': 'Fusionist', 'market_cap_rank': 135},
        {'symbol': 'NFP', 'name': 'NFPrompt', 'market_cap_rank': 136},
        {'symbol': 'XAI', 'name': 'Xai', 'market_cap_rank': 137},
        {'symbol': 'MANTA', 'name': 'Manta Network', 'market_cap_rank': 138},
        {'symbol': 'ACH', 'name': 'Alchemy Pay', 'market_cap_rank': 139},
        {'symbol': 'PORTAL', 'name': 'Portal', 'market_cap_rank': 140},
        {'symbol': 'PIXEL', 'name': 'Pixels', 'market_cap_rank': 141},
        {'symbol': 'AEVO', 'name': 'Aevo', 'market_cap_rank': 142},
        {'symbol': 'PRIME', 'name': 'Echelon Prime', 'market_cap_rank': 143},
        {'symbol': 'OMNI', 'name': 'Omni Network', 'market_cap_rank': 144},
        {'symbol': 'SAGA', 'name': 'Saga', 'market_cap_rank': 145},
        {'symbol': 'TNSR', 'name': 'Tensor', 'market_cap_rank': 146},
        {'symbol': 'W', 'name': 'Wormhole', 'market_cap_rank': 147},
        {'symbol': 'ENA', 'name': 'Ethena', 'market_cap_rank': 148},
        {'symbol': 'REZ', 'name': 'Renzo', 'market_cap_rank': 149},
        {'symbol': 'BB', 'name': 'BounceBit', 'market_cap_rank': 150},
        # Top 151-200
        {'symbol': 'NOT', 'name': 'Notcoin', 'market_cap_rank': 151},
        {'symbol': 'IO', 'name': 'io.net', 'market_cap_rank': 152},
        {'symbol': 'ZK', 'name': 'zkSync', 'market_cap_rank': 153},
        {'symbol': 'ZRO', 'name': 'LayerZero', 'market_cap_rank': 154},
        {'symbol': 'G', 'name': 'Gravity', 'market_cap_rank': 155},
        {'symbol': 'DOGS', 'name': 'Dogs', 'market_cap_rank': 156},
        {'symbol': 'TON', 'name': 'Toncoin', 'market_cap_rank': 157},
        {'symbol': 'CATI', 'name': 'Catizen', 'market_cap_rank': 158},
        {'symbol': 'HMSTR', 'name': 'Hamster Kombat', 'market_cap_rank': 159},
        {'symbol': 'NEIRO', 'name': 'Neiro', 'market_cap_rank': 160},
        {'symbol': 'EIGEN', 'name': 'Eigenlayer', 'market_cap_rank': 161},
        {'symbol': 'TURBO', 'name': 'Turbo', 'market_cap_rank': 162},
        {'symbol': 'BOME', 'name': 'BOOK OF MEME', 'market_cap_rank': 163},
        {'symbol': 'PEOPLE', 'name': 'ConstitutionDAO', 'market_cap_rank': 164},
        {'symbol': 'RENDER', 'name': 'Render Token', 'market_cap_rank': 165},
        {'symbol': 'FTT', 'name': 'FTX Token', 'market_cap_rank': 166},
        {'symbol': 'BSV', 'name': 'Bitcoin SV', 'market_cap_rank': 167},
        {'symbol': 'MKR', 'name': 'Maker', 'market_cap_rank': 168},
        {'symbol': 'STX', 'name': 'Stacks', 'market_cap_rank': 169},
        {'symbol': 'RUNE', 'name': 'THORChain', 'market_cap_rank': 170},
        {'symbol': 'CAKE', 'name': 'PancakeSwap', 'market_cap_rank': 171},
        {'symbol': 'ONE', 'name': 'Harmony', 'market_cap_rank': 172},
        {'symbol': 'AUDIO', 'name': 'Audius', 'market_cap_rank': 173},
        {'symbol': 'CTSI', 'name': 'Cartesi', 'market_cap_rank': 174},
        {'symbol': 'IRIS', 'name': 'IRISnet', 'market_cap_rank': 175},
        {'symbol': 'NKN', 'name': 'NKN', 'market_cap_rank': 176},
        {'symbol': 'OG', 'name': 'OG Fan Token', 'market_cap_rank': 177},
        {'symbol': 'PERL', 'name': 'PERL.eco', 'market_cap_rank': 178},
        {'symbol': 'PUNDIX', 'name': 'Pundi X', 'market_cap_rank': 179},
        {'symbol': 'QUICK', 'name': 'QuickSwap', 'market_cap_rank': 180},
        {'symbol': 'REEF', 'name': 'Reef', 'market_cap_rank': 181},
        {'symbol': 'SFP', 'name': 'SafePal', 'market_cap_rank': 182},
        {'symbol': 'TROY', 'name': 'Troy', 'market_cap_rank': 183},
        {'symbol': 'TWT', 'name': 'Trust Wallet Token', 'market_cap_rank': 184},
        {'symbol': 'UNFI', 'name': 'Unifi Protocol', 'market_cap_rank': 185},
        {'symbol': 'VIDT', 'name': 'VIDT DAO', 'market_cap_rank': 186},
        {'symbol': 'WIN', 'name': 'WINkLink', 'market_cap_rank': 187},
        {'symbol': 'WRX', 'name': 'WazirX', 'market_cap_rank': 188},
        {'symbol': 'XVG', 'name': 'Verge', 'market_cap_rank': 189},
        {'symbol': 'XVS', 'name': 'Venus', 'market_cap_rank': 190},
        {'symbol': 'BAKE', 'name': 'BakeryToken', 'market_cap_rank': 191},
        {'symbol': 'BURGER', 'name': 'Burger Swap', 'market_cap_rank': 192},
        {'symbol': 'SLP', 'name': 'Smooth Love Potion', 'market_cap_rank': 193},
        {'symbol': 'TLM', 'name': 'Alien Worlds', 'market_cap_rank': 194},
        {'symbol': 'C98', 'name': 'Coin98', 'market_cap_rank': 195},
        {'symbol': 'CLV', 'name': 'Clover Finance', 'market_cap_rank': 196},
        {'symbol': 'FOR', 'name': 'ForTube', 'market_cap_rank': 197},
        {'symbol': 'POLS', 'name': 'Polkastarter', 'market_cap_rank': 198},
        {'symbol': 'CHESS', 'name': 'Tranchess', 'market_cap_rank': 199},
        {'symbol': 'VOXEL', 'name': 'Voxies', 'market_cap_rank': 200},
    ]
    
    # Return only the requested number
    result = top_binance_coins[:limit]
    print(f"   ✅ Loaded {len(result)} pre-validated Binance coins")
    return result

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
        # Initial population - fetch 5 YEARS for all timeframes
        return {
            '15m': 175200,  # 5 years (365 * 5 * 24 * 4)
            '1h': 43800,    # 5 years (365 * 5 * 24)
            '4h': 10950,    # 5 years (365 * 5 * 6)
            '1d': 1825,     # 5 years (365 * 5)
            '1w': 260       # 5 years (52 * 5)
        }.get(timeframe, 1000)
    
    # -----------------------------
    # ✅ FIX: Ensure last_time is timezone-aware
    # -----------------------------
    if last_time.tzinfo is None:
        last_time = last_time.replace(tzinfo=timezone.utc)
    
    # Calculate time since last candle
    now = datetime.now(timezone.utc)
    time_diff = now - last_time
    
    # Add buffer to account for incomplete candles
    timeframe_minutes = {
        '15m': 15,
        '1h': 60,
        '4h': 240,
        '1d': 1440,
        '1w': 10080
    }
    
    minutes_elapsed = time_diff.total_seconds() / 60
    candles_behind = int(minutes_elapsed / timeframe_minutes.get(timeframe, 60))
    
    # Add 2 candle buffer to ensure we don't miss any
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
            current_time = datetime.now()
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