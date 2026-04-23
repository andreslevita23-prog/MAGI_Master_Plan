"""Run Baltasar phase 3 experiments."""

from pathlib import Path

from src.config import load_config
from src.phase3.pipeline import run_phase3


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run Baltasar phase 3 experiments.")
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
        help="Reference training run identifier. Defaults to latest successful run.",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_config(config_path)
    run_phase3(config, project_root=config_path.resolve().parent.parent, run_id=args.run_id)


if __name__ == "__main__":
    main()
