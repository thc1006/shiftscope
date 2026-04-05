"""Helm chart parser — extracts chart metadata and content for analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def parse_chart(chart_dir: str | Path) -> dict[str, Any]:
    """Parse a Helm chart directory and extract analysis context."""
    chart_dir = Path(chart_dir)
    chart_yaml = chart_dir / "Chart.yaml"

    if not chart_yaml.exists():
        raise FileNotFoundError(f"Missing Chart.yaml in {chart_dir}")

    chart_data = yaml.safe_load(chart_yaml.read_text(encoding="utf-8")) or {}
    api_version = chart_data.get("apiVersion")
    chart_name = chart_data.get("name")

    templates_content = ""
    templates_dir = chart_dir / "templates"
    if templates_dir.exists():
        for p in sorted(p for p in templates_dir.rglob("*") if p.is_file()):
            if p.name.endswith((".yaml", ".yml", ".tpl")):
                try:
                    templates_content += f"\n# file: {p.name}\n" + p.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue

    helmignore = ""
    helmignore_path = chart_dir / ".helmignore"
    if helmignore_path.exists():
        helmignore = helmignore_path.read_text(encoding="utf-8")

    values_text = ""
    values_path = chart_dir / "values.yaml"
    if values_path.exists():
        values_text = values_path.read_text(encoding="utf-8")

    return {
        "api_version": api_version,
        "name": chart_name,
        "chart_dir": str(chart_dir),
        "templates_content": templates_content,
        "helmignore": helmignore,
        "values_text": values_text,
    }
