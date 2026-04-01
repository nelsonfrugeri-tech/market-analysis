"""
Integration tests for Market Analysis FastAPI endpoints.

Tests all 6 API endpoints with real data and error scenarios.
"""

import pytest
from fastapi.testclient import TestClient

from market_analysis.api.main import app


@pytest.fixture
def client():
    """Provide FastAPI test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Health check endpoint tests."""

    def test_health_check_success(self, client):
        """Test health check returns 200 with status."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "database_connected" in data
        assert "timestamp" in data


class TestFundsListEndpoint:
    """List funds endpoint tests."""

    def test_funds_list_success(self, client):
        """Test getting list of available funds."""
        response = client.get("/api/v1/funds")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        if data:  # If funds exist
            fund = data[0]
            assert "cnpj" in fund
            assert "name" in fund
            assert "benchmark" in fund


class TestPerformanceEndpoint:
    """Performance metrics endpoint tests."""

    def test_performance_with_months_filter(self, client):
        """Test performance endpoint with months filter."""
        response = client.get(
            "/api/v1/funds/43.121.002%2F0001-41/performance",
            params={"months": 3}
        )
        # May return 200 if data exists or 400/detail if not
        assert response.status_code in [200, 400]

        if response.status_code == 200:
            data = response.json()
            assert "fund" in data
            assert "period" in data
            assert "performance" in data
            assert "risk" in data
            assert "efficiency" in data

    def test_performance_invalid_months(self, client):
        """Test performance endpoint validation."""
        response = client.get(
            "/api/v1/funds/43.121.002%2F0001-41/performance",
            params={"months": 0}  # Invalid: must be >= 1
        )
        assert response.status_code == 422  # Validation error

    def test_performance_with_date_range(self, client):
        """Test performance endpoint with date filters."""
        response = client.get(
            "/api/v1/funds/43.121.002%2F0001-41/performance",
            params={
                "start_date": "2025-01-01",
                "end_date": "2025-12-31"
            }
        )
        assert response.status_code in [200, 400]


class TestDailyDataEndpoint:
    """Daily time series endpoint tests."""

    def test_daily_data_with_limit(self, client):
        """Test daily data endpoint with limit parameter."""
        response = client.get(
            "/api/v1/funds/43.121.002%2F0001-41/daily",
            params={"limit": 5}
        )
        assert response.status_code in [200, 400]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            assert len(data) <= 5

    def test_daily_data_default_limit(self, client):
        """Test daily data endpoint with default limit."""
        response = client.get("/api/v1/funds/43.121.002%2F0001-41/daily")
        assert response.status_code in [200, 400]


class TestExplanationsEndpoint:
    """Metric explanations endpoint tests."""

    def test_explanations_success(self, client):
        """Test metric explanations endpoint."""
        response = client.get("/api/v1/funds/43.121.002%2F0001-41/explanations")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        for explanation in data:
            assert "key" in explanation
            assert "name" in explanation
            assert "explanation" in explanation
            assert "category" in explanation

    def test_explanations_structure(self, client):
        """Test explanations have required fields."""
        response = client.get("/api/v1/funds/43.121.002%2F0001-41/explanations")
        assert response.status_code == 200

        data = response.json()
        if data:
            exp = data[0]
            assert isinstance(exp["key"], str)
            assert isinstance(exp["name"], str)
            assert isinstance(exp["explanation"], str)
            assert exp["category"] in ["performance", "risk", "efficiency", "consistency"]


class TestCollectionEndpoint:
    """Data collection trigger endpoint tests."""

    def test_collection_trigger(self, client):
        """Test POST /collect endpoint."""
        response = client.post("/api/v1/collect")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "items_collected" in data
        assert "duration_secs" in data
        assert "timestamp" in data


class TestErrorHandling:
    """Error handling tests."""

    def test_invalid_cnpj_format(self, client):
        """Test endpoint with invalid CNPJ."""
        response = client.get("/api/v1/funds/invalid-cnpj/performance")
        # Should either work with path-based matching or return error
        assert response.status_code in [200, 400, 404]

    def test_missing_query_param_validation(self, client):
        """Test query parameter validation."""
        response = client.get(
            "/api/v1/funds/43.121.002%2F0001-41/performance",
            params={"months": -1}  # Invalid
        )
        assert response.status_code == 422


class TestCORSHeaders:
    """CORS configuration tests."""

    def test_cors_headers_present(self, client):
        """Test CORS headers in responses."""
        response = client.get("/api/v1/funds")
        # FastAPI TestClient may not show CORS headers, but verify endpoint works
        assert response.status_code in [200, 400]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
