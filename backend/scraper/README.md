# Indian Customs Tariff Data Scraper

Comprehensive web scraper for collecting Indian customs tariff data from multiple authoritative sources.

## Overview

This scraper collects data from:

1. **ICEGATE Tariff Search** (old.icegate.gov.in) - Complete tariff schedule with CTH codes, descriptions, and BCD rates
2. **CBIC Notifications** (cbic.gov.in) - Recent customs notifications with rate changes
3. **Indian Trade Portal** (indiantradeportal.in) - Backup source for verification

## Features

- **Robust Error Handling**: All network calls wrapped in try/except with database logging
- **Rate Limiting**: 2-second delays between requests to respect server resources
- **Data Validation**: CTH code format validation and BCD rate parsing
- **Multiple Sources**: Combines data from three official sources
- **PDF Parsing**: Extracts CTH codes from notification PDFs using pdfplumber
- **Deduplication**: Removes duplicate entries and merges data intelligently
- **Detailed Logging**: Comprehensive error logs for debugging

## Installation

### 1. Install Python Dependencies

```bash
cd backend/scraper
pip install -r requirements.txt
```

### 2. Install Playwright (Optional - for Indian Trade Portal)

The Indian Trade Portal is JavaScript-heavy and requires Playwright:

```bash
pip install playwright
playwright install chromium
```

### 3. Database Setup (Optional)

If using database storage:

```bash
# PostgreSQL example
psql -U postgres -d customs_db -f database_schema.sql
```

## Usage

### Quick Start - Test Individual Functions

```python
from scrape_cbic import (
    scrape_icegate_chapter,
    scrape_cbic_notifications,
    download_and_parse_pdf
)

# Test ICEGATE scraper for chapter 01
chapter_data = scrape_icegate_chapter(1)
print(f"Found {len(chapter_data)} entries for chapter 01")

# Get recent notifications (last 30 days)
notifications = scrape_cbic_notifications(days_back=30)
print(f"Found {len(notifications)} notifications")

# Parse a notification PDF
if notifications:
    pdf_url = notifications[0]['pdf_url']
    cth_codes = download_and_parse_pdf(pdf_url)
    print(f"Extracted {len(cth_codes)} CTH codes from PDF")
```

### Full Scrape - All Sources

```python
from scrape_cbic import run_full_scrape
import json

# Run comprehensive scrape
results = run_full_scrape(
    scrape_icegate=True,
    scrape_cbic=True,
    scrape_indian_portal=False,  # Requires Playwright
    chapter_range=(1, 99),  # All chapters
    notification_days=90
)

# Save results
with open('scrape_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Scraped {len(results['icegate_tariffs'])} ICEGATE entries")
print(f"Found {len(results['cbic_notifications'])} notifications")
print(f"Extracted {len(results['cbic_cth_changes'])} CTH changes")
```

### Using Utility Functions

```python
from utils import (
    validate_cth_code,
    normalize_cth_code,
    format_cth_code,
    parse_bcd_rate,
    deduplicate_entries,
    generate_summary_stats
)

# Validate and format CTH codes
cth = "1234.56.78"
if validate_cth_code(cth):
    normalized = normalize_cth_code(cth)  # "12345678"
    formatted = format_cth_code(normalized, 'dotted')  # "1234.56.78"

# Parse BCD rates
rate = parse_bcd_rate("10%")  # 10.0
free_rate = parse_bcd_rate("Nil")  # 0.0

# Remove duplicates
unique_entries = deduplicate_entries(
    entries=all_entries,
    key_fields=['cth_code', 'source']
)

# Generate statistics
stats = generate_summary_stats(results)
print(json.dumps(stats, indent=2))
```

## Configuration

### Rate Limiting

Default: 2 seconds between requests. Adjust in `scrape_cbic.py`:

```python
RATE_LIMIT_DELAY = 2  # seconds
```

### User-Agent

Standard User-Agent for all requests:

```python
USER_AGENT = "Mozilla/5.0 (compatible; CustomsClassifierBot/1.0; research purposes)"
```

### Request Timeout

Default: 30 seconds. Adjust if needed:

```python
REQUEST_TIMEOUT = 30  # seconds
```

## Data Structure

### Tariff Entry (ICEGATE/Indian Portal)

```json
{
  "cth_code": "12345678",
  "description": "Product description",
  "bcd_rate": "10%",
  "unit": "KGS",
  "chapter": "12",
  "source": "icegate",
  "scrape_timestamp": "2024-03-27T10:30:00"
}
```

### CBIC Notification

```json
{
  "notification_number": "12/2024-Customs",
  "title": "Notification title",
  "date": "2024-03-15T00:00:00",
  "pdf_url": "https://cbic.gov.in/...",
  "scrape_timestamp": "2024-03-27T10:30:00"
}
```

### CTH Change (from PDF)

```json
{
  "cth_code": "12345678",
  "formatted_cth": "1234.56.78",
  "context": "...surrounding text...",
  "page_number": 2,
  "notification_number": "12/2024-Customs",
  "pdf_url": "https://cbic.gov.in/...",
  "scrape_timestamp": "2024-03-27T10:30:00"
}
```

## Error Handling

All errors are logged to:
1. **Console** (using Python logging)
2. **Log file** (`scrape_errors.log`)
3. **Database** (scrape_log table - if configured)

### Error Log Entry

```python
{
  "timestamp": "2024-03-27T10:30:00",
  "function_name": "scrape_icegate_chapter",
  "input_params": {"chapter": 1},
  "error_type": "ConnectionError",
  "error_message": "Failed to connect to server",
  "traceback": "..."
}
```

## Database Integration

### Setup

1. Create database:
```bash
createdb customs_db
```

2. Run schema:
```bash
psql -U postgres -d customs_db -f database_schema.sql
```

3. Update `scrape_cbic.py` to insert into database instead of returning lists

### Sample Integration

```python
import psycopg2

def save_to_database(entries, table_name):
    conn = psycopg2.connect(
        dbname="customs_db",
        user="postgres",
        password="your_password",
        host="localhost"
    )
    cur = conn.cursor()

    for entry in entries:
        cur.execute("""
            INSERT INTO tariff_entries
            (cth_code, description, bcd_rate, unit, chapter, source)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (cth_code, source) DO UPDATE SET
                description = EXCLUDED.description,
                bcd_rate = EXCLUDED.bcd_rate,
                updated_at = CURRENT_TIMESTAMP
        """, (
            entry['cth_code'],
            entry['description'],
            entry.get('bcd_rate'),
            entry.get('unit'),
            entry.get('chapter'),
            entry.get('source', 'icegate')
        ))

    conn.commit()
    cur.close()
    conn.close()
```

## Scheduling

### Cron Job (Linux/Mac)

```bash
# Run daily at 2 AM
0 2 * * * cd /path/to/project && python backend/scraper/scrape_cbic.py >> scrape.log 2>&1
```

### Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., daily at 2 AM)
4. Action: Start a program
   - Program: `python.exe`
   - Arguments: `C:\path\to\project\backend\scraper\scrape_cbic.py`
   - Start in: `C:\path\to\project\backend\scraper`

### Python APScheduler

```python
from apscheduler.schedulers.blocking import BlockingScheduler

scheduler = BlockingScheduler()

@scheduler.scheduled_job('cron', hour=2)
def scheduled_scrape():
    results = run_full_scrape(
        scrape_icegate=True,
        scrape_cbic=True,
        chapter_range=(1, 99),
        notification_days=90
    )
    # Save results...

scheduler.start()
```

## Testing

Run the built-in tests:

```bash
python scrape_cbic.py
```

This will test:
- ICEGATE chapter 01 scraping
- CBIC notifications (last 30 days)
- PDF parsing (first notification)

## Troubleshooting

### Common Issues

**1. Connection Errors**
- Check internet connectivity
- Verify URLs are accessible
- Check if site is blocking automated access

**2. HTML Structure Changed**
- Update BeautifulSoup selectors in code
- Check page source for new element IDs/classes

**3. PDF Parsing Fails**
- Ensure pdfplumber is installed
- Check if PDF is password-protected
- Verify PDF is not scanned image (needs OCR)

**4. Rate Limiting**
- Increase `RATE_LIMIT_DELAY`
- Check site's robots.txt
- Consider using proxy rotation

**5. Playwright Issues**
- Run: `playwright install chromium`
- Check if JavaScript is required for page
- Increase timeout values

## Legal and Ethical Considerations

- **Respect robots.txt**: Check site's robots.txt before scraping
- **Rate Limiting**: Always include delays between requests
- **User-Agent**: Use descriptive User-Agent identifying your bot
- **Terms of Service**: Review site's TOS before scraping
- **Data Usage**: Use scraped data responsibly and legally

## Contributing

To add new data sources:

1. Create new scraper function following the pattern:
```python
def scrape_new_source(params) -> List[Dict]:
    function_name = "scrape_new_source"
    input_params = {"params": params}

    try:
        # Scraping logic
        pass
    except Exception as e:
        ScrapeLogger.log_error(function_name, input_params, ...)
    finally:
        time.sleep(RATE_LIMIT_DELAY)

    return results
```

2. Add to `run_full_scrape()` orchestration function
3. Update database schema if needed
4. Add tests

## License

This scraper is provided as-is for educational and research purposes. Ensure compliance with all applicable laws and website terms of service.

## Support

For issues or questions:
1. Check error logs: `scrape_errors.log`
2. Review database scrape_log table
3. Enable DEBUG logging: `logging.basicConfig(level=logging.DEBUG)`

## Version History

- **v1.0** (2024-03-27): Initial release
  - ICEGATE scraper
  - CBIC notifications scraper
  - PDF parser with CTH extraction
  - Indian Trade Portal scraper (Playwright)
  - Comprehensive error handling and logging
