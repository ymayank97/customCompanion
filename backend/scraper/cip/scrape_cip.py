"""
CIP Scraper Orchestrator.

Main entry point for scraping all CTH codes from the CIP portal.
Supports checkpoint/resume, batching by chapter, and graceful shutdown.
"""

import json
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import (
    CIP_RESULTS_DIR,
    CHECKPOINT_FILE,
    ERROR_LOG_FILE,
    REQUEST_DELAY,
    BATCH_SIZE,
    CHAPTER_RANGE,
)
from .cth_seed import build_cth_master_list, get_chapters_summary
from .cip_client import CIPBrowserClient
from .models import CIPRecord

logger = logging.getLogger(__name__)


class CIPScraper:
    """
    Orchestrates scraping of all CTH codes from CIP portal.

    Features:
    - Checkpoint/resume: saves progress after each batch
    - Chapter-based output: one JSON file per chapter
    - Graceful shutdown: Ctrl+C saves progress before exit
    - Progress tracking with tqdm
    - Error logging
    """

    def __init__(
        self,
        headless: bool = True,
        chapters: Optional[list[int]] = None,
        cth_codes: Optional[list[str]] = None,
    ):
        """
        Args:
            headless: Run browser in headless mode
            chapters: Specific chapters to scrape (default: all 01-98)
            cth_codes: Specific CTH codes to scrape (overrides chapters)
        """
        self.headless = headless
        self.target_chapters = chapters
        self.target_codes = cth_codes
        self.client: Optional[CIPBrowserClient] = None
        self.checkpoint: dict = {}
        self.results: dict[str, list[dict]] = {}  # chapter -> list of records
        self._shutdown_requested = False
        self._stats = {
            "total": 0,
            "scraped": 0,
            "skipped": 0,
            "errors": 0,
            "start_time": None,
        }

    def _setup_signal_handlers(self):
        """Handle Ctrl+C gracefully."""
        def handler(signum, frame):
            if self._shutdown_requested:
                logger.warning("Force shutdown requested")
                sys.exit(1)
            logger.info("\nShutdown requested. Saving progress...")
            self._shutdown_requested = True

        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def _load_checkpoint(self) -> set[str]:
        """Load checkpoint of already-scraped CTH codes."""
        if CHECKPOINT_FILE.exists():
            try:
                with open(CHECKPOINT_FILE, "r") as f:
                    self.checkpoint = json.load(f)
                completed = set(self.checkpoint.get("completed_codes", []))
                logger.info(f"Loaded checkpoint: {len(completed)} codes already scraped")
                return completed
            except Exception as e:
                logger.warning(f"Could not load checkpoint: {e}")
        return set()

    def _save_checkpoint(self, completed_codes: set[str]):
        """Save checkpoint to disk."""
        self.checkpoint["completed_codes"] = sorted(completed_codes)
        self.checkpoint["last_updated"] = datetime.now().isoformat()
        self.checkpoint["stats"] = self._stats.copy()
        self.checkpoint["stats"]["start_time"] = str(self.checkpoint["stats"]["start_time"])

        with open(CHECKPOINT_FILE, "w") as f:
            json.dump(self.checkpoint, f, indent=2)
        logger.debug(f"Checkpoint saved: {len(completed_codes)} codes")

    def _save_chapter_results(self, chapter: str, records: list[dict]):
        """Save results for a chapter to disk."""
        outfile = CIP_RESULTS_DIR / f"chapter_{chapter}.json"
        existing = []
        if outfile.exists():
            try:
                with open(outfile, "r") as f:
                    existing = json.load(f)
            except Exception:
                pass

        # Merge: update existing records, append new ones
        existing_codes = {r["cth_code"] for r in existing}
        for rec in records:
            if rec["cth_code"] in existing_codes:
                # Update existing
                for i, e in enumerate(existing):
                    if e["cth_code"] == rec["cth_code"]:
                        existing[i] = rec
                        break
            else:
                existing.append(rec)

        existing.sort(key=lambda x: x["cth_code"])

        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(existing)} records to {outfile}")

    def _log_error(self, cth_code: str, error: str):
        """Append error to log file."""
        try:
            with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "function": "scrape_cip",
                    "cth_code": cth_code,
                    "error": error,
                }) + "\n")
        except Exception:
            pass

    def _get_codes_to_scrape(self) -> list[dict]:
        """Build the list of CTH codes to scrape."""
        if self.target_codes:
            return [{"cth_code": c, "description": "", "chapter": c[:2]} for c in self.target_codes]

        all_codes = build_cth_master_list()

        if self.target_chapters:
            chapters_str = {f"{c:02d}" for c in self.target_chapters}
            all_codes = [c for c in all_codes if c["chapter"] in chapters_str]

        return all_codes

    def run(self):
        """
        Run the full scraping pipeline.

        1. Build/load CTH master list
        2. Load checkpoint (skip already scraped codes)
        3. Launch browser
        4. Iterate through codes, scrape each one
        5. Save results per chapter, checkpoint regularly
        6. Handle shutdown gracefully
        """
        self._setup_signal_handlers()
        self._stats["start_time"] = datetime.now()

        # Step 1: Get codes to scrape
        all_codes = self._get_codes_to_scrape()
        self._stats["total"] = len(all_codes)
        logger.info(f"Total CTH codes to process: {len(all_codes)}")

        # Step 2: Load checkpoint
        completed = self._load_checkpoint()
        remaining = [c for c in all_codes if c["cth_code"] not in completed]
        self._stats["skipped"] = len(all_codes) - len(remaining)
        logger.info(f"Remaining after checkpoint: {len(remaining)} codes")

        if not remaining:
            logger.info("All codes already scraped! Use --force to re-scrape.")
            return

        # Step 3: Progress bar
        try:
            from tqdm import tqdm
            progress = tqdm(total=len(remaining), desc="Scraping CIP", unit="code")
        except ImportError:
            progress = None

        # Step 4: Launch browser and scrape
        chapter_buffer: dict[str, list[dict]] = {}
        batch_count = 0

        self.client = CIPBrowserClient(headless=self.headless)

        try:
            self.client.start()

            for code_info in remaining:
                if self._shutdown_requested:
                    break

                cth_code = code_info["cth_code"]
                chapter = code_info["chapter"]

                # Scrape
                record = self.client.scrape_cth(cth_code)
                record_dict = record.to_dict()

                # Track results
                if record.error:
                    self._stats["errors"] += 1
                    self._log_error(cth_code, record.error)
                    logger.warning(f"Error for {cth_code}: {record.error}")
                else:
                    self._stats["scraped"] += 1

                # Buffer by chapter
                if chapter not in chapter_buffer:
                    chapter_buffer[chapter] = []
                chapter_buffer[chapter].append(record_dict)

                # Mark completed
                completed.add(cth_code)
                batch_count += 1

                # Save checkpoint every BATCH_SIZE codes
                if batch_count >= BATCH_SIZE:
                    self._save_checkpoint(completed)
                    for ch, records in chapter_buffer.items():
                        self._save_chapter_results(ch, records)
                    chapter_buffer.clear()
                    batch_count = 0

                if progress:
                    progress.update(1)
                    progress.set_postfix({
                        "ok": self._stats["scraped"],
                        "err": self._stats["errors"],
                        "ch": chapter,
                    })

                # Rate limit
                time.sleep(REQUEST_DELAY)

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # Save remaining buffer
            logger.info("Saving final results...")
            self._save_checkpoint(completed)
            for ch, records in chapter_buffer.items():
                self._save_chapter_results(ch, records)

            if progress:
                progress.close()

            # Stop browser
            if self.client:
                self.client.stop()

            # Print summary
            self._print_summary()

    def _print_summary(self):
        """Print scraping summary."""
        elapsed = datetime.now() - self._stats["start_time"] if self._stats["start_time"] else None
        print("\n" + "=" * 60)
        print("CIP SCRAPING SUMMARY")
        print("=" * 60)
        print(f"Total CTH codes:   {self._stats['total']}")
        print(f"Scraped (success): {self._stats['scraped']}")
        print(f"Skipped (cached):  {self._stats['skipped']}")
        print(f"Errors:            {self._stats['errors']}")
        if elapsed:
            print(f"Duration:          {elapsed}")
            total_done = self._stats["scraped"] + self._stats["errors"]
            if total_done > 0:
                avg = elapsed.total_seconds() / total_done
                remaining_est = avg * (self._stats["total"] - self._stats["skipped"] - total_done)
                print(f"Avg per code:      {avg:.1f}s")
                if remaining_est > 0:
                    print(f"Est. remaining:    {remaining_est/3600:.1f} hours")
        print(f"Results saved to:  {CIP_RESULTS_DIR}")
        print(f"Checkpoint:        {CHECKPOINT_FILE}")
        print("=" * 60)

    def test(self, cth_code: str = "84714110") -> CIPRecord:
        """
        Test scraping a single CTH code.

        Args:
            cth_code: CTH code to test with (default: 84714110 = Laptops)

        Returns:
            CIPRecord with scraped data
        """
        logger.info(f"Testing CIP scraper with CTH {cth_code}")

        with CIPBrowserClient(headless=self.headless) as client:
            # Test connection first
            if not client.test_connection():
                logger.error("CIP portal not accessible")
                return CIPRecord(cth_code=cth_code, error="Portal not accessible")

            record = client.scrape_cth(cth_code)

            print(f"\n{'=' * 60}")
            print(f"TEST RESULT: CTH {cth_code}")
            print(f"{'=' * 60}")
            print(f"Page title:  {record.page_title}")
            print(f"Page URL:    {record.page_url}")
            print(f"Tables:      {len(record.tables)}")
            print(f"Text length: {len(record.text_content)} chars")
            print(f"Error:       {record.error or 'None'}")

            if record.raw_data:
                print(f"\nRaw data keys: {list(record.raw_data.keys())}")
                if record.raw_data.get("tables"):
                    for i, t in enumerate(record.raw_data["tables"]):
                        print(f"\n  Table {i+1}: {len(t.get('rows', []))} rows")
                        if t.get("headers"):
                            print(f"  Headers: {t['headers']}")
                if record.raw_data.get("key_value_pairs"):
                    print(f"\n  Key-value pairs:")
                    for kv in record.raw_data["key_value_pairs"][:10]:
                        print(f"    {kv['key']}: {kv['value']}")

            if record.text_content:
                print(f"\nFirst 500 chars of text:")
                print(record.text_content[:500])

            return record


def export_all_results(output_file: Optional[str] = None) -> Path:
    """
    Combine all chapter JSON files into a single output file.

    Args:
        output_file: Output path (default: data/cip_all_results.json)

    Returns:
        Path to the output file
    """
    if output_file:
        outpath = Path(output_file)
    else:
        outpath = CIP_RESULTS_DIR.parent / "cip_all_results.json"

    all_records = []
    for chapter_file in sorted(CIP_RESULTS_DIR.glob("chapter_*.json")):
        try:
            with open(chapter_file, "r") as f:
                records = json.load(f)
            all_records.extend(records)
            logger.info(f"Loaded {len(records)} records from {chapter_file.name}")
        except Exception as e:
            logger.warning(f"Error loading {chapter_file}: {e}")

    all_records.sort(key=lambda x: x.get("cth_code", ""))

    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(all_records, f, indent=2, ensure_ascii=False)

    logger.info(f"Exported {len(all_records)} total records to {outpath}")
    return outpath


def export_to_csv(output_file: Optional[str] = None) -> Path:
    """Export all results to CSV format."""
    import pandas as pd

    if output_file:
        outpath = Path(output_file)
    else:
        outpath = CIP_RESULTS_DIR.parent / "cip_all_results.csv"

    all_records = []
    for chapter_file in sorted(CIP_RESULTS_DIR.glob("chapter_*.json")):
        try:
            with open(chapter_file, "r") as f:
                records = json.load(f)
            for rec in records:
                flat = {
                    "cth_code": rec.get("cth_code"),
                    "page_title": rec.get("page_title"),
                    "text_content_preview": rec.get("text_content", "")[:500],
                    "num_tables": len(rec.get("tables", [])),
                    "error": rec.get("error", ""),
                    "scrape_timestamp": rec.get("scrape_timestamp"),
                }
                all_records.append(flat)
        except Exception as e:
            logger.warning(f"Error loading {chapter_file}: {e}")

    df = pd.DataFrame(all_records)
    df.to_csv(outpath, index=False, encoding="utf-8")
    logger.info(f"Exported {len(df)} records to {outpath}")
    return outpath


# === CLI Entry Point ===

def main():
    import argparse

    parser = argparse.ArgumentParser(description="CIP Portal Scraper")
    parser.add_argument("--test", type=str, nargs="?", const="84714110",
                        help="Test with a single CTH code (default: 84714110)")
    parser.add_argument("--chapters", type=int, nargs="+",
                        help="Specific chapters to scrape (e.g., 70 84 85)")
    parser.add_argument("--codes", type=str, nargs="+",
                        help="Specific CTH codes to scrape")
    parser.add_argument("--visible", action="store_true",
                        help="Run browser in visible (non-headless) mode")
    parser.add_argument("--export", action="store_true",
                        help="Export all results to combined JSON/CSV")
    parser.add_argument("--force", action="store_true",
                        help="Force re-scrape (ignore checkpoint)")
    parser.add_argument("--seed", action="store_true",
                        help="Only build/refresh the CTH master list")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.seed:
        codes = build_cth_master_list(force_refresh=True)
        summary = get_chapters_summary(codes)
        print(f"CTH master list: {len(codes)} codes across {len(summary)} chapters")
        return

    if args.export:
        json_path = export_all_results()
        csv_path = export_to_csv()
        print(f"Exported to:\n  JSON: {json_path}\n  CSV:  {csv_path}")
        return

    if args.force and CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        logger.info("Checkpoint cleared")

    headless = not args.visible

    if args.test:
        scraper = CIPScraper(headless=headless)
        scraper.test(args.test)
        return

    scraper = CIPScraper(
        headless=headless,
        chapters=args.chapters,
        cth_codes=args.codes,
    )
    scraper.run()


if __name__ == "__main__":
    main()
