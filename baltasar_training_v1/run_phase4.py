"""Consolidate Baltasar v1.1 as the official baseline."""

from pathlib import Path

from src.config import load_config
from src.phase4.consolidation import run_phase4_consolidation


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Consolidate Baltasar v1.1 official baseline.")
    parser.add_argument(
        "--config",
        type=str,
        default="config/experiment.yaml",
        help="Path to experiment YAML config.",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Reference run identifier. Defaults to latest phase 3 summary.",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_config(config_path)
    run_phase4_consolidation(config, project_root=config_path.resolve().parent.parent, run_id=args.run_id)


if __name__ == "__main__":
    main()
