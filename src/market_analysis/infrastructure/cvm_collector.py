"""CVM data collector for fund daily information.

Downloads monthly ZIP files from CVM open data portal, parses the CSV
inside, and filters by CNPJ to extract daily NAV and equity data.

Provides both:
- Low-level sync functions for direct use
- AsyncCVMCollector class satisfying the BaseCollector Protocol

Data source: https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/
"""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from datetime import date, datetime
from typing import Any

import httpx
from pydantic import ValidationError

from market_analysis.domain.exceptions import CollectionError
from market_analysis.domain.models.collection import (
    CollectionResult,
    CollectionStatus,
    ErrorResult,
    ValidationResult,
)
from market_analysis.domain.models.fund import FundDailyRecord
from market_analysis.domain.schemas_cvm import CvmDailyRow

logger = logging.getLogger(__name__)

CVM_BASE_URL = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS"
NU_RESERVA_CNPJ = "43.121.002/0001-41"
DEFAULT_TIMEOUT = 60
USER_AGENT = "MarketAnalysis/1.0"


class CVMCollectorError(CollectionError):
    """Raised when CVM data collection fails."""

    def __init__(self, message: str, month: str | None = None) -> None:
        super().__init__(message)
        self.month = month


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _build_url(year: int, month: int) -> str:
    """Build the CVM ZIP download URL for a given year/month."""
    return f"{CVM_BASE_URL}/inf_diario_fi_{year:04d}{month:02d}.zip"


def _parse_csv_from_zip(
    zip_bytes: bytes,
    cnpj_filter: str,
) -> list[dict[str, str]]:
    """Extract CSV from ZIP and filter rows by CNPJ."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        raise CVMCollectorError("Invalid ZIP file from CVM") from exc

    csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
    if not csv_names:
        raise CVMCollectorError("No CSV file found in CVM ZIP")

    rows: list[dict[str, str]] = []
    with zf.open(csv_names[0]) as f:
        reader = csv.DictReader(
            io.TextIOWrapper(f, encoding="latin-1"),
            delimiter=";",
        )
        for row in reader:
            cnpj = row.get("CNPJ_FUNDO_CLASSE", row.get("CNPJ_FUNDO", ""))
            if cnpj == cnpj_filter:
                rows.append(dict(row))

    logger.info("Found %d rows for CNPJ %s", len(rows), cnpj_filter)
    return rows


def _validate_row(row: dict[str, str]) -> CvmDailyRow | None:
    """Validate a raw CSV row using Pydantic schema.

    Returns the validated schema or None if validation fails.
    """
    normalized = dict(row)
    if "CNPJ_FUNDO_CLASSE" not in normalized and "CNPJ_FUNDO" in normalized:
        normalized["CNPJ_FUNDO_CLASSE"] = normalized["CNPJ_FUNDO"]

    try:
        return CvmDailyRow(**normalized)
    except ValidationError as exc:
        logger.warning("Row validation failed: %s", exc.error_count())
        return None


def _row_to_record(row: dict[str, str]) -> FundDailyRecord:
    """Convert a raw CSV row dict to a FundDailyRecord.

    Uses Pydantic validation internally for type safety.
    Falls back to direct parsing if validation fails.
    """
    validated = _validate_row(row)
    if validated is not None:
        return FundDailyRecord(
            cnpj=validated.CNPJ_FUNDO_CLASSE,
            date=validated.to_date(),
            nav=validated.to_nav(),
            equity=validated.to_equity(),
            total_value=validated.to_total_value(),
            deposits=validated.to_deposits(),
            withdrawals=validated.to_withdrawals(),
            shareholders=validated.to_shareholders(),
        )

    # Direct parsing fallback
    return FundDailyRecord(
        cnpj=row.get("CNPJ_FUNDO_CLASSE", row.get("CNPJ_FUNDO", "")),
        date=date.fromisoformat(row["DT_COMPTC"]),
        nav=float(row["VL_QUOTA"].replace(",", ".")),
        equity=float(row["VL_PATRIM_LIQ"].replace(",", ".")),
        total_value=float(row["VL_TOTAL"].replace(",", ".")),
        deposits=float(row["CAPTC_DIA"].replace(",", ".")),
        withdrawals=float(row["RESG_DIA"].replace(",", ".")),
        shareholders=int(row["NR_COTST"]),
    )


# ---------------------------------------------------------------------------
# Sync HTTP
# ---------------------------------------------------------------------------


def _download_zip(url: str, timeout: int = DEFAULT_TIMEOUT) -> bytes:
    """Download a ZIP file from CVM (sync), returning raw bytes."""
    logger.info("Downloading CVM data from %s", url)
    try:
        with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
            response = client.get(url, timeout=timeout)
            response.raise_for_status()
        logger.info("Downloaded %d bytes from CVM", len(response.content))
        return response.content
    except httpx.HTTPStatusError as exc:
        raise CVMCollectorError(
            f"CVM returned HTTP {exc.response.status_code} for {url}"
        ) from exc
    except httpx.RequestError as exc:
        raise CVMCollectorError(
            f"Failed to download {url}: {exc}"
        ) from exc


def collect_fund_data(
    cnpj: str = NU_RESERVA_CNPJ,
    months: list[tuple[int, int]] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[FundDailyRecord]:
    """Collect daily fund data from CVM for the specified months.

    Args:
        cnpj: Fund CNPJ to filter (default: Nu Reserva Planejada).
        months: List of (year, month) tuples. Defaults to current month.
        timeout: HTTP timeout in seconds.

    Returns:
        List of FundDailyRecord sorted by date ascending.

    Raises:
        CVMCollectorError: If download or parsing fails.
    """
    if months is None:
        today = date.today()
        months = [(today.year, today.month)]

    all_records: list[FundDailyRecord] = []

    for year, month in months:
        url = _build_url(year, month)
        try:
            zip_bytes = _download_zip(url, timeout=timeout)
            rows = _parse_csv_from_zip(zip_bytes, cnpj)
            records = [_row_to_record(r) for r in rows]
            all_records.extend(records)
        except CVMCollectorError:
            logger.warning(
                "Failed to collect CVM data for %04d-%02d", year, month
            )
            raise

    all_records.sort(key=lambda r: r.date)
    return all_records


def collect_multiple_months(
    cnpj: str = NU_RESERVA_CNPJ,
    num_months: int = 3,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[FundDailyRecord]:
    """Collect data for the last N months.

    Args:
        cnpj: Fund CNPJ to filter.
        num_months: Number of months to look back (including current).
        timeout: HTTP timeout in seconds.

    Returns:
        List of FundDailyRecord sorted by date ascending.
    """
    today = date.today()
    months: list[tuple[int, int]] = []
    for i in range(num_months):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        months.append((y, m))

    months.reverse()

    all_records: list[FundDailyRecord] = []
    for year, month in months:
        try:
            records = collect_fund_data(cnpj, [(year, month)], timeout)
            all_records.extend(records)
        except CVMCollectorError:
            logger.warning(
                "Skipping %04d-%02d (data may not be available yet)",
                year,
                month,
            )

    all_records.sort(key=lambda r: r.date)
    return all_records


# ---------------------------------------------------------------------------
# Async HTTP helper
# ---------------------------------------------------------------------------


async def _download_zip_async(
    client: httpx.AsyncClient,
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> bytes:
    """Download a ZIP file from CVM asynchronously."""
    logger.info("Downloading CVM data from %s", url)
    try:
        response = await client.get(url, timeout=timeout)
        response.raise_for_status()
        logger.info("Downloaded %d bytes from CVM", len(response.content))
        return response.content
    except httpx.HTTPStatusError as exc:
        raise CVMCollectorError(
            f"CVM returned HTTP {exc.response.status_code} for {url}"
        ) from exc
    except httpx.RequestError as exc:
        raise CVMCollectorError(
            f"Failed to download {url}: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Async collector class (implements BaseCollector Protocol)
# ---------------------------------------------------------------------------


class AsyncCVMCollector:
    """Async CVM data collector satisfying the BaseCollector Protocol.

    Uses httpx.AsyncClient for non-blocking HTTP requests.
    Validates data with Pydantic schemas before returning results.
    """

    def __init__(
        self,
        cnpj: str = NU_RESERVA_CNPJ,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self._cnpj = cnpj
        self._timeout = timeout

    @property
    def source_name(self) -> str:
        """Unique identifier for this data source."""
        return "cvm"

    async def collect(self) -> CollectionResult:
        """Execute full collection cycle for current and previous month.

        Returns:
            CollectionResult with FundDailyRecord items.
        """
        started_at = datetime.now()
        today = date.today()
        months = self._recent_months(today, count=2)

        all_records: list[FundDailyRecord] = []
        errors: list[ErrorResult] = []

        async with httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT}
        ) as client:
            for year, month in months:
                url = _build_url(year, month)
                try:
                    zip_bytes = await _download_zip_async(
                        client, url, self._timeout
                    )
                    rows = _parse_csv_from_zip(zip_bytes, self._cnpj)
                    records = [_row_to_record(r) for r in rows]
                    all_records.extend(records)
                except CVMCollectorError as exc:
                    logger.warning(
                        "Failed to collect CVM data for %04d-%02d: %s",
                        year,
                        month,
                        exc,
                    )
                    errors.append(
                        ErrorResult(
                            source="cvm",
                            error_type="collection_error",
                            message=str(exc),
                            details={
                                "year": str(year),
                                "month": str(month),
                            },
                        )
                    )

        all_records.sort(key=lambda r: r.date)
        finished_at = datetime.now()

        if not all_records and errors:
            status = CollectionStatus.ERROR
        elif errors:
            status = CollectionStatus.PARTIAL
        else:
            status = CollectionStatus.SUCCESS

        return CollectionResult(
            source="cvm",
            status=status,
            records=all_records,
            errors=errors,
            started_at=started_at,
            finished_at=finished_at,
            metadata={
                "cnpj": self._cnpj,
                "months_requested": [
                    f"{y:04d}-{m:02d}" for y, m in months
                ],
            },
        )

    async def validate(
        self, raw_data: list[dict[str, str]]
    ) -> ValidationResult:
        """Validate a batch of raw CSV rows using Pydantic schemas.

        Args:
            raw_data: List of raw CSV row dicts.

        Returns:
            ValidationResult with valid and invalid records separated.
        """
        valid: list[CvmDailyRow] = []
        invalid: list[dict[str, Any]] = []

        for row in raw_data:
            validated = _validate_row(row)
            if validated is not None:
                valid.append(validated)
            else:
                invalid.append({"row": row, "reason": "validation_failed"})

        return ValidationResult(
            valid_records=valid,
            invalid_records=invalid,
        )

    async def health_check(self) -> bool:
        """Check if CVM data portal is reachable.

        Returns:
            True if CVM responds without error.
        """
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": USER_AGENT}
            ) as client:
                response = await client.head(
                    CVM_BASE_URL,
                    timeout=10,
                    follow_redirects=True,
                )
                return response.status_code < 400
        except httpx.RequestError:
            return False

    @staticmethod
    def _recent_months(
        reference: date, count: int = 2
    ) -> list[tuple[int, int]]:
        """Generate list of (year, month) tuples going back N months."""
        months: list[tuple[int, int]] = []
        for i in range(count):
            m = reference.month - i
            y = reference.year
            while m <= 0:
                m += 12
                y -= 1
            months.append((y, m))
        months.reverse()
        return months
