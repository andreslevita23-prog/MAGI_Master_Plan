from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.gaspar.diagnostics import run_diagnostics


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Gaspar dataset diagnostics.")
    parser.add_argument("--data-path", default="data", help="CSV/JSONL file or directory exported by Bot_A_sub2.")
    parser.add_argument("--output-root", default=".", help="Root where diagnostics are written.")
    parser.add_argument("--target-version", choices=["v1", "v2", "v3"], default="v1", help="Heuristic target version.")
    args = parser.parse_args()

    try:
        summary = run_diagnostics(Path(args.data_path), Path(args.output_root), target_version=args.target_version)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Gaspar diagnostics aborted: {exc}", file=sys.stderr)
        sys.exit(2)

    print(f"Gaspar diagnostics complete. target={args.target_version} rows={summary['rows']}")


if __name__ == "__main__":
    main()
