"""
Database Setup Script for Crypto EMA Scanner
Creates all necessary tables and indexes
"""

import psycopg
import os
from datetime import datetime

def setup_database(database_url):
    """Setup PostgreSQL database with all required tables"""
    
    print("🔧 Connecting to database...")
    
    try:
        conn = psycopg.connect(database_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("✅ Connected!")
        
        # Create candles table
        print("\n📊 Creating 'candles' table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS candles (
                id SERIAL PRIMARY KEY,
                time TIMESTAMPTZ NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                open DOUBLE PRECISION,
                high DOUBLE PRECISION,
                low DOUBLE PRECISION,
                close DOUBLE PRECISION,
                volume DOUBLE PRECISION,
                ema50 DOUBLE PRECISION,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(time, symbol, timeframe)
            );
        """)
        print("   ✅ Candles table created")
        
        # Create indexes for fast queries
        print("   📌 Creating indexes...")
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_candles_symbol_timeframe 
            ON candles (symbol, timeframe, time DESC);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_candles_time 
            ON candles (time DESC);
        """)
        print("   ✅ Indexes created")
        
        # Create coins metadata table
        print("\n💰 Creating 'coins' table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS coins (
                symbol TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                market_cap_rank INTEGER,
                market_cap DOUBLE PRECISION,
                current_price DOUBLE PRECISION,
                binance_symbol TEXT,
                data_source TEXT,
                last_updated TIMESTAMPTZ DEFAULT NOW(),
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        print("   ✅ Coins table created")
        
        # Create current prices table (for WebSocket updates)
        print("\n💵 Creating 'current_prices' table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS current_prices (
                symbol TEXT PRIMARY KEY,
                price DOUBLE PRECISION NOT NULL,
                price_change_24h DOUBLE PRECISION,
                volume_24h DOUBLE PRECISION,
                last_updated TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        print("   ✅ Current prices table created")
        
        # Create scan history table
        print("\n📋 Creating 'scan_history' table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scan_history (
                id SERIAL PRIMARY KEY,
                scan_date TIMESTAMPTZ NOT NULL,
                top_n INTEGER NOT NULL,
                coins_scanned INTEGER NOT NULL,
                coins_above_weekly INTEGER,
                coins_below_weekly INTEGER,
                coins_above_daily INTEGER,
                coins_below_daily INTEGER,
                scan_duration_seconds INTEGER,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        print("   ✅ Scan history table created")
        
        # Create EMA analysis table (pre-computed results)
        print("\n📈 Creating 'ema_analysis' table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ema_analysis (
                id SERIAL PRIMARY KEY,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                current_price DOUBLE PRECISION,
                ema50 DOUBLE PRECISION,
                pct_from_ema50 DOUBLE PRECISION,
                above_ema50 BOOLEAN,
                analysis_date TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(symbol, timeframe, analysis_date)
            );
        """)
        print("   ✅ EMA analysis table created")
        
        # Create index for fast EMA queries
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_ema_analysis_lookup 
            ON ema_analysis (symbol, timeframe, analysis_date DESC);
        """)
        
        # Get table counts
        print("\n📊 Database Statistics:")
        cur.execute("SELECT COUNT(*) FROM candles;")
        candle_count = cur.fetchone()[0]
        print(f"   Candles: {candle_count:,} rows")
        
        cur.execute("SELECT COUNT(*) FROM coins;")
        coin_count = cur.fetchone()[0]
        print(f"   Coins: {coin_count:,} rows")
        
        cur.execute("SELECT COUNT(*) FROM ema_analysis;")
        analysis_count = cur.fetchone()[0]
        print(f"   EMA Analysis: {analysis_count:,} rows")
        
        cur.close()
        conn.close()
        
        print("\n✅ Database setup complete!")
        print("\n🎉 You're ready to start storing candle data!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error setting up database: {e}")
        return False

if __name__ == "__main__":
    # Get DATABASE_URL from environment or use default
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL environment variable not found")
        print("\nPlease set it with:")
        print('export DATABASE_URL="postgresql://user:pass@host:port/dbname"')
        print("\nOr get it from Railway Variables tab")
        exit(1)
    
    print("=" * 60)
    print("🐘 CRYPTO SCANNER DATABASE SETUP")
    print("=" * 60)
    
    setup_database(DATABASE_URL)