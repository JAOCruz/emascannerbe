#!/usr/bin/env python3
"""
Test script for Crypto EMA Scanner
Tests with only top 10 coins for quick validation
"""

import sys
sys.path.append('/home/claude')

from crypto_ema_scanner import CryptoEMAScanner

def test_scanner():
    """Test the scanner with a small sample"""
    print("\n" + "=" * 100)
    print("CRYPTO EMA SCANNER - TEST MODE")
    print("Testing with TOP 10 coins only")
    print("=" * 100 + "\n")
    
    # Initialize scanner with small sample size
    scanner = CryptoEMAScanner(
        cmc_api_key=None,  # No CMC API for testing
        top_n=10,  # Only test with top 10 coins
        cache_duration_minutes=5  # Short cache for testing
    )
    
    try:
        # Run the scanner
        scanner.run()
        
        print("\n" + "=" * 100)
        print("✅ TEST COMPLETED SUCCESSFULLY!")
        print("=" * 100)
        print("\nThe scanner is working correctly. You can now:")
        print("1. Run with more coins: Change TOP_N_COINS to 50, 100, or 200")
        print("2. Add CoinMarketCap API key for more data coverage")
        print("3. Adjust cache duration as needed")
        print("\nTo run full scan:")
        print("  python crypto_ema_scanner.py")
        
    except Exception as e:
        print("\n" + "=" * 100)
        print("❌ TEST FAILED")
        print("=" * 100)
        print(f"\nError: {str(e)}")
        print("\nPlease check:")
        print("1. Internet connection is active")
        print("2. API endpoints are accessible")
        print("3. Required packages are installed (requests, pandas)")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_scanner()
