"""Ollama local model client."""

from __future__ import annotations

import logging
import time

import httpx

from market_analysis.ai.clients.base import LLMClient, LLMClientError, LLMResponse

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "deepseek-coder:6.7b"
DEFAULT_HOST = "http://localhost:11434"


class OllamaClient(LLMClient):
    """LLM client for models running locally via Ollama."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        model: str = DEFAULT_MODEL,
        timeout: int = 120,
    ) -> None:
        self._host = host.rstrip("/")
        self._model = model
        self._timeout = timeout

    @property
    def provider_name(self) -> str:
        return "ollama"

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 300,
        temperature: float = 0.3,
    ) -> LLMResponse:
        payload = {
            "model": self._model,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._host}/api/chat",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise LLMClientError(f"Ollama error: {exc}") from exc

        latency = (time.monotonic() - t0) * 1000
        text = data.get("message", {}).get("content", "").strip()

        if not text:
            raise LLMClientError("Ollama returned empty response")

        return LLMResponse(
            text=text,
            model=data.get("model", self._model),
            latency_ms=round(latency, 1),
            provider=self.provider_name,
        )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self._host}/api/tags")
                if resp.status_code != 200:
                    return False
                models = resp.json().get("models", [])
                base = self._model.split(":")[0].lower()
                return any(base in m.get("name", "").lower() for m in models)
        except Exception:
            return False
