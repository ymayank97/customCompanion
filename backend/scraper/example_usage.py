"""
Example usage scripts for the CBIC customs data scraper.

This file demonstrates various use cases and integration patterns.
"""

import json
import time
from datetime import datetime
from pathlib import Path

from scrape_cbic import (
    scrape_icegate_chapter,
    scrape_all_icegate_chapters,
    scrape_cbic_notifications,
    download_and_parse_pdf,
    process_all_notification_pdfs,
    scrape_indian_trade_portal_chapter,
    run_full_scrape
)

from utils import (
    validate_cth_code,
    normalize_cth_code,
    format_cth_code,
    parse_bcd_rate,
    deduplicate_entries,
    merge_tariff_sources,
    filter_by_date_range,
    generate_summary_stats,
    export_to_csv,
    export_to_json,
    validate_scrape_results
)


# ============================================================
# EXAMPLE 1: Quick Test - Single Chapter
# ============================================================

def example_single_chapter():
    """
    Scrape a single chapter for testing.
    """
    print("\n" + "="*60)
    print("EXAMPLE 1: Single Chapter Scrape")
    print("="*60)

    chapter = 1
    print(f"\nScraping chapter {chapter:02d} from ICEGATE...")

    entries = scrape_icegate_chapter(chapter)

    print(f"\nResults: {len(entries)} entries found")

    if entries:
        print("\nSample entry:")
        print(json.dumps(entries[0], indent=2))

        # Save to file
        output_file = f"chapter_{chapter:02d}_data.json"
        export_to_json(entries, output_file)


# ============================================================
# EXAMPLE 2: Recent Notifications Only
# ============================================================

def example_recent_notifications():
    """
    Get recent notifications without processing PDFs.
    """
    print("\n" + "="*60)
    print("EXAMPLE 2: Recent CBIC Notifications")
    print("="*60)

    days_back = 30
    print(f"\nFetching notifications from last {days_back} days...")

    notifications = scrape_cbic_notifications(days_back=days_back)

    print(f"\nResults: {len(notifications)} notifications found")

    if notifications:
        print("\nRecent notifications:")
        for i, notif in enumerate(notifications[:5], 1):
            print(f"\n{i}. {notif['notification_number']}")
            print(f"   Date: {notif['date']}")
            print(f"   Title: {notif['title'][:80]}...")

        # Save to file
        export_to_json(notifications, "recent_notifications.json")


# ============================================================
# EXAMPLE 3: Process Specific PDF
# ============================================================

def example_process_specific_pdf():
    """
    Download and parse a specific notification PDF.
    """
    print("\n" + "="*60)
    print("EXAMPLE 3: Parse Specific PDF")
    print("="*60)

    # First, get a notification to extract PDF URL
    notifications = scrape_cbic_notifications(days_back=30)

    if not notifications:
        print("No notifications found!")
        return

    # Process first notification PDF
    notification = notifications[0]
    pdf_url = notification['pdf_url']

    print(f"\nProcessing: {notification['notification_number']}")
    print(f"PDF URL: {pdf_url}")

    cth_codes = download_and_parse_pdf(pdf_url)

    print(f"\nResults: {len(cth_codes)} CTH codes extracted")

    if cth_codes:
        print("\nSample CTH entries:")
        for entry in cth_codes[:3]:
            print(f"\n  CTH: {entry['formatted_cth']}")
            print(f"  Page: {entry['page_number']}")
            print(f"  Context: {entry['context'][:100]}...")

        # Save to file
        export_to_json(cth_codes, "extracted_cth_codes.json")


# ============================================================
# EXAMPLE 4: Full Scrape with All Sources
# ============================================================

def example_full_scrape():
    """
    Run comprehensive scrape from all sources.
    """
    print("\n" + "="*60)
    print("EXAMPLE 4: Full Comprehensive Scrape")
    print("="*60)

    print("\nThis will scrape:")
    print("  - ICEGATE chapters 1-10 (limited for demo)")
    print("  - CBIC notifications (last 30 days)")
    print("  - All notification PDFs")
    print("\nEstimated time: 5-10 minutes")

    response = input("\nProceed? (y/n): ")
    if response.lower() != 'y':
        print("Skipped.")
        return

    start_time = time.time()

    # Run full scrape
    results = run_full_scrape(
        scrape_icegate=True,
        scrape_cbic=True,
        scrape_indian_portal=False,  # Skip Playwright for demo
        chapter_range=(1, 10),  # Limited range for demo
        notification_days=30
    )

    elapsed_time = time.time() - start_time

    # Generate statistics
    stats = generate_summary_stats(results)

    print("\n" + "="*60)
    print("SCRAPE COMPLETE")
    print("="*60)
    print(f"\nTime elapsed: {elapsed_time:.1f} seconds")
    print(f"\nStatistics:")
    print(json.dumps(stats, indent=2))

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"full_scrape_{timestamp}.json"
    export_to_json(results, output_file)

    # Generate CSV exports for each data type
    if results['icegate_tariffs']:
        export_to_csv(results['icegate_tariffs'], f"icegate_tariffs_{timestamp}.csv")

    if results['cbic_notifications']:
        export_to_csv(results['cbic_notifications'], f"notifications_{timestamp}.csv")

    if results['cbic_cth_changes']:
        export_to_csv(results['cbic_cth_changes'], f"cth_changes_{timestamp}.csv")


# ============================================================
# EXAMPLE 5: Data Validation and Quality Check
# ============================================================

def example_data_validation():
    """
    Validate scraped data quality.
    """
    print("\n" + "="*60)
    print("EXAMPLE 5: Data Validation")
    print("="*60)

    # Scrape sample data
    print("\nScraping sample data for validation...")
    results = {
        'icegate_tariffs': scrape_icegate_chapter(1),
        'cbic_notifications': scrape_cbic_notifications(days_back=7),
        'cbic_cth_changes': [],
        'indian_portal_tariffs': []
    }

    # Validate
    print("\nValidating data quality...")
    validation_report = validate_scrape_results(results)

    print("\n" + "-"*60)
    print("VALIDATION REPORT")
    print("-"*60)
    print(json.dumps(validation_report, indent=2))

    # Save report
    export_to_json(validation_report, "validation_report.json")


# ============================================================
# EXAMPLE 6: Merge Data from Multiple Sources
# ============================================================

def example_merge_sources():
    """
    Merge tariff data from multiple sources.
    """
    print("\n" + "="*60)
    print("EXAMPLE 6: Merge Multiple Data Sources")
    print("="*60)

    chapter = 1

    # Scrape from ICEGATE
    print(f"\nScraping chapter {chapter} from ICEGATE...")
    icegate_data = scrape_icegate_chapter(chapter)

    # Scrape from Indian Trade Portal (if available)
    print(f"\nScraping chapter {chapter} from Indian Trade Portal...")
    indian_portal_data = scrape_indian_trade_portal_chapter(chapter, use_playwright=False)

    # Merge with priority to ICEGATE
    print("\nMerging data sources...")
    merged_data = merge_tariff_sources(
        primary_source=icegate_data,
        secondary_source=indian_portal_data,
        key_field='cth_code'
    )

    print(f"\nResults:")
    print(f"  ICEGATE entries: {len(icegate_data)}")
    print(f"  Indian Portal entries: {len(indian_portal_data)}")
    print(f"  Merged entries: {len(merged_data)}")

    # Remove duplicates
    unique_data = deduplicate_entries(
        merged_data,
        key_fields=['cth_code']
    )

    print(f"  Unique entries: {len(unique_data)}")

    # Save merged data
    export_to_json(unique_data, "merged_tariff_data.json")


# ============================================================
# EXAMPLE 7: Track Changes Over Time
# ============================================================

def example_track_changes():
    """
    Compare current data with previous scrape to track changes.
    """
    print("\n" + "="*60)
    print("EXAMPLE 7: Track Changes Over Time")
    print("="*60)

    chapter = 1
    previous_file = f"chapter_{chapter:02d}_previous.json"
    current_file = f"chapter_{chapter:02d}_current.json"

    # Check if previous data exists
    if not Path(previous_file).exists():
        print(f"\nNo previous data found. Scraping and saving as baseline...")
        data = scrape_icegate_chapter(chapter)
        export_to_json(data, previous_file)
        print(f"Saved {len(data)} entries to {previous_file}")
        print("Run this script again later to compare changes.")
        return

    # Load previous data
    print(f"\nLoading previous data from {previous_file}...")
    with open(previous_file, 'r', encoding='utf-8') as f:
        previous_data = json.load(f)

    # Scrape current data
    print(f"\nScraping current data for chapter {chapter}...")
    current_data = scrape_icegate_chapter(chapter)

    # Save current data
    export_to_json(current_data, current_file)

    # Compare
    print("\nComparing data...")

    # Create lookup dictionaries
    prev_dict = {entry['cth_code']: entry for entry in previous_data}
    curr_dict = {entry['cth_code']: entry for entry in current_data}

    # Find changes
    new_entries = [code for code in curr_dict if code not in prev_dict]
    removed_entries = [code for code in prev_dict if code not in curr_dict]

    rate_changes = []
    for code in curr_dict:
        if code in prev_dict:
            prev_rate = prev_dict[code].get('bcd_rate')
            curr_rate = curr_dict[code].get('bcd_rate')
            if prev_rate != curr_rate:
                rate_changes.append({
                    'cth_code': code,
                    'previous_rate': prev_rate,
                    'current_rate': curr_rate
                })

    # Report
    print("\n" + "-"*60)
    print("CHANGE REPORT")
    print("-"*60)
    print(f"\nNew entries: {len(new_entries)}")
    if new_entries[:5]:
        print(f"  Sample: {new_entries[:5]}")

    print(f"\nRemoved entries: {len(removed_entries)}")
    if removed_entries[:5]:
        print(f"  Sample: {removed_entries[:5]}")

    print(f"\nRate changes: {len(rate_changes)}")
    if rate_changes:
        print("\n  Details:")
        for change in rate_changes[:5]:
            print(f"    {change['cth_code']}: {change['previous_rate']} -> {change['current_rate']}")

    # Save change report
    change_report = {
        'comparison_date': datetime.now().isoformat(),
        'chapter': chapter,
        'new_entries': new_entries,
        'removed_entries': removed_entries,
        'rate_changes': rate_changes
    }
    export_to_json(change_report, f"change_report_chapter_{chapter:02d}.json")


# ============================================================
# EXAMPLE 8: Export for Database Import
# ============================================================

def example_database_export():
    """
    Scrape and format data for database import.
    """
    print("\n" + "="*60)
    print("EXAMPLE 8: Export for Database Import")
    print("="*60)

    print("\nScraping data for chapters 1-5...")

    all_entries = []
    for chapter in range(1, 6):
        print(f"  Processing chapter {chapter}...")
        entries = scrape_icegate_chapter(chapter)
        all_entries.extend(entries)

    print(f"\nTotal entries: {len(all_entries)}")

    # Format for database
    print("\nFormatting for database import...")

    db_ready_entries = []
    for entry in all_entries:
        # Normalize CTH code
        normalized_cth = normalize_cth_code(entry.get('cth_code', ''))

        # Parse BCD rate
        bcd_numeric = parse_bcd_rate(entry.get('bcd_rate', ''))

        db_entry = {
            'cth_code': normalized_cth,
            'description': entry.get('description', ''),
            'bcd_rate_text': entry.get('bcd_rate', ''),
            'bcd_rate_numeric': bcd_numeric,
            'unit': entry.get('unit', ''),
            'chapter': entry.get('chapter', ''),
            'source': 'icegate',
            'scrape_timestamp': entry.get('scrape_timestamp', datetime.now().isoformat())
        }

        if normalized_cth:  # Only include valid CTH codes
            db_ready_entries.append(db_entry)

    print(f"Valid entries for import: {len(db_ready_entries)}")

    # Export to CSV for database COPY command
    export_to_csv(db_ready_entries, "database_import.csv")

    # Also save as JSON
    export_to_json(db_ready_entries, "database_import.json")

    print("\nFiles ready for database import:")
    print("  - database_import.csv")
    print("  - database_import.json")


# ============================================================
# MAIN MENU
# ============================================================

def main():
    """
    Interactive menu for examples.
    """
    examples = {
        '1': ('Single Chapter Scrape', example_single_chapter),
        '2': ('Recent Notifications', example_recent_notifications),
        '3': ('Parse Specific PDF', example_process_specific_pdf),
        '4': ('Full Comprehensive Scrape', example_full_scrape),
        '5': ('Data Validation', example_data_validation),
        '6': ('Merge Multiple Sources', example_merge_sources),
        '7': ('Track Changes Over Time', example_track_changes),
        '8': ('Export for Database', example_database_export),
    }

    print("\n" + "="*60)
    print("CBIC CUSTOMS DATA SCRAPER - EXAMPLES")
    print("="*60)
    print("\nAvailable examples:")

    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")

    print("  0. Exit")

    while True:
        choice = input("\nSelect example (0-8): ").strip()

        if choice == '0':
            print("\nGoodbye!")
            break

        if choice in examples:
            name, func = examples[choice]
            try:
                func()
            except KeyboardInterrupt:
                print("\n\nInterrupted by user.")
            except Exception as e:
                print(f"\nError running example: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("Invalid choice. Please select 0-8.")


if __name__ == "__main__":
    main()
