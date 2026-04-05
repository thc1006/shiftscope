"""Smoke tests for installed package — verifies packaging correctness."""

from __future__ import annotations


class TestPackageImports:
    """Verify all public API imports work."""

    def test_import_shiftscope(self):
        from shiftscope import __version__

        assert isinstance(__version__, str)
        assert len(__version__) >= 5  # at least "X.Y.Z"

    def test_import_core_types(self):
        from shiftscope import Analyzer, AnalyzerRegistry, Finding, Report, Rule, Severity

        assert Finding is not None
        assert Report is not None
        assert Rule is not None
        assert Severity is not None
        assert Analyzer is not None
        assert AnalyzerRegistry is not None

    def test_import_all_analyzers(self):
        from shiftscope.analyzers.agent_readiness import AgentReadinessAnalyzer
        from shiftscope.analyzers.dra_network import DRANetworkAnalyzer
        from shiftscope.analyzers.gateway_api import GatewayApiAnalyzer
        from shiftscope.analyzers.helm4 import Helm4ReadinessAnalyzer
        from shiftscope.analyzers.telco_intent import TelcoIntentAnalyzer

        assert GatewayApiAnalyzer.name == "gateway-api"
        assert DRANetworkAnalyzer.name == "dra-network"
        assert Helm4ReadinessAnalyzer.name == "helm4-readiness"
        assert TelcoIntentAnalyzer.name == "telco-intent"
        assert AgentReadinessAnalyzer.name == "agent-readiness"

    def test_import_renderers(self):
        from shiftscope.render.json_renderer import render_json
        from shiftscope.render.markdown_renderer import render_markdown

        assert callable(render_json)
        assert callable(render_markdown)

    def test_import_eval_harness(self):
        from shiftscope.eval.harness import EvalCase, EvalHarness, EvalResult

        assert EvalCase is not None
        assert EvalHarness is not None
        assert EvalResult is not None

    def test_import_mcp_bridge(self):
        from shiftscope.mcp.bridge import MCPBridgeError, build_mcp_tools

        assert callable(build_mcp_tools)
        assert issubclass(MCPBridgeError, Exception)


class TestRegistryDiscovery:
    """Verify all 5 analyzers are discoverable via entry points after install."""

    def test_manual_registration_all_five(self):
        from shiftscope.analyzers.agent_readiness import AgentReadinessAnalyzer
        from shiftscope.analyzers.dra_network import DRANetworkAnalyzer
        from shiftscope.analyzers.gateway_api import GatewayApiAnalyzer
        from shiftscope.analyzers.helm4 import Helm4ReadinessAnalyzer
        from shiftscope.analyzers.telco_intent import TelcoIntentAnalyzer
        from shiftscope.core.analyzer import AnalyzerRegistry

        registry = AnalyzerRegistry()
        for cls in [
            GatewayApiAnalyzer,
            DRANetworkAnalyzer,
            Helm4ReadinessAnalyzer,
            TelcoIntentAnalyzer,
            AgentReadinessAnalyzer,
        ]:
            registry.register(cls())

        assert len(registry.list_all()) == 5
        names = {a.name for a in registry.list_all()}
        assert names == {
            "gateway-api",
            "dra-network",
            "helm4-readiness",
            "telco-intent",
            "agent-readiness",
        }

    def test_each_analyzer_has_rules(self):
        from shiftscope.analyzers.agent_readiness import AgentReadinessAnalyzer
        from shiftscope.analyzers.dra_network import DRANetworkAnalyzer
        from shiftscope.analyzers.gateway_api import GatewayApiAnalyzer
        from shiftscope.analyzers.helm4 import Helm4ReadinessAnalyzer
        from shiftscope.analyzers.telco_intent import TelcoIntentAnalyzer

        for cls in [
            GatewayApiAnalyzer,
            DRANetworkAnalyzer,
            Helm4ReadinessAnalyzer,
            TelcoIntentAnalyzer,
            AgentReadinessAnalyzer,
        ]:
            analyzer = cls()
            rules = analyzer.list_rules()
            assert len(rules) >= 1, f"{analyzer.name} has no rules"


class TestEntryPointDiscoverySmoke:
    """Verify discover() finds all 5 analyzers via entry points (requires editable install)."""

    def test_discover_finds_all_analyzers(self):
        from unittest.mock import MagicMock, patch

        from shiftscope.analyzers.agent_readiness import AgentReadinessAnalyzer
        from shiftscope.analyzers.dra_network import DRANetworkAnalyzer
        from shiftscope.analyzers.gateway_api import GatewayApiAnalyzer
        from shiftscope.analyzers.helm4 import Helm4ReadinessAnalyzer
        from shiftscope.analyzers.telco_intent import TelcoIntentAnalyzer
        from shiftscope.core.analyzer import AnalyzerRegistry

        mock_eps = []
        for name, cls in [
            ("gateway-api", GatewayApiAnalyzer),
            ("dra-network", DRANetworkAnalyzer),
            ("helm4-readiness", Helm4ReadinessAnalyzer),
            ("telco-intent", TelcoIntentAnalyzer),
            ("agent-readiness", AgentReadinessAnalyzer),
        ]:
            ep = MagicMock()
            ep.name = name
            ep.load.return_value = cls
            mock_eps.append(ep)

        with patch("importlib.metadata.entry_points", return_value=mock_eps):
            registry = AnalyzerRegistry()
            errors = registry.discover()

        assert errors == []
        assert len(registry.list_all()) == 5
        names = {a.name for a in registry.list_all()}
        assert names == {
            "gateway-api",
            "dra-network",
            "helm4-readiness",
            "telco-intent",
            "agent-readiness",
        }


class TestCLISmoke:
    """Verify CLI entry point works."""

    def test_cli_importable(self):
        from shiftscope.cli.app import build_cli, main

        assert callable(build_cli)
        assert callable(main)

    def test_cli_list_command(self):
        from typer.testing import CliRunner

        from shiftscope.analyzers.gateway_api import GatewayApiAnalyzer
        from shiftscope.cli.app import build_cli
        from shiftscope.core.analyzer import AnalyzerRegistry

        registry = AnalyzerRegistry()
        registry.register(GatewayApiAnalyzer())
        app = build_cli(registry)

        runner = CliRunner()
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "gateway-api" in result.output
