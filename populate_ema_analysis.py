"""
Populate EMA Analysis Table from Existing Candle Data
Run this once to fill the ema_analysis table
"""

import psycopg
import os
from datetime import datetime

DATABASE_URL = os.getenv('DATABASE_URL')

def populate_ema_analysis():
    """Populate ema_analysis from candles table"""
    
    print("🔄 Connecting to database...")
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Get all unique symbol/timeframe combinations
    cur.execute("""
        SELECT DISTINCT symbol, timeframe 
        FROM candles 
        WHERE ema50 IS NOT NULL
        ORDER BY symbol, timeframe
    """)
    
    combinations = cur.fetchall()
    print(f"📊 Found {len(combinations)} symbol/timeframe combinations")
    
    analysis_count = 0
    
    for symbol, timeframe in combinations:
        # Get latest candle data for this symbol/timeframe
        cur.execute("""
            SELECT time, close, ema50
            FROM candles
            WHERE symbol = %s AND timeframe = %s
            ORDER BY time DESC
            LIMIT 1
        """, (symbol, timeframe))
        
        result = cur.fetchone()
        
        if result:
            time, current_price, ema50 = result
            
            if current_price and ema50:
                # Calculate percentage from EMA
                pct_from_ema = ((current_price - ema50) / ema50) * 100
                above_ema = current_price > ema50
                
                # Insert into ema_analysis
                cur.execute("""
                    INSERT INTO ema_analysis 
                    (symbol, timeframe, current_price, ema50, pct_from_ema50, above_ema50, analysis_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol, timeframe, analysis_date) 
                    DO UPDATE SET
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
                
                analysis_count += 1
                print(f"   [{analysis_count}/{len(combinations)}] {symbol} ({timeframe}): {pct_from_ema:+.2f}%")
    
    conn.commit()
    
    # Verify results
    cur.execute("SELECT COUNT(*) FROM ema_analysis")
    total = cur.fetchone()[0]
    
    cur.execute("""
        SELECT timeframe, COUNT(*) as count
        FROM ema_analysis
        WHERE analysis_date = CURRENT_DATE
        GROUP BY timeframe
        ORDER BY timeframe
    """)
    
    by_timeframe = cur.fetchall()
    
    print("\n" + "=" * 60)
    print("✅ EMA Analysis Population Complete!")
    print("=" * 60)
    print(f"Total analysis records: {total}")
    print("\nBy timeframe:")
    for tf, count in by_timeframe:
        print(f"   {tf}: {count} coins")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in environment")
        print("Run: export DATABASE_URL='your-connection-string'")
        exit(1)
    
    print("=" * 60)
    print("🔄 POPULATING EMA ANALYSIS TABLE")
    print("=" * 60)
    
    populate_ema_analysis()