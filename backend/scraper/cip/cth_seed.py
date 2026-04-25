"""
CTH Seed List Builder.

Downloads and builds the master list of all valid 8-digit Indian CTH codes
from multiple sources (GitHub HSN repo, CBIC PDFs, etc.).
"""

import csv
import json
import logging
import re
import time
from io import StringIO
from pathlib import Path
from typing import Optional

import requests

from .config import (
    CTH_MASTER_FILE,
    HSN_GITHUB_CSV_URL,
    HSN_GITHUB_JSON_URL,
    HSN_PAGES_CSV_URL,
    HSN_PAGES_JSON_URL,
    DATA_DIR,
)

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; CustomsClassifierBot/1.0; research purposes)"


def download_hsn_csv_from_github(url: Optional[str] = None) -> list[dict]:
    """
    Download HSN codes CSV from frontlook-admin/HSN-Code-Classifier repo.
    Returns list of dicts with cth_code, description, chapter.
    """
    url = url or HSN_GITHUB_CSV_URL
    logger.info(f"Downloading HSN CSV from {url}")

    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=60,
        )
        resp.raise_for_status()
        text = resp.text

        reader = csv.DictReader(StringIO(text))
        codes = []
        for row in reader:
            # The CSV may have various column names; try common ones
            code = (
                row.get("HSNCode")
                or row.get("hsn_code")
                or row.get("code")
                or row.get("Code")
                or row.get("HsnCode")
                or ""
            ).strip().replace(".", "")

            description = (
                row.get("Description")
                or row.get("description")
                or row.get("Desc")
                or ""
            ).strip()

            # Only keep 8-digit codes (full CTH)
            if re.match(r"^\d{8}$", code):
                chapter = code[:2]
                # Filter to customs chapters 01-98
                if 1 <= int(chapter) <= 98:
                    codes.append({
                        "cth_code": code,
                        "description": description,
                        "chapter": chapter,
                    })

        logger.info(f"Extracted {len(codes)} 8-digit CTH codes from GitHub CSV")
        return codes

    except Exception as e:
        logger.warning(f"Failed to download GitHub CSV: {e}")
        return []


def download_hsn_json_from_github(url: Optional[str] = None) -> list[dict]:
    """
    Download HSN codes JSON from frontlook-admin/HSN-Code-Classifier repo.
    Fallback if CSV fails.
    """
    url = url or HSN_GITHUB_JSON_URL
    logger.info(f"Downloading HSN JSON from {url}")

    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        codes = []
        # Handle both list-of-dicts and nested formats
        items = data if isinstance(data, list) else data.get("codes", data.get("data", []))

        for item in items:
            if isinstance(item, dict):
                code = str(
                    item.get("HSNCode")
                    or item.get("hsn_code")
                    or item.get("code")
                    or item.get("Code")
                    or item.get("HsnCode")
                    or ""
                ).strip().replace(".", "")

                description = str(
                    item.get("Description")
                    or item.get("description")
                    or item.get("Desc")
                    or ""
                ).strip()
            elif isinstance(item, str):
                code = item.strip().replace(".", "")
                description = ""
            else:
                continue

            if re.match(r"^\d{8}$", code):
                chapter = code[:2]
                if 1 <= int(chapter) <= 98:
                    codes.append({
                        "cth_code": code,
                        "description": description,
                        "chapter": chapter,
                    })

        logger.info(f"Extracted {len(codes)} 8-digit CTH codes from GitHub JSON")
        return codes

    except Exception as e:
        logger.warning(f"Failed to download GitHub JSON: {e}")
        return []


def generate_chapter_codes() -> list[dict]:
    """
    Generate a basic set of CTH codes by creating all possible 4-digit headings
    for chapters 01-98, with common subheading patterns.
    This is a last-resort fallback that generates candidate codes.
    """
    logger.info("Generating candidate CTH codes from chapter structure")
    codes = []
    for chapter in range(1, 99):
        ch = f"{chapter:02d}"
        # Generate headings: chapter + 2-digit heading (01-30 typical range)
        for heading in range(1, 30):
            h4 = f"{ch}{heading:02d}"
            # Common subheading patterns
            for sub in ["0000", "1000", "1010", "1020", "1090", "2000", "9000", "9010", "9090"]:
                code = f"{h4}{sub}"
                if len(code) == 8:
                    codes.append({
                        "cth_code": code,
                        "description": "",
                        "chapter": ch,
                    })
    logger.info(f"Generated {len(codes)} candidate CTH codes")
    return codes


def build_cth_master_list(force_refresh: bool = False) -> list[dict]:
    """
    Build or load the CTH master list.

    Tries sources in order:
    1. Cached file (if exists and not force_refresh)
    2. GitHub CSV
    3. GitHub JSON
    4. Generated candidates (fallback)

    Returns sorted list of unique CTH code dicts.
    """
    # Check cache first
    if not force_refresh and CTH_MASTER_FILE.exists():
        logger.info(f"Loading cached CTH master list from {CTH_MASTER_FILE}")
        with open(CTH_MASTER_FILE, "r", encoding="utf-8") as f:
            codes = json.load(f)
        logger.info(f"Loaded {len(codes)} CTH codes from cache")
        return codes

    # Try GitHub CSV (raw URL)
    codes = download_hsn_csv_from_github()

    # Fallback: GitHub Pages CSV
    if not codes:
        time.sleep(2)
        codes = download_hsn_csv_from_github(url=HSN_PAGES_CSV_URL)

    # Fallback: GitHub JSON (raw URL)
    if not codes:
        time.sleep(2)
        codes = download_hsn_json_from_github()

    # Fallback: GitHub Pages JSON
    if not codes:
        time.sleep(2)
        codes = download_hsn_json_from_github(url=HSN_PAGES_JSON_URL)

    # Last resort: generate candidates
    if not codes:
        codes = generate_chapter_codes()

    # Deduplicate by cth_code
    seen = set()
    unique_codes = []
    for c in codes:
        if c["cth_code"] not in seen:
            seen.add(c["cth_code"])
            unique_codes.append(c)

    # Sort by cth_code
    unique_codes.sort(key=lambda x: x["cth_code"])

    # Save to cache
    CTH_MASTER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CTH_MASTER_FILE, "w", encoding="utf-8") as f:
        json.dump(unique_codes, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(unique_codes)} CTH codes to {CTH_MASTER_FILE}")

    return unique_codes


def load_cth_master_list() -> list[dict]:
    """Load existing CTH master list or build it."""
    return build_cth_master_list(force_refresh=False)


def get_chapters_summary(codes: Optional[list[dict]] = None) -> dict:
    """Get a summary of CTH codes per chapter."""
    if codes is None:
        codes = load_cth_master_list()

    summary = {}
    for c in codes:
        ch = c["chapter"]
        summary[ch] = summary.get(ch, 0) + 1

    return dict(sorted(summary.items()))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    codes = build_cth_master_list(force_refresh=True)
    print(f"\nTotal CTH codes: {len(codes)}")
    summary = get_chapters_summary(codes)
    print(f"Chapters covered: {len(summary)}")
    for ch, count in list(summary.items())[:10]:
        print(f"  Chapter {ch}: {count} codes")
    print("  ...")
