"""File-based cache for BCB benchmark data.

Stores raw API responses as JSON files, one per series code.
Merges new records with existing cache on write.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path(".cache/bcb")


class BenchmarkCacheManager:
    """Simple file-based cache for BCB series data."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._cache_dir = cache_dir or DEFAULT_CACHE_DIR

    def read(
        self,
        series_code: int,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, str]]:
        """Read cached BCB records for a series within a date range.

        Returns raw BCB-format dicts: [{"data": "dd/mm/yyyy", "valor": "..."}]
        """
        path = self._path(series_code)
        if not path.exists():
            return []
        try:
            records = json.loads(path.read_text())
            filtered = []
            for r in records:
                ref_date = date.fromisoformat(r["date"])
                if start_date <= ref_date <= end_date:
                    filtered.append({"data": ref_date.strftime("%d/%m/%Y"), "valor": r["value"]})
            logger.debug("Cache hit: %d records for series %d", len(filtered), series_code)
            return filtered
        except Exception as exc:
            logger.warning("Failed to read cache for series %d: %s", series_code, exc)
            return []

    def write(
        self,
        series_code: int,
        records: list[dict[str, str]],
    ) -> None:
        """Write BCB records to cache, merging with existing data.

        Args:
            series_code: BCB SGS series number.
            records: Raw BCB-format dicts with "data" (dd/mm/yyyy) and "valor".
        """
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            path = self._path(series_code)

            # Normalize to internal format: {"date": "YYYY-MM-DD", "value": "..."}
            new_entries = []
            for r in records:
                try:
                    parts = r["data"].split("/")
                    iso_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
                    new_entries.append({"date": iso_date, "value": r["valor"]})
                except (KeyError, IndexError, ValueError):
                    continue

            # Merge with existing
            existing: list[dict[str, str]] = []
            if path.exists():
                existing = json.loads(path.read_text())

            existing_dates = {r["date"] for r in existing}
            for entry in new_entries:
                if entry["date"] not in existing_dates:
                    existing.append(entry)

            # Sort by date
            existing.sort(key=lambda r: r["date"])
            path.write_text(json.dumps(existing, indent=2))
            logger.debug("Cached %d total records for series %d", len(existing), series_code)
        except Exception as exc:
            logger.warning("Failed to write cache for series %d: %s", series_code, exc)

    def _path(self, series_code: int) -> Path:
        return self._cache_dir / f"series_{series_code}.json"
