"""Tests for the async News collector."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock

import httpx
import pytest

from market_analysis.domain.models import (
    CollectionResult,
    CollectionStatus,
    CollectorType,
    ErrorResult,
    NewsItem,
    ValidationResult,
)
from market_analysis.infrastructure.news_collector import NewsCollector

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

RSS_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Nubank - Google News</title>
    {items}
  </channel>
</rss>
"""

RSS_ITEM_TEMPLATE = """\
<item>
  <title>{title}</title>
  <link>{link}</link>
  <pubDate>{pub_date}</pubDate>
  <description>{description}</description>
  <source url="https://example.com">{source}</source>
</item>
"""


def _make_rss_xml(
    items: list[dict[str, str]],
) -> bytes:
    """Build fake RSS XML bytes."""
    items_xml = "\n".join(
        RSS_ITEM_TEMPLATE.format(**item) for item in items
    )
    return RSS_TEMPLATE.format(items=items_xml).encode("utf-8")


SAMPLE_RSS_ITEMS = [
    {
        "title": "Nubank lanca nova funcionalidade",
        "link": "https://example.com/news/1",
        "pub_date": "Mon, 05 Jan 2026 10:00:00 GMT",
        "description": "Nubank announced a new feature",
        "source": "Folha",
    },
    {
        "title": "Nu Reserva Planejada atinge novo marco",
        "link": "https://example.com/news/2",
        "pub_date": "Tue, 06 Jan 2026 14:30:00 GMT",
        "description": "Fund reaches new milestone",
        "source": "Valor Economico",
    },
    {
        "title": "Mercado financeiro em alta",
        "link": "https://example.com/news/3",
        "pub_date": "Wed, 07 Jan 2026 08:00:00 GMT",
        "description": "Markets are up",
        "source": "InfoMoney",
    },
]


def _mock_response(
    data: bytes, status: int = 200
) -> httpx.Response:
    """Create a mock httpx.Response with raw content."""
    return httpx.Response(
        status_code=status,
        content=data,
        request=httpx.Request("GET", "https://fake"),
    )


# ---------------------------------------------------------------------------
# collector_type
# ---------------------------------------------------------------------------


class TestCollectorType:
    def test_returns_news(self) -> None:
        collector = NewsCollector()
        assert collector.collector_type == CollectorType.NEWS


# ---------------------------------------------------------------------------
# collect - happy path
# ---------------------------------------------------------------------------


class TestCollectHappyPath:
    @pytest.mark.asyncio
    async def test_collects_news(self) -> None:
        """Valid RSS feed -> SUCCESS with items."""
        rss_bytes = _make_rss_xml(SAMPLE_RSS_ITEMS)
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response(rss_bytes))

        collector = NewsCollector(client=client)
        result = await collector.collect(date(2026, 1, 1), date(2026, 1, 31))

        assert isinstance(result, CollectionResult)
        assert result.status == CollectionStatus.SUCCESS
        assert result.items_count == 3
        assert result.collector_type == CollectorType.NEWS

    @pytest.mark.asyncio
    async def test_filters_by_date_range(self) -> None:
        """Only items within date range are included."""
        rss_bytes = _make_rss_xml(SAMPLE_RSS_ITEMS)
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response(rss_bytes))

        collector = NewsCollector(client=client)
        # Only Jan 5-6
        result = await collector.collect(date(2026, 1, 5), date(2026, 1, 6))

        assert isinstance(result, CollectionResult)
        assert result.items_count == 2

    @pytest.mark.asyncio
    async def test_respects_max_items(self) -> None:
        """Limits results to max_items."""
        rss_bytes = _make_rss_xml(SAMPLE_RSS_ITEMS)
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response(rss_bytes))

        collector = NewsCollector(max_items=1, client=client)
        result = await collector.collect(date(2026, 1, 1), date(2026, 1, 31))

        assert isinstance(result, CollectionResult)
        assert result.items_count == 1

    @pytest.mark.asyncio
    async def test_empty_feed(self) -> None:
        """Empty RSS feed returns SUCCESS with 0 items."""
        rss_bytes = _make_rss_xml([])
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response(rss_bytes))

        collector = NewsCollector(client=client)
        result = await collector.collect(date(2026, 1, 1), date(2026, 1, 31))

        assert isinstance(result, CollectionResult)
        assert result.status == CollectionStatus.SUCCESS
        assert result.items_count == 0


# ---------------------------------------------------------------------------
# collect - errors
# ---------------------------------------------------------------------------


class TestCollectErrors:
    @pytest.mark.asyncio
    async def test_connection_error(self) -> None:
        """Connection error -> ErrorResult."""
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        collector = NewsCollector(client=client)
        result = await collector.collect(date(2026, 1, 1), date(2026, 1, 31))

        assert isinstance(result, ErrorResult)
        assert result.status == CollectionStatus.FAILURE
        assert result.error.code == "NEWS_FETCH_ERROR"
        assert result.error.retryable is True

    @pytest.mark.asyncio
    async def test_http_500_error(self) -> None:
        """HTTP 500 -> ErrorResult."""
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Server Error",
                request=httpx.Request("GET", "https://fake"),
                response=httpx.Response(500),
            )
        )

        collector = NewsCollector(client=client)
        result = await collector.collect(date(2026, 1, 1), date(2026, 1, 31))

        assert isinstance(result, ErrorResult)
        assert result.error.retryable is True


# ---------------------------------------------------------------------------
# collect - deduplication
# ---------------------------------------------------------------------------


class TestDeduplication:
    @pytest.mark.asyncio
    async def test_removes_duplicates(self) -> None:
        """Duplicate links are removed."""
        duped_items = SAMPLE_RSS_ITEMS + [SAMPLE_RSS_ITEMS[0]]
        rss_bytes = _make_rss_xml(duped_items)
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response(rss_bytes))

        collector = NewsCollector(client=client)
        result = await collector.collect(date(2026, 1, 1), date(2026, 1, 31))

        assert isinstance(result, CollectionResult)
        assert result.items_count == 3  # Not 4


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


class TestValidate:
    @pytest.mark.asyncio
    async def test_valid_items(self) -> None:
        collector = NewsCollector()
        items = [
            NewsItem(
                title="Test News",
                link="https://example.com/1",
                published_at=datetime(2026, 1, 5, 10, 0, tzinfo=UTC),
                description="A test news item",
                source="TestSource",
            ),
        ]
        result = await collector.validate(items)

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.items_accepted == 1

    @pytest.mark.asyncio
    async def test_invalid_link(self) -> None:
        collector = NewsCollector()
        items = [
            NewsItem(
                title="Test",
                link="not-a-url",
                published_at=datetime(2026, 1, 5, 10, 0, tzinfo=UTC),
                description="",
                source="TestSource",
            ),
        ]
        result = await collector.validate(items)

        assert result.is_valid is False
        assert result.items_rejected == 1

    @pytest.mark.asyncio
    async def test_empty_list(self) -> None:
        collector = NewsCollector()
        result = await collector.validate([])
        assert result.is_valid is True
        assert result.items_accepted == 0


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy(self) -> None:
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(
            return_value=_mock_response(b"<rss></rss>")
        )

        collector = NewsCollector(client=client)
        assert await collector.health_check() is True

    @pytest.mark.asyncio
    async def test_unhealthy(self) -> None:
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        collector = NewsCollector(client=client)
        assert await collector.health_check() is False
