"""
Test suite for customs data scraper.

Run this to verify the scraper is working correctly.
"""

import sys
import json
from datetime import datetime


def test_imports():
    """Test that all required modules can be imported."""
    print("\n" + "="*60)
    print("TEST 1: Import Verification")
    print("="*60)

    try:
        print("  Importing scrape_cbic...")
        import scrape_cbic
        print("  ✓ scrape_cbic imported")

        print("  Importing utils...")
        import utils
        print("  ✓ utils imported")

        print("  Importing config...")
        import config
        print("  ✓ config imported")

        print("\n  Required packages:")

        try:
            import requests
            print("  ✓ requests")
        except ImportError:
            print("  ✗ requests (REQUIRED - run: pip install requests)")
            return False

        try:
            from bs4 import BeautifulSoup
            print("  ✓ beautifulsoup4")
        except ImportError:
            print("  ✗ beautifulsoup4 (REQUIRED - run: pip install beautifulsoup4)")
            return False

        try:
            import pdfplumber
            print("  ✓ pdfplumber")
        except ImportError:
            print("  ✗ pdfplumber (REQUIRED - run: pip install pdfplumber)")
            return False

        try:
            from playwright.sync_api import sync_playwright
            print("  ✓ playwright (optional)")
        except ImportError:
            print("  ⚠ playwright (optional - needed for Indian Trade Portal)")

        print("\n✓ All imports successful!")
        return True

    except Exception as e:
        print(f"\n✗ Import failed: {e}")
        return False


def test_utilities():
    """Test utility functions."""
    print("\n" + "="*60)
    print("TEST 2: Utility Functions")
    print("="*60)

    try:
        from utils import (
            validate_cth_code,
            normalize_cth_code,
            format_cth_code,
            parse_bcd_rate
        )

        print("\n  Testing CTH validation:")
        test_codes = ['12345678', '1234.56.78', '1234 56 78', 'invalid', '123']

        for code in test_codes:
            is_valid = validate_cth_code(code)
            normalized = normalize_cth_code(code)
            status = "✓" if is_valid else "✗"
            print(f"    {status} {code:15} -> Valid: {is_valid}, Normalized: {normalized}")

        print("\n  Testing BCD rate parsing:")
        test_rates = ['10%', '15.5%', 'Nil', 'Free', '0', 'invalid']

        for rate in test_rates:
            parsed = parse_bcd_rate(rate)
            print(f"    {rate:10} -> {parsed}")

        print("\n✓ Utility tests passed!")
        return True

    except Exception as e:
        print(f"\n✗ Utility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_configuration():
    """Test configuration loading."""
    print("\n" + "="*60)
    print("TEST 3: Configuration")
    print("="*60)

    try:
        import config

        print(f"\n  Rate Limit Delay: {config.RATE_LIMIT_DELAY}s")
        print(f"  Request Timeout: {config.REQUEST_TIMEOUT}s")
        print(f"  User-Agent: {config.USER_AGENT[:50]}...")
        print(f"\n  Output Directory: {config.OUTPUT_DIR}")
        print(f"  Logs Directory: {config.LOGS_DIR}")

        print("\n  Data Sources:")
        print(f"    ICEGATE: {'Enabled' if config.ENABLE_ICEGATE else 'Disabled'}")
        print(f"    CBIC: {'Enabled' if config.ENABLE_CBIC else 'Disabled'}")
        print(f"    Indian Portal: {'Enabled' if config.ENABLE_INDIAN_PORTAL else 'Disabled'}")

        print("\n✓ Configuration loaded successfully!")
        return True

    except Exception as e:
        print(f"\n✗ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_session_creation():
    """Test HTTP session creation."""
    print("\n" + "="*60)
    print("TEST 4: HTTP Session")
    print("="*60)

    try:
        from scrape_cbic import create_session

        print("  Creating HTTP session...")
        session = create_session()

        print(f"  User-Agent: {session.headers.get('User-Agent', 'Not set')[:50]}...")
        print(f"  Accept: {session.headers.get('Accept', 'Not set')[:50]}...")

        print("\n✓ Session created successfully!")
        return True

    except Exception as e:
        print(f"\n✗ Session creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_scrape_logger():
    """Test error logging functionality."""
    print("\n" + "="*60)
    print("TEST 5: Error Logging")
    print("="*60)

    try:
        from scrape_cbic import ScrapeLogger

        print("  Testing error logger...")

        ScrapeLogger.log_error(
            function_name="test_function",
            input_params={"test": "value"},
            error_type="TestError",
            error_message="This is a test error",
            trace="Test traceback"
        )

        print("  ✓ Error logged successfully")
        print(f"  Check log file: scrape_errors.log")

        print("\n✓ Logger test passed!")
        return True

    except Exception as e:
        print(f"\n✗ Logger test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_live_scraping():
    """Test actual scraping (requires internet)."""
    print("\n" + "="*60)
    print("TEST 6: Live Scraping (requires internet)")
    print("="*60)

    print("\n⚠ This test will make actual HTTP requests to government websites.")
    print("  It respects rate limits (2 second delays).")

    response = input("\nProceed with live scraping test? (y/n): ")

    if response.lower() != 'y':
        print("  Skipped live scraping test.")
        return None  # Neither pass nor fail

    try:
        from scrape_cbic import scrape_icegate_chapter

        print("\n  Scraping ICEGATE chapter 01...")
        print("  (This will take ~2 seconds due to rate limiting)")

        entries = scrape_icegate_chapter(1)

        print(f"\n  Results:")
        print(f"    Entries found: {len(entries)}")

        if entries:
            print(f"\n  Sample entry:")
            sample = entries[0]
            print(f"    CTH Code: {sample.get('cth_code', 'N/A')}")
            print(f"    Description: {sample.get('description', 'N/A')[:50]}...")
            print(f"    BCD Rate: {sample.get('bcd_rate', 'N/A')}")
            print(f"    Chapter: {sample.get('chapter', 'N/A')}")
        else:
            print("  ⚠ No entries found (may indicate site structure changed)")

        print("\n✓ Live scraping test completed!")
        return True

    except Exception as e:
        print(f"\n✗ Live scraping test failed: {e}")
        import traceback
        traceback.print_exc()
        print("\nPossible causes:")
        print("  - No internet connection")
        print("  - Website is down")
        print("  - Website structure has changed")
        print("  - Firewall/proxy blocking request")
        return False


def run_all_tests():
    """Run all tests and generate report."""
    print("\n" + "#"*60)
    print("# CBIC CUSTOMS DATA SCRAPER - TEST SUITE")
    print("#"*60)
    print(f"\nTest started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {
        'imports': test_imports(),
        'utilities': test_utilities(),
        'configuration': test_configuration(),
        'session': test_session_creation(),
        'logger': test_scrape_logger(),
        'live_scraping': test_live_scraping()
    }

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)

    for test_name, result in results.items():
        if result is True:
            status = "✓ PASS"
        elif result is False:
            status = "✗ FAIL"
        else:
            status = "⊘ SKIP"

        print(f"  {status:8} - {test_name.replace('_', ' ').title()}")

    print("\n" + "-"*60)
    print(f"  Total: {len(results)} tests")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Skipped: {skipped}")
    print("-"*60)

    if failed == 0:
        print("\n🎉 All tests passed!")
        print("\nYou can now:")
        print("  1. Run example_usage.py for demonstrations")
        print("  2. Start scraping with scrape_cbic.py")
        print("  3. Review QUICKSTART.md for usage guide")
        return 0
    else:
        print("\n⚠ Some tests failed. Please review the errors above.")
        print("\nTroubleshooting:")
        print("  1. Install missing dependencies: pip install -r requirements.txt")
        print("  2. Check internet connection for live tests")
        print("  3. Review error messages and stack traces")
        print("  4. Check scrape_errors.log for details")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
