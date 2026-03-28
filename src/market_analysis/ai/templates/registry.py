"""Template registry that loads and serves prompt templates."""

from __future__ import annotations

import importlib.resources
from pathlib import Path
from typing import Optional

import yaml

from market_analysis.ai.templates.models import PromptTemplate


_TEMPLATES_DIR = Path(__file__).parent


class TemplateRegistry:
    """Central registry for all metric prompt templates.

    Loads templates from YAML and provides lookup by metric name or category.
    """

    def __init__(self, yaml_path: Optional[Path] = None) -> None:
        self._templates: dict[str, PromptTemplate] = {}
        self._by_category: dict[str, list[PromptTemplate]] = {}
        path = yaml_path or _TEMPLATES_DIR / "prompt_templates.yaml"
        self._load(path)

    # -- Public API ----------------------------------------------------------

    def get_template(self, metric_name: str) -> PromptTemplate:
        """Return template for a specific metric.

        Raises:
            KeyError: if metric_name is not found.
        """
        return self._templates[metric_name]

    def get_all_by_category(self, category: str) -> list[PromptTemplate]:
        """Return all templates in a category, sorted by priority."""
        return sorted(
            self._by_category.get(category, []),
            key=lambda t: t.priority,
        )

    def list_categories(self) -> list[str]:
        """Return available category names."""
        return sorted(self._by_category.keys())

    def list_metrics(self) -> list[str]:
        """Return all registered metric names."""
        return sorted(self._templates.keys())

    @property
    def system_prompt(self) -> str:
        """Return the shared system prompt loaded from YAML."""
        return self._system_prompt

    # -- Internal ------------------------------------------------------------

    def _load(self, path: Path) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self._system_prompt = data.get("system_prompt", "")

        for entry in data.get("templates", []):
            tpl = PromptTemplate(
                category=entry["category"],
                metric_name=entry["metric_name"],
                display_name=entry["display_name"],
                system_prompt=self._system_prompt,
                user_template=entry["user_template"],
                interpretation_scale=entry.get("interpretation_scale", {}),
                example_output=entry.get("example_output", ""),
                unit=entry.get("unit", ""),
                priority=entry.get("priority", 1),
                glossary_term=entry.get("glossary_term", ""),
                analogy=entry.get("analogy", ""),
                max_words=entry.get("max_words", 120),
            )
            self._templates[tpl.metric_name] = tpl
            self._by_category.setdefault(tpl.category, []).append(tpl)
