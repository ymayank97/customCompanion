"""
Configuration for the CIP (Compliance Information Portal) scraper.
All configurable parameters in one place.
"""

import os
from pathlib import Path

# === Paths ===
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
CIP_RESULTS_DIR = DATA_DIR / "cip_results"
CTH_MASTER_FILE = DATA_DIR / "cth_master.json"
CHECKPOINT_FILE = DATA_DIR / "cip_checkpoint.json"
ERROR_LOG_FILE = PROJECT_ROOT / "scrape_errors.log"

# Ensure directories exist
CIP_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# === CIP Portal ===
CIP_BASE_URL = "https://cip.icegate.gov.in/CIP/#/home"
CIP_IMPORT_DUTY_URL = "https://cip.icegate.gov.in/CIP/#/importDuty"

# === CTH Seed Sources ===
HSN_GITHUB_CSV_URL = "https://raw.githubusercontent.com/frontlook-admin/HSN-Code-Classifier/Master/HSNCodes.csv"
HSN_GITHUB_JSON_URL = "https://raw.githubusercontent.com/frontlook-admin/HSN-Code-Classifier/Master/HsnCodes.json"
# GitHub Pages fallbacks
HSN_PAGES_CSV_URL = "https://frontlook-admin.github.io/HSN-Code-Classifier/HSNCodes.csv"
HSN_PAGES_JSON_URL = "https://frontlook-admin.github.io/HSN-Code-Classifier/HsnCodes.json"

# === Rate Limiting ===
REQUEST_DELAY = float(os.environ.get("CIP_REQUEST_DELAY", "3.0"))  # seconds between requests
PAGE_LOAD_TIMEOUT = int(os.environ.get("CIP_PAGE_TIMEOUT", "30000"))  # ms
NAVIGATION_TIMEOUT = int(os.environ.get("CIP_NAV_TIMEOUT", "60000"))  # ms

# === Retry ===
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 5  # seconds; retries at 5s, 10s, 20s

# === Browser ===
HEADLESS = os.environ.get("CIP_HEADLESS", "true").lower() == "true"
BROWSER_TYPE = "chromium"  # chromium, firefox, webkit
VIEWPORT_WIDTH = 1280
VIEWPORT_HEIGHT = 720
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# === Scraping Batch ===
BATCH_SIZE = 50  # save checkpoint every N codes
CHAPTER_RANGE = (1, 98)  # chapters 01-98
