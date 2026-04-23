"""Dataset loading helpers."""

from __future__ import annotations

from fnmatch import fnmatch
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pandas as pd


def resolve_path(project_root: Path, configured_path: str) -> Path:
    """Resolve config paths relative to the project root."""
    path = Path(configured_path)
    return path if path.is_absolute() else (project_root / path).resolve()


def load_dataset(config: dict, project_root: Path) -> pd.DataFrame:
    """Load the configured dataset source."""
    source = config["dataset"]["source"]
    source_type = source["type"].lower()
    dataset_path = resolve_path(project_root, source["path"])

    if source_type == "zip":
        return load_csvs_from_zip(dataset_path, source.get("zip_glob", "*.csv"))
    if source_type == "csv":
        return pd.read_csv(dataset_path)

    raise ValueError(f"Unsupported dataset source type: {source_type}")


def load_csvs_from_zip(zip_path: Path, pattern: str = "*.csv") -> pd.DataFrame:
    """Read and concatenate matching CSV files from a zip archive."""
    frames: list[pd.DataFrame] = []
    with ZipFile(zip_path) as archive:
        for entry in archive.namelist():
            if fnmatch(entry, pattern):
                with archive.open(entry) as file:
                    frames.append(pd.read_csv(BytesIO(file.read())))

    if not frames:
        raise FileNotFoundError(f"No files matching {pattern!r} found inside {zip_path}.")

    return pd.concat(frames, ignore_index=True)
