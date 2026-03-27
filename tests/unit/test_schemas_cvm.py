"""Tests for CVM Pydantic validation schemas."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from market_analysis.domain.schemas_cvm import CvmDailyRow


def _valid_row(**overrides: str) -> dict[str, str]:
    """Build a valid CVM row dict with optional overrides."""
    base = {
        "CNPJ_FUNDO_CLASSE": "43.121.002/0001-41",
        "DT_COMPTC": "2026-03-02",
        "VL_QUOTA": "1.584266900000",
        "VL_PATRIM_LIQ": "803419359.49",
        "VL_TOTAL": "804230879.60",
        "CAPTC_DIA": "3512850.44",
        "RESG_DIA": "2207364.80",
        "NR_COTST": "51414",
    }
    base.update(overrides)
    return base


class TestCvmDailyRow:
    def test_valid_row(self) -> None:
        row = CvmDailyRow(**_valid_row())
        assert row.CNPJ_FUNDO_CLASSE == "43.121.002/0001-41"
        assert row.to_date() == date(2026, 3, 2)
        assert row.to_nav() == pytest.approx(1.5842669)
        assert row.to_shareholders() == 51414

    def test_invalid_date_raises(self) -> None:
        with pytest.raises(ValidationError, match="Invalid date"):
            CvmDailyRow(**_valid_row(DT_COMPTC="not-a-date"))

    def test_non_numeric_nav_raises(self) -> None:
        with pytest.raises(ValidationError, match="Non-numeric"):
            CvmDailyRow(**_valid_row(VL_QUOTA="abc"))

    def test_negative_value_raises(self) -> None:
        with pytest.raises(ValidationError, match="Negative"):
            CvmDailyRow(**_valid_row(VL_QUOTA="-1.0"))

    def test_negative_shareholders_raises(self) -> None:
        with pytest.raises(ValidationError, match="Negative"):
            CvmDailyRow(**_valid_row(NR_COTST="-5"))

    def test_non_integer_shareholders_raises(self) -> None:
        with pytest.raises(ValidationError, match="Non-integer"):
            CvmDailyRow(**_valid_row(NR_COTST="abc"))

    def test_comma_decimal_separator(self) -> None:
        row = CvmDailyRow(**_valid_row(VL_QUOTA="1,584266900000"))
        assert row.to_nav() == pytest.approx(1.5842669)

    def test_frozen(self) -> None:
        row = CvmDailyRow(**_valid_row())
        with pytest.raises(ValidationError):
            row.CNPJ_FUNDO_CLASSE = "changed"  # type: ignore[misc]

    def test_to_equity(self) -> None:
        row = CvmDailyRow(**_valid_row())
        assert row.to_equity() == pytest.approx(803419359.49)

    def test_to_deposits_withdrawals(self) -> None:
        row = CvmDailyRow(**_valid_row())
        assert row.to_deposits() == pytest.approx(3512850.44)
        assert row.to_withdrawals() == pytest.approx(2207364.80)

    @pytest.mark.parametrize(
        "field", ["VL_QUOTA", "VL_PATRIM_LIQ", "VL_TOTAL", "CAPTC_DIA", "RESG_DIA"]
    )
    def test_zero_values_allowed(self, field: str) -> None:
        row = CvmDailyRow(**_valid_row(**{field: "0.00"}))
        assert row is not None

    def test_missing_required_field_raises(self) -> None:
        data = _valid_row()
        del data["VL_QUOTA"]
        with pytest.raises(ValidationError):
            CvmDailyRow(**data)
