# Quick Start Guide

Get started with the CBIC Customs Data Scraper in 5 minutes.

## Installation

### 1. Install Dependencies

```bash
cd backend/scraper
pip install -r requirements.txt
```

### 2. Optional: Install Playwright (for Indian Trade Portal)

```bash
pip install playwright
playwright install chromium
```

## Basic Usage

### Test 1: Scrape a Single Chapter

```python
from scrape_cbic import scrape_icegate_chapter

# Scrape chapter 1 (Live Animals)
entries = scrape_icegate_chapter(1)

print(f"Found {len(entries)} tariff entries")
print(f"First entry: {entries[0]}")
```

**Expected output:**
```
Found 50 tariff entries
First entry: {
  'cth_code': '01011010',
  'description': 'Horses, pure-bred breeding animals',
  'bcd_rate': '0%',
  'unit': 'NMB',
  'chapter': '01'
}
```

### Test 2: Get Recent Notifications

```python
from scrape_cbic import scrape_cbic_notifications

# Get notifications from last 30 days
notifications = scrape_cbic_notifications(days_back=30)

for notif in notifications[:3]:
    print(f"{notif['notification_number']} - {notif['title']}")
```

### Test 3: Extract CTH from PDF

```python
from scrape_cbic import download_and_parse_pdf

pdf_url = "https://www.cbic.gov.in/resources/htdocs-cbec/customs/cs-act/notifications/notfns-2024/cs-tarr2024/cs01-2024.pdf"

cth_codes = download_and_parse_pdf(pdf_url)

print(f"Extracted {len(cth_codes)} CTH codes from PDF")
```

## Run Examples

We've prepared 8 example scripts covering common use cases:

```bash
python example_usage.py
```

**Available examples:**
1. Single Chapter Scrape - Test scraping one chapter
2. Recent Notifications - Fetch latest notifications
3. Parse Specific PDF - Extract CTH from a PDF
4. Full Comprehensive Scrape - Scrape all sources
5. Data Validation - Validate scraped data
6. Merge Multiple Sources - Combine data
7. Track Changes Over Time - Compare scrapes
8. Export for Database - Format for DB import

## Common Tasks

### Scrape All Chapters

```python
from scrape_cbic import scrape_all_icegate_chapters

all_data = scrape_all_icegate_chapters(start_chapter=1, end_chapter=99)

print(f"Total entries: {len(all_data)}")
```

**Note:** This will take 3-4 hours due to rate limiting (2s between requests).

### Full Comprehensive Scrape

```python
from scrape_cbic import run_full_scrape

results = run_full_scrape(
    scrape_icegate=True,
    scrape_cbic=True,
    scrape_indian_portal=False,
    chapter_range=(1, 99),
    notification_days=90
)

# Save results
import json
with open('results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
```

### Validate CTH Codes

```python
from utils import validate_cth_code, normalize_cth_code

# Test various formats
codes = ['12345678', '1234.56.78', '1234 56 78', 'invalid']

for code in codes:
    is_valid = validate_cth_code(code)
    normalized = normalize_cth_code(code)
    print(f"{code:15} -> Valid: {is_valid}, Normalized: {normalized}")
```

## Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` to customize:
- Rate limiting settings
- Database connection (optional)
- API endpoints
- Logging preferences

## Troubleshooting

### Problem: Connection timeout

**Solution:** Increase timeout in config:
```python
# In scrape_cbic.py or config.py
REQUEST_TIMEOUT = 60  # Increase from 30 to 60 seconds
```

### Problem: Rate limit errors

**Solution:** Increase delay:
```python
RATE_LIMIT_DELAY = 5  # Increase from 2 to 5 seconds
```

### Problem: PDF parsing fails

**Solution:** Check if pdfplumber is installed:
```bash
pip install pdfplumber
```

### Problem: HTML structure changed

**Solution:** The scraper uses flexible selectors with regex patterns. If a site's HTML changes significantly:

1. Check the error log: `scrape_errors.log`
2. View the raw HTML (enable in config)
3. Update the BeautifulSoup selectors in `scrape_cbic.py`

## Next Steps

1. **Review the full documentation:** [README.md](README.md)
2. **Check database schema:** [database_schema.sql](database_schema.sql)
3. **Explore utilities:** [utils.py](utils.py)
4. **Run examples:** [example_usage.py](example_usage.py)

## Testing the Scraper

Run the built-in tests:

```bash
python scrape_cbic.py
```

This will:
- Scrape chapter 01 from ICEGATE
- Fetch last 30 days of notifications
- Parse the first notification PDF
- Display results and sample data

## Performance Notes

### Scraping Times (approximate)

| Task | Duration | Requests |
|------|----------|----------|
| Single chapter | 2-5 seconds | 1 |
| All 99 chapters | 3-4 hours | 99 |
| Notifications (90 days) | 10-20 seconds | 1 |
| Single PDF parsing | 5-10 seconds | 1 |
| Full comprehensive scrape | 4-6 hours | ~200 |

**Rate limiting:** All scrapers include 2-second delays between requests to respect server resources.

## Error Handling

All errors are automatically logged to:
- Console (with logger)
- `scrape_errors.log` file
- Database `scrape_log` table (if configured)

Check logs if scraping fails:

```bash
tail -f scrape_errors.log
```

## Support

For issues or questions:
1. Check error logs
2. Review troubleshooting section
3. Enable DEBUG mode: `LOG_LEVEL=DEBUG` in `.env`
4. Check database scrape_log table

## Legal Notice

This scraper is for educational and research purposes. Always:
- Respect the website's terms of service
- Check robots.txt
- Use rate limiting
- Identify your bot with User-Agent
- Use data responsibly and legally
