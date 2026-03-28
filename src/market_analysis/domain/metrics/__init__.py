"""Advanced financial metrics for fund analysis.

Modules:
    formulas - Pure math functions (no domain deps)
    calculator - Orchestrator that computes all metrics from domain models
"""

from .calculator import AdvancedMetrics, compute_advanced_metrics

__all__ = ["AdvancedMetrics", "compute_advanced_metrics"]
