"""NetworkIntent JSON parser."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_intent(path: str | Path) -> dict[str, Any]:
    """Parse a NetworkIntent JSON file and return a normalized dict."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    alpha_raw = data.get("alpha") or {}
    return {
        "name": data.get("name", ""),
        "namespace": data.get("namespace", "default"),
        "workload_kind": data.get("workload_kind", "Job"),
        "gpu_count": int(data.get("gpu_count", 0)),
        "requires_rdma": bool(data.get("requires_rdma", False)),
        "min_bandwidth_gbps": data.get("min_bandwidth_gbps"),
        "low_latency": bool(data.get("low_latency", False)),
        "require_topology_alignment": bool(data.get("require_topology_alignment", False)),
        "secondary_networks": list(data.get("secondary_networks") or []),
        "preferred_device_class": data.get("preferred_device_class"),
        "legacy_bridge": bool(data.get("legacy_bridge", False)),
        "alpha": {
            "extended_resource_mapping": bool(alpha_raw.get("extended_resource_mapping", False)),
            "consumable_capacity": bool(alpha_raw.get("consumable_capacity", False)),
            "partitionable_devices": bool(alpha_raw.get("partitionable_devices", False)),
        },
    }
