"""Consolidate Baltasar v1.2 as the official laboratory baseline."""

from pathlib import Path

from src.config import load_config
from src.phase6.consolidation import run_v12_consolidation


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Consolidate Baltasar v1.2.")
    parser.add_argument(
        "--config",
        type=str,
        default="config/experiment.yaml",
        help="Path to experiment YAML config.",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_config(config_path)
    run_v12_consolidation(config, project_root=config_path.resolve().parent.parent)


if __name__ == "__main__":
    main()
