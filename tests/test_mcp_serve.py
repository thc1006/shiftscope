"""Tests for mcp-serve CLI command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from shiftscope.cli.app import build_cli
from shiftscope.core.analyzer import AnalyzerRegistry
from tests.stubs import StubAnalyzer


def _build_app():
    registry = AnalyzerRegistry()
    registry.register(StubAnalyzer())
    return build_cli(registry)


class TestMCPServeCommand:
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(_build_app(), ["mcp-serve", "--help"])
        assert result.exit_code == 0
        assert "stdio" in result.output

    def test_no_transport_error(self):
        runner = CliRunner()
        result = runner.invoke(_build_app(), ["mcp-serve"])
        assert result.exit_code == 1
        assert "specify --stdio or --http" in result.output

    def test_mutual_exclusion_error(self):
        runner = CliRunner()
        result = runner.invoke(_build_app(), ["mcp-serve", "--stdio", "--http"])
        assert result.exit_code == 1
        assert "mutually exclusive" in result.output

    def test_stdio_calls_mcp_run(self):
        mock_mcp = MagicMock()
        with patch("shiftscope.mcp.bridge.create_mcp_server", return_value=mock_mcp) as mock_create:
            runner = CliRunner()
            result = runner.invoke(_build_app(), ["mcp-serve", "--stdio"])
            assert result.exit_code == 0
            mock_create.assert_called_once()
            # stdio mode should NOT pass host/port
            assert "host" not in (mock_create.call_args[1] or {})
            mock_mcp.run.assert_called_once_with(transport="stdio")

    def test_http_calls_mcp_run_with_port(self):
        mock_mcp = MagicMock()
        with patch("shiftscope.mcp.bridge.create_mcp_server", return_value=mock_mcp) as mock_create:
            runner = CliRunner()
            result = runner.invoke(
                _build_app(), ["mcp-serve", "--http", "--host", "0.0.0.0", "--port", "9090"]
            )
            assert result.exit_code == 0
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args
            assert call_kwargs[1]["host"] == "0.0.0.0"
            assert call_kwargs[1]["port"] == 9090
            mock_mcp.run.assert_called_once_with(transport="streamable-http")

    def test_http_default_host_is_localhost(self):
        mock_mcp = MagicMock()
        with patch("shiftscope.mcp.bridge.create_mcp_server", return_value=mock_mcp) as mock_create:
            runner = CliRunner()
            result = runner.invoke(_build_app(), ["mcp-serve", "--http"])
            assert result.exit_code == 0
            call_kwargs = mock_create.call_args
            assert call_kwargs[1]["host"] == "127.0.0.1"
