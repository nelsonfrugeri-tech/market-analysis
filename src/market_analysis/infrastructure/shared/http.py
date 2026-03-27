"""Shared HTTP utilities for infrastructure components."""

import aiohttp
import requests
from typing import Optional, Dict, Any


class HttpClient:
    """Shared HTTP client with common configuration."""

    def __init__(self, timeout: int = 30, headers: Optional[Dict[str, str]] = None):
        self.timeout = timeout
        self.headers = headers or {}

    def get_session_headers(self) -> Dict[str, str]:
        """Get common headers for HTTP requests."""
        return {
            "User-Agent": "MarketAnalysis/1.0",
            **self.headers
        }

    async def get_async(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make async GET request with common configuration."""
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers=self.get_session_headers()
        ) as session:
            return await session.get(url, **kwargs)

    def get_sync(self, url: str, **kwargs) -> requests.Response:
        """Make synchronous GET request with common configuration."""
        return requests.get(
            url,
            timeout=self.timeout,
            headers=self.get_session_headers(),
            **kwargs
        )