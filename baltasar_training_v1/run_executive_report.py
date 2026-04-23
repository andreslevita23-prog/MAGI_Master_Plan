"""Generate the final executive report for Baltasar v1.1."""

from pathlib import Path

from src.config import load_config
from src.phase4.executive import generate_executive_report


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate Baltasar v1.1 executive report.")
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
        help="Reference run identifier. Defaults to latest official v1.1 summary.",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_config(config_path)
    generate_executive_report(config, project_root=config_path.resolve().parent.parent, run_id=args.run_id)


if __name__ == "__main__":
    main()
