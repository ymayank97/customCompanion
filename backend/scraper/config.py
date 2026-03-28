"""
Configuration settings for customs data scraper.

This file contains all configurable parameters for the scraping operations.
You can override these settings by creating a .env file or modifying values here.
"""

import os
from pathlib import Path

# ============================================================
# PROJECT PATHS
# ============================================================

# Base directory
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent

# Output directories
OUTPUT_DIR = PROJECT_ROOT / "data" / "scraped"
LOGS_DIR = PROJECT_ROOT / "logs"
CACHE_DIR = PROJECT_ROOT / "cache"

# Create directories if they don't exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# SCRAPING SETTINGS
# ============================================================

# Rate limiting (seconds between requests)
RATE_LIMIT_DELAY = float(os.getenv('RATE_LIMIT_DELAY', '2.0'))

# Request timeout (seconds)
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))

# User-Agent string
USER_AGENT = os.getenv(
    'USER_AGENT',
    'Mozilla/5.0 (compatible; CustomsClassifierBot/1.0; research purposes)'
)

# Retry settings
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
RETRY_BACKOFF_FACTOR = float(os.getenv('RETRY_BACKOFF_FACTOR', '1.0'))

# ============================================================
# DATA SOURCE URLS
# ============================================================

# ICEGATE (old portal)
ICEGATE_BASE_URL = os.getenv(
    'ICEGATE_BASE_URL',
    'https://old.icegate.gov.in/Webappl/'
)

# CBIC Notifications
CBIC_NOTIFICATIONS_URL = os.getenv(
    'CBIC_NOTIFICATIONS_URL',
    'https://www.cbic.gov.in/htdocs-cbec/customs/custom-tariff'
)

# Indian Trade Portal
INDIAN_TRADE_PORTAL_URL = os.getenv(
    'INDIAN_TRADE_PORTAL_URL',
    'https://www.indiantradeportal.in/'
)

# ============================================================
# SCRAPING PARAMETERS
# ============================================================

# Default chapter range
DEFAULT_CHAPTER_START = int(os.getenv('DEFAULT_CHAPTER_START', '1'))
DEFAULT_CHAPTER_END = int(os.getenv('DEFAULT_CHAPTER_END', '99'))

# Default notification lookback period (days)
DEFAULT_NOTIFICATION_DAYS = int(os.getenv('DEFAULT_NOTIFICATION_DAYS', '90'))

# Enable/disable sources
ENABLE_ICEGATE = os.getenv('ENABLE_ICEGATE', 'true').lower() == 'true'
ENABLE_CBIC = os.getenv('ENABLE_CBIC', 'true').lower() == 'true'
ENABLE_INDIAN_PORTAL = os.getenv('ENABLE_INDIAN_PORTAL', 'false').lower() == 'true'

# ============================================================
# PDF PROCESSING SETTINGS
# ============================================================

# Maximum PDF size to process (MB)
MAX_PDF_SIZE_MB = int(os.getenv('MAX_PDF_SIZE_MB', '50'))

# PDF extraction settings
PDF_EXTRACT_IMAGES = os.getenv('PDF_EXTRACT_IMAGES', 'false').lower() == 'true'

# CTH code regex pattern
CTH_CODE_PATTERN = r'\b(\d{4}\.?\d{2}\.?\d{2})\b'

# Context window for CTH extraction (characters before/after)
CTH_CONTEXT_CHARS = int(os.getenv('CTH_CONTEXT_CHARS', '50'))

# ============================================================
# DATABASE SETTINGS (optional)
# ============================================================

# Database connection string
DATABASE_URL = os.getenv('DATABASE_URL', None)

# Database settings
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
DB_NAME = os.getenv('DB_NAME', 'customs_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

# Enable database logging
ENABLE_DB_LOGGING = os.getenv('ENABLE_DB_LOGGING', 'false').lower() == 'true'

# ============================================================
# LOGGING SETTINGS
# ============================================================

# Log file paths
ERROR_LOG_FILE = LOGS_DIR / 'scrape_errors.log'
INFO_LOG_FILE = LOGS_DIR / 'scrape_info.log'

# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Log format
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Maximum log file size (MB)
MAX_LOG_SIZE_MB = int(os.getenv('MAX_LOG_SIZE_MB', '100'))

# Number of log file backups to keep
LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))

# ============================================================
# CACHE SETTINGS
# ============================================================

# Enable caching
ENABLE_CACHE = os.getenv('ENABLE_CACHE', 'true').lower() == 'true'

# Cache TTL (seconds)
CACHE_TTL = int(os.getenv('CACHE_TTL', '86400'))  # 24 hours

# Cache directory
CACHE_PATH = CACHE_DIR / 'scraper_cache'
CACHE_PATH.mkdir(exist_ok=True)

# ============================================================
# PLAYWRIGHT SETTINGS (for JS-heavy sites)
# ============================================================

# Browser type (chromium, firefox, webkit)
PLAYWRIGHT_BROWSER = os.getenv('PLAYWRIGHT_BROWSER', 'chromium')

# Headless mode
PLAYWRIGHT_HEADLESS = os.getenv('PLAYWRIGHT_HEADLESS', 'true').lower() == 'true'

# Page load timeout (ms)
PLAYWRIGHT_TIMEOUT = int(os.getenv('PLAYWRIGHT_TIMEOUT', '30000'))

# ============================================================
# DATA VALIDATION SETTINGS
# ============================================================

# Validate CTH codes
VALIDATE_CTH_FORMAT = os.getenv('VALIDATE_CTH_FORMAT', 'true').lower() == 'true'

# Minimum description length (characters)
MIN_DESCRIPTION_LENGTH = int(os.getenv('MIN_DESCRIPTION_LENGTH', '10'))

# Skip entries with missing critical fields
SKIP_INCOMPLETE_ENTRIES = os.getenv('SKIP_INCOMPLETE_ENTRIES', 'true').lower() == 'true'

# ============================================================
# EXPORT SETTINGS
# ============================================================

# Default export format (json, csv, both)
DEFAULT_EXPORT_FORMAT = os.getenv('DEFAULT_EXPORT_FORMAT', 'both')

# Include metadata in exports
INCLUDE_METADATA = os.getenv('INCLUDE_METADATA', 'true').lower() == 'true'

# Pretty print JSON
JSON_INDENT = int(os.getenv('JSON_INDENT', '2'))

# CSV delimiter
CSV_DELIMITER = os.getenv('CSV_DELIMITER', ',')

# ============================================================
# SCHEDULING SETTINGS
# ============================================================

# Enable scheduled scraping
ENABLE_SCHEDULER = os.getenv('ENABLE_SCHEDULER', 'false').lower() == 'true'

# Schedule time (24-hour format, e.g., "02:00" for 2 AM)
SCHEDULE_TIME = os.getenv('SCHEDULE_TIME', '02:00')

# Days of week to run (0=Monday, 6=Sunday)
SCHEDULE_DAYS = [int(d) for d in os.getenv('SCHEDULE_DAYS', '0,1,2,3,4').split(',')]

# ============================================================
# NOTIFICATION SETTINGS (optional)
# ============================================================

# Email notifications
ENABLE_EMAIL_NOTIFICATIONS = os.getenv('ENABLE_EMAIL_NOTIFICATIONS', 'false').lower() == 'true'
EMAIL_TO = os.getenv('EMAIL_TO', '')
EMAIL_FROM = os.getenv('EMAIL_FROM', '')
SMTP_HOST = os.getenv('SMTP_HOST', '')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')

# Slack notifications
ENABLE_SLACK_NOTIFICATIONS = os.getenv('ENABLE_SLACK_NOTIFICATIONS', 'false').lower() == 'true'
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')

# ============================================================
# DEVELOPMENT/DEBUG SETTINGS
# ============================================================

# Debug mode
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

# Dry run (don't save data)
DRY_RUN = os.getenv('DRY_RUN', 'false').lower() == 'true'

# Limit scraping for testing
TEST_MODE = os.getenv('TEST_MODE', 'false').lower() == 'true'
TEST_CHAPTER_LIMIT = int(os.getenv('TEST_CHAPTER_LIMIT', '5'))
TEST_NOTIFICATION_LIMIT = int(os.getenv('TEST_NOTIFICATION_LIMIT', '10'))

# Save raw HTML for debugging
SAVE_RAW_HTML = os.getenv('SAVE_RAW_HTML', 'false').lower() == 'true'
RAW_HTML_DIR = CACHE_DIR / 'raw_html'
if SAVE_RAW_HTML:
    RAW_HTML_DIR.mkdir(exist_ok=True)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_output_file(filename: str, format: str = 'json') -> Path:
    """
    Get full path for output file.

    Args:
        filename: Base filename
        format: File format (json, csv)

    Returns:
        Full path to output file
    """
    if not filename.endswith(f'.{format}'):
        filename = f"{filename}.{format}"
    return OUTPUT_DIR / filename


def get_log_file(log_type: str = 'error') -> Path:
    """
    Get log file path.

    Args:
        log_type: Type of log (error, info)

    Returns:
        Full path to log file
    """
    if log_type == 'error':
        return ERROR_LOG_FILE
    else:
        return INFO_LOG_FILE


def get_cache_file(key: str) -> Path:
    """
    Get cache file path.

    Args:
        key: Cache key

    Returns:
        Full path to cache file
    """
    return CACHE_PATH / f"{key}.json"


def print_config():
    """Print current configuration."""
    print("\n" + "="*60)
    print("SCRAPER CONFIGURATION")
    print("="*60)
    print(f"\nPaths:")
    print(f"  Output: {OUTPUT_DIR}")
    print(f"  Logs: {LOGS_DIR}")
    print(f"  Cache: {CACHE_DIR}")
    print(f"\nScraping:")
    print(f"  Rate Limit: {RATE_LIMIT_DELAY}s")
    print(f"  Timeout: {REQUEST_TIMEOUT}s")
    print(f"  Max Retries: {MAX_RETRIES}")
    print(f"\nData Sources:")
    print(f"  ICEGATE: {'Enabled' if ENABLE_ICEGATE else 'Disabled'}")
    print(f"  CBIC: {'Enabled' if ENABLE_CBIC else 'Disabled'}")
    print(f"  Indian Portal: {'Enabled' if ENABLE_INDIAN_PORTAL else 'Disabled'}")
    print(f"\nDefaults:")
    print(f"  Chapters: {DEFAULT_CHAPTER_START}-{DEFAULT_CHAPTER_END}")
    print(f"  Notification Days: {DEFAULT_NOTIFICATION_DAYS}")
    print(f"\nFeatures:")
    print(f"  Cache: {'Enabled' if ENABLE_CACHE else 'Disabled'}")
    print(f"  DB Logging: {'Enabled' if ENABLE_DB_LOGGING else 'Disabled'}")
    print(f"  Scheduler: {'Enabled' if ENABLE_SCHEDULER else 'Disabled'}")
    print(f"  Debug Mode: {'On' if DEBUG else 'Off'}")
    print(f"  Test Mode: {'On' if TEST_MODE else 'Off'}")
    print("="*60)


# ============================================================
# LOAD FROM .env FILE (if exists)
# ============================================================

def load_env_file():
    """Load configuration from .env file if it exists."""
    env_file = PROJECT_ROOT / '.env'

    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            print(f"Loaded configuration from {env_file}")
        except ImportError:
            print("python-dotenv not installed. Skipping .env file.")
    else:
        print("No .env file found. Using default configuration.")


# Auto-load .env on import
load_env_file()


if __name__ == "__main__":
    # Print configuration when run directly
    print_config()
