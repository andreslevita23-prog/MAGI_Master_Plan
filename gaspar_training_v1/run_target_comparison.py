from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from src.gaspar.data import load_dataset
from src.gaspar.targeting import attach_heuristic_target


def target_distribution(data: pd.DataFrame, version: str) -> dict:
    prepared = attach_heuristic_target(data, target_version=version, overwrite=True)
    counts = prepared["voto"].value_counts().reindex(["GOOD", "FAIR", "POOR"]).fillna(0).astype(int)
    pct = (counts / max(1, len(prepared)) * 100).round(2)
    return {
        "target_version": version,
        "rows": int(len(prepared)),
        "counts": counts.to_dict(),
        "percent": pct.to_dict(),
        "score": {
            "min": float(prepared["score_oportunidad"].min()),
            "max": float(prepared["score_oportunidad"].max()),
            "mean": float(prepared["score_oportunidad"].mean()),
            "p50": float(prepared["score_oportunidad"].quantile(0.50)),
            "p95": float(prepared["score_oportunidad"].quantile(0.95)),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Gaspar heuristic target versions.")
    parser.add_argument("--data-path", required=True, help="CSV/JSONL file or directory exported by Bot_A_sub2.")
    parser.add_argument("--output-root", default=".", help="Root where comparison report is written.")
    args = parser.parse_args()

    try:
        raw = load_dataset(Path(args.data_path))
    except (FileNotFoundError, ValueError) as exc:
        print(f"Gaspar target comparison aborted: {exc}", file=sys.stderr)
        sys.exit(2)

    comparison = {
        "data_path": str(args.data_path),
        "targets": [
            target_distribution(raw, "v1"),
            target_distribution(raw, "v2"),
            target_distribution(raw, "v3"),
            target_distribution(raw, "v4"),
        ],
    }
    output_dir = Path(args.output_root) / "artifacts" / "metrics"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "gaspar_target_comparison.json"
    output_path.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    print(json.dumps(comparison, indent=2))


if __name__ == "__main__":
    main()
