"""Run the full Baltasar training experiment."""

from pathlib import Path

from src.config import load_config
from src.models.training import run_training_experiment


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run Baltasar training experiment.")
    parser.add_argument(
        "--config",
        type=str,
        default="config/experiment.yaml",
        help="Path to experiment YAML config.",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_config(config_path)
    run_training_experiment(config, project_root=config_path.resolve().parent.parent)


if __name__ == "__main__":
    main()
