"""HTTP utilities for infrastructure layer."""

from __future__ import annotations

from typing import Any

import httpx


class NoCloseClient:
    """Wraps an externally-owned httpx.AsyncClient to prevent closing it.

    This is useful when a collector accepts an optional client for dependency
    injection but should not close it since the client is owned by the caller.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def __aenter__(self) -> httpx.AsyncClient:
        return self._client

    async def __aexit__(self, *args: Any) -> None:
        pass  # Do not close the external client