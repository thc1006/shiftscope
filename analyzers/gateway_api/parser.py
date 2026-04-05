"""Ingress manifest parser — extracts Ingress resources from Kubernetes YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_ingresses(path: str | Path) -> list[dict[str, Any]]:
    """Parse Kubernetes YAML and extract Ingress resources as dicts.

    Returns a list of dicts, each with:
      - name, namespace, annotations, tls_hosts, rules
    """
    ingresses: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for doc in yaml.safe_load_all(f):
            if not isinstance(doc, dict):
                continue
            if doc.get("kind") != "Ingress":
                continue
            metadata = doc.get("metadata") or {}
            spec = doc.get("spec") or {}
            tls_hosts: list[str] = []
            for tls_entry in spec.get("tls") or []:
                tls_hosts.extend(tls_entry.get("hosts") or [])
            ingresses.append({
                "name": metadata.get("name", "unknown"),
                "namespace": metadata.get("namespace", "default"),
                "annotations": metadata.get("annotations") or {},
                "tls_hosts": tls_hosts,
                "rules": spec.get("rules") or [],
            })
    return ingresses
