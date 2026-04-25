"""Generate the Baltasar v1.2 executive markdown, HTML and PDF report."""

from pathlib import Path

from src.config import load_config
from src.phase6.executive_report import generate_v12_executive_report


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate Baltasar v1.2 executive PDF report.")
    parser.add_argument(
        "--config",
        type=str,
        default="config/experiment.yaml",
        help="Path to experiment YAML config.",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_config(config_path)
    generate_v12_executive_report(config, project_root=config_path.resolve().parent.parent)


if __name__ == "__main__":
    main()
