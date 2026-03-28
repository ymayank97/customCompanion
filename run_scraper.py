"""
Simple script to run the CBIC customs tariff scraper and save data to files.

This script will:
1. Scrape ICEGATE data for specified chapters
2. Scrape CBIC notifications
3. Save results to JSON and CSV files in the data/scraped directory
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add backend directory to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from scraper.scrape_cbic import (
    scrape_icegate_chapter,
    scrape_cbic_notifications,
    download_and_parse_pdf
)
from scraper.utils import export_to_json, export_to_csv

# Create output directory
output_dir = Path(__file__).parent / "data" / "scraped"
output_dir.mkdir(parents=True, exist_ok=True)

def main():
    """Main function to run the scraper."""
    print("=" * 60)
    print("CBIC Customs Tariff Data Scraper")
    print("=" * 60)
    print()

    # Test with a few chapters first (chapters 1-5)
    print("Step 1: Scraping ICEGATE data for chapters 1-5...")
    print("-" * 60)

    all_icegate_entries = []
    test_chapters = [1, 2, 3, 4, 5]

    for chapter in test_chapters:
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

    print(f"\n[OK] Total ICEGATE entries collected: {len(all_icegate_entries)}")

    # Save ICEGATE data
    if all_icegate_entries:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save to JSON
        json_file = output_dir / f"icegate_data_{timestamp}.json"
        print(f"\nSaving ICEGATE data to: {json_file}")
        export_to_json(all_icegate_entries, json_file)
        print(f"  [OK] Saved {len(all_icegate_entries)} entries to JSON")

        # Save to CSV
        csv_file = output_dir / f"icegate_data_{timestamp}.csv"
        print(f"Saving ICEGATE data to: {csv_file}")
        export_to_csv(all_icegate_entries, csv_file)
        print(f"  [OK] Saved {len(all_icegate_entries)} entries to CSV")

    print("\n" + "=" * 60)
    print("Step 2: Scraping CBIC notifications (last 90 days)...")
    print("-" * 60)

    try:
        notifications = scrape_cbic_notifications(days_back=90)
        print(f"\n[OK] Found {len(notifications)} notifications")

        # Save notifications data
        if notifications:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Save to JSON
            json_file = output_dir / f"cbic_notifications_{timestamp}.json"
            print(f"\nSaving notifications to: {json_file}")
            export_to_json(notifications, json_file)
            print(f"  [OK] Saved {len(notifications)} notifications to JSON")

            # Save to CSV
            csv_file = output_dir / f"cbic_notifications_{timestamp}.csv"
            print(f"Saving notifications to: {csv_file}")
            export_to_csv(notifications, csv_file)
            print(f"  [OK] Saved {len(notifications)} notifications to CSV")

            # Display sample notifications
            print("\nSample notifications:")
            for notif in notifications[:3]:
                print(f"  - {notif.get('notification_number', 'N/A')}: {notif.get('title', 'N/A')[:60]}...")

    except Exception as e:
        print(f"  [ERROR] Error scraping notifications: {e}")

    print("\n" + "=" * 60)
    print("Scraping Complete!")
    print("=" * 60)
    print(f"\nData saved to: {output_dir}")
    print("\nNext steps:")
    print("1. Review the scraped data in the data/scraped directory")
    print("2. To scrape all chapters (1-99), modify test_chapters in this script")
    print("3. To process notification PDFs, use the download_and_parse_pdf function")
    print()

if __name__ == "__main__":
    main()
