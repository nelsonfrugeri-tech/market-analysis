"""Data models for prompt templates."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class PromptTemplate:
    """Structured template for LLM-powered metric explanation.

    Each template encodes:
    - What the metric is (system_prompt sets the tone)
    - How to ask for an explanation (user_template with placeholders)
    - How to judge the value (interpretation_scale)
    - What good output looks like (example_output)
    """

    category: str  # "performance" | "risk" | "efficiency" | "consistency"
    metric_name: str  # e.g. "sharpe_ratio"
    display_name: str  # e.g. "Indice Sharpe"
    system_prompt: str  # Tone/voice instructions for the LLM
    user_template: str  # Template with {value}, {benchmark}, {period}, etc.
    interpretation_scale: dict[str, str]  # e.g. {"low": "<0.5", "high": ">1.0"}
    example_output: str  # Example of desired output
    unit: str = ""  # "%" | "x" | "R$" | ""
    priority: int = 1  # Display order within category (1 = most important)
    glossary_term: str = ""  # Plain-language definition (1 sentence)
    analogy: str = ""  # Real-world analogy for the concept
    max_words: int = 120  # Max words for the explanation
