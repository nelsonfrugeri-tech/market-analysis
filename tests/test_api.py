"""
Comprehensive tests for Market Analysis FastAPI endpoints.

All 6 endpoints are tested with mocked service layer to ensure
deterministic, fast, and reliable test execution.
"""

from datetime import date
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from market_analysis.api.main import METRIC_EXPLANATIONS, app
from market_analysis.domain.models.fund import FundDailyRecord, FundPerformance

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NU_RESERVA_CNPJ = "43.121.002/0001-41"


@pytest.fixture
def client() -> TestClient:
    """Provide FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_fund_performance() -> FundPerformance:
    """Build a realistic FundPerformance fixture."""
    return FundPerformance(
        fund_cnpj=NU_RESERVA_CNPJ,
        fund_name="Nu Reserva Planejada",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 3, 31),
        nav_start=1.234567,
        nav_end=1.256789,
        return_pct=0.018,
        equity_start=500_000_000.0,
        equity_end=520_000_000.0,
        volatility=0.0123,
        shareholders_current=150_000,
        benchmark_selic=0.032,
        benchmark_cdi=0.031,
        benchmark_ipca=0.012,
        vs_selic=-14.0,
        vs_cdi=-13.0,
        vs_ipca=6.0,
        trend_30d="up",
        sharpe_ratio=1.45,
        alpha=0.002,
        beta=0.95,
        var_95=-0.003,
        max_drawdown=-0.005,
    )


@pytest.fixture
def sample_daily_records() -> list[FundDailyRecord]:
    """Build sample daily records for testing."""
    return [
        FundDailyRecord(
            cnpj=NU_RESERVA_CNPJ,
            date=date(2025, 3, 28),
            nav=1.254321,
            equity=518_000_000.0,
            total_value=518_000_000.0,
            deposits=1_000_000.0,
            withdrawals=500_000.0,
            shareholders=149_500,
        ),
        FundDailyRecord(
            cnpj=NU_RESERVA_CNPJ,
            date=date(2025, 3, 31),
            nav=1.256789,
            equity=520_000_000.0,
            total_value=520_000_000.0,
            deposits=2_000_000.0,
            withdrawals=800_000.0,
            shareholders=150_000,
        ),
    ]


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """GET /api/v1/health tests."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """Health endpoint always returns 200 even when DB is absent."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] in ("healthy", "unhealthy")
        assert "timestamp" in data
        assert "database_connected" in data

    def test_health_does_not_collect_data(self, client: TestClient) -> None:
        """Health endpoint must NOT call any data collection functions."""
        with patch(
            "market_analysis.api.main.collect_multiple_months"
        ) as mock_collect:
            response = client.get("/api/v1/health")
            assert response.status_code == 200
            mock_collect.assert_not_called()

    @patch("market_analysis.api.main._DB_PATH")
    def test_health_db_not_found(
        self, mock_path: object, client: TestClient
    ) -> None:
        """Health reports healthy but database_connected=False when no DB."""
        mock_path.exists.return_value = False  # type: ignore[union-attr]
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database_connected"] is False


# ---------------------------------------------------------------------------
# Funds list endpoint
# ---------------------------------------------------------------------------


class TestFundsListEndpoint:
    """GET /api/v1/funds tests."""

    def test_funds_list_returns_array(self, client: TestClient) -> None:
        """Returns a list of fund summaries."""
        response = client.get("/api/v1/funds")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_funds_list_structure(self, client: TestClient) -> None:
        """Each fund has required fields."""
        response = client.get("/api/v1/funds")
        data = response.json()
        fund = data[0]

        required_keys = {
            "cnpj",
            "name",
            "short_name",
            "fund_type",
            "manager",
            "benchmark",
            "status",
        }
        assert required_keys.issubset(fund.keys())

    def test_funds_list_contains_nu_reserva(
        self, client: TestClient
    ) -> None:
        """Nu Reserva fund must be present in the list."""
        response = client.get("/api/v1/funds")
        data = response.json()
        cnpjs = [f["cnpj"] for f in data]
        assert NU_RESERVA_CNPJ in cnpjs


# ---------------------------------------------------------------------------
# Performance endpoint
# ---------------------------------------------------------------------------


class TestPerformanceEndpoint:
    """GET /api/v1/funds/{cnpj}/performance tests."""

    @patch("market_analysis.api.service.compute_performance")
    @patch("market_analysis.api.service.collect_all_benchmarks_sync")
    @patch("market_analysis.api.service.collect_multiple_months")
    def test_performance_success(
        self,
        mock_collect: object,
        mock_benchmarks: object,
        mock_compute: object,
        client: TestClient,
        sample_fund_performance: FundPerformance,
        sample_daily_records: list[FundDailyRecord],
    ) -> None:
        """Performance endpoint returns typed response on success."""
        mock_collect.return_value = sample_daily_records  # type: ignore[union-attr]
        mock_benchmarks.return_value = {}  # type: ignore[union-attr]
        mock_compute.return_value = sample_fund_performance  # type: ignore[union-attr]

        response = client.get(
            f"/api/v1/funds/{NU_RESERVA_CNPJ}/performance",
            params={"months": 3},
        )
        assert response.status_code == 200

        data = response.json()
        # Verify typed structure (no raw dicts)
        assert isinstance(data["period"]["start"], str)
        assert isinstance(data["period"]["days"], int)
        assert isinstance(data["performance"]["return_pct"], float)
        assert isinstance(data["risk"]["volatility"], float)
        assert isinstance(data["efficiency"]["alpha"], float)
        assert isinstance(data["benchmarks"]["cdi"]["accumulated"], float)
        assert isinstance(data["benchmarks"]["cdb"]["estimated"], float)
        assert isinstance(data["market"]["trend_30d"], str)
        assert isinstance(data["market"]["shareholders"], int)

    def test_performance_invalid_months_zero(
        self, client: TestClient
    ) -> None:
        """months=0 triggers 422 validation error."""
        response = client.get(
            f"/api/v1/funds/{NU_RESERVA_CNPJ}/performance",
            params={"months": 0},
        )
        assert response.status_code == 422

    def test_performance_invalid_months_negative(
        self, client: TestClient
    ) -> None:
        """Negative months triggers 422 validation error."""
        response = client.get(
            f"/api/v1/funds/{NU_RESERVA_CNPJ}/performance",
            params={"months": -1},
        )
        assert response.status_code == 422

    def test_performance_months_too_large(
        self, client: TestClient
    ) -> None:
        """months > 60 triggers 422 validation error."""
        response = client.get(
            f"/api/v1/funds/{NU_RESERVA_CNPJ}/performance",
            params={"months": 100},
        )
        assert response.status_code == 422

    @patch("market_analysis.api.service.collect_multiple_months")
    def test_performance_unsupported_cnpj(
        self, mock_collect: object, client: TestClient
    ) -> None:
        """Unsupported CNPJ returns 400."""
        response = client.get(
            "/api/v1/funds/00.000.000%2F0000-00/performance",
            params={"months": 3},
        )
        assert response.status_code == 400
        assert "Only Nu Reserva" in response.json()["detail"]

    @patch("market_analysis.api.service.collect_multiple_months")
    def test_performance_no_data_returns_400(
        self, mock_collect: object, client: TestClient
    ) -> None:
        """Empty data collection returns 400."""
        mock_collect.return_value = []  # type: ignore[union-attr]
        response = client.get(
            f"/api/v1/funds/{NU_RESERVA_CNPJ}/performance",
            params={"months": 3},
        )
        assert response.status_code == 400

    @patch("market_analysis.api.service.compute_performance")
    @patch("market_analysis.api.service.collect_all_benchmarks_sync")
    @patch("market_analysis.api.service.collect_multiple_months")
    def test_performance_with_date_range(
        self,
        mock_collect: object,
        mock_benchmarks: object,
        mock_compute: object,
        client: TestClient,
        sample_fund_performance: FundPerformance,
        sample_daily_records: list[FundDailyRecord],
    ) -> None:
        """Performance works with start_date and end_date params."""
        mock_collect.return_value = sample_daily_records  # type: ignore[union-attr]
        mock_benchmarks.return_value = {}  # type: ignore[union-attr]
        mock_compute.return_value = sample_fund_performance  # type: ignore[union-attr]

        response = client.get(
            f"/api/v1/funds/{NU_RESERVA_CNPJ}/performance",
            params={
                "start_date": "2025-01-01",
                "end_date": "2025-03-31",
            },
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Daily data endpoint
# ---------------------------------------------------------------------------


class TestDailyDataEndpoint:
    """GET /api/v1/funds/{cnpj}/daily tests."""

    @patch("market_analysis.api.service.collect_multiple_months")
    def test_daily_data_success(
        self,
        mock_collect: object,
        client: TestClient,
        sample_daily_records: list[FundDailyRecord],
    ) -> None:
        """Returns daily records with correct structure."""
        mock_collect.return_value = sample_daily_records  # type: ignore[union-attr]

        response = client.get(
            f"/api/v1/funds/{NU_RESERVA_CNPJ}/daily",
            params={"limit": 90},
        )
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

        record = data[0]
        required_keys = {
            "date",
            "nav",
            "equity",
            "deposits",
            "withdrawals",
            "shareholders",
            "net_flow",
        }
        assert required_keys.issubset(record.keys())

    @patch("market_analysis.api.service.collect_multiple_months")
    def test_daily_data_respects_limit(
        self,
        mock_collect: object,
        client: TestClient,
        sample_daily_records: list[FundDailyRecord],
    ) -> None:
        """Limit parameter truncates results."""
        mock_collect.return_value = sample_daily_records  # type: ignore[union-attr]

        response = client.get(
            f"/api/v1/funds/{NU_RESERVA_CNPJ}/daily",
            params={"limit": 1},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    @patch("market_analysis.api.service.collect_multiple_months")
    def test_daily_data_net_flow_calculated(
        self,
        mock_collect: object,
        client: TestClient,
        sample_daily_records: list[FundDailyRecord],
    ) -> None:
        """net_flow = deposits - withdrawals."""
        mock_collect.return_value = sample_daily_records  # type: ignore[union-attr]

        response = client.get(
            f"/api/v1/funds/{NU_RESERVA_CNPJ}/daily",
            params={"limit": 90},
        )
        data = response.json()
        for record in data:
            expected_flow = record["deposits"] - record["withdrawals"]
            assert record["net_flow"] == pytest.approx(expected_flow)

    def test_daily_data_invalid_limit(self, client: TestClient) -> None:
        """limit=0 triggers 422."""
        response = client.get(
            f"/api/v1/funds/{NU_RESERVA_CNPJ}/daily",
            params={"limit": 0},
        )
        assert response.status_code == 422

    def test_daily_data_limit_too_large(self, client: TestClient) -> None:
        """limit > 365 triggers 422."""
        response = client.get(
            f"/api/v1/funds/{NU_RESERVA_CNPJ}/daily",
            params={"limit": 500},
        )
        assert response.status_code == 422

    @patch("market_analysis.api.service.collect_multiple_months")
    def test_daily_data_unsupported_cnpj(
        self, mock_collect: object, client: TestClient
    ) -> None:
        """Unsupported CNPJ returns 500 (ValueError wrapped)."""
        response = client.get(
            "/api/v1/funds/00.000.000%2F0000-00/daily",
            params={"limit": 10},
        )
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# Explanations endpoint
# ---------------------------------------------------------------------------


class TestExplanationsEndpoint:
    """GET /api/v1/funds/{cnpj}/explanations tests."""

    def test_explanations_returns_list(self, client: TestClient) -> None:
        """Returns a non-empty list of explanations."""
        response = client.get(
            f"/api/v1/funds/{NU_RESERVA_CNPJ}/explanations"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 20  # We now have 30 explanations

    def test_explanations_structure(self, client: TestClient) -> None:
        """Each explanation has required fields."""
        response = client.get(
            f"/api/v1/funds/{NU_RESERVA_CNPJ}/explanations"
        )
        data = response.json()
        for exp in data:
            assert isinstance(exp["key"], str)
            assert isinstance(exp["name"], str)
            assert isinstance(exp["explanation"], str)
            assert exp["category"] in (
                "performance",
                "risk",
                "efficiency",
                "consistency",
                "comparison",
            )

    def test_explanations_categories_coverage(
        self, client: TestClient
    ) -> None:
        """All categories are represented."""
        response = client.get(
            f"/api/v1/funds/{NU_RESERVA_CNPJ}/explanations"
        )
        data = response.json()
        categories = {exp["category"] for exp in data}
        expected = {"performance", "risk", "efficiency", "consistency", "comparison"}
        assert expected == categories

    def test_explanations_keys_unique(self, client: TestClient) -> None:
        """All metric keys are unique."""
        response = client.get(
            f"/api/v1/funds/{NU_RESERVA_CNPJ}/explanations"
        )
        data = response.json()
        keys = [exp["key"] for exp in data]
        assert len(keys) == len(set(keys))

    def test_explanations_count_matches_constant(self) -> None:
        """Module constant matches expected count."""
        assert len(METRIC_EXPLANATIONS) == 29


# ---------------------------------------------------------------------------
# Collection endpoint
# ---------------------------------------------------------------------------


class TestCollectionEndpoint:
    """POST /api/v1/collect tests."""

    @patch("market_analysis.api.main.collect_all_benchmarks_sync")
    @patch("market_analysis.api.main.collect_multiple_months")
    def test_collection_success(
        self,
        mock_collect: object,
        mock_benchmarks: object,
        client: TestClient,
        sample_daily_records: list[FundDailyRecord],
    ) -> None:
        """Successful collection returns status=success."""
        mock_collect.return_value = sample_daily_records  # type: ignore[union-attr]
        mock_benchmarks.return_value = {}  # type: ignore[union-attr]

        response = client.post("/api/v1/collect")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["items_collected"] == 5  # 2 records + 3 benchmarks
        assert data["duration_secs"] >= 0
        assert "timestamp" in data
        assert data["error"] is None

    @patch("market_analysis.api.main.collect_multiple_months")
    def test_collection_error(
        self, mock_collect: object, client: TestClient
    ) -> None:
        """Failed collection returns status=error with message."""
        mock_collect.side_effect = RuntimeError("Network error")  # type: ignore[union-attr]

        response = client.post("/api/v1/collect")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "error"
        assert data["items_collected"] == 0
        assert "Network error" in data["error"]


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Cross-cutting error handling tests."""

    def test_nonexistent_route_returns_404(
        self, client: TestClient
    ) -> None:
        """Unknown routes return 404."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code in (404, 405)

    def test_wrong_method_returns_405(self, client: TestClient) -> None:
        """POST to GET-only endpoint returns 405."""
        response = client.post("/api/v1/funds")
        assert response.status_code == 405

    @patch("market_analysis.api.service.collect_multiple_months")
    def test_service_exception_returns_500(
        self, mock_collect: object, client: TestClient
    ) -> None:
        """Unexpected service errors return 500."""
        mock_collect.side_effect = RuntimeError("Unexpected")  # type: ignore[union-attr]

        response = client.get(
            f"/api/v1/funds/{NU_RESERVA_CNPJ}/daily",
            params={"limit": 10},
        )
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


class TestCORS:
    """CORS configuration tests."""

    def test_cors_allows_localhost_3001(self, client: TestClient) -> None:
        """Preflight from localhost:3001 returns CORS headers."""
        response = client.options(
            "/api/v1/funds",
            headers={
                "Origin": "http://localhost:3001",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") == (
            "http://localhost:3001"
        )

    def test_cors_blocks_unknown_origin(
        self, client: TestClient
    ) -> None:
        """Unknown origins do not get CORS headers."""
        response = client.options(
            "/api/v1/funds",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") is None


# ---------------------------------------------------------------------------
# OpenAPI / docs
# ---------------------------------------------------------------------------


class TestDocs:
    """API documentation endpoint tests."""

    def test_openapi_json_available(self, client: TestClient) -> None:
        """OpenAPI schema is available."""
        response = client.get("/api/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "Market Analysis API"
        assert schema["info"]["version"] == "0.2.0"

    def test_swagger_docs_available(self, client: TestClient) -> None:
        """Swagger UI is available."""
        response = client.get("/api/docs")
        assert response.status_code == 200
