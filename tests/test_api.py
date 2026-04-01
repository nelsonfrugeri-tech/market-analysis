"""
Unit tests for Market Analysis FastAPI endpoints.

All external dependencies (CVM, BCB) are mocked for fast, reliable tests.
"""

from datetime import date, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from market_analysis.api.main import app


@pytest.fixture
def client():
    """Provide FastAPI test client."""
    return TestClient(app)


# ─── Mock data factories ────────────────────────────────────────────


def _mock_fund_metadata():
    """Return mock fund metadata matching service output."""
    return [
        {
            "cnpj": "43.121.002/0001-41",
            "name": "Nu Reserva Planejada",
            "short_name": "Nu Reserva",
            "fund_type": "Renda Fixa",
            "manager": "Nu Asset Management",
            "benchmark": "CDI",
            "status": "active",
        }
    ]


class _MockRecord:
    """Minimal mock for CVM daily record."""

    def __init__(self, day_offset: int = 0):
        self.date = date(2026, 3, 1 + day_offset)
        self.nav = 1.50 + day_offset * 0.001
        self.equity = 5_000_000.0
        self.deposits = 100_000.0
        self.withdrawals = 50_000.0
        self.shareholders = 12000


class _MockPerformance:
    """Minimal mock for FundPerformance domain object."""

    fund_cnpj = "43.121.002/0001-41"
    fund_name = "Nu Reserva Planejada"
    period_start = date(2026, 1, 1)
    period_end = date(2026, 3, 31)
    return_pct = 0.0312
    nav_start = 1.450000
    nav_end = 1.495260
    volatility = 0.0245
    sharpe_ratio = 1.2731
    max_drawdown = -0.0082
    var_95 = -0.0015
    alpha = 0.0021
    beta = 0.95
    benchmark_cdi = 0.0298
    benchmark_selic = 0.0302
    benchmark_ipca = 0.0145
    vs_cdi = 14.0
    vs_selic = 10.0
    vs_ipca = 167.0
    trend_30d = "up"
    shareholders_current = 12000
    equity_end = 5_200_000.0


# ─── Health endpoint ─────────────────────────────────────────────────


class TestHealthEndpoint:
    """Tests for GET /api/v1/health."""

    def test_health_returns_200(self, client):
        """Health check is lightweight and always succeeds."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["database_connected"] is True
        assert "timestamp" in data

    def test_health_response_schema(self, client):
        """Health response contains all required fields."""
        data = client.get("/api/v1/health").json()
        required_fields = {"status", "timestamp", "database_connected"}
        assert required_fields.issubset(data.keys())


# ─── Funds list endpoint ─────────────────────────────────────────────


class TestFundsListEndpoint:
    """Tests for GET /api/v1/funds."""

    @patch(
        "market_analysis.api.main.get_fund_metadata",
        new_callable=AsyncMock,
        return_value=_mock_fund_metadata(),
    )
    def test_funds_list_success(self, mock_meta, client):
        """Returns list of available funds."""
        response = client.get("/api/v1/funds")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

        fund = data[0]
        assert fund["cnpj"] == "43.121.002/0001-41"
        assert fund["name"] == "Nu Reserva Planejada"
        assert fund["benchmark"] == "CDI"
        assert fund["status"] == "active"

    @patch(
        "market_analysis.api.main.get_fund_metadata",
        new_callable=AsyncMock,
        return_value=_mock_fund_metadata(),
    )
    def test_funds_list_schema(self, mock_meta, client):
        """Each fund has all required fields."""
        data = client.get("/api/v1/funds").json()
        required = {"cnpj", "name", "short_name", "fund_type", "manager", "benchmark", "status"}
        for fund in data:
            assert required.issubset(fund.keys())


# ─── Performance endpoint ────────────────────────────────────────────


class TestPerformanceEndpoint:
    """Tests for GET /api/v1/funds/{cnpj}/performance."""

    @patch(
        "market_analysis.api.main.calculate_fund_performance",
        new_callable=AsyncMock,
        return_value=_MockPerformance(),
    )
    def test_performance_success(self, mock_perf, client):
        """Returns typed performance response for valid request."""
        response = client.get(
            "/api/v1/funds/43.121.002%2F0001-41/performance",
            params={"months": 3},
        )
        assert response.status_code == 200

        data = response.json()
        # Verify all top-level typed sections
        assert "fund" in data
        assert "period" in data
        assert "performance" in data
        assert "risk" in data
        assert "efficiency" in data
        assert "benchmarks" in data
        assert "market" in data
        assert "updated_at" in data

    @patch(
        "market_analysis.api.main.calculate_fund_performance",
        new_callable=AsyncMock,
        return_value=_MockPerformance(),
    )
    def test_performance_typed_models(self, mock_perf, client):
        """All nested fields use typed Pydantic models (not Dict[str, Any])."""
        data = client.get(
            "/api/v1/funds/43.121.002%2F0001-41/performance",
            params={"months": 3},
        ).json()

        # Period uses PeriodInfo (typed dates)
        period = data["period"]
        assert "start" in period
        assert "end" in period
        assert "days" in period
        assert isinstance(period["days"], int)

        # Performance uses PerformanceMetrics
        perf = data["performance"]
        assert "return_pct" in perf
        assert "nav_start" in perf
        assert "nav_end" in perf

        # Risk uses RiskMetrics
        risk = data["risk"]
        assert "volatility" in risk
        assert "sharpe_ratio" in risk
        assert "max_drawdown" in risk
        assert "var_95" in risk

        # Efficiency uses EfficiencyMetrics
        eff = data["efficiency"]
        assert "alpha" in eff
        assert "beta" in eff

        # Benchmarks uses BenchmarkComparison with BenchmarkDetail
        bench = data["benchmarks"]
        assert "cdi" in bench
        assert "accumulated" in bench["cdi"]
        assert "vs_fund" in bench["cdi"]

        # Market uses MarketContext
        market = data["market"]
        assert "trend_30d" in market
        assert "shareholders" in market
        assert "equity_millions" in market

    def test_performance_invalid_months_zero(self, client):
        """Rejects months=0 with 422."""
        response = client.get(
            "/api/v1/funds/43.121.002%2F0001-41/performance",
            params={"months": 0},
        )
        assert response.status_code == 422

    def test_performance_invalid_months_negative(self, client):
        """Rejects negative months with 422."""
        response = client.get(
            "/api/v1/funds/43.121.002%2F0001-41/performance",
            params={"months": -1},
        )
        assert response.status_code == 422

    @patch(
        "market_analysis.api.main.calculate_fund_performance",
        new_callable=AsyncMock,
        side_effect=ValueError("Only Nu Reserva CNPJ is supported"),
    )
    def test_performance_unsupported_cnpj(self, mock_perf, client):
        """Returns 400 for unsupported CNPJ."""
        response = client.get("/api/v1/funds/00.000.000%2F0000-00/performance")
        assert response.status_code == 400
        assert "supported" in response.json()["detail"].lower()


# ─── Daily data endpoint ─────────────────────────────────────────────


class TestDailyDataEndpoint:
    """Tests for GET /api/v1/funds/{cnpj}/daily."""

    @patch(
        "market_analysis.api.main.get_fund_daily_data",
        new_callable=AsyncMock,
        return_value=[_MockRecord(i) for i in range(10)],
    )
    def test_daily_data_success(self, mock_daily, client):
        """Returns list of daily data points."""
        response = client.get("/api/v1/funds/43.121.002%2F0001-41/daily")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 10

        point = data[0]
        assert "date" in point
        assert "nav" in point
        assert "equity" in point
        assert "net_flow" in point

    @patch(
        "market_analysis.api.main.get_fund_daily_data",
        new_callable=AsyncMock,
        return_value=[_MockRecord(i) for i in range(10)],
    )
    def test_daily_data_respects_limit(self, mock_daily, client):
        """Limit parameter caps number of returned records."""
        response = client.get(
            "/api/v1/funds/43.121.002%2F0001-41/daily",
            params={"limit": 5},
        )
        assert response.status_code == 200
        assert len(response.json()) <= 5


# ─── Explanations endpoint ───────────────────────────────────────────


class TestExplanationsEndpoint:
    """Tests for GET /api/v1/funds/{cnpj}/explanations."""

    def test_explanations_success(self, client):
        """Returns list of metric explanations."""
        response = client.get("/api/v1/funds/43.121.002%2F0001-41/explanations")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 20  # We now have 24 explanations

    def test_explanations_schema(self, client):
        """Each explanation has required fields."""
        data = client.get("/api/v1/funds/43.121.002%2F0001-41/explanations").json()

        for exp in data:
            assert "key" in exp
            assert "name" in exp
            assert "explanation" in exp
            assert "category" in exp
            assert isinstance(exp["explanation"], str)
            assert len(exp["explanation"]) > 10  # Not empty/placeholder

    def test_explanations_categories(self, client):
        """Explanations cover all metric categories."""
        data = client.get("/api/v1/funds/43.121.002%2F0001-41/explanations").json()
        categories = {exp["category"] for exp in data}
        expected = {"performance", "risk", "efficiency", "benchmark", "market", "flow"}
        assert expected.issubset(categories)

    def test_explanations_keys_unique(self, client):
        """All explanation keys are unique."""
        data = client.get("/api/v1/funds/43.121.002%2F0001-41/explanations").json()
        keys = [exp["key"] for exp in data]
        assert len(keys) == len(set(keys))


# ─── Collection endpoint ─────────────────────────────────────────────


class TestCollectionEndpoint:
    """Tests for POST /api/v1/collect."""

    @patch(
        "market_analysis.api.main.collect_all_benchmarks_sync",
        return_value={"cdi": [], "selic": [], "ipca": []},
    )
    @patch(
        "market_analysis.api.main.collect_multiple_months",
        return_value=[_MockRecord(0), _MockRecord(1)],
    )
    def test_collection_success(self, mock_cvm, mock_bcb, client):
        """Collection endpoint triggers data collection and returns summary."""
        response = client.post("/api/v1/collect")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["items_collected"] > 0
        assert "duration_secs" in data
        assert "timestamp" in data

    @patch(
        "market_analysis.api.main.collect_multiple_months",
        side_effect=Exception("CVM service unavailable"),
    )
    def test_collection_handles_error(self, mock_cvm, client):
        """Collection endpoint handles errors gracefully."""
        response = client.post("/api/v1/collect")
        assert response.status_code == 200  # Returns 200 with error status

        data = response.json()
        assert data["status"] == "error"
        assert data["items_collected"] == 0
        assert "error" in data


# ─── Error handling ──────────────────────────────────────────────────


class TestErrorHandling:
    """Cross-cutting error handling tests."""

    def test_nonexistent_route_returns_404(self, client):
        """Unknown routes return 404."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    def test_invalid_months_type(self, client):
        """Non-integer months returns 422."""
        response = client.get(
            "/api/v1/funds/43.121.002%2F0001-41/performance",
            params={"months": "abc"},
        )
        assert response.status_code == 422
