"""Concrete repository implementations backed by SQLite (aiosqlite).

Each class satisfies the corresponding Protocol defined in
``market_analysis.domain.interfaces``.  All SQL is parameterised --
no string interpolation.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import aiosqlite

from market_analysis.domain.models import (
    BcbDataPoint,
    CollectionResult,
    CollectionStatus,
    CollectorType,
    ErrorDetail,
    ErrorResult,
    FundMetadata,
    NewsItem,
    Recipient,
    SeriesCode,
)
from market_analysis.infrastructure.database import get_connection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso(dt: datetime | date) -> str:
    """Convert a datetime/date to ISO 8601 string."""
    return dt.isoformat()


# ---------------------------------------------------------------------------
# BcbRepository
# ---------------------------------------------------------------------------


class SqliteBcbRepository:
    """SQLite-backed BCB data repository."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    async def upsert_data_points(self, points: list[BcbDataPoint]) -> int:
        """Insert or update BCB data points. Returns affected row count."""
        if not points:
            return 0

        sql = """
            INSERT INTO bcb_data (series_code, indicator, reference_date, value)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (series_code, reference_date) DO UPDATE SET
                value = excluded.value,
                collected_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
        """
        affected = 0
        async with get_connection(self._db_path) as db:
            for point in points:
                indicator = _indicator_from_series(point.series_code)
                await db.execute(
                    sql,
                    (
                        point.series_code.value,
                        indicator,
                        _iso(point.reference_date),
                        str(point.value),
                    ),
                )
                affected += 1
            await db.commit()
        return affected

    async def get_series(
        self,
        series_code: str,
        start_date: date,
        end_date: date,
    ) -> list[BcbDataPoint]:
        """Retrieve data points for a series within a date range."""
        sql = """
            SELECT series_code, reference_date, value
            FROM bcb_data
            WHERE series_code = ?
              AND reference_date BETWEEN ? AND ?
            ORDER BY reference_date
        """
        async with get_connection(self._db_path) as db:
            cursor = await db.execute(
                sql, (series_code, _iso(start_date), _iso(end_date))
            )
            rows = await cursor.fetchall()
        return [
            BcbDataPoint(
                series_code=SeriesCode(row["series_code"]),
                reference_date=date.fromisoformat(row["reference_date"]),
                value=Decimal(row["value"]),
            )
            for row in rows
        ]

    async def get_latest_date(self, series_code: str) -> date | None:
        """Return the most recent reference_date for a series, or None."""
        sql = """
            SELECT MAX(reference_date) AS latest
            FROM bcb_data
            WHERE series_code = ?
        """
        async with get_connection(self._db_path) as db:
            cursor = await db.execute(sql, (series_code,))
            row = await cursor.fetchone()
        if row and row["latest"]:
            return date.fromisoformat(row["latest"])
        return None


# ---------------------------------------------------------------------------
# NewsRepository
# ---------------------------------------------------------------------------


class SqliteNewsRepository:
    """SQLite-backed news repository."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    async def insert_items(self, items: list[NewsItem]) -> int:
        """Insert news items, skipping duplicates by link. Returns inserted count."""
        if not items:
            return 0

        sql = """
            INSERT OR IGNORE INTO news_data
                (title, link, published_at, description, source)
            VALUES (?, ?, ?, ?, ?)
        """
        inserted = 0
        async with get_connection(self._db_path) as db:
            for item in items:
                cursor = await db.execute(
                    sql,
                    (
                        item.title,
                        item.link,
                        _iso(item.published_at),
                        item.description,
                        item.source,
                    ),
                )
                if cursor.rowcount > 0:
                    inserted += 1
            await db.commit()
        return inserted

    async def get_recent(
        self,
        since: datetime,
        limit: int = 50,
    ) -> list[NewsItem]:
        """Retrieve recent news items ordered by published_at desc."""
        sql = """
            SELECT title, link, published_at, description, source
            FROM news_data
            WHERE published_at >= ?
            ORDER BY published_at DESC
            LIMIT ?
        """
        async with get_connection(self._db_path) as db:
            cursor = await db.execute(sql, (_iso(since), limit))
            rows = await cursor.fetchall()
        return [
            NewsItem(
                title=row["title"],
                link=row["link"],
                published_at=datetime.fromisoformat(row["published_at"]),
                description=row["description"],
                source=row["source"],
            )
            for row in rows
        ]


# ---------------------------------------------------------------------------
# FundRepository
# ---------------------------------------------------------------------------


class SqliteFundRepository:
    """SQLite-backed fund metadata repository."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    async def get_by_cnpj(self, cnpj: str) -> FundMetadata | None:
        """Return fund metadata or None if not found."""
        sql = "SELECT cnpj, name, fund_type, manager FROM funds_metadata WHERE cnpj = ?"
        async with get_connection(self._db_path) as db:
            cursor = await db.execute(sql, (cnpj,))
            row = await cursor.fetchone()
        if row is None:
            return None
        return FundMetadata(
            cnpj=row["cnpj"],
            name=row["name"],
            fund_type=row["fund_type"],
            manager=row["manager"],
        )

    async def upsert(self, fund: FundMetadata) -> None:
        """Insert or update fund metadata."""
        sql = """
            INSERT INTO funds_metadata (cnpj, name, fund_type, manager)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (cnpj) DO UPDATE SET
                name = excluded.name,
                fund_type = excluded.fund_type,
                manager = excluded.manager,
                updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
        """
        async with get_connection(self._db_path) as db:
            await db.execute(
                sql, (fund.cnpj, fund.name, fund.fund_type, fund.manager)
            )
            await db.commit()


# ---------------------------------------------------------------------------
# RecipientRepository
# ---------------------------------------------------------------------------


class SqliteRecipientRepository:
    """SQLite-backed recipient repository."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    async def get_active(self) -> list[Recipient]:
        """Return all active recipients."""
        sql = "SELECT name, email, active FROM recipients WHERE active = 1"
        async with get_connection(self._db_path) as db:
            cursor = await db.execute(sql)
            rows = await cursor.fetchall()
        return [
            Recipient(name=row["name"], email=row["email"], active=True)
            for row in rows
        ]


# ---------------------------------------------------------------------------
# CollectionMetadataRepository
# ---------------------------------------------------------------------------


class SqliteCollectionMetadataRepository:
    """SQLite-backed collection run tracking."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    async def record_run(
        self,
        result: CollectionResult | ErrorResult,
    ) -> None:
        """Record the outcome of a collection run."""
        if isinstance(result, CollectionResult):
            sql = """
                INSERT INTO collection_metadata
                    (collector_type, status, started_at, finished_at,
                     items_count, duration_secs)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            finished = datetime.utcnow()
            async with get_connection(self._db_path) as db:
                await db.execute(
                    sql,
                    (
                        result.collector_type.value,
                        result.status.value,
                        _iso(result.collected_at),
                        _iso(finished),
                        result.items_count,
                        result.duration_seconds,
                    ),
                )
                await db.commit()
        else:
            sql = """
                INSERT INTO collection_metadata
                    (collector_type, status, started_at, finished_at,
                     items_count, duration_secs, retry_count,
                     error_code, error_message, error_context)
                VALUES (?, ?, ?, ?, 0, 0, ?, ?, ?, ?)
            """
            finished = datetime.utcnow()
            ctx = json.dumps(result.error.context) if result.error.context else None
            async with get_connection(self._db_path) as db:
                await db.execute(
                    sql,
                    (
                        result.collector_type.value,
                        result.status.value,
                        _iso(result.attempted_at),
                        _iso(finished),
                        result.attempts,
                        result.error.code,
                        result.error.message,
                        ctx,
                    ),
                )
                await db.commit()

    async def get_last_success(
        self,
        collector_type: CollectorType,
    ) -> datetime | None:
        """Return timestamp of last successful run, or None."""
        sql = """
            SELECT finished_at
            FROM collection_metadata
            WHERE collector_type = ? AND status = 'success'
            ORDER BY finished_at DESC
            LIMIT 1
        """
        async with get_connection(self._db_path) as db:
            cursor = await db.execute(sql, (collector_type.value,))
            row = await cursor.fetchone()
        if row and row["finished_at"]:
            return datetime.fromisoformat(row["finished_at"])
        return None

    async def get_recent_errors(
        self,
        collector_type: CollectorType,
        limit: int = 10,
    ) -> list[ErrorResult]:
        """Return recent error results for diagnostics."""
        sql = """
            SELECT collector_type, status, started_at, retry_count,
                   error_code, error_message, error_context
            FROM collection_metadata
            WHERE collector_type = ? AND status = 'failure'
            ORDER BY started_at DESC
            LIMIT ?
        """
        async with get_connection(self._db_path) as db:
            cursor = await db.execute(sql, (collector_type.value, limit))
            rows = await cursor.fetchall()
        results: list[ErrorResult] = []
        for row in rows:
            ctx = json.loads(row["error_context"]) if row["error_context"] else {}
            results.append(
                ErrorResult(
                    collector_type=CollectorType(row["collector_type"]),
                    attempted_at=datetime.fromisoformat(row["started_at"]),
                    error=ErrorDetail(
                        code=row["error_code"] or "UNKNOWN",
                        message=row["error_message"] or "",
                        context=ctx,
                    ),
                    attempts=row["retry_count"],
                    status=CollectionStatus.FAILURE,
                )
            )
        return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SERIES_TO_INDICATOR: dict[str, str] = {
    "432": "SELIC",
    "4389": "CDI",
    "433": "IPCA",
}


def _indicator_from_series(code: SeriesCode) -> str:
    """Map a SeriesCode to its indicator name for the DB column."""
    return _SERIES_TO_INDICATOR[code.value]
