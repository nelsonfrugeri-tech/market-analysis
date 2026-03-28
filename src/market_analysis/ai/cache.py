"""File-based cache for LLM explanations."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path(".cache/llm_explanations")
DEFAULT_TTL_HOURS = 72


class ExplanationCache:
    """Persistent file-based cache keyed by metric + rounded value + period.

    Each entry is a JSON file named by the SHA-256 of the cache key.
    TTL-based expiration avoids serving stale explanations forever.
    """

    def __init__(
        self,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        ttl_hours: float = DEFAULT_TTL_HOURS,
    ) -> None:
        self._dir = cache_dir
        self._ttl_seconds = ttl_hours * 3600

    @staticmethod
    def _build_key(metric_name: str, value: float, period: str) -> str:
        """Deterministic key: metric + value rounded to 2dp + period."""
        raw = f"{metric_name}:{round(value, 2)}:{period}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(
        self,
        metric_name: str,
        value: float,
        period: str,
    ) -> Optional[str]:
        """Return cached explanation or None."""
        key = self._build_key(metric_name, value, period)
        path = self._dir / f"{key}.json"

        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            created = data.get("created_at", 0)
            if time.time() - created > self._ttl_seconds:
                path.unlink(missing_ok=True)
                return None
            return data.get("text")
        except Exception as exc:
            logger.debug("Cache read error for %s: %s", key, exc)
            return None

    def put(
        self,
        metric_name: str,
        value: float,
        period: str,
        text: str,
        *,
        provider: str = "",
        model: str = "",
    ) -> None:
        """Store an explanation."""
        self._dir.mkdir(parents=True, exist_ok=True)
        key = self._build_key(metric_name, value, period)
        path = self._dir / f"{key}.json"

        try:
            payload = {
                "metric_name": metric_name,
                "value": value,
                "period": period,
                "text": text,
                "provider": provider,
                "model": model,
                "created_at": time.time(),
            }
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("Cache write error for %s: %s", key, exc)

    def clear(self) -> int:
        """Remove all cached entries. Returns count of files removed."""
        if not self._dir.exists():
            return 0
        count = 0
        for f in self._dir.glob("*.json"):
            f.unlink(missing_ok=True)
            count += 1
        return count
