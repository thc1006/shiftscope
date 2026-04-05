"""Integration tests for analyzer plugin discovery via entry points."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from shiftscope.core.analyzer import AnalyzerRegistry
from shiftscope.core.models import Report
from tests.stubs import StubAnalyzer


class TestEntryPointDiscovery:
    def test_discover_loads_registered_entry_points(self):
        """Simulate an installed package exposing an analyzer via entry points."""
        mock_ep = MagicMock()
        mock_ep.name = "stub-analyzer"
        mock_ep.load.return_value = StubAnalyzer

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            registry = AnalyzerRegistry()
            errors = registry.discover()

        assert errors == []
        assert len(registry.list_all()) == 1
        assert registry.get("stub-analyzer").name == "stub-analyzer"

    def test_discover_handles_import_error_gracefully(self):
        """If an entry point fails to load, it should log and continue."""
        mock_ep = MagicMock()
        mock_ep.name = "broken-analyzer"
        mock_ep.load.side_effect = ImportError("missing dependency")

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            registry = AnalyzerRegistry()
            errors = registry.discover()

        assert errors == ["broken-analyzer"]
        assert registry.list_all() == []

    def test_discover_handles_constructor_error(self):
        """If an analyzer class __init__ raises, it should be caught."""

        def bad_constructor():
            raise TypeError("required arg missing")

        mock_ep = MagicMock()
        mock_ep.name = "bad-init"
        mock_ep.load.return_value = bad_constructor

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            registry = AnalyzerRegistry()
            errors = registry.discover()

        assert errors == ["bad-init"]
        assert registry.list_all() == []

    def test_discover_multiple_mixed(self):
        """Mix of working and broken entry points."""
        good_ep = MagicMock()
        good_ep.name = "good"
        good_ep.load.return_value = StubAnalyzer

        bad_ep = MagicMock()
        bad_ep.name = "bad"
        bad_ep.load.side_effect = ImportError("nope")

        with patch("importlib.metadata.entry_points", return_value=[good_ep, bad_ep]):
            registry = AnalyzerRegistry()
            errors = registry.discover()

        assert errors == ["bad"]
        assert len(registry.list_all()) == 1
        assert registry.get("stub-analyzer").name == "stub-analyzer"

    def test_discover_non_callable_skipped(self):
        """If entry point loads a non-callable, it should be skipped (not registered)."""
        mock_ep = MagicMock()
        mock_ep.name = "not-callable"
        mock_ep.load.return_value = "just a string"

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            registry = AnalyzerRegistry()
            errors = registry.discover()

        assert errors == []
        assert registry.list_all() == []

    def test_discover_with_real_group_no_crash(self):
        """Calling discover with the real group shouldn't crash even with no plugins."""
        registry = AnalyzerRegistry()
        errors = registry.discover(group="shiftscope.analyzers")
        assert isinstance(errors, list)

    def test_discovered_analyzer_produces_valid_report(self):
        """End-to-end: discovered analyzer can analyze and produce a Report."""
        mock_ep = MagicMock()
        mock_ep.name = "stub"
        mock_ep.load.return_value = StubAnalyzer

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            registry = AnalyzerRegistry()
            registry.discover()

        analyzer = registry.get("stub-analyzer")
        report = analyzer.analyze("test.yaml")
        assert isinstance(report, Report)
        assert report.analyzer_name == "stub-analyzer"
        assert len(report.findings) >= 1
