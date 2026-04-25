"""
Unified scraper runner for Indian Customs tariff data.

Supports two modes:
1. CIP Scraper (NEW) — Playwright-based scraper for cip.icegate.gov.in
2. Legacy CBIC Scraper — requests-based scraper for old ICEGATE/CBIC

Usage:
    # CIP Scraper (recommended)
    python run_scraper.py cip                    # Scrape all CTH codes
    python run_scraper.py cip --test             # Test with single code
    python run_scraper.py cip --test 70134900    # Test specific code
    python run_scraper.py cip --chapters 70 84   # Scrape specific chapters
    python run_scraper.py cip --codes 84714110 85171210  # Specific codes
    python run_scraper.py cip --visible          # Show browser window
    python run_scraper.py cip --seed             # Only build CTH master list
    python run_scraper.py cip --export           # Export all results to JSON/CSV

    # Legacy scraper
    python run_scraper.py legacy                 # Run old ICEGATE scraper
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add backend directory to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))


def run_cip_scraper():
    """Run the CIP portal scraper."""
    # Remove 'cip' from argv so argparse in scrape_cip sees the rest
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    from scraper.cip.scrape_cip import main
    main()


def run_legacy_scraper():
    """Run the legacy CBIC/ICEGATE scraper."""
    from scraper.scrape_cbic import (
        scrape_icegate_chapter,
        scrape_cbic_notifications,
    )
    from scraper.utils import export_to_json, export_to_csv

    output_dir = Path(__file__).parent / "data" / "scraped"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Legacy CBIC Customs Tariff Data Scraper")
    print("=" * 60)

    # Test with chapters 1-5
    print("\nStep 1: Scraping ICEGATE data for chapters 1-5...")
    all_icegate_entries = []
    for chapter in [1, 2, 3, 4, 5]:
        print(f"\nScraping chapter {chapter:02d}...")
        try:
            entries = scrape_icegate_chapter(chapter)
            if entries:
                all_icegate_entries.extend(entries)
                print(f"  [OK] Found {len(entries)} entries in chapter {chapter:02d}")
            else:
                print(f"  [WARN] No entries found in chapter {chapter:02d}")
        except Exception as e:
            print(f"  [ERROR] Error scraping chapter {chapter:02d}: {e}")

    print(f"\nTotal ICEGATE entries: {len(all_icegate_entries)}")

    if all_icegate_entries:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_to_json(all_icegate_entries, output_dir / f"icegate_data_{ts}.json")
        export_to_csv(all_icegate_entries, output_dir / f"icegate_data_{ts}.csv")

    print("\nStep 2: Scraping CBIC notifications (last 90 days)...")
    try:
        notifications = scrape_cbic_notifications(days_back=90)
        print(f"Found {len(notifications)} notifications")
        if notifications:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_to_json(notifications, output_dir / f"cbic_notifications_{ts}.json")
            export_to_csv(notifications, output_dir / f"cbic_notifications_{ts}.csv")
    except Exception as e:
        print(f"  [ERROR] {e}")

    print(f"\nData saved to: {output_dir}")


def show_usage():
    print(__doc__)
    print("Quick start:")
    print("  python run_scraper.py cip --seed     # Build CTH code list first")
    print("  python run_scraper.py cip --test     # Test single code")
    print("  python run_scraper.py cip            # Full scrape")


def main():
    if len(sys.argv) < 2:
        show_usage()
        sys.exit(0)

    mode = sys.argv[1].lower()

    if mode == "cip":
        run_cip_scraper()
    elif mode == "legacy":
        run_legacy_scraper()
    elif mode in ("-h", "--help", "help"):
        show_usage()
    else:
        print(f"Unknown mode: {mode}")
        show_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
