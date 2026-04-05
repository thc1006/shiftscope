"""ShiftScope — Migration intelligence for cloud-native infrastructure."""

__version__ = "0.3.1"

from shiftscope.core.analyzer import Analyzer, AnalyzerRegistry
from shiftscope.core.models import Finding, Report, Severity
from shiftscope.core.rule import Rule

__all__ = [
    "Analyzer",
    "AnalyzerRegistry",
    "Finding",
    "Report",
    "Rule",
    "Severity",
]
