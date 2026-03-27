"""SQLite connection manager with schema initialisation."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

try:
    import structlog

    logger = structlog.get_logger()
except ModuleNotFoundError:
    import logging

    logger = logging.getLogger(__name__)  # type: ignore[assignment]

_SCHEMA_PATH = Path(__file__).resolve().parents[4] / "sql" / "schema.sql"
_DEFAULT_DB_PATH = Path(__file__).resolve().parents[4] / "data" / "market_analysis.db"


class DatabaseManager:
    """Manages a single SQLite database file.

    Responsibilities:
      - Create the file and parent directories if absent.
      - Apply the DDL schema on first use.
      - Provide a context-managed connection with WAL mode enabled.
    """

    def __init__(
        self,
        db_path: Path = _DEFAULT_DB_PATH,
        schema_path: Path = _SCHEMA_PATH,
    ) -> None:
        self._db_path = db_path
        self._schema_path = schema_path
        self._initialised = False

    @property
    def db_path(self) -> Path:
        return self._db_path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def initialise(self) -> None:
        """Create the database file and apply the schema idempotently."""
        if self._initialised:
            return

        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        with self.connect() as conn:
            schema_sql = self._schema_path.read_text(encoding="utf-8")
            conn.executescript(schema_sql)
            logger.info(
                "database_initialised",
                db_path=str(self._db_path),
            )

        self._initialised = True

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Yield a connection that auto-commits on success and rolls back on error."""
        conn = sqlite3.connect(
            str(self._db_path),
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")

        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def execute(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Run a single statement and return all rows."""
        with self.connect() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchall()


# Module-level singleton for simple usage.
_default_db: DatabaseManager | None = None


def get_database(
    db_path: Path = _DEFAULT_DB_PATH,
    schema_path: Path = _SCHEMA_PATH,
) -> DatabaseManager:
    """Return (and optionally create) the module-level DatabaseManager."""
    global _default_db
    if _default_db is None:
        _default_db = DatabaseManager(db_path=db_path, schema_path=schema_path)
        _default_db.initialise()
    return _default_db
