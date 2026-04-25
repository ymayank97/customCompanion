"""
Data models for CIP scraper output.
Raw data collection — no preprocessing, store everything the portal returns.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


@dataclass
class CIPRecord:
    """A single CTH record scraped from the CIP portal."""
    cth_code: str
    raw_data: dict = field(default_factory=dict)
    page_title: str = ""
    page_url: str = ""
    tables: list = field(default_factory=list)
    text_content: str = ""
    scrape_timestamp: str = ""
    error: str = ""

    def __post_init__(self):
        if not self.scrape_timestamp:
            self.scrape_timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "CIPRecord":
        return CIPRecord(**{k: v for k, v in d.items() if k in CIPRecord.__dataclass_fields__})


def parse_html_table(table_element) -> list[dict[str, Any]]:
    """
    Parse a Playwright ElementHandle table into a list of row dicts.
    Returns list of dicts with header keys.
    """
    rows = []
    # Will be called with already-extracted data from Playwright
    return rows
