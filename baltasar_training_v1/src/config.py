"""Configuration helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import json
import subprocess

try:
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback for limited runtimes
    yaml = None


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load a YAML configuration file."""
    if yaml is not None:
        with config_path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file)

    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            f"Get-Content -Raw '{config_path}' | "
            "ConvertFrom-Yaml | ConvertTo-Json -Depth 100"
        ),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=True)
    return json.loads(completed.stdout)
