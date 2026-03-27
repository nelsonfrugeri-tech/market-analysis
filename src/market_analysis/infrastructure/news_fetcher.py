"""Synchronous Google News RSS fetcher for report generation.

Fetches recent Nubank-related news from Google News RSS feed.
Lightweight sync module for US-004 (PDF report pipeline).
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
DEFAULT_TIMEOUT = 15


@dataclass(frozen=True, slots=True)
class NewsItem:
    """A single news item from Google News RSS."""

    title: str
    link: str
    pub_date: datetime
    source: str


class NewsFetchError(Exception):
    """Raised when news fetching fails."""


def _parse_rss(xml_bytes: bytes) -> list[NewsItem]:
    """Parse Google News RSS XML into NewsItem list."""
    root = ET.fromstring(xml_bytes)
    items: list[NewsItem] = []

    for item_el in root.iter("item"):
        title = item_el.findtext("title", "")
        link = item_el.findtext("link", "")
        pub_date_str = item_el.findtext("pubDate", "")
        source_el = item_el.find("source")
        source = source_el.text if source_el is not None and source_el.text else "Unknown"

        try:
            pub_date = parsedate_to_datetime(pub_date_str)
        except (ValueError, TypeError):
            pub_date = datetime.now()

        items.append(
            NewsItem(
                title=title,
                link=link,
                pub_date=pub_date,
                source=source,
            )
        )

    return items


def collect_news(
    query: str = "Nubank Nu Reserva Planejada",
    max_items: int = 10,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[NewsItem]:
    """Collect recent news from Google News RSS.

    Args:
        query: Search query for Google News.
        max_items: Maximum number of items to return.
        timeout: HTTP timeout in seconds.

    Returns:
        List of NewsItem sorted by pub_date descending.

    Raises:
        NewsFetchError: If fetching or parsing fails.
    """
    url = GOOGLE_NEWS_RSS.format(query=quote(query))
    logger.info("Fetching news from Google RSS: %s", query)

    req = Request(url, headers={"User-Agent": "MarketAnalysis/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = resp.read()
    except Exception as exc:
        raise NewsFetchError(f"Failed to fetch Google News: {exc}") from exc

    try:
        items = _parse_rss(data)
    except ET.ParseError as exc:
        raise NewsFetchError(f"Failed to parse RSS XML: {exc}") from exc

    items.sort(key=lambda n: n.pub_date, reverse=True)
    return items[:max_items]
