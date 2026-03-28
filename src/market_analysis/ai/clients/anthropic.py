"""Claude client using httpx (no SDK dependency)."""

from __future__ import annotations

import logging
import os
import time

import httpx

from market_analysis.ai.clients.base import LLMClient, LLMClientError, LLMResponse

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-4-20250514"
API_VERSION = "2023-06-01"


class AnthropicClient(LLMClient):
    """Claude via Anthropic Messages API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        timeout: int = 30,
    ) -> None:
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._model = model
        self._timeout = timeout

    @property
    def provider_name(self) -> str:
        return "anthropic"

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 300,
        temperature: float = 0.3,
    ) -> LLMResponse:
        if not self._api_key:
            raise LLMClientError("ANTHROPIC_API_KEY not set")

        payload = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }

        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    ANTHROPIC_API_URL,
                    json=payload,
                    headers={
                        "x-api-key": self._api_key,
                        "anthropic-version": API_VERSION,
                        "content-type": "application/json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise LLMClientError(
                f"Anthropic API {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMClientError(f"Anthropic HTTP error: {exc}") from exc

        latency = (time.monotonic() - t0) * 1000
        text = data["content"][0]["text"].strip()
        usage = data.get("usage", {})

        return LLMResponse(
            text=text,
            model=data.get("model", self._model),
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            latency_ms=round(latency, 1),
            provider=self.provider_name,
        )

    async def health_check(self) -> bool:
        if not self._api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    ANTHROPIC_API_URL,
                    json={
                        "model": self._model,
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "ping"}],
                    },
                    headers={
                        "x-api-key": self._api_key,
                        "anthropic-version": API_VERSION,
                        "content-type": "application/json",
                    },
                )
                return resp.status_code == 200
        except Exception:
            return False
