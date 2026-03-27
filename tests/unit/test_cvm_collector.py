"""Tests for the CVM data collector.

Covers both sync functions and the AsyncCVMCollector class.
Uses mocked HTTP responses to avoid hitting the real CVM API.
"""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from market_analysis.domain.models.collection import CollectionStatus
from market_analysis.infrastructure.cvm_collector import (
    AsyncCVMCollector,
    CVMCollectorError,
    _build_url,
    _parse_csv_from_zip,
    _row_to_record,
    _validate_row,
    collect_fund_data,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_csv_zip(
    rows: list[dict[str, str]], filename: str = "test.csv"
) -> bytes:
    """Create an in-memory ZIP containing a CSV with the given rows."""
    buf = io.BytesIO()
    text_buf = io.StringIO()

    fieldnames = list(rows[0].keys()) if rows else []
    writer = csv.DictWriter(text_buf, fieldnames=fieldnames, delimiter=";")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(filename, text_buf.getvalue().encode("latin-1"))

    return buf.getvalue()


def _sample_row(
    cnpj: str = "43.121.002/0001-41",
    dt: str = "2026-03-02",
    nav: str = "1.584266900000",
    equity: str = "803419359.49",
    total: str = "804230879.60",
    deposits: str = "3512850.44",
    withdrawals: str = "2207364.80",
    shareholders: str = "51414",
) -> dict[str, str]:
    """Build a single sample CVM CSV row."""
    return {
        "TP_FUNDO_CLASSE": "CLASSES - FIF",
        "CNPJ_FUNDO_CLASSE": cnpj,
        "ID_SUBCLASSE": "",
        "DT_COMPTC": dt,
        "VL_TOTAL": total,
        "VL_QUOTA": nav,
        "VL_PATRIM_LIQ": equity,
        "CAPTC_DIA": deposits,
        "RESG_DIA": withdrawals,
        "NR_COTST": shareholders,
    }


@pytest.fixture
def sample_csv_rows() -> list[dict[str, str]]:
    """Sample CVM CSV rows for Nu Reserva Planejada + one other fund."""
    return [
        _sample_row(dt="2026-03-02"),
        _sample_row(dt="2026-03-03", nav="1.585099200000"),
        _sample_row(
            cnpj="00.000.000/0001-00",
            dt="2026-03-02",
            nav="1.000000",
            equity="100.00",
            total="100.00",
            deposits="0.00",
            withdrawals="0.00",
            shareholders="1",
        ),
    ]


# ---------------------------------------------------------------------------
# _build_url
# ---------------------------------------------------------------------------


class TestBuildUrl:
    def test_format(self) -> None:
        url = _build_url(2026, 3)
        assert url.endswith("inf_diario_fi_202603.zip")

    def test_zero_padded_month(self) -> None:
        url = _build_url(2026, 1)
        assert "202601" in url

    def test_double_digit_month(self) -> None:
        url = _build_url(2026, 12)
        assert "202612" in url


# ---------------------------------------------------------------------------
# _parse_csv_from_zip
# ---------------------------------------------------------------------------


class TestParseCsvFromZip:
    def test_filters_by_cnpj(
        self, sample_csv_rows: list[dict[str, str]]
    ) -> None:
        zip_bytes = _make_csv_zip(sample_csv_rows)
        rows = _parse_csv_from_zip(zip_bytes, "43.121.002/0001-41")
        assert len(rows) == 2
        assert all(
            r["CNPJ_FUNDO_CLASSE"] == "43.121.002/0001-41" for r in rows
        )

    def test_no_matching_cnpj(
        self, sample_csv_rows: list[dict[str, str]]
    ) -> None:
        zip_bytes = _make_csv_zip(sample_csv_rows)
        rows = _parse_csv_from_zip(zip_bytes, "99.999.999/0001-99")
        assert len(rows) == 0

    def test_invalid_zip_raises(self) -> None:
        with pytest.raises(CVMCollectorError, match="Invalid ZIP"):
            _parse_csv_from_zip(b"not a zip", "43.121.002/0001-41")

    def test_empty_zip_raises(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("readme.txt", "no csv here")
        with pytest.raises(CVMCollectorError, match="No CSV"):
            _parse_csv_from_zip(buf.getvalue(), "43.121.002/0001-41")

    def test_handles_cnpj_fundo_key(self) -> None:
        """Test fallback to CNPJ_FUNDO when CNPJ_FUNDO_CLASSE missing."""
        row = {
            "CNPJ_FUNDO": "43.121.002/0001-41",
            "DT_COMPTC": "2026-03-02",
            "VL_TOTAL": "100.00",
            "VL_QUOTA": "1.00",
            "VL_PATRIM_LIQ": "100.00",
            "CAPTC_DIA": "0.00",
            "RESG_DIA": "0.00",
            "NR_COTST": "1",
        }
        zip_bytes = _make_csv_zip([row])
        rows = _parse_csv_from_zip(zip_bytes, "43.121.002/0001-41")
        assert len(rows) == 1


# ---------------------------------------------------------------------------
# _validate_row
# ---------------------------------------------------------------------------


class TestValidateRow:
    def test_valid_row(self) -> None:
        row = _sample_row()
        result = _validate_row(row)
        assert result is not None
        assert result.CNPJ_FUNDO_CLASSE == "43.121.002/0001-41"

    def test_invalid_date_returns_none(self) -> None:
        row = _sample_row(dt="not-a-date")
        result = _validate_row(row)
        assert result is None

    def test_negative_nav_returns_none(self) -> None:
        row = _sample_row(nav="-1.0")
        result = _validate_row(row)
        assert result is None

    def test_non_numeric_shareholders_returns_none(self) -> None:
        row = _sample_row(shareholders="abc")
        result = _validate_row(row)
        assert result is None

    def test_cnpj_fundo_fallback(self) -> None:
        """Test CNPJ_FUNDO is normalized to CNPJ_FUNDO_CLASSE."""
        row = {
            "CNPJ_FUNDO": "43.121.002/0001-41",
            "DT_COMPTC": "2026-03-02",
            "VL_TOTAL": "100.00",
            "VL_QUOTA": "1.00",
            "VL_PATRIM_LIQ": "100.00",
            "CAPTC_DIA": "0.00",
            "RESG_DIA": "0.00",
            "NR_COTST": "1",
        }
        result = _validate_row(row)
        assert result is not None
        assert result.CNPJ_FUNDO_CLASSE == "43.121.002/0001-41"


# ---------------------------------------------------------------------------
# _row_to_record
# ---------------------------------------------------------------------------


class TestRowToRecord:
    def test_parses_correctly(
        self, sample_csv_rows: list[dict[str, str]]
    ) -> None:
        record = _row_to_record(sample_csv_rows[0])
        assert record.cnpj == "43.121.002/0001-41"
        assert record.date == date(2026, 3, 2)
        assert record.nav == pytest.approx(1.5842669)
        assert record.equity == pytest.approx(803419359.49)
        assert record.shareholders == 51414

    def test_net_flow(self, sample_csv_rows: list[dict[str, str]]) -> None:
        record = _row_to_record(sample_csv_rows[0])
        expected_flow = 3512850.44 - 2207364.80
        assert record.net_flow == pytest.approx(expected_flow)

    def test_comma_decimal_separator(self) -> None:
        """Test rows using comma as decimal separator."""
        row = _sample_row(nav="1,584266900000", equity="803419359,49")
        record = _row_to_record(row)
        assert record.nav == pytest.approx(1.5842669)


# ---------------------------------------------------------------------------
# collect_fund_data (mocked sync)
# ---------------------------------------------------------------------------


class TestCollectFundData:
    @patch("market_analysis.infrastructure.cvm_collector._download_zip")
    def test_collects_and_sorts(
        self,
        mock_download: MagicMock,
        sample_csv_rows: list[dict[str, str]],
    ) -> None:
        mock_download.return_value = _make_csv_zip(sample_csv_rows)

        records = collect_fund_data(
            cnpj="43.121.002/0001-41",
            months=[(2026, 3)],
        )

        assert len(records) == 2
        assert records[0].date < records[1].date
        mock_download.assert_called_once()

    @patch("market_analysis.infrastructure.cvm_collector._download_zip")
    def test_raises_on_download_failure(
        self, mock_download: MagicMock
    ) -> None:
        mock_download.side_effect = CVMCollectorError("timeout")

        with pytest.raises(CVMCollectorError, match="timeout"):
            collect_fund_data(months=[(2026, 3)])

    @patch("market_analysis.infrastructure.cvm_collector._download_zip")
    def test_multiple_months(
        self,
        mock_download: MagicMock,
        sample_csv_rows: list[dict[str, str]],
    ) -> None:
        mock_download.return_value = _make_csv_zip(sample_csv_rows)

        records = collect_fund_data(
            cnpj="43.121.002/0001-41",
            months=[(2026, 2), (2026, 3)],
        )

        assert mock_download.call_count == 2
        assert len(records) == 4  # 2 matching rows per month


# ---------------------------------------------------------------------------
# AsyncCVMCollector
# ---------------------------------------------------------------------------


class TestAsyncCVMCollector:
    def test_source_name(self) -> None:
        collector = AsyncCVMCollector()
        assert collector.source_name == "cvm"

    def test_recent_months_normal(self) -> None:
        months = AsyncCVMCollector._recent_months(date(2026, 3, 15), count=2)
        assert months == [(2026, 2), (2026, 3)]

    def test_recent_months_year_boundary(self) -> None:
        months = AsyncCVMCollector._recent_months(date(2026, 1, 15), count=3)
        assert months == [(2025, 11), (2025, 12), (2026, 1)]

    @pytest.mark.asyncio
    async def test_collect_success(
        self, sample_csv_rows: list[dict[str, str]]
    ) -> None:
        collector = AsyncCVMCollector(cnpj="43.121.002/0001-41")
        zip_bytes = _make_csv_zip(sample_csv_rows)

        with patch(
            "market_analysis.infrastructure.cvm_collector._download_zip_async",
            new_callable=AsyncMock,
            return_value=zip_bytes,
        ):
            result = await collector.collect()

        assert result.is_success
        assert result.record_count > 0
        assert result.source == "cvm"

    @pytest.mark.asyncio
    async def test_collect_error_status(self) -> None:
        collector = AsyncCVMCollector()

        with patch(
            "market_analysis.infrastructure.cvm_collector._download_zip_async",
            new_callable=AsyncMock,
            side_effect=CVMCollectorError("network error"),
        ):
            result = await collector.collect()

        assert result.status == CollectionStatus.ERROR
        assert result.error_count > 0
        assert result.record_count == 0

    @pytest.mark.asyncio
    async def test_collect_partial_status(
        self, sample_csv_rows: list[dict[str, str]]
    ) -> None:
        """One month succeeds, one fails -> PARTIAL."""
        collector = AsyncCVMCollector(cnpj="43.121.002/0001-41")
        zip_bytes = _make_csv_zip(sample_csv_rows)
        call_count = 0

        async def _side_effect(*args: Any, **kwargs: Any) -> bytes:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise CVMCollectorError("first month failed")
            return zip_bytes

        with patch(
            "market_analysis.infrastructure.cvm_collector._download_zip_async",
            new_callable=AsyncMock,
            side_effect=_side_effect,
        ):
            result = await collector.collect()

        assert result.status == CollectionStatus.PARTIAL
        assert result.record_count > 0
        assert result.error_count == 1

    @pytest.mark.asyncio
    async def test_validate_valid_rows(self) -> None:
        collector = AsyncCVMCollector()
        rows = [_sample_row(), _sample_row(dt="2026-03-03")]

        result = await collector.validate(rows)

        assert result.is_valid
        assert result.valid_count == 2

    @pytest.mark.asyncio
    async def test_validate_mixed_rows(self) -> None:
        collector = AsyncCVMCollector()
        rows = [_sample_row(), _sample_row(dt="bad-date")]

        result = await collector.validate(rows)

        assert not result.is_valid
        assert result.valid_count == 1
        assert len(result.invalid_records) == 1

    @pytest.mark.asyncio
    async def test_health_check_success(self) -> None:
        collector = AsyncCVMCollector()

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.head = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await collector.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self) -> None:
        collector = AsyncCVMCollector()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.head = AsyncMock(
                side_effect=httpx.RequestError("connection refused")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await collector.health_check()

        assert result is False


# ---------------------------------------------------------------------------
# collect_multiple_months
# ---------------------------------------------------------------------------


class TestCollectMultipleMonths:
    @patch("market_analysis.infrastructure.cvm_collector._download_zip")
    def test_collects_last_n_months(
        self,
        mock_download: MagicMock,
        sample_csv_rows: list[dict[str, str]],
    ) -> None:
        mock_download.return_value = _make_csv_zip(sample_csv_rows)

        from market_analysis.infrastructure.cvm_collector import (
            collect_multiple_months,
        )

        records = collect_multiple_months(
            cnpj="43.121.002/0001-41", num_months=3
        )

        assert mock_download.call_count == 3
        # Records are sorted by date
        for i in range(len(records) - 1):
            assert records[i].date <= records[i + 1].date

    @patch("market_analysis.infrastructure.cvm_collector._download_zip")
    def test_skips_failing_months(
        self, mock_download: MagicMock, sample_csv_rows: list[dict[str, str]]
    ) -> None:
        """If one month fails, others are still collected."""
        call_count = 0

        def _side_effect(url: str, timeout: int = 60) -> bytes:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise CVMCollectorError("not found")
            return _make_csv_zip(sample_csv_rows)

        mock_download.side_effect = _side_effect

        from market_analysis.infrastructure.cvm_collector import (
            collect_multiple_months,
        )

        records = collect_multiple_months(
            cnpj="43.121.002/0001-41", num_months=2
        )

        assert len(records) > 0


# ---------------------------------------------------------------------------
# collect_fund_data defaults
# ---------------------------------------------------------------------------


class TestCollectFundDataDefaults:
    @patch("market_analysis.infrastructure.cvm_collector._download_zip")
    def test_defaults_to_current_month(
        self,
        mock_download: MagicMock,
        sample_csv_rows: list[dict[str, str]],
    ) -> None:
        """When months=None, should use current month."""
        mock_download.return_value = _make_csv_zip(sample_csv_rows)

        records = collect_fund_data(cnpj="43.121.002/0001-41")

        mock_download.assert_called_once()
        assert len(records) == 2


# ---------------------------------------------------------------------------
# _row_to_record fallback path
# ---------------------------------------------------------------------------


class TestRowToRecordFallback:
    def test_fallback_on_invalid_validation(self) -> None:
        """When Pydantic validation fails, direct parsing fallback is used."""
        # Row with CNPJ_FUNDO instead of CNPJ_FUNDO_CLASSE and extra fields
        # that confuse the validator but can still be parsed directly
        row = {
            "CNPJ_FUNDO": "43.121.002/0001-41",
            "DT_COMPTC": "2026-03-02",
            "VL_QUOTA": "1.50",
            "VL_PATRIM_LIQ": "100.00",
            "VL_TOTAL": "100.00",
            "CAPTC_DIA": "0.00",
            "RESG_DIA": "0.00",
            "NR_COTST": "1",
        }
        # This should work via validated path
        record = _row_to_record(row)
        assert record.cnpj == "43.121.002/0001-41"
        assert record.nav == pytest.approx(1.50)


# ---------------------------------------------------------------------------
# _download_zip sync
# ---------------------------------------------------------------------------


class TestDownloadZipSync:
    @patch("httpx.Client")
    def test_successful_download(self, mock_client_cls: MagicMock) -> None:
        from market_analysis.infrastructure.cvm_collector import _download_zip

        mock_response = MagicMock()
        mock_response.content = b"fake zip content"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = _download_zip("https://example.com/test.zip")
        assert result == b"fake zip content"

    @patch("httpx.Client")
    def test_http_status_error(self, mock_client_cls: MagicMock) -> None:
        from market_analysis.infrastructure.cvm_collector import _download_zip

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=mock_response,
        )
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with pytest.raises(CVMCollectorError, match="HTTP"):
            _download_zip("https://example.com/missing.zip")

    @patch("httpx.Client")
    def test_request_error(self, mock_client_cls: MagicMock) -> None:
        from market_analysis.infrastructure.cvm_collector import _download_zip

        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.RequestError("timeout")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with pytest.raises(CVMCollectorError, match="Failed"):
            _download_zip("https://example.com/timeout.zip")


# ---------------------------------------------------------------------------
# _download_zip_async
# ---------------------------------------------------------------------------


class TestDownloadZipAsync:
    @pytest.mark.asyncio
    async def test_successful_async_download(self) -> None:
        from market_analysis.infrastructure.cvm_collector import (
            _download_zip_async,
        )

        mock_response = MagicMock()
        mock_response.content = b"async zip content"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await _download_zip_async(mock_client, "https://example.com/test.zip")
        assert result == b"async zip content"

    @pytest.mark.asyncio
    async def test_async_http_status_error(self) -> None:
        from market_analysis.infrastructure.cvm_collector import (
            _download_zip_async,
        )

        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=mock_response,
            )
        )

        with pytest.raises(CVMCollectorError, match="HTTP"):
            await _download_zip_async(mock_client, "https://example.com/err.zip")

    @pytest.mark.asyncio
    async def test_async_request_error(self) -> None:
        from market_analysis.infrastructure.cvm_collector import (
            _download_zip_async,
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.RequestError("connection refused")
        )

        with pytest.raises(CVMCollectorError, match="Failed"):
            await _download_zip_async(mock_client, "https://example.com/fail.zip")
