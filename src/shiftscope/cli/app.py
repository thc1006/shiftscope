"""CLI scaffolding — auto-generate Typer CLI from registered analyzers."""

from __future__ import annotations

import typer

from shiftscope.core.analyzer import AnalyzerRegistry
from shiftscope.render.json_renderer import render_json
from shiftscope.render.markdown_renderer import render_markdown


def build_cli(registry: AnalyzerRegistry) -> typer.Typer:
    """Build a Typer CLI app from a populated AnalyzerRegistry."""

    app = typer.Typer(
        name="shiftscope",
        help="Migration intelligence for cloud-native infrastructure.",
        no_args_is_help=True,
    )

    @app.command()
    def analyze(
        analyzer_name: str = typer.Argument(help="Name of the analyzer to run"),
        input_path: str = typer.Argument(help="Path to the input manifest/config"),
        output: str = typer.Option("json", help="Output format: json or markdown"),
    ) -> None:
        """Run a migration analyzer on an input file."""
        if output not in ("json", "markdown"):
            typer.echo(
                f"Error: unsupported output format '{output}'. Use 'json' or 'markdown'.",
                err=True,
            )
            raise typer.Exit(code=1)

        try:
            analyzer = registry.get(analyzer_name)
        except KeyError:
            typer.echo(f"Error: analyzer '{analyzer_name}' not found.", err=True)
            raise typer.Exit(code=1) from None

        try:
            report = analyzer.analyze(input_path)
        except FileNotFoundError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(code=1) from None
        except Exception as e:
            typer.echo(f"Error analyzing '{input_path}': {type(e).__name__}: {e}", err=True)
            raise typer.Exit(code=1) from None

        if output == "markdown":
            typer.echo(render_markdown(report))
        else:
            typer.echo(render_json(report))

    @app.command(name="list")
    def list_analyzers() -> None:
        """List all registered analyzers."""
        analyzers = registry.list_all()
        if not analyzers:
            typer.echo("No analyzers registered.")
            return
        for a in analyzers:
            typer.echo(f"  {a.name} (v{a.version}) — {a.description}")

    return app


def main() -> None:
    """Entry point for the shiftscope CLI."""
    registry = AnalyzerRegistry()
    errors = registry.discover()
    if errors:
        for name in errors:
            typer.echo(f"Warning: failed to load analyzer '{name}'", err=True)
    app = build_cli(registry)
    app()
