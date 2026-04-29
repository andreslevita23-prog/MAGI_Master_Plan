from __future__ import annotations

import argparse
import json
from dataclasses import fields
from pathlib import Path
from typing import Any

from magi.baltasar import BaltasarRuleBased
from magi.ceo_magi import CeoMagiRuleBased
from magi.gaspar import GasparRuleBased
from magi.melchor import MelchorRuleBased
from magi.adapters.baltasar_real_adapter import BaltasarRealAdapter
from magi.adapters.gaspar_real_adapter import GasparRealAdapter
from magi.adapters.melchor_real_adapter import MelchorRealAdapter
from simulator.ceo_training_dataset import generate_ceo_training_dataset
from simulator.execution import ExecutionEngine
from simulator.loaders import load_bot_a_snapshots
from simulator.metrics import calculate_metrics, metrics_markdown
from simulator.reporting import create_run_dir, write_config, write_csv, write_json, write_jsonl, write_manifest, write_text
from simulator.schemas import SimulationConfig
from simulator.timeline import iter_timeline
from simulator.validation import build_quality_report, validate_snapshot


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    if args.input_path:
        config = replace_config(config, input_path=args.input_path)
    if args.output_root:
        config = replace_config(config, output_root=args.output_root)

    snapshots, parse_errors = load_bot_a_snapshots(config.input_path, config.input_format)
    snapshots = apply_filters(snapshots, config.filters)
    quality = build_quality_report(snapshots, parse_errors)
    ordered = list(iter_timeline(snapshots))

    melchor = build_melchor(config)
    baltasar = build_baltasar(config)
    gaspar = build_gaspar(config)
    if config.ceo_training_mode:
        run_dir, summary = generate_ceo_training_dataset(config, ordered, melchor, baltasar, gaspar, quality)
        print(f"CEO training dataset created: {run_dir}")
        print(f"Snapshots processed: {len(ordered)}")
        print(f"Records written: {summary['records_generated']}")
        print(f"Invalid snapshots: {quality.invalid_snapshots}")
        return 0

    ceo = CeoMagiRuleBased(config.ceo_magi)
    execution = ExecutionEngine(config.execution)

    votes = []
    decisions = []
    last_snapshot = None
    for snapshot in ordered:
        last_snapshot = snapshot
        baltasar_vote = baltasar.evaluate(snapshot)
        gaspar_vote = evaluate_gaspar(gaspar, snapshot, baltasar_vote)
        melchor_vote = melchor.evaluate(snapshot)
        votes.extend([melchor_vote, baltasar_vote, gaspar_vote])
        decision = ceo.decide(snapshot, melchor_vote, baltasar_vote, gaspar_vote)
        decisions.append(decision)
        execution.on_snapshot(snapshot, decision)

    execution.close_end_of_data(last_snapshot)
    metrics = calculate_metrics(execution.closed_trades)

    run_dir = create_run_dir(config.output_root, config.run_name)
    write_config(run_dir / "config_resolved.yaml", config)
    write_json(run_dir / "data_quality_report.json", quality)
    write_jsonl(run_dir / "votes.jsonl", votes)
    write_jsonl(run_dir / "ceo_decisions.jsonl", decisions)
    write_jsonl(run_dir / "trades.jsonl", execution.closed_trades)
    write_csv(run_dir / "closed_trades.csv", execution.closed_trades, CLOSED_TRADE_FIELDS)
    write_csv(run_dir / "equity_curve.csv", execution.equity_curve, EQUITY_CURVE_FIELDS)
    write_json(run_dir / "metrics.json", metrics)
    write_text(run_dir / "metrics.md", metrics_markdown(metrics))
    write_manifest(
        run_dir / "run_manifest.json",
        config,
        quality,
        {
            "votes": len(votes),
            "ceo_decisions": len(decisions),
            "snapshots_processed": len(ordered),
            "closed_trades": len(execution.closed_trades),
            "equity_points": len(execution.equity_curve),
            "trade_attempts_blocked_by_open_trade": execution.trade_attempts_blocked_by_open_trade,
        },
    )

    print(f"Simulation run created: {run_dir}")
    print(f"Snapshots processed: {len(ordered)}")
    print(f"Votes written: {len(votes)}")
    print(f"CEO decisions written: {len(decisions)}")
    print(f"Closed trades written: {len(execution.closed_trades)}")
    print(f"Invalid snapshots: {quality.invalid_snapshots}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run MAGI simulator v0.1.")
    parser.add_argument("--config", default="config/simulator_v01.yaml", help="Path to simulator config.")
    parser.add_argument("--input-path", default=None, help="Override Bot A input dataset path.")
    parser.add_argument("--output-root", default=None, help="Override output root.")
    return parser.parse_args()


def load_config(path: str | Path) -> SimulationConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return SimulationConfig(
        schema_version=data.get("schema_version", "simulator_config_v0.1"),
        input_path=data.get("input_path", "data/input"),
        output_root=data.get("output_root", "data/output/simulations"),
        input_format=data.get("input_format", "auto"),
        run_name=data.get("run_name", "magi_v01_phase1"),
        melchor_mode=data.get("melchor_mode", data.get("melchor", {}).get("mode", "rule_based")),
        baltasar_mode=data.get("baltasar_mode", data.get("baltasar", {}).get("mode", "rule_based")),
        gaspar_mode=data.get("gaspar_mode", data.get("gaspar", {}).get("mode", "rule_based")),
        ceo_training_mode=bool(data.get("ceo_training_mode", False)),
        horizons_bars=list(data.get("horizons_bars", [12, 48, 96, 288])),
        output_ceo_training_path=data.get("output_ceo_training_path", "data/output/ceo_training"),
        flat_threshold_pips=float(data.get("flat_threshold_pips", 3.0)),
        filters=data.get("filters", {}),
        melchor=data.get("melchor", {}),
        baltasar=data.get("baltasar", {}),
        gaspar=data.get("gaspar", {}),
        ceo_magi=data.get("ceo_magi", {}),
        execution=data.get("execution", {}),
    )


def replace_config(config: SimulationConfig, **changes: Any) -> SimulationConfig:
    data = {field.name: getattr(config, field.name) for field in fields(config)}
    data.update(changes)
    return SimulationConfig(**data)


def apply_filters(snapshots, filters: dict[str, Any]):
    symbols = {str(item) for item in filters.get("symbols", [])}
    only_valid = bool(filters.get("only_valid_snapshots", False))
    filtered = []
    for snapshot in snapshots:
        if symbols and snapshot.symbol not in symbols:
            continue
        if only_valid and any(issue.severity == "error" for issue in validate_snapshot(snapshot)):
            continue
        filtered.append(snapshot)
    return filtered


def build_melchor(config: SimulationConfig):
    mode = str(config.melchor_mode or "rule_based").lower()
    if mode == "rule_based":
        return MelchorRuleBased(config.melchor)
    if mode == "real":
        return MelchorRealAdapter(config.melchor, config.execution)
    raise ValueError(f"Unsupported melchor_mode: {config.melchor_mode}")


def build_baltasar(config: SimulationConfig):
    mode = str(config.baltasar_mode or "rule_based").lower()
    if mode == "rule_based":
        return BaltasarRuleBased(config.baltasar)
    if mode == "real":
        return BaltasarRealAdapter(config.baltasar)
    raise ValueError(f"Unsupported baltasar_mode: {config.baltasar_mode}")


def build_gaspar(config: SimulationConfig):
    mode = str(config.gaspar_mode or "rule_based").lower()
    if mode == "rule_based":
        return GasparRuleBased(config.gaspar)
    if mode == "real":
        return GasparRealAdapter(config.gaspar)
    raise ValueError(f"Unsupported gaspar_mode: {config.gaspar_mode}")


def evaluate_gaspar(gaspar, snapshot, baltasar_vote):
    try:
        return gaspar.evaluate(snapshot, baltasar_vote)
    except TypeError:
        return gaspar.evaluate(snapshot)


CLOSED_TRADE_FIELDS = [
    "schema_version",
    "trade_id",
    "decision_id",
    "entry_snapshot_id",
    "exit_snapshot_id",
    "symbol",
    "direction",
    "entry_timestamp",
    "exit_timestamp",
    "entry_price",
    "exit_price",
    "sl",
    "tp",
    "exit_reason",
    "pnl_r",
    "snapshots_held",
    "ambiguous_intrabar",
]

EQUITY_CURVE_FIELDS = [
    "timestamp",
    "snapshot_id",
    "closed_trades",
    "equity_r",
    "drawdown_r",
]


if __name__ == "__main__":
    raise SystemExit(main())
