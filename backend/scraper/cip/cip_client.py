"""
CIP Browser Client using Playwright (Chromium).

Automates the Compliance Information Portal at cip.icegate.gov.in
to scrape import duty and compliance data for CTH codes.
"""

import json
import logging
import time
import traceback
from datetime import datetime
from typing import Optional

from .config import (
    CIP_BASE_URL,
    CIP_IMPORT_DUTY_URL,
    HEADLESS,
    BROWSER_TYPE,
    VIEWPORT_WIDTH,
    VIEWPORT_HEIGHT,
    USER_AGENT,
    PAGE_LOAD_TIMEOUT,
    NAVIGATION_TIMEOUT,
    REQUEST_DELAY,
    MAX_RETRIES,
    RETRY_BACKOFF_BASE,
)
from .models import CIPRecord

logger = logging.getLogger(__name__)


class CIPBrowserClient:
    """
    Playwright-based browser client for the CIP portal.

    Usage:
        client = CIPBrowserClient()
        client.start()
        record = client.scrape_cth("70134900")
        client.stop()

    Or as context manager:
        with CIPBrowserClient() as client:
            record = client.scrape_cth("70134900")
    """

    def __init__(self, headless: bool = HEADLESS):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._started = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False

    def start(self):
        """Launch browser and navigate to CIP portal."""
        if self._started:
            return

        from playwright.sync_api import sync_playwright

        logger.info(f"Launching {BROWSER_TYPE} (headless={self.headless})")
        self.playwright = sync_playwright().start()

        launcher = getattr(self.playwright, BROWSER_TYPE)
        self.browser = launcher.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )

        self.context = self.browser.new_context(
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            user_agent=USER_AGENT,
            java_script_enabled=True,
            ignore_https_errors=True,
        )

        self.page = self.context.new_page()
        self.page.set_default_timeout(PAGE_LOAD_TIMEOUT)
        self.page.set_default_navigation_timeout(NAVIGATION_TIMEOUT)

        # Navigate to CIP home to establish session
        logger.info(f"Navigating to {CIP_BASE_URL}")
        self.page.goto(CIP_BASE_URL, wait_until="networkidle")
        time.sleep(2)  # let Angular fully initialize
        self._started = True
        logger.info("CIP portal loaded successfully")

    def stop(self):
        """Close browser and cleanup."""
        if self.page:
            try:
                self.page.close()
            except Exception:
                pass
        if self.context:
            try:
                self.context.close()
            except Exception:
                pass
        if self.browser:
            try:
                self.browser.close()
            except Exception:
                pass
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception:
                pass
        self._started = False
        logger.info("Browser closed")

    def _navigate_to_import_duty(self):
        """Navigate to the Import Duty search page."""
        current_url = self.page.url
        if "importDuty" not in current_url:
            logger.debug("Navigating to Import Duty page")
            self.page.goto(CIP_IMPORT_DUTY_URL, wait_until="networkidle")
            time.sleep(1)

    def _find_and_fill_cth_input(self, cth_code: str) -> bool:
        """
        Find the CTH input field and fill it.
        Tries multiple selector strategies for robustness.
        """
        selectors = [
            # By placeholder text
            'input[placeholder*="CTH" i]',
            'input[placeholder*="tariff" i]',
            'input[placeholder*="HSN" i]',
            'input[placeholder*="code" i]',
            'input[placeholder*="search" i]',
            # By common Angular form field patterns
            'input[formcontrolname*="cth" i]',
            'input[formcontrolname*="tariff" i]',
            'input[formcontrolname*="hsn" i]',
            'input[formcontrolname*="search" i]',
            'input[formcontrolname*="code" i]',
            # By name/id
            'input[name*="cth" i]',
            'input[name*="tariff" i]',
            'input[name*="hsn" i]',
            'input[id*="cth" i]',
            'input[id*="tariff" i]',
            'input[id*="hsn" i]',
            # By type
            'input[type="search"]',
            'input[type="text"]',
            # By ng-model (AngularJS)
            'input[ng-model*="cth" i]',
            'input[ng-model*="search" i]',
        ]

        for selector in selectors:
            try:
                el = self.page.query_selector(selector)
                if el and el.is_visible():
                    el.click()
                    el.fill("")
                    time.sleep(0.3)
                    el.fill(cth_code)
                    logger.debug(f"Filled CTH input using selector: {selector}")
                    return True
            except Exception:
                continue

        # Fallback: try all visible text inputs
        try:
            inputs = self.page.query_selector_all("input[type='text'], input:not([type])")
            for inp in inputs:
                if inp.is_visible():
                    inp.click()
                    inp.fill("")
                    time.sleep(0.3)
                    inp.fill(cth_code)
                    logger.debug("Filled CTH using fallback (first visible text input)")
                    return True
        except Exception:
            pass

        return False

    def _click_search_button(self) -> bool:
        """
        Click the search/submit button.
        Tries multiple selector strategies.
        """
        selectors = [
            'button[type="submit"]',
            'button:has-text("Search")',
            'button:has-text("Submit")',
            'button:has-text("search")',
            'button:has-text("submit")',
            'button:has-text("Go")',
            'button:has-text("Find")',
            'input[type="submit"]',
            'a:has-text("Search")',
            'a:has-text("Submit")',
            # Material/Angular buttons
            'button.mat-raised-button',
            'button.mat-flat-button',
            'button.btn-primary',
            'button.btn-search',
            # Icon buttons (search icon)
            'button .fa-search',
            'button .material-icons',
        ]

        for selector in selectors:
            try:
                el = self.page.query_selector(selector)
                if el and el.is_visible():
                    el.click()
                    logger.debug(f"Clicked search button using selector: {selector}")
                    return True
            except Exception:
                continue

        # Fallback: press Enter in the input field
        try:
            self.page.keyboard.press("Enter")
            logger.debug("Pressed Enter as search fallback")
            return True
        except Exception:
            pass

        return False

    def _wait_for_results(self) -> bool:
        """Wait for results to load after search."""
        # Wait for any of these result indicators
        result_selectors = [
            "table",
            ".result",
            ".duty",
            ".tariff",
            ".compliance",
            ".mat-table",
            ".data-table",
            "[class*='result']",
            "[class*='duty']",
            "[class*='detail']",
        ]

        try:
            # First wait for network to settle
            self.page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        # Then check for result elements
        for selector in result_selectors:
            try:
                self.page.wait_for_selector(selector, timeout=5000)
                logger.debug(f"Results detected with selector: {selector}")
                return True
            except Exception:
                continue

        # Give Angular extra time to render
        time.sleep(3)
        return True  # proceed anyway, we'll extract whatever is there

    def _extract_all_tables(self) -> list[list[dict]]:
        """Extract all HTML tables from the current page."""
        tables_data = self.page.evaluate("""
            () => {
                const tables = document.querySelectorAll('table');
                const result = [];
                for (const table of tables) {
                    const tableData = [];
                    const headers = [];
                    const headerRow = table.querySelector('thead tr, tr:first-child');
                    if (headerRow) {
                        headerRow.querySelectorAll('th, td').forEach(cell => {
                            headers.push(cell.innerText.trim());
                        });
                    }
                    const rows = table.querySelectorAll('tbody tr, tr');
                    for (let i = (headers.length > 0 ? 0 : 1); i < rows.length; i++) {
                        const row = rows[i];
                        // Skip if this is the header row
                        if (row.querySelector('th') && i === 0) continue;
                        const cells = row.querySelectorAll('td');
                        if (cells.length === 0) continue;
                        const rowData = {};
                        cells.forEach((cell, idx) => {
                            const key = idx < headers.length ? headers[idx] : `col_${idx}`;
                            rowData[key] = cell.innerText.trim();
                        });
                        tableData.push(rowData);
                    }
                    if (tableData.length > 0) {
                        result.push(tableData);
                    }
                }
                return result;
            }
        """)
        return tables_data or []

    def _extract_page_text(self) -> str:
        """Extract all visible text content from the page."""
        try:
            text = self.page.evaluate("""
                () => {
                    // Get main content area, excluding nav/header/footer
                    const main = document.querySelector('main, .main-content, .content, app-root, #content')
                        || document.body;
                    return main.innerText || '';
                }
            """)
            return text.strip()
        except Exception:
            return ""

    def _extract_all_data(self) -> dict:
        """
        Extract everything visible on the page.
        Returns raw data dict with tables, text, links, etc.
        """
        data = self.page.evaluate("""
            () => {
                const result = {
                    tables: [],
                    lists: [],
                    cards: [],
                    links: [],
                    headings: [],
                    key_value_pairs: [],
                    all_text: '',
                };

                // Extract tables
                document.querySelectorAll('table').forEach(table => {
                    const headers = [];
                    const headerRow = table.querySelector('thead tr, tr:first-child');
                    if (headerRow) {
                        headerRow.querySelectorAll('th, td').forEach(c => headers.push(c.innerText.trim()));
                    }
                    const rows = [];
                    table.querySelectorAll('tbody tr').forEach(tr => {
                        const cells = {};
                        tr.querySelectorAll('td').forEach((td, i) => {
                            cells[i < headers.length ? headers[i] : 'col_' + i] = td.innerText.trim();
                        });
                        if (Object.keys(cells).length > 0) rows.push(cells);
                    });
                    if (rows.length > 0) result.tables.push({headers, rows});
                });

                // Extract list items
                document.querySelectorAll('ul, ol').forEach(list => {
                    const items = [];
                    list.querySelectorAll('li').forEach(li => {
                        items.push(li.innerText.trim());
                    });
                    if (items.length > 0) result.lists.push(items);
                });

                // Extract card-like elements (common in Angular Material)
                document.querySelectorAll('.mat-card, .card, [class*="card"]').forEach(card => {
                    result.cards.push(card.innerText.trim());
                });

                // Extract headings
                document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(h => {
                    result.headings.push({level: h.tagName, text: h.innerText.trim()});
                });

                // Extract key-value pairs (label: value pattern)
                document.querySelectorAll('.row, .form-group, [class*="detail"], [class*="info"]').forEach(el => {
                    const label = el.querySelector('label, .label, strong, b, dt, th');
                    const value = el.querySelector('.value, span, dd, td:last-child, p');
                    if (label && value) {
                        result.key_value_pairs.push({
                            key: label.innerText.trim(),
                            value: value.innerText.trim()
                        });
                    }
                });

                // Extract links
                document.querySelectorAll('a[href]').forEach(a => {
                    result.links.push({text: a.innerText.trim(), href: a.href});
                });

                // Full text
                const main = document.querySelector('main, .main-content, app-root') || document.body;
                result.all_text = main.innerText || '';

                return result;
            }
        """)
        return data or {}

    def _click_cth_result_link(self, cth_code: str) -> bool:
        """
        If results show a list of CTH codes, click the specific one.
        Some portals show a list first, then details on click.
        """
        try:
            # Try clicking a link/row that contains our CTH code
            link = self.page.query_selector(f'a:has-text("{cth_code}")')
            if link and link.is_visible():
                link.click()
                time.sleep(2)
                self.page.wait_for_load_state("networkidle", timeout=10000)
                return True

            # Try clicking a table row
            row = self.page.query_selector(f'tr:has-text("{cth_code}")')
            if row and row.is_visible():
                row.click()
                time.sleep(2)
                return True

            # Try with formatted code (XXXX.XX.XX)
            formatted = f"{cth_code[:4]}.{cth_code[4:6]}.{cth_code[6:8]}"
            link = self.page.query_selector(f'a:has-text("{formatted}")')
            if link and link.is_visible():
                link.click()
                time.sleep(2)
                return True

        except Exception as e:
            logger.debug(f"Could not click CTH result link: {e}")

        return False

    def scrape_cth(self, cth_code: str) -> CIPRecord:
        """
        Scrape all available data for a given CTH code from CIP portal.

        Args:
            cth_code: 8-digit CTH code (e.g., "70134900")

        Returns:
            CIPRecord with all extracted data
        """
        if not self._started:
            raise RuntimeError("Browser not started. Call start() first.")

        record = CIPRecord(cth_code=cth_code)
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"Scraping CTH {cth_code} (attempt {attempt}/{MAX_RETRIES})")

                # Step 1: Navigate to import duty page
                self._navigate_to_import_duty()
                time.sleep(1)

                # Step 2: Fill CTH input
                if not self._find_and_fill_cth_input(cth_code):
                    logger.warning(f"Could not find CTH input field for {cth_code}")
                    record.error = "CTH input field not found"
                    # Take screenshot for debugging
                    self._save_debug_screenshot(cth_code, "no_input")
                    if attempt < MAX_RETRIES:
                        # Reload and retry
                        self.page.reload(wait_until="networkidle")
                        time.sleep(RETRY_BACKOFF_BASE * attempt)
                        continue
                    return record

                time.sleep(0.5)

                # Step 3: Click search
                if not self._click_search_button():
                    logger.warning(f"Could not find search button for {cth_code}")
                    record.error = "Search button not found"
                    self._save_debug_screenshot(cth_code, "no_button")
                    if attempt < MAX_RETRIES:
                        self.page.reload(wait_until="networkidle")
                        time.sleep(RETRY_BACKOFF_BASE * attempt)
                        continue
                    return record

                # Step 4: Wait for results
                self._wait_for_results()

                # Step 5: Try to click into specific CTH detail
                self._click_cth_result_link(cth_code)

                # Step 6: Extract everything
                record.page_url = self.page.url
                record.page_title = self.page.title()
                record.raw_data = self._extract_all_data()
                record.tables = self._extract_all_tables()
                record.text_content = self._extract_page_text()
                record.error = ""

                logger.info(f"Successfully scraped CTH {cth_code}: "
                           f"{len(record.tables)} tables, "
                           f"{len(record.text_content)} chars text")
                return record

            except Exception as e:
                last_error = str(e)
                trace = traceback.format_exc()
                logger.warning(f"Attempt {attempt} failed for CTH {cth_code}: {last_error}")

                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                    logger.info(f"Retrying in {wait}s...")
                    time.sleep(wait)
                    # Try to recover browser state
                    try:
                        self.page.goto(CIP_BASE_URL, wait_until="networkidle")
                        time.sleep(2)
                    except Exception:
                        # Browser might be broken, restart it
                        logger.warning("Restarting browser...")
                        self.stop()
                        self.start()

        record.error = f"All {MAX_RETRIES} attempts failed. Last error: {last_error}"
        return record

    def _save_debug_screenshot(self, cth_code: str, label: str):
        """Save a screenshot for debugging."""
        try:
            from .config import CIP_RESULTS_DIR
            path = CIP_RESULTS_DIR / f"debug_{cth_code}_{label}.png"
            self.page.screenshot(path=str(path))
            logger.debug(f"Debug screenshot saved: {path}")
        except Exception as e:
            logger.debug(f"Could not save screenshot: {e}")

    def scrape_cth_batch(self, cth_codes: list[str]) -> list[CIPRecord]:
        """
        Scrape a batch of CTH codes.

        Args:
            cth_codes: List of 8-digit CTH codes

        Returns:
            List of CIPRecord objects
        """
        results = []
        for i, code in enumerate(cth_codes):
            logger.info(f"[{i+1}/{len(cth_codes)}] Scraping {code}")
            record = self.scrape_cth(code)
            results.append(record)
            time.sleep(REQUEST_DELAY)
        return results

    def test_connection(self) -> bool:
        """Test if CIP portal is accessible."""
        try:
            if not self._started:
                self.start()

            title = self.page.title()
            text = self._extract_page_text()
            logger.info(f"CIP portal title: {title}")
            logger.info(f"Page text length: {len(text)} chars")
            return len(text) > 0

        except Exception as e:
            logger.error(f"CIP connection test failed: {e}")
            return False
