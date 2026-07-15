"""Statistical analysis, plots, and research tables."""

from analysis.report import (
    AnalysisPlan,
    ComparisonSpec,
    RunSpec,
    analyze_plan,
    load_analysis_plan,
)
from analysis.results import load_paired_outcomes, load_pass_fail_vector
from analysis.stats import (
    BootstrapInterval,
    McNemarResult,
    bootstrap_pass_at_1,
    mcnemar_exact,
)

__all__ = [
    "BootstrapInterval",
    "AnalysisPlan",
    "ComparisonSpec",
    "McNemarResult",
    "RunSpec",
    "analyze_plan",
    "bootstrap_pass_at_1",
    "load_paired_outcomes",
    "load_pass_fail_vector",
    "load_analysis_plan",
    "mcnemar_exact",
]
