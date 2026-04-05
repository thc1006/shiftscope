"""Analyzer ABC and AnalyzerRegistry — behavioral contracts for migration analyzers.

An Analyzer is a collection of Rules for a specific migration domain.
The AnalyzerRegistry provides plugin discovery via importlib.metadata.entry_points.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from shiftscope.core.models import Finding, Report
from shiftscope.core.rule import Rule


class Analyzer(ABC):
    """Abstract base class for migration domain analyzers.

    Subclasses must define name, version, description, and implement
    analyze() and list_rules() methods.
    """

    name: str
    version: str
    description: str

    @abstractmethod
    def analyze(self, input_path: str, **kwargs: Any) -> Report:
        """Run all applicable rules against the input and produce a Report."""

    @abstractmethod
    def list_rules(self) -> list[Rule]:
        """Return all rules this analyzer can evaluate."""

    def run_rules(self, context: dict[str, Any]) -> list[Finding]:
        """Run all rules with applies_to short-circuit and collect findings.

        Shared helper to avoid repeating the applies_to → evaluate loop
        in every analyzer implementation.
        """
        findings: list[Finding] = []
        for rule in self.list_rules():
            if rule.applies_to(context):
                finding = rule.evaluate(context)
                if finding is not None:
                    findings.append(finding)
        return findings


class AnalyzerRegistry:
    """Registry for discovering and managing analyzer plugins.

    Analyzers can be registered manually or discovered via
    importlib.metadata.entry_points (Phase 2).
    """

    def __init__(self) -> None:
        self._analyzers: dict[str, Analyzer] = {}

    def register(self, analyzer: Analyzer) -> None:
        """Register an analyzer by its name."""
        self._analyzers[analyzer.name] = analyzer

    def get(self, name: str) -> Analyzer:
        """Get a registered analyzer by name. Raises KeyError if not found."""
        return self._analyzers[name]

    def list_all(self) -> list[Analyzer]:
        """Return all registered analyzers."""
        return list(self._analyzers.values())

    def discover(self, group: str = "shiftscope.analyzers") -> list[str]:
        """Discover and register analyzers from installed entry points.

        Returns a list of entry point names that failed to load.
        """
        import logging
        from importlib.metadata import entry_points

        logger = logging.getLogger(__name__)
        errors: list[str] = []

        eps = entry_points()
        discovered = eps.get(group, []) if isinstance(eps, dict) else eps.select(group=group)
        for ep in discovered:
            try:
                analyzer_cls = ep.load()
                if callable(analyzer_cls):
                    self.register(analyzer_cls())
            except Exception:
                logger.warning("Failed to load analyzer entry point: %s", ep.name, exc_info=True)
                errors.append(ep.name)
        return errors
