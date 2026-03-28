"""Abstract base for LLM clients."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Normalized response from any LLM provider."""

    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    provider: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class LLMClient(ABC):
    """Protocol that all LLM clients must satisfy."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier."""

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 300,
        temperature: float = 0.3,
    ) -> LLMResponse:
        """Send a prompt and return the generated text.

        Raises:
            LLMClientError: on any recoverable failure.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable and ready."""


class LLMClientError(Exception):
    """Raised when an LLM call fails in a potentially recoverable way."""
