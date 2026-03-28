"""
Utility functions for customs data scraping and processing.
"""

import re
from typing import List, Dict, Optional
from datetime import datetime


def validate_cth_code(cth_code: str) -> bool:
    """
    Validate CTH code format.

    Valid formats:
    - 8 digits: 12345678
    - Formatted: 1234.56.78
    - With spaces: 1234 56 78

    Args:
        cth_code: CTH code to validate

    Returns:
        True if valid, False otherwise
    """
    if not cth_code:
        return False

    # Remove formatting characters
    cleaned = re.sub(r'[\s.\-]', '', cth_code)

    # Must be exactly 8 digits
    return bool(re.match(r'^\d{8}$', cleaned))


def normalize_cth_code(cth_code: str) -> Optional[str]:
    """
    Normalize CTH code to standard 8-digit format.

    Args:
        cth_code: CTH code in any format

    Returns:
        Normalized 8-digit CTH code, or None if invalid
    """
    if not cth_code:
        return None

    # Remove all non-digit characters
    cleaned = re.sub(r'\D', '', cth_code)

    # Validate length
    if len(cleaned) != 8:
        return None

    return cleaned


def format_cth_code(cth_code: str, format_type: str = 'dotted') -> Optional[str]:
    """
    Format CTH code to specified format.

    Args:
        cth_code: 8-digit CTH code
        format_type: 'dotted' (1234.56.78) or 'plain' (12345678)

    Returns:
        Formatted CTH code, or None if invalid
    """
    normalized = normalize_cth_code(cth_code)

    if not normalized:
        return None

    if format_type == 'dotted':
        return f"{normalized[:4]}.{normalized[4:6]}.{normalized[6:8]}"
    elif format_type == 'plain':
        return normalized
    else:
        return normalized


def parse_bcd_rate(rate_text: str) -> Optional[float]:
    """
    Parse BCD rate from text to numeric value.

    Handles formats like:
    - "10%"
    - "10.5%"
    - "Nil"
    - "Free"

    Args:
        rate_text: Rate text from scraping

    Returns:
        Numeric rate (0-100), or None if cannot parse
    """
    if not rate_text:
        return None

    rate_text = rate_text.strip().lower()

    # Handle special cases
    if rate_text in ['nil', 'free', 'exempt', '0', '0%']:
        return 0.0

    # Extract numeric value
    match = re.search(r'(\d+(?:\.\d+)?)', rate_text)

    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None

    return None


def extract_chapter_from_cth(cth_code: str) -> Optional[str]:
    """
    Extract chapter code (first 2 digits) from CTH code.

    Args:
        cth_code: CTH code in any format

    Returns:
        2-digit chapter code, or None if invalid
    """
    normalized = normalize_cth_code(cth_code)

    if not normalized:
        return None

    return normalized[:2]


def deduplicate_entries(entries: List[Dict], key_fields: List[str]) -> List[Dict]:
    """
    Remove duplicate entries based on specified key fields.

    Args:
        entries: List of dictionaries
        key_fields: Fields to use for deduplication

    Returns:
        List with duplicates removed (keeps first occurrence)
    """
    seen = set()
    unique_entries = []

    for entry in entries:
        # Create tuple of key values
        key = tuple(entry.get(field) for field in key_fields)

        if key not in seen:
            seen.add(key)
            unique_entries.append(entry)

    return unique_entries


def merge_tariff_sources(
    primary_source: List[Dict],
    secondary_source: List[Dict],
    key_field: str = 'cth_code'
) -> List[Dict]:
    """
    Merge tariff data from multiple sources, preferring primary source.

    Args:
        primary_source: Primary data source (higher priority)
        secondary_source: Secondary data source (fills gaps)
        key_field: Field to use for matching entries

    Returns:
        Merged list with entries from both sources
    """
    # Create lookup dict for primary source
    primary_dict = {entry.get(key_field): entry for entry in primary_source}

    # Add secondary entries that don't exist in primary
    for entry in secondary_source:
        key = entry.get(key_field)
        if key and key not in primary_dict:
            primary_dict[key] = entry

    return list(primary_dict.values())


def filter_by_date_range(
    entries: List[Dict],
    date_field: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict]:
    """
    Filter entries by date range.

    Args:
        entries: List of dictionaries with date field
        date_field: Name of field containing date (ISO format string)
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        Filtered list of entries
    """
    filtered = []

    for entry in entries:
        date_str = entry.get(date_field)

        if not date_str:
            continue

        try:
            # Parse ISO format date
            entry_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))

            # Check date range
            if start_date and entry_date < start_date:
                continue

            if end_date and entry_date > end_date:
                continue

            filtered.append(entry)

        except (ValueError, AttributeError):
            # Skip entries with invalid dates
            continue

    return filtered


def extract_notification_number(text: str) -> Optional[str]:
    """
    Extract notification number from text.

    Common patterns:
    - Notification No. 12/2024
    - Notfn. 45/2023-Customs
    - No. 78/2024-Cus

    Args:
        text: Text containing notification number

    Returns:
        Extracted notification number, or None if not found
    """
    patterns = [
        r'(?:Notification|Notfn\.?|No\.?)\s*(\d+/\d{4}(?:-(?:Customs?|Cus))?)',
        r'(\d+/\d{4}-(?:Customs?|Cus))',
        r'No\.?\s*(\d+/\d{4})'
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def generate_summary_stats(scrape_results: Dict[str, List[Dict]]) -> Dict:
    """
    Generate summary statistics from scrape results.

    Args:
        scrape_results: Dictionary from run_full_scrape()

    Returns:
        Dictionary with summary statistics
    """
    stats = {
        'total_icegate_entries': len(scrape_results.get('icegate_tariffs', [])),
        'total_notifications': len(scrape_results.get('cbic_notifications', [])),
        'total_cth_changes': len(scrape_results.get('cbic_cth_changes', [])),
        'total_indian_portal_entries': len(scrape_results.get('indian_portal_tariffs', [])),
        'unique_chapters': set(),
        'date_range': {
            'earliest': None,
            'latest': None
        }
    }

    # Count unique chapters
    for entry in scrape_results.get('icegate_tariffs', []):
        chapter = extract_chapter_from_cth(entry.get('cth_code', ''))
        if chapter:
            stats['unique_chapters'].add(chapter)

    stats['unique_chapters'] = len(stats['unique_chapters'])

    # Find date range for notifications
    notification_dates = []
    for notif in scrape_results.get('cbic_notifications', []):
        date_str = notif.get('date')
        if date_str:
            try:
                notification_dates.append(datetime.fromisoformat(date_str))
            except ValueError:
                pass

    if notification_dates:
        stats['date_range']['earliest'] = min(notification_dates).isoformat()
        stats['date_range']['latest'] = max(notification_dates).isoformat()

    return stats


def export_to_csv(entries: List[Dict], output_file: str):
    """
    Export scraping results to CSV file.

    Args:
        entries: List of dictionaries
        output_file: Path to output CSV file
    """
    import pandas as pd

    if not entries:
        print(f"No entries to export")
        return

    df = pd.DataFrame(entries)
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"Exported {len(entries)} entries to {output_file}")


def export_to_json(data: Dict, output_file: str):
    """
    Export scraping results to JSON file.

    Args:
        data: Dictionary or list to export
        output_file: Path to output JSON file
    """
    import json

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Exported data to {output_file}")


# ============================================================
# DATA VALIDATION
# ============================================================

def validate_tariff_entry(entry: Dict) -> tuple[bool, List[str]]:
    """
    Validate a tariff entry for completeness and correctness.

    Args:
        entry: Tariff entry dictionary

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check required fields
    required_fields = ['cth_code', 'description']

    for field in required_fields:
        if not entry.get(field):
            errors.append(f"Missing required field: {field}")

    # Validate CTH code format
    cth_code = entry.get('cth_code')
    if cth_code and not validate_cth_code(cth_code):
        errors.append(f"Invalid CTH code format: {cth_code}")

    # Validate BCD rate if present
    bcd_rate = entry.get('bcd_rate')
    if bcd_rate:
        parsed_rate = parse_bcd_rate(bcd_rate)
        if parsed_rate is None and bcd_rate.lower() not in ['nil', 'free', 'exempt']:
            errors.append(f"Cannot parse BCD rate: {bcd_rate}")

    return (len(errors) == 0, errors)


def validate_scrape_results(results: Dict[str, List[Dict]]) -> Dict:
    """
    Validate complete scrape results and generate report.

    Args:
        results: Dictionary from run_full_scrape()

    Returns:
        Validation report dictionary
    """
    report = {
        'total_entries': 0,
        'valid_entries': 0,
        'invalid_entries': 0,
        'errors_by_type': {},
        'validation_timestamp': datetime.now().isoformat()
    }

    # Validate ICEGATE entries
    for entry in results.get('icegate_tariffs', []):
        report['total_entries'] += 1
        is_valid, errors = validate_tariff_entry(entry)

        if is_valid:
            report['valid_entries'] += 1
        else:
            report['invalid_entries'] += 1
            for error in errors:
                report['errors_by_type'][error] = report['errors_by_type'].get(error, 0) + 1

    # Validate Indian Portal entries
    for entry in results.get('indian_portal_tariffs', []):
        report['total_entries'] += 1
        is_valid, errors = validate_tariff_entry(entry)

        if is_valid:
            report['valid_entries'] += 1
        else:
            report['invalid_entries'] += 1
            for error in errors:
                report['errors_by_type'][error] = report['errors_by_type'].get(error, 0) + 1

    return report


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    """Test utility functions"""

    # Test CTH validation
    print("Testing CTH validation:")
    test_codes = ['12345678', '1234.56.78', '1234 56 78', 'invalid', '123456']

    for code in test_codes:
        is_valid = validate_cth_code(code)
        normalized = normalize_cth_code(code)
        formatted = format_cth_code(code)
        print(f"  {code:15} -> Valid: {is_valid}, Normalized: {normalized}, Formatted: {formatted}")

    # Test BCD rate parsing
    print("\nTesting BCD rate parsing:")
    test_rates = ['10%', '15.5%', 'Nil', 'Free', '0', 'N/A']

    for rate in test_rates:
        parsed = parse_bcd_rate(rate)
        print(f"  {rate:10} -> {parsed}")

    # Test notification number extraction
    print("\nTesting notification number extraction:")
    test_texts = [
        "Notification No. 12/2024-Customs",
        "Notfn. 45/2023",
        "As per No. 78/2024-Cus"
    ]

    for text in test_texts:
        number = extract_notification_number(text)
        print(f"  {text:40} -> {number}")
