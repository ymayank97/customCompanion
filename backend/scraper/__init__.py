"""
Customs tariff data scraping module.

This module provides comprehensive web scraping functionality for Indian customs data
from multiple authoritative sources including ICEGATE, CBIC, and Indian Trade Portal.
"""

from .scrape_cbic import (
    scrape_icegate_chapter,
    scrape_all_icegate_chapters,
    scrape_cbic_notifications,
    download_and_parse_pdf,
    process_all_notification_pdfs,
    scrape_indian_trade_portal_chapter,
    run_full_scrape,
    ScrapeLogger,
    create_session,
)

from .utils import (
    validate_cth_code,
    normalize_cth_code,
    format_cth_code,
    parse_bcd_rate,
    extract_chapter_from_cth,
    deduplicate_entries,
    merge_tariff_sources,
    filter_by_date_range,
    extract_notification_number,
    generate_summary_stats,
    export_to_csv,
    export_to_json,
    validate_tariff_entry,
    validate_scrape_results,
)

__all__ = [
    # Scraping functions
    'scrape_icegate_chapter',
    'scrape_all_icegate_chapters',
    'scrape_cbic_notifications',
    'download_and_parse_pdf',
    'process_all_notification_pdfs',
    'scrape_indian_trade_portal_chapter',
    'run_full_scrape',
    'ScrapeLogger',
    'create_session',

    # Utility functions
    'validate_cth_code',
    'normalize_cth_code',
    'format_cth_code',
    'parse_bcd_rate',
    'extract_chapter_from_cth',
    'deduplicate_entries',
    'merge_tariff_sources',
    'filter_by_date_range',
    'extract_notification_number',
    'generate_summary_stats',
    'export_to_csv',
    'export_to_json',
    'validate_tariff_entry',
    'validate_scrape_results',
]

__version__ = "1.0.0"
