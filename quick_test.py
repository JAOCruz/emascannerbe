#!/usr/bin/env python3
"""
Quick test with only 5 coins to verify API connectivity and basic functionality
"""

import sys
sys.path.append('/home/claude')

from crypto_ema_scanner import CryptoEMAScanner

def quick_test():
    """Test with minimal coins for speed"""
    print("\n" + "=" * 80)
    print("QUICK TEST - TOP 5 COINS ONLY")
    print("=" * 80 + "\n")
    
    scanner = CryptoEMAScanner(
        cmc_api_key=None,
        top_n=5,  # Just 5 coins for quick test
        cache_duration_minutes=1
    )
    
    try:
        scanner.run()
        print("\n✅ Quick test passed! Bot is working correctly.")
        print("\nYou can now run the full scanner:")
        print("  python crypto_ema_scanner.py")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    quick_test()
