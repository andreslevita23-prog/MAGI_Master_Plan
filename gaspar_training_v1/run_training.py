from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.gaspar.training import train_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Gaspar opportunity-quality baseline.")
    parser.add_argument("--data-path", default="data", help="CSV/JSONL file or directory exported by Bot_A_sub2.")
    parser.add_argument("--output-root", default=".", help="Root where artifacts and reports are written.")
    parser.add_argument("--target-version", choices=["v1", "v2", "v3", "v4"], default="v1", help="Heuristic target version.")
    args = parser.parse_args()

    try:
        metrics = train_pipeline(Path(args.data_path), Path(args.output_root), target_version=args.target_version)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Gaspar training aborted: {exc}", file=sys.stderr)
        sys.exit(2)

    print(f"Gaspar training complete. target={args.target_version} rows={metrics['rows']} f1_macro={metrics['f1_macro']:.4f}")


if __name__ == "__main__":
    main()
