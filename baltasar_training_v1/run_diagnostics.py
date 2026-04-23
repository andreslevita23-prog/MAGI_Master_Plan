"""Run the Baltasar diagnostic phase."""

from pathlib import Path

from src.config import load_config
from src.diagnostics.pipeline import run_diagnostics


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run Baltasar diagnostics.")
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
        help="Existing run identifier to diagnose. Defaults to latest successful run.",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_config(config_path)
    run_diagnostics(config, project_root=config_path.resolve().parent.parent, run_id=args.run_id)


if __name__ == "__main__":
    main()
