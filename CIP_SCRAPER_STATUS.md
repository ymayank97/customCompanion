# CIP Scraper - Implementation Status Report

## Overview

A Playwright-based (Chromium) web scraper for the **Compliance Information Portal (CIP)** at `cip.icegate.gov.in`, designed to scrape import duty and compliance data for all ~12,000 Indian Customs Tariff Heading (CTH) codes.

---

## What's Done

### 1. `backend/scraper/cip/config.py` — Configuration
- All configurable parameters in one place
- CIP portal URLs (`cip.icegate.gov.in/CIP/#/home`, `#/importDuty`)
- CTH seed source URLs (GitHub HSN repo CSV/JSON + GitHub Pages fallbacks)
- Rate limiting: 3s delay between requests (configurable via `CIP_REQUEST_DELAY` env var)
- Browser settings: headless Chromium, 1280x720 viewport, realistic User-Agent
- Retry: 3 attempts with 5s/10s/20s exponential backoff
- Checkpoint: saves progress every 50 codes
- All paths derived from project root

### 2. `backend/scraper/cip/models.py` — Data Models
- `CIPRecord` dataclass storing raw scraped data per CTH code
- Fields: `cth_code`, `raw_data` (dict), `page_title`, `page_url`, `tables` (list), `text_content`, `scrape_timestamp`, `error`
- `to_dict()` / `from_dict()` serialization
- Designed for raw collection — no preprocessing, store everything

### 3. `backend/scraper/cip/cth_seed.py` — CTH Code Master List Builder
- Downloads all valid 8-digit CTH codes from GitHub HSN repo
- Tries 4 URLs in order: raw GitHub CSV, GitHub Pages CSV, raw GitHub JSON, GitHub Pages JSON
- Last-resort fallback: generates ~25K candidate codes from chapter/heading patterns
- Caches to `data/cth_master.json` (only downloads once unless `--force`)
- Filters to 8-digit codes in chapters 01-98 only
- Deduplicates and sorts

### 4. `backend/scraper/cip/cip_client.py` — Playwright Browser Client
- `CIPBrowserClient` class with context manager support
- Launches headless Chromium with anti-detection flags (`--disable-blink-features=AutomationControlled`)
- **Multi-strategy element detection**: tries 20+ CSS selectors for input fields and buttons
  - By placeholder, formcontrolname, name, id, type, ng-model
  - Fallback: first visible text input + Enter key
- **Scraping flow per CTH code**:
  1. Navigate to Import Duty page
  2. Find and fill CTH input field
  3. Click search/submit button
  4. Wait for Angular to render results (networkidle + selector detection)
  5. Click into CTH detail link if results show a list
  6. Extract ALL data: tables, lists, cards, headings, key-value pairs, links, full text
- JavaScript-based extraction runs in browser context
- Debug screenshots on failure
- Browser restart on fatal errors
- Retry with exponential backoff (3 attempts)

### 5. `backend/scraper/cip/scrape_cip.py` — Main Orchestrator
- `CIPScraper` class with full pipeline
- **Checkpoint/resume**: tracks completed codes in `data/cip_checkpoint.json`
- **Chapter-based output**: one JSON file per chapter in `data/cip_results/`
- **Graceful shutdown**: Ctrl+C saves progress before exiting (double Ctrl+C for force quit)
- **Progress bar**: tqdm with live stats (success/error counts, current chapter)
- **Error logging**: all failures appended to `scrape_errors.log`
- **Export**: combine all chapter files into single JSON/CSV
- **CLI with argparse**:
  - `--test [CTH]` — test single code
  - `--chapters 70 84` — specific chapters
  - `--codes 84714110 85171210` — specific codes
  - `--visible` — show browser window
  - `--export` — combine results to JSON/CSV
  - `--force` — ignore checkpoint, re-scrape
  - `--seed` — only build CTH master list

### 6. `run_scraper.py` — Unified Runner
- Two modes: `cip` (new Playwright scraper) and `legacy` (old requests-based)
- Routes CLI args to the appropriate module

### 7. `data/cth_master.json` — Seed Data
- 25,578 candidate CTH codes across 98 chapters (generated fallback)
- When run on local machine with internet, downloads real ~12K codes with descriptions

---

## What Needs to Be Done (On User's Machine)

### Required Setup
```bash
# 1. Install Python dependencies
pip install -r backend/scraper/requirements.txt

# 2. Install Playwright browsers (REQUIRED — downloads Chromium)
playwright install chromium

# 3. (Optional) Install system dependencies for Playwright
playwright install-deps
```

### First Run — Test Connectivity
```bash
# Build the real CTH master list (downloads from GitHub)
python run_scraper.py cip --seed

# Test with a single CTH code (visible browser for debugging)
python run_scraper.py cip --test --visible

# Test specific code
python run_scraper.py cip --test 70134900 --visible
```

### Known Issues to Resolve on First Run

1. **CIP Portal Element Selectors**: The scraper uses 20+ CSS selector strategies to find the CTH input field and search button. On the real CIP Angular SPA, the actual selectors may differ. After running `--test --visible`, you can:
   - See which selectors match in the logs
   - If none match, inspect the page in the visible browser and update the selector lists in `cip_client.py`

2. **CIP Portal Navigation Flow**: The portal may have a different flow than expected (e.g., dropdown menus, multi-step forms, country selection). The `--visible` mode lets you observe and adjust.

3. **CAPTCHA**: The ICEGATE duty calculator has CAPTCHA. The CIP portal may or may not. If it does, the scraper will need a CAPTCHA-solving integration.

4. **Rate Limiting / IP Blocking**: Government portals may block rapid requests. The default 3s delay should be safe, but increase via `CIP_REQUEST_DELAY=5` if needed.

5. **CTH Master List**: The GitHub HSN repo URLs may need adjustment if the repo structure changes. The fallback generator creates candidate codes, but the real list from GitHub will have accurate codes with descriptions.

---

## Architecture

```
run_scraper.py                          # Entry point
  └─ backend/scraper/cip/
       ├── __init__.py                  # Package init
       ├── config.py                    # All settings
       ├── models.py                    # CIPRecord dataclass
       ├── cth_seed.py                  # CTH code list builder
       ├── cip_client.py               # Playwright browser automation
       └── scrape_cip.py               # Orchestrator + CLI

data/
  ├── cth_master.json                   # All CTH codes (seed)
  ├── cip_checkpoint.json               # Resume progress
  └── cip_results/
       ├── chapter_01.json              # Per-chapter results
       ├── chapter_02.json
       └── ...
```

## Data Flow

```
1. cth_seed.py → downloads/generates CTH code list → data/cth_master.json
2. scrape_cip.py → loads CTH list → iterates codes
3. cip_client.py → for each code:
     a. Navigate to CIP Import Duty page
     b. Fill CTH input, click Search
     c. Wait for Angular to render
     d. Extract ALL page data (tables, text, links, key-value pairs)
     e. Return CIPRecord
4. scrape_cip.py → saves CIPRecord to data/cip_results/chapter_XX.json
5. Checkpoint saved every 50 codes → resume on restart
```

## Usage Reference

```bash
# Full scrape (all ~12K codes, ~8-10 hours at 3s/code)
python run_scraper.py cip

# Scrape specific chapters
python run_scraper.py cip --chapters 70 84 85

# Scrape specific codes
python run_scraper.py cip --codes 84714110 85171210 70134900

# Test single code with visible browser
python run_scraper.py cip --test 70134900 --visible

# Only build CTH code list
python run_scraper.py cip --seed

# Export all scraped results to combined JSON + CSV
python run_scraper.py cip --export

# Force re-scrape (clear checkpoint)
python run_scraper.py cip --force

# Environment variables
CIP_REQUEST_DELAY=5      # seconds between requests (default: 3)
CIP_HEADLESS=false        # show browser (default: true)
CIP_PAGE_TIMEOUT=60000    # page load timeout ms (default: 30000)
```

## Dependencies

All in `backend/scraper/requirements.txt`:
- `playwright>=1.40.0` — browser automation (Chromium)
- `requests>=2.31.0` — HTTP for CTH seed downloads
- `pandas>=2.0.0` — CSV export
- `tqdm>=4.66.0` — progress bar
- `beautifulsoup4>=4.12.0` — HTML parsing (legacy scraper)

## Estimated Scrape Times

| Scope | Codes | At 3s/code | At 5s/code |
|-------|-------|-----------|-----------|
| Single chapter | ~120 | ~6 min | ~10 min |
| 5 chapters | ~600 | ~30 min | ~50 min |
| All 98 chapters | ~12,000 | ~10 hours | ~17 hours |

The checkpoint system allows stopping and resuming at any point.
