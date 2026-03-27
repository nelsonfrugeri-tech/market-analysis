"""Google News RSS async collector.

Implements the BaseCollector protocol defined in domain/interfaces.py.
Fetches news from Google News RSS feed using httpx + feedparser.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote

import feedparser
import httpx

from market_analysis.domain.models import (
    CollectionResult,
    CollectionStatus,
    CollectorType,
    ErrorDetail,
    ErrorResult,
    NewsItem,
    ValidationResult,
)
from market_analysis.domain.schemas import NewsRssEntry

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = (
    "https://news.google.com/rss/search"
    "?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
)
DEFAULT_TIMEOUT = 15
DEFAULT_MAX_ITEMS = 20
MIN_REQUEST_INTERVAL = 2.0  # seconds between requests (rate limiting)


class NewsCollector:
    """Async collector for Google News RSS feed.

    Satisfies the BaseCollector protocol:
      - collector_type -> CollectorType.NEWS
      - collect(start_date, end_date) -> CollectionResult | ErrorResult
      - validate(items) -> ValidationResult
      - health_check() -> bool
    """

    def __init__(
        self,
        query: str = "Nubank Nu Reserva Planejada",
        max_items: int = DEFAULT_MAX_ITEMS,
        timeout: int = DEFAULT_TIMEOUT,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._query = query
        self._max_items = max_items
        self._timeout = timeout
        self._external_client = client
        self._last_request_time: float = 0.0
        self._seen_links: set[str] = set()
        self._last_collected: list[NewsItem] = []

    @property
    def last_collected(self) -> list[NewsItem]:
        """Items from the most recent collect() call, for persistence."""
        return list(self._last_collected)

    @property
    def collector_type(self) -> CollectorType:
        return CollectorType.NEWS

    async def collect(
        self,
        start_date: date,
        end_date: date,
    ) -> CollectionResult | ErrorResult:
        """Fetch news from Google News RSS for the given date range."""
        started_at = datetime.now(UTC)

        self._last_collected = []

        try:
            await self._respect_rate_limit()
            raw_xml = await self._fetch_rss()
            items = self._parse_feed(raw_xml, start_date, end_date)
            items = self._deduplicate(items)
            items = items[: self._max_items]
        except Exception as exc:
            finished_at = datetime.now(UTC)
            return ErrorResult(
                collector_type=CollectorType.NEWS,
                attempted_at=finished_at,
                error=ErrorDetail(
                    code="NEWS_FETCH_ERROR",
                    message=str(exc),
                    retryable=True,
                ),
                attempts=1,
                status=CollectionStatus.FAILURE,
            )

        finished_at = datetime.now(UTC)
        duration = (finished_at - started_at).total_seconds()

        self._last_collected = items

        if not items:
            return CollectionResult(
                collector_type=CollectorType.NEWS,
                collected_at=finished_at,
                items_count=0,
                duration_seconds=duration,
                status=CollectionStatus.SUCCESS,
            )

        return CollectionResult(
            collector_type=CollectorType.NEWS,
            collected_at=finished_at,
            items_count=len(items),
            duration_seconds=duration,
            status=CollectionStatus.SUCCESS,
        )

    async def validate(
        self,
        items: list[NewsItem],  # type: ignore[override]
    ) -> ValidationResult:
        """Validate news items using Pydantic schema."""
        errors: list[str] = []
        warnings: list[str] = []
        accepted = 0
        rejected = 0

        for item in items:
            try:
                NewsRssEntry(
                    title=item.title,
                    link=item.link,
                    published=item.published_at,
                    description=item.description,
                    source=item.source,
                )
                accepted += 1
            except Exception as exc:
                errors.append(f"Invalid news item '{item.title[:50]}': {exc}")
                rejected += 1

        return ValidationResult(
            is_valid=rejected == 0,
            errors=errors,
            warnings=warnings,
            items_accepted=accepted,
            items_rejected=rejected,
        )

    async def health_check(self) -> bool:
        """Check if Google News RSS is reachable."""
        url = GOOGLE_NEWS_RSS.format(query=quote("test"))
        try:
            async with self._get_client() as client:
                resp = await client.get(url, timeout=10)
                return resp.status_code == 200
        except Exception:
            return False

    # -----------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------

    def _get_client(self) -> httpx.AsyncClient | _NoCloseClient:
        """Return an httpx client."""
        if self._external_client is not None:
            return _NoCloseClient(self._external_client)
        return httpx.AsyncClient(
            headers={"User-Agent": "MarketAnalysis/1.0"},
            timeout=self._timeout,
        )

    async def _respect_rate_limit(self) -> None:
        """Enforce minimum interval between requests."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < MIN_REQUEST_INTERVAL and self._last_request_time > 0:
            import asyncio

            await asyncio.sleep(MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.monotonic()

    async def _fetch_rss(self) -> bytes:
        """Fetch the raw RSS XML bytes."""
        url = GOOGLE_NEWS_RSS.format(query=quote(self._query))
        logger.info("Fetching Google News RSS: %s", self._query)

        async with self._get_client() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    def _parse_feed(
        self,
        xml_bytes: bytes,
        start_date: date,
        end_date: date,
    ) -> list[NewsItem]:
        """Parse RSS feed and filter by date range."""
        feed = feedparser.parse(xml_bytes)
        items: list[NewsItem] = []

        for entry in feed.entries:
            try:
                published_at = self._parse_pub_date(entry)
                if published_at is None:
                    continue

                pub_date = published_at.date()
                if pub_date < start_date or pub_date > end_date:
                    continue

                source = getattr(entry, "source", {})
                source_name = (
                    source.get("title", "Unknown")
                    if isinstance(source, dict)
                    else "Unknown"
                )

                items.append(
                    NewsItem(
                        title=entry.get("title", ""),
                        link=entry.get("link", ""),
                        published_at=published_at,
                        description=entry.get("summary", ""),
                        source=source_name,
                    )
                )
            except Exception as exc:
                logger.debug("Skipping RSS entry: %s", exc)

        # Sort by date descending
        items.sort(key=lambda n: n.published_at, reverse=True)
        return items

    def _parse_pub_date(self, entry: Any) -> datetime | None:
        """Parse publication date from an RSS entry."""
        pub_date_str = entry.get("published", "")
        if not pub_date_str:
            return None
        try:
            return parsedate_to_datetime(pub_date_str)
        except (ValueError, TypeError):
            return None

    def _deduplicate(self, items: list[NewsItem]) -> list[NewsItem]:
        """Remove duplicate news items by link hash."""
        unique: list[NewsItem] = []
        for item in items:
            link_hash = hashlib.md5(item.link.encode()).hexdigest()
            if link_hash not in self._seen_links:
                self._seen_links.add(link_hash)
                unique.append(item)
        return unique


class _NoCloseClient:
    """Wraps an externally-owned httpx.AsyncClient to prevent closing it."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def __aenter__(self) -> httpx.AsyncClient:
        return self._client

    async def __aexit__(self, *args: Any) -> None:
        pass
