"""
Comprehensive Web Scraper for Indian Customs Tariff Data

This module implements robust web scraping for multiple Indian customs data sources:
1. ICEGATE Tariff Search (old portal)
2. CBIC Tariff Notifications
3. Indian Trade Portal (backup source)

All scrapers include:
- Rate limiting (2 seconds between requests)
- Error handling with database logging
- Proper User-Agent headers
- Data validation and quality checks
"""

import re
import time
import logging
import traceback
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from io import BytesIO

import requests
from bs4 import BeautifulSoup
import pdfplumber
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import urllib3

# Disable SSL warnings for old government sites
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
USER_AGENT = "Mozilla/5.0 (compatible; CustomsClassifierBot/1.0; research purposes)"
REQUEST_TIMEOUT = 30
RATE_LIMIT_DELAY = 2  # seconds between requests

# URL Constants
ICEGATE_BASE_URL = "https://old.icegate.gov.in/Webappl/"
CBIC_NOTIFICATIONS_URL = "https://www.cbic.gov.in/htdocs-cbec/customs/custom-tariff"
INDIAN_TRADE_PORTAL_URL = "https://www.indiantradeportal.in/"


# ============================================================
# DATABASE LOGGING (Placeholder - integrate with your DB)
# ============================================================

class ScrapeLogger:
    """
    Logs scraping errors to database.
    Replace with actual database implementation.
    """

    @staticmethod
    def log_error(
        function_name: str,
        input_params: Dict[str, Any],
        error_type: str,
        error_message: str,
        trace: Optional[str] = None
    ):
        """
        Log scraping error to scrape_log table.

        Args:
            function_name: Name of function where error occurred
            input_params: Parameters passed to the function
            error_type: Exception class name
            error_message: Error description
            trace: Optional stack trace
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "function_name": function_name,
            "input_params": str(input_params),
            "error_type": error_type,
            "error_message": error_message,
            "traceback": trace
        }

        # TODO: Insert into actual database
        logger.error(f"SCRAPE_ERROR: {log_entry}")

        # For now, write to a log file
        try:
            with open("scrape_errors.log", "a", encoding="utf-8") as f:
                f.write(f"{log_entry}\n")
        except Exception as e:
            logger.error(f"Failed to write error log: {e}")


# ============================================================
# HTTP SESSION WITH RETRY LOGIC
# ============================================================

def create_session(verify_ssl: bool = True) -> requests.Session:
    """
    Create a requests session with retry logic and proper headers.

    Args:
        verify_ssl: Whether to verify SSL certificates (default: True)

    Returns:
        Configured requests.Session object
    """
    session = requests.Session()

    # Disable SSL verification if requested (for old government sites)
    session.verify = verify_ssl

    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set default headers
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    })

    return session


# ============================================================
# 1. ICEGATE TARIFF SCRAPER
# ============================================================

def scrape_icegate_chapter(chapter: int, session: Optional[requests.Session] = None) -> List[Dict]:
    """
    Scrape tariff entries for a given customs chapter from ICEGATE.

    This function extracts all tariff entries for a specified chapter code (01-99)
    from the old ICEGATE portal. It parses HTML tables to extract CTH codes,
    descriptions, BCD rates, and units.

    Args:
        chapter: Chapter code (1-99)
        session: Optional requests session (creates new if not provided)

    Returns:
        List of dictionaries with keys:
        - cth_code: 8-digit CTH code
        - description: Item description
        - bcd_rate: Basic Customs Duty rate
        - unit: Unit of measurement
        - chapter: Chapter code
        - scrape_timestamp: ISO timestamp

    Raises:
        ValueError: If chapter is not in valid range (1-99)
    """
    function_name = "scrape_icegate_chapter"
    input_params = {"chapter": chapter}

    # Validate chapter code
    if not (1 <= chapter <= 99):
        error_msg = f"Invalid chapter code: {chapter}. Must be between 1 and 99."
        ScrapeLogger.log_error(function_name, input_params, "ValueError", error_msg)
        raise ValueError(error_msg)

    # Format chapter code with leading zero if needed
    chapter_code = f"{chapter:02d}"

    if session is None:
        # Disable SSL verification for old ICEGATE site with certificate issues
        session = create_session(verify_ssl=False)

    tariff_entries = []

    try:
        # Construct search URL - Note: Actual URL structure may vary
        # This is a placeholder based on common patterns
        search_url = f"{ICEGATE_BASE_URL}?chapter={chapter_code}"

        logger.info(f"Fetching ICEGATE data for chapter {chapter_code}")

        # Make request
        response = session.get(
            search_url,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find tariff table - adjust selectors based on actual HTML structure
        # Common patterns: table with class 'tariff-table', 'data-table', etc.
        tariff_table = soup.find('table', {'class': re.compile(r'tariff|data|result', re.I)})

        if not tariff_table:
            # Try alternative selectors
            tariff_table = soup.find('table', {'id': re.compile(r'tariff|data|result', re.I)})

        if not tariff_table:
            logger.warning(f"No tariff table found for chapter {chapter_code}")
            return tariff_entries

        # Extract table rows (skip header)
        rows = tariff_table.find_all('tr')[1:]  # Skip header row

        for row in rows:
            cells = row.find_all(['td', 'th'])

            if len(cells) < 3:  # Minimum: CTH, description, rate
                continue

            try:
                # Extract data - adjust indices based on actual table structure
                entry = {
                    'cth_code': cells[0].get_text(strip=True),
                    'description': cells[1].get_text(strip=True),
                    'unit': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                    'bcd_rate': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                    'chapter': chapter_code,
                    'scrape_timestamp': datetime.now().isoformat()
                }

                # Validate CTH code format (should be 8 digits)
                if re.match(r'^\d{8}$', entry['cth_code'].replace('.', '')):
                    tariff_entries.append(entry)
                else:
                    logger.debug(f"Skipping invalid CTH: {entry['cth_code']}")

            except Exception as e:
                logger.warning(f"Error parsing row: {e}")
                continue

        logger.info(f"Extracted {len(tariff_entries)} entries for chapter {chapter_code}")

    except requests.exceptions.RequestException as e:
        error_type = type(e).__name__
        error_msg = str(e)
        trace = traceback.format_exc()

        ScrapeLogger.log_error(function_name, input_params, error_type, error_msg, trace)
        logger.error(f"Request error for chapter {chapter_code}: {error_msg}")

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        trace = traceback.format_exc()

        ScrapeLogger.log_error(function_name, input_params, error_type, error_msg, trace)
        logger.error(f"Unexpected error for chapter {chapter_code}: {error_msg}")

    finally:
        # Rate limiting - sleep regardless of success/failure
        time.sleep(RATE_LIMIT_DELAY)

    return tariff_entries


def scrape_all_icegate_chapters(start_chapter: int = 1, end_chapter: int = 99) -> List[Dict]:
    """
    Scrape all chapters from ICEGATE (01-99).

    Args:
        start_chapter: Starting chapter (default 1)
        end_chapter: Ending chapter (default 99)

    Returns:
        Combined list of all tariff entries
    """
    all_entries = []
    session = create_session()

    logger.info(f"Starting full ICEGATE scrape: chapters {start_chapter} to {end_chapter}")

    for chapter in range(start_chapter, end_chapter + 1):
        logger.info(f"Processing chapter {chapter}/{end_chapter}")
        entries = scrape_icegate_chapter(chapter, session)
        all_entries.extend(entries)

    logger.info(f"Total entries scraped: {len(all_entries)}")
    return all_entries


# ============================================================
# 2. CBIC NOTIFICATIONS SCRAPER
# ============================================================

def scrape_cbic_notifications(days_back: int = 90, session: Optional[requests.Session] = None) -> List[Dict]:
    """
    Scrape recent CBIC notifications within specified date range.

    This function fetches customs notifications from the CBIC website,
    filters by publication date, and extracts metadata including PDF links.

    Args:
        days_back: Number of days to look back (default 90)
        session: Optional requests session

    Returns:
        List of dictionaries with keys:
        - notification_number: Official notification number
        - title: Notification title
        - date: Publication date (ISO format)
        - pdf_url: Direct link to PDF file
        - scrape_timestamp: ISO timestamp
    """
    function_name = "scrape_cbic_notifications"
    input_params = {"days_back": days_back}

    if session is None:
        session = create_session()

    notifications = []
    cutoff_date = datetime.now() - timedelta(days=days_back)

    try:
        logger.info(f"Fetching CBIC notifications from last {days_back} days")

        # Make request
        response = session.get(
            CBIC_NOTIFICATIONS_URL,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find notifications list - adjust selectors based on actual HTML structure
        # Common patterns: div/table with class containing 'notification', 'list', etc.
        notification_container = soup.find('div', {'class': re.compile(r'notification|list|content', re.I)})

        if not notification_container:
            notification_container = soup.find('table', {'class': re.compile(r'notification|list', re.I)})

        if not notification_container:
            logger.warning("No notification container found on page")
            return notifications

        # Extract notification entries
        # Try multiple patterns for different HTML structures
        entries = notification_container.find_all(['tr', 'li', 'div'], recursive=True)

        for entry in entries:
            try:
                # Look for date pattern (common formats: DD/MM/YYYY, DD-MM-YYYY)
                date_text = entry.get_text()
                date_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', date_text)

                if not date_match:
                    continue

                # Parse date
                day, month, year = date_match.groups()
                notification_date = datetime(int(year), int(month), int(day))

                # Filter by cutoff date
                if notification_date < cutoff_date:
                    continue

                # Extract PDF link
                pdf_link = entry.find('a', href=re.compile(r'\.pdf$', re.I))

                if not pdf_link:
                    continue

                pdf_url = pdf_link.get('href')

                # Make absolute URL if relative
                if not pdf_url.startswith('http'):
                    base_url = '/'.join(CBIC_NOTIFICATIONS_URL.split('/')[:3])
                    pdf_url = base_url + pdf_url if pdf_url.startswith('/') else f"{CBIC_NOTIFICATIONS_URL}/{pdf_url}"

                # Extract notification number (pattern: Notification No. XX/YYYY)
                notif_num_match = re.search(r'(?:No\.?|Number)\s*(\d+/\d{4})', date_text, re.I)
                notification_number = notif_num_match.group(1) if notif_num_match else "Unknown"

                # Extract title
                title = pdf_link.get_text(strip=True)
                if not title:
                    title = entry.get_text(strip=True)[:100]

                notification = {
                    'notification_number': notification_number,
                    'title': title,
                    'date': notification_date.isoformat(),
                    'pdf_url': pdf_url,
                    'scrape_timestamp': datetime.now().isoformat()
                }

                notifications.append(notification)
                logger.debug(f"Found notification: {notification_number} - {title[:50]}")

            except Exception as e:
                logger.warning(f"Error parsing notification entry: {e}")
                continue

        logger.info(f"Extracted {len(notifications)} notifications")

    except requests.exceptions.RequestException as e:
        error_type = type(e).__name__
        error_msg = str(e)
        trace = traceback.format_exc()

        ScrapeLogger.log_error(function_name, input_params, error_type, error_msg, trace)
        logger.error(f"Request error fetching notifications: {error_msg}")

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        trace = traceback.format_exc()

        ScrapeLogger.log_error(function_name, input_params, error_type, error_msg, trace)
        logger.error(f"Unexpected error fetching notifications: {error_msg}")

    finally:
        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)

    return notifications


# ============================================================
# 3. PDF DOWNLOADER AND PARSER
# ============================================================

def download_and_parse_pdf(pdf_url: str, session: Optional[requests.Session] = None) -> List[Dict]:
    """
    Download customs notification PDF and extract CTH code changes.

    This function downloads a PDF file, extracts text content using pdfplumber,
    and identifies CTH codes using regex pattern matching. It captures both
    formatted (XXXX.XX.XX) and unformatted (XXXXXXXX) CTH codes.

    Args:
        pdf_url: Direct URL to PDF file
        session: Optional requests session

    Returns:
        List of dictionaries with keys:
        - cth_code: Extracted CTH code
        - context: Surrounding text (50 chars before/after)
        - page_number: Page where code was found
        - pdf_url: Source PDF URL
        - scrape_timestamp: ISO timestamp
    """
    function_name = "download_and_parse_pdf"
    input_params = {"pdf_url": pdf_url}

    if session is None:
        session = create_session()

    extracted_cth_codes = []

    try:
        logger.info(f"Downloading PDF: {pdf_url}")

        # Download PDF
        response = session.get(
            pdf_url,
            timeout=REQUEST_TIMEOUT,
            stream=True
        )
        response.raise_for_status()

        # Check if content is actually a PDF
        content_type = response.headers.get('Content-Type', '')
        if 'pdf' not in content_type.lower():
            logger.warning(f"URL may not be a PDF. Content-Type: {content_type}")

        # Read PDF bytes
        pdf_bytes = response.content

        if len(pdf_bytes) == 0:
            error_msg = "Downloaded PDF has zero bytes"
            ScrapeLogger.log_error(function_name, input_params, "ValueError", error_msg)
            logger.error(error_msg)
            return extracted_cth_codes

        logger.info(f"Downloaded {len(pdf_bytes)} bytes. Parsing PDF...")

        # Parse PDF with pdfplumber
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            # Extract text from each page
            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text()

                    if not text:
                        logger.debug(f"No text found on page {page_num}")
                        continue

                    # Pattern matches:
                    # - Formatted: 1234.56.78
                    # - Unformatted: 12345678
                    cth_pattern = r'\b(\d{4}\.?\d{2}\.?\d{2})\b'

                    matches = re.finditer(cth_pattern, text)

                    for match in matches:
                        cth_code = match.group(1)

                        # Normalize format (remove dots)
                        normalized_cth = cth_code.replace('.', '')

                        # Validate it's exactly 8 digits
                        if len(normalized_cth) != 8 or not normalized_cth.isdigit():
                            continue

                        # Extract context (50 chars before and after)
                        start_pos = max(0, match.start() - 50)
                        end_pos = min(len(text), match.end() + 50)
                        context = text[start_pos:end_pos].strip()

                        # Clean context (remove excess whitespace)
                        context = ' '.join(context.split())

                        cth_entry = {
                            'cth_code': normalized_cth,
                            'formatted_cth': f"{normalized_cth[:4]}.{normalized_cth[4:6]}.{normalized_cth[6:8]}",
                            'context': context,
                            'page_number': page_num,
                            'pdf_url': pdf_url,
                            'scrape_timestamp': datetime.now().isoformat()
                        }

                        extracted_cth_codes.append(cth_entry)
                        logger.debug(f"Found CTH {normalized_cth} on page {page_num}")

                except Exception as e:
                    logger.warning(f"Error parsing page {page_num}: {e}")
                    continue

        # Remove duplicates (same CTH on same page)
        seen = set()
        unique_codes = []

        for entry in extracted_cth_codes:
            key = (entry['cth_code'], entry['page_number'])
            if key not in seen:
                seen.add(key)
                unique_codes.append(entry)

        logger.info(f"Extracted {len(unique_codes)} unique CTH codes from PDF")
        extracted_cth_codes = unique_codes

    except requests.exceptions.RequestException as e:
        error_type = type(e).__name__
        error_msg = str(e)
        trace = traceback.format_exc()

        ScrapeLogger.log_error(function_name, input_params, error_type, error_msg, trace)
        logger.error(f"Request error downloading PDF: {error_msg}")

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        trace = traceback.format_exc()

        ScrapeLogger.log_error(function_name, input_params, error_type, error_msg, trace)
        logger.error(f"Unexpected error parsing PDF: {error_msg}")

    finally:
        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)

    return extracted_cth_codes


def process_all_notification_pdfs(notifications: List[Dict]) -> List[Dict]:
    """
    Download and parse all PDFs from a list of notifications.

    Args:
        notifications: List of notification dicts (from scrape_cbic_notifications)

    Returns:
        Combined list of all extracted CTH codes with notification metadata
    """
    all_cth_changes = []
    session = create_session()

    logger.info(f"Processing {len(notifications)} notification PDFs")

    for i, notification in enumerate(notifications, 1):
        pdf_url = notification.get('pdf_url')

        if not pdf_url:
            logger.warning(f"No PDF URL for notification {notification.get('notification_number')}")
            continue

        logger.info(f"Processing PDF {i}/{len(notifications)}: {notification.get('notification_number')}")

        cth_codes = download_and_parse_pdf(pdf_url, session)

        # Enrich with notification metadata
        for cth_entry in cth_codes:
            cth_entry['notification_number'] = notification.get('notification_number')
            cth_entry['notification_date'] = notification.get('date')
            cth_entry['notification_title'] = notification.get('title')

        all_cth_changes.extend(cth_codes)

    logger.info(f"Total CTH codes extracted from all PDFs: {len(all_cth_changes)}")
    return all_cth_changes


# ============================================================
# 4. INDIAN TRADE PORTAL SCRAPER (Playwright for JS-heavy sites)
# ============================================================

def scrape_indian_trade_portal_chapter(
    chapter: int,
    use_playwright: bool = False
) -> List[Dict]:
    """
    Scrape tariff data from Indian Trade Portal (JavaScript-heavy site).

    Note: This site requires JavaScript execution, so Playwright is recommended.
    Falls back to requests if Playwright is not available.

    Args:
        chapter: Chapter code (1-99)
        use_playwright: If True, use Playwright for JS rendering

    Returns:
        List of tariff entry dictionaries
    """
    function_name = "scrape_indian_trade_portal_chapter"
    input_params = {"chapter": chapter, "use_playwright": use_playwright}

    tariff_entries = []
    chapter_code = f"{chapter:02d}"

    if use_playwright:
        try:
            from playwright.sync_api import sync_playwright

            logger.info(f"Using Playwright for Indian Trade Portal chapter {chapter_code}")

            with sync_playwright() as p:
                # Launch browser in headless mode
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=USER_AGENT)
                page = context.new_page()

                # Navigate to search page
                page.goto(INDIAN_TRADE_PORTAL_URL, timeout=REQUEST_TIMEOUT * 1000)

                # Wait for page load and interact with search
                # Note: Adjust selectors based on actual site structure
                try:
                    # Example: Fill search box with chapter code
                    page.fill('input[name="hsn"]', chapter_code)
                    page.click('button[type="submit"]')

                    # Wait for results
                    page.wait_for_selector('.result-table', timeout=10000)

                    # Extract results
                    content = page.content()
                    soup = BeautifulSoup(content, 'html.parser')

                    # Parse results table
                    table = soup.find('table', {'class': re.compile(r'result|data', re.I)})

                    if table:
                        rows = table.find_all('tr')[1:]

                        for row in rows:
                            cells = row.find_all('td')

                            if len(cells) >= 3:
                                entry = {
                                    'cth_code': cells[0].get_text(strip=True),
                                    'description': cells[1].get_text(strip=True),
                                    'bcd_rate': cells[2].get_text(strip=True),
                                    'chapter': chapter_code,
                                    'source': 'indian_trade_portal',
                                    'scrape_timestamp': datetime.now().isoformat()
                                }
                                tariff_entries.append(entry)

                except Exception as e:
                    logger.warning(f"Error during Playwright interaction: {e}")

                finally:
                    browser.close()

        except ImportError:
            logger.warning("Playwright not installed. Install with: pip install playwright")
            logger.info("Falling back to requests method")
            use_playwright = False

        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            trace = traceback.format_exc()

            ScrapeLogger.log_error(function_name, input_params, error_type, error_msg, trace)
            logger.error(f"Playwright error: {error_msg}")

    # Fallback to requests (may not work for JS-heavy sites)
    if not use_playwright:
        session = create_session()

        try:
            logger.info(f"Using requests for Indian Trade Portal chapter {chapter_code}")

            response = session.get(
                f"{INDIAN_TRADE_PORTAL_URL}?hsn={chapter_code}",
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Parse static HTML (if available)
            table = soup.find('table', {'class': re.compile(r'result|data', re.I)})

            if table:
                rows = table.find_all('tr')[1:]

                for row in rows:
                    cells = row.find_all('td')

                    if len(cells) >= 3:
                        entry = {
                            'cth_code': cells[0].get_text(strip=True),
                            'description': cells[1].get_text(strip=True),
                            'bcd_rate': cells[2].get_text(strip=True),
                            'chapter': chapter_code,
                            'source': 'indian_trade_portal',
                            'scrape_timestamp': datetime.now().isoformat()
                        }
                        tariff_entries.append(entry)

        except requests.exceptions.RequestException as e:
            error_type = type(e).__name__
            error_msg = str(e)
            trace = traceback.format_exc()

            ScrapeLogger.log_error(function_name, input_params, error_type, error_msg, trace)
            logger.error(f"Request error: {error_msg}")

    # Rate limiting
    time.sleep(RATE_LIMIT_DELAY)

    logger.info(f"Extracted {len(tariff_entries)} entries from Indian Trade Portal")
    return tariff_entries


# ============================================================
# 5. ORCHESTRATION - Run all scrapers in sequence
# ============================================================

def run_full_scrape(
    scrape_icegate: bool = True,
    scrape_cbic: bool = True,
    scrape_indian_portal: bool = False,
    chapter_range: tuple = (1, 99),
    notification_days: int = 90
) -> Dict[str, List[Dict]]:
    """
    Run all scrapers in the recommended order.

    Args:
        scrape_icegate: Enable ICEGATE scraper
        scrape_cbic: Enable CBIC notifications scraper
        scrape_indian_portal: Enable Indian Trade Portal scraper
        chapter_range: Tuple of (start_chapter, end_chapter)
        notification_days: Days back for notifications

    Returns:
        Dictionary with keys:
        - icegate_tariffs: List of tariff entries
        - cbic_notifications: List of notifications
        - cbic_cth_changes: List of CTH codes from PDFs
        - indian_portal_tariffs: List of tariff entries
    """
    results = {
        'icegate_tariffs': [],
        'cbic_notifications': [],
        'cbic_cth_changes': [],
        'indian_portal_tariffs': []
    }

    logger.info("=" * 60)
    logger.info("STARTING COMPREHENSIVE CUSTOMS DATA SCRAPE")
    logger.info("=" * 60)

    # 1. ICEGATE Tariff Search
    if scrape_icegate:
        logger.info("\n[1/3] ICEGATE Tariff Search")
        logger.info("-" * 60)
        start_chapter, end_chapter = chapter_range
        results['icegate_tariffs'] = scrape_all_icegate_chapters(start_chapter, end_chapter)
        logger.info(f"ICEGATE complete: {len(results['icegate_tariffs'])} entries")

    # 2. CBIC Notifications
    if scrape_cbic:
        logger.info("\n[2/3] CBIC Notifications")
        logger.info("-" * 60)
        results['cbic_notifications'] = scrape_cbic_notifications(notification_days)
        logger.info(f"Found {len(results['cbic_notifications'])} notifications")

        if results['cbic_notifications']:
            logger.info("Processing notification PDFs...")
            results['cbic_cth_changes'] = process_all_notification_pdfs(
                results['cbic_notifications']
            )
            logger.info(f"Extracted {len(results['cbic_cth_changes'])} CTH codes from PDFs")

    # 3. Indian Trade Portal (backup source)
    if scrape_indian_portal:
        logger.info("\n[3/3] Indian Trade Portal (Backup Source)")
        logger.info("-" * 60)
        start_chapter, end_chapter = chapter_range

        for chapter in range(start_chapter, end_chapter + 1):
            entries = scrape_indian_trade_portal_chapter(chapter, use_playwright=True)
            results['indian_portal_tariffs'].extend(entries)

        logger.info(f"Indian Trade Portal complete: {len(results['indian_portal_tariffs'])} entries")

    logger.info("\n" + "=" * 60)
    logger.info("SCRAPE COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total ICEGATE entries: {len(results['icegate_tariffs'])}")
    logger.info(f"Total CBIC notifications: {len(results['cbic_notifications'])}")
    logger.info(f"Total CTH changes from PDFs: {len(results['cbic_cth_changes'])}")
    logger.info(f"Total Indian Portal entries: {len(results['indian_portal_tariffs'])}")

    return results


# ============================================================
# 6. MAIN - For testing and standalone execution
# ============================================================

if __name__ == "__main__":
    """
    Example usage and testing
    """

    # Test individual functions
    print("\n" + "=" * 60)
    print("TESTING INDIVIDUAL SCRAPERS")
    print("=" * 60)

    # Test 1: Single chapter from ICEGATE
    print("\n[Test 1] ICEGATE Chapter 01")
    print("-" * 60)
    chapter_01_data = scrape_icegate_chapter(1)
    print(f"Result: {len(chapter_01_data)} entries")
    if chapter_01_data:
        print(f"Sample entry: {chapter_01_data[0]}")

    # Test 2: CBIC Notifications (last 30 days)
    print("\n[Test 2] CBIC Notifications (last 30 days)")
    print("-" * 60)
    notifications = scrape_cbic_notifications(days_back=30)
    print(f"Result: {len(notifications)} notifications")
    if notifications:
        print(f"Sample notification: {notifications[0]}")

    # Test 3: Download and parse first PDF (if available)
    if notifications:
        print("\n[Test 3] Parse first notification PDF")
        print("-" * 60)
        first_pdf = notifications[0]['pdf_url']
        cth_codes = download_and_parse_pdf(first_pdf)
        print(f"Result: {len(cth_codes)} CTH codes extracted")
        if cth_codes:
            print(f"Sample CTH entry: {cth_codes[0]}")

    # Full scrape (uncomment to run)
    # print("\n" + "=" * 60)
    # print("RUNNING FULL SCRAPE")
    # print("=" * 60)
    #
    # results = run_full_scrape(
    #     scrape_icegate=True,
    #     scrape_cbic=True,
    #     scrape_indian_portal=False,  # Requires Playwright
    #     chapter_range=(1, 5),  # Test with first 5 chapters
    #     notification_days=30
    # )
    #
    # # Save results to JSON
    # import json
    # with open('scrape_results.json', 'w', encoding='utf-8') as f:
    #     json.dump(results, f, indent=2, ensure_ascii=False)
    #
    # print("\nResults saved to scrape_results.json")
