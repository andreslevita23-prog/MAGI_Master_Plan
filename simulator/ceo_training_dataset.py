from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from magi.contracts import MageVote
from simulator.reporting import create_run_dir, to_jsonable, write_json, write_jsonl, write_text
from simulator.schemas import DataQualityReport, SimulationConfig, Snapshot, timestamp_to_iso
from simulator.validation import validate_snapshot


SCHEMA_VERSION = "ceo_training_record_v0.1"
FORBIDDEN_FEATURE_KEYWORDS = (
    "future",
    "outcome",
    "pnl",
    "mfe",
    "mae",
    "target",
    "label",
    "forward_return",
    "hit_tp",
    "hit_sl",
)


def generate_ceo_training_dataset(
    config: SimulationConfig,
    snapshots: list[Snapshot],
    melchor: Any,
    baltasar: Any,
    gaspar: Any,
    quality: DataQualityReport,
) -> tuple[Path, dict[str, Any]]:
    records, summary = build_ceo_training_records(
        snapshots=snapshots,
        melchor=melchor,
        baltasar=baltasar,
        gaspar=gaspar,
        horizons_bars=config.horizons_bars,
        flat_threshold_pips=config.flat_threshold_pips,
    )
    run_dir = create_run_dir(config.output_ceo_training_path, config.run_name)
    summary = {
        **summary,
        "schema_version": "ceo_training_summary_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config": {
            "input_path": config.input_path,
            "input_format": config.input_format,
            "run_name": config.run_name,
            "melchor_mode": config.melchor_mode,
            "baltasar_mode": config.baltasar_mode,
            "gaspar_mode": config.gaspar_mode,
            "horizons_bars": config.horizons_bars,
            "flat_threshold_pips": config.flat_threshold_pips,
        },
        "quality_summary": {
            "total_snapshots": quality.total_snapshots,
            "valid_snapshots": quality.valid_snapshots,
            "invalid_snapshots": quality.invalid_snapshots,
            "parse_errors": len(quality.parse_errors),
        },
    }
    write_jsonl(run_dir / "ceo_training_records.jsonl", records)
    write_json(run_dir / "ceo_training_summary.json", summary)
    write_text(run_dir / "ceo_training_summary.md", ceo_training_summary_markdown(summary))
    return run_dir, summary


def build_ceo_training_records(
    snapshots: list[Snapshot],
    melchor: Any,
    baltasar: Any,
    gaspar: Any,
    horizons_bars: list[int],
    flat_threshold_pips: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_symbol = group_by_symbol(snapshots)
    records: list[dict[str, Any]] = []
    skipped = Counter()
    vote_counts = Counter()
    outcome_horizons = Counter()

    for symbol, symbol_snapshots in by_symbol.items():
        for index, snapshot in enumerate(symbol_snapshots):
            if has_validation_error(snapshot):
                skipped["invalid_snapshot"] += 1
                continue

            baltasar_vote = baltasar.evaluate(snapshot)
            gaspar_vote = evaluate_gaspar(gaspar, snapshot, baltasar_vote)
            melchor_vote = melchor.evaluate(snapshot)
            future_outcomes = calculate_future_outcomes(
                symbol_snapshots=symbol_snapshots,
                index=index,
                horizons_bars=horizons_bars,
                proposed_direction=baltasar_vote.direction or "NEUTRAL",
                flat_threshold_pips=flat_threshold_pips,
            )
            if not future_outcomes:
                skipped["insufficient_future_bars"] += 1
                continue

            for horizon in future_outcomes:
                outcome_horizons[str(horizon)] += 1
            vote_counts[f"melchor_{melchor_vote.vote or 'NONE'}"] += 1
            vote_counts[f"baltasar_{baltasar_vote.direction or 'NONE'}"] += 1
            vote_counts[f"gaspar_{gaspar_vote.quality or 'NONE'}"] += 1

            features = features_at_decision_time(snapshot)
            leakage_guard = {
                "features_cutoff_timestamp": timestamp_to_iso(snapshot.timestamp),
                "labels_generated_after_timestamp": timestamp_to_iso(snapshot.timestamp),
                "forbidden_feature_keywords": list(FORBIDDEN_FEATURE_KEYWORDS),
                "removed_feature_paths": find_leakage_paths(snapshot.raw),
                "features_clean": not has_forbidden_key(features),
            }
            records.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "snapshot_id": snapshot.snapshot_id,
                    "symbol": symbol,
                    "timestamp": timestamp_to_iso(snapshot.timestamp),
                    "anchor_bar_timestamp": timestamp_to_iso(snapshot.anchor_bar_timestamp),
                    "features_at_decision_time": features,
                    "melchor_vote": to_jsonable(melchor_vote),
                    "baltasar_vote": to_jsonable(baltasar_vote),
                    "gaspar_vote": to_jsonable(gaspar_vote),
                    "future_outcomes": future_outcomes,
                    "leakage_guard": leakage_guard,
                }
            )

    summary = {
        "records_generated": len(records),
        "snapshots_received": len(snapshots),
        "symbols": {symbol: len(items) for symbol, items in by_symbol.items()},
        "skipped": dict(skipped),
        "vote_counts": dict(vote_counts),
        "outcome_records_by_horizon": dict(outcome_horizons),
    }
    return records, summary


def calculate_future_outcomes(
    symbol_snapshots: list[Snapshot],
    index: int,
    horizons_bars: list[int],
    proposed_direction: str,
    flat_threshold_pips: float,
) -> dict[str, dict[str, Any]]:
    snapshot = symbol_snapshots[index]
    entry_price = price(snapshot)
    if entry_price is None:
        return {}
    pip = pip_size(snapshot.symbol)
    outcomes: dict[str, dict[str, Any]] = {}
    direction = proposed_direction if proposed_direction in {"BUY", "SELL"} else "NEUTRAL"

    for horizon in sorted({int(item) for item in horizons_bars if int(item) > 0}):
        end_index = index + horizon
        if end_index >= len(symbol_snapshots):
            continue
        future_slice = symbol_snapshots[index + 1 : end_index + 1]
        future_price = price(symbol_snapshots[end_index])
        if future_price is None:
            continue
        highs = [item.high if item.high is not None else price(item) for item in future_slice]
        lows = [item.low if item.low is not None else price(item) for item in future_slice]
        highs = [item for item in highs if item is not None]
        lows = [item for item in lows if item is not None]
        if not highs or not lows:
            continue

        future_return = (future_price - entry_price) / entry_price
        future_return_pips = (future_price - entry_price) / pip
        reached_up_pips = max(0.0, (max(highs) - entry_price) / pip)
        reached_down_pips = max(0.0, (entry_price - min(lows)) / pip)
        mfe_pips, mae_pips = directional_excursions(direction, reached_up_pips, reached_down_pips)
        outcomes[str(horizon)] = {
            "horizon_bars": horizon,
            "future_timestamp": timestamp_to_iso(symbol_snapshots[end_index].anchor_bar_timestamp),
            "proposed_direction": direction,
            "future_return": round(future_return, 10),
            "future_return_pips": round(future_return_pips, 5),
            "max_favorable_excursion": round(mfe_pips, 5),
            "max_adverse_excursion": round(mae_pips, 5),
            "real_direction": real_direction(future_return_pips, flat_threshold_pips),
            "reached_up_pips": round(reached_up_pips, 5),
            "reached_down_pips": round(reached_down_pips, 5),
        }
    return outcomes


def features_at_decision_time(snapshot: Snapshot) -> dict[str, Any]:
    raw = sanitize_features(snapshot.raw)
    base = {
        "schema_version": snapshot.schema_version,
        "run_id": snapshot.run_id,
        "symbol": snapshot.symbol,
        "timeframe": snapshot.timeframe,
        "open": snapshot.open,
        "high": snapshot.high,
        "low": snapshot.low,
        "close": snapshot.close,
        "current_price": snapshot.current_price,
        "spread_pips": snapshot.spread_pips,
        "active_session": snapshot.active_session,
        "features": sanitize_features(snapshot.features),
        "gaspar_context": sanitize_features(snapshot.gaspar_context),
        "account": sanitize_features(snapshot.account),
        "source_file": snapshot.source_file,
        "source_line": snapshot.source_line,
        "raw": raw,
    }
    return sanitize_features(base)


def sanitize_features(value: Any) -> Any:
    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            if is_forbidden_feature_key(str(key)):
                continue
            clean[str(key)] = sanitize_features(item)
        return clean
    if isinstance(value, list):
        return [sanitize_features(item) for item in value]
    return value


def find_leakage_paths(value: Any, prefix: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            current = f"{prefix}.{key}" if prefix else str(key)
            if is_forbidden_feature_key(str(key)):
                paths.append(current)
                continue
            paths.extend(find_leakage_paths(item, current))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(find_leakage_paths(item, f"{prefix}[{index}]"))
    return paths


def has_forbidden_key(value: Any) -> bool:
    return bool(find_leakage_paths(value))


def is_forbidden_feature_key(key: str) -> bool:
    normalized = key.lower()
    return any(keyword in normalized for keyword in FORBIDDEN_FEATURE_KEYWORDS)


def directional_excursions(direction: str, reached_up_pips: float, reached_down_pips: float) -> tuple[float, float]:
    if direction == "BUY":
        return reached_up_pips, -reached_down_pips
    if direction == "SELL":
        return reached_down_pips, -reached_up_pips
    return max(reached_up_pips, reached_down_pips), -min(reached_up_pips, reached_down_pips)


def real_direction(future_return_pips: float, flat_threshold_pips: float) -> str:
    if future_return_pips > flat_threshold_pips:
        return "BUY"
    if future_return_pips < -flat_threshold_pips:
        return "SELL"
    return "FLAT"


def group_by_symbol(snapshots: list[Snapshot]) -> dict[str, list[Snapshot]]:
    grouped: dict[str, list[Snapshot]] = defaultdict(list)
    for snapshot in snapshots:
        grouped[snapshot.symbol].append(snapshot)
    return {
        symbol: sorted(items, key=lambda item: (item.anchor_bar_timestamp, item.snapshot_id))
        for symbol, items in sorted(grouped.items())
    }


def has_validation_error(snapshot: Snapshot) -> bool:
    return any(issue.severity == "error" for issue in validate_snapshot(snapshot))


def evaluate_gaspar(gaspar: Any, snapshot: Snapshot, baltasar_vote: MageVote) -> MageVote:
    try:
        return gaspar.evaluate(snapshot, baltasar_vote)
    except TypeError:
        return gaspar.evaluate(snapshot)


def price(snapshot: Snapshot) -> float | None:
    if snapshot.current_price is not None:
        return snapshot.current_price
    return snapshot.close


def pip_size(symbol: str) -> float:
    return 0.01 if symbol.upper().endswith("JPY") else 0.0001


def ceo_training_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# CEO-MAGI Training Dataset Summary",
        "",
        f"- records_generated: {summary.get('records_generated', 0)}",
        f"- snapshots_received: {summary.get('snapshots_received', 0)}",
        f"- horizons_bars: {summary.get('config', {}).get('horizons_bars', [])}",
        f"- flat_threshold_pips: {summary.get('config', {}).get('flat_threshold_pips')}",
        f"- melchor_mode: {summary.get('config', {}).get('melchor_mode')}",
        f"- baltasar_mode: {summary.get('config', {}).get('baltasar_mode')}",
        f"- gaspar_mode: {summary.get('config', {}).get('gaspar_mode')}",
        "",
        "## Skipped",
    ]
    skipped = summary.get("skipped", {})
    if skipped:
        lines.extend(f"- {key}: {value}" for key, value in sorted(skipped.items()))
    else:
        lines.append("- none: 0")
    lines.extend(["", "## Symbols"])
    symbols = summary.get("symbols", {})
    if symbols:
        lines.extend(f"- {key}: {value}" for key, value in sorted(symbols.items()))
    else:
        lines.append("- none: 0")
    return "\n".join(lines) + "\n"
