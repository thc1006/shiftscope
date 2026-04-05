"""Helm chart parser — extracts chart metadata and content for analysis."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def parse_chart(chart_dir: str | Path) -> dict[str, Any]:
    """Parse a Helm chart directory and extract analysis context."""
    chart_dir = Path(chart_dir)
    chart_yaml = chart_dir / "Chart.yaml"

    if not chart_yaml.exists():
        raise FileNotFoundError(f"Missing Chart.yaml in {chart_dir}")

    chart_text = chart_yaml.read_text(encoding="utf-8")
    api_match = re.search(r"^apiVersion:\s*(.+)$", chart_text, re.MULTILINE)
    name_match = re.search(r"^name:\s*(.+)$", chart_text, re.MULTILINE)

    templates_content = ""
    templates_dir = chart_dir / "templates"
    if templates_dir.exists():
        for p in sorted(templates_dir.rglob("*.yaml")):
            templates_content += f"\n# file: {p.name}\n" + p.read_text(encoding="utf-8")

    helmignore = ""
    helmignore_path = chart_dir / ".helmignore"
    if helmignore_path.exists():
        helmignore = helmignore_path.read_text(encoding="utf-8")

    values_text = ""
    values_path = chart_dir / "values.yaml"
    if values_path.exists():
        values_text = values_path.read_text(encoding="utf-8")

    return {
        "api_version": api_match.group(1).strip() if api_match else None,
        "name": name_match.group(1).strip() if name_match else None,
        "chart_dir": str(chart_dir),
        "templates_content": templates_content,
        "helmignore": helmignore,
        "values_text": values_text,
    }
