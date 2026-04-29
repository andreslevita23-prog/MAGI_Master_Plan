from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from magi.contracts import MageVote
from simulator.schemas import Snapshot, as_float


GASPAR_FEATURE_COLUMNS = [
    "proposed_direction",
    "h4_structure",
    "d1_structure",
    "directional_alignment",
    "distance_to_d1_support",
    "distance_to_d1_resistance",
    "position_in_d1_range",
    "near_key_level",
    "active_session",
    "daily_atr_consumed_pct",
    "available_range_to_next_level",
    "h4_candle_pattern",
    "day_of_week",
    "d1_volatility_vs_20d_avg",
    "current_d1_range_vs_atr",
]

GASPAR_REQUIRED_COLUMNS = GASPAR_FEATURE_COLUMNS.copy()

GASPAR_FORBIDDEN_LEAKAGE_COLUMNS = {
    "ema_20",
    "ema_50",
    "ema_200",
    "rsi_14",
    "momentum",
    "confidence",
    "probability",
    "baltasar_confidence",
    "baltasar_probability",
    "baltasar_score",
    "ceo_decision",
    "pnl",
    "pnl_r",
    "mfe",
    "mae",
    "outcome",
    "target",
}


class GasparRealAdapter:
    """Adapter from Bot A sub3 gaspar_context to the real Gaspar joblib pipeline."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.version = str(config.get("real_version") or "gaspar_real_adapter_v0.5")
        self.model_path = Path(config.get("model_path", "gaspar_training_v1/artifacts/models/gaspar_baseline.joblib"))
        self.target_version = str(config.get("target_version", "v1"))
        self.model: Any | None = config.get("_model")
        self._model_load_error: str | None = None

    def evaluate(self, snapshot: Snapshot, baltasar_vote: MageVote | None = None) -> MageVote:
        context = self.context_with_baltasar_direction(snapshot, baltasar_vote)
        leakage = self.detect_context_leakage(context)
        if leakage:
            return self.safe_poor(snapshot, f"Gaspar real blocked leakage fields: {', '.join(leakage)}")

        row = self.snapshot_to_gaspar_row(snapshot, context)
        missing = [column for column in GASPAR_REQUIRED_COLUMNS if row.get(column) in (None, "")]
        if missing:
            return self.safe_poor(snapshot, f"Gaspar real missing required columns: {', '.join(missing)}")

        try:
            model = self.load_model()
            quality, confidence = self.predict(model, row)
        except Exception as exc:  # noqa: BLE001 - adapter must fail safely
            return self.safe_poor(snapshot, f"Gaspar real adapter failed: {exc}")

        return MageVote(
            schema_version="mage_vote_v1",
            snapshot_id=snapshot.snapshot_id,
            agent="GASPAR",
            agent_version=self.version,
            vote=None,
            direction=None,
            quality=quality,
            confidence=confidence,
            risk_flag="LOW" if quality == "GOOD" else "MEDIUM" if quality == "FAIR" else "HIGH",
            context_tag=f"gaspar_{self.target_version}",
            features_used=GASPAR_FEATURE_COLUMNS.copy(),
            reason=f"Gaspar real {self.target_version} model predicted {quality}.",
        )

    def context_with_baltasar_direction(self, snapshot: Snapshot, baltasar_vote: MageVote | None) -> dict[str, Any]:
        context = deepcopy(snapshot.gaspar_context or {})
        direction = baltasar_vote.direction if baltasar_vote and baltasar_vote.direction in {"BUY", "SELL", "NEUTRAL"} else None
        if direction:
            context["proposed_direction"] = direction
            context["proposed_direction_source"] = "baltasar_vote"
            htf = context.setdefault("higher_timeframe_confluence", {})
            htf["directional_alignment"] = self.directional_alignment(
                direction,
                str(htf.get("h4_structure", "")).lower(),
                str(htf.get("d1_structure", "")).lower(),
            )
        return context

    def snapshot_to_gaspar_row(self, snapshot: Snapshot, context: dict[str, Any]) -> dict[str, Any]:
        htf = context.get("higher_timeframe_confluence", {}) if isinstance(context.get("higher_timeframe_confluence"), dict) else {}
        position = context.get("price_structure_position", {}) if isinstance(context.get("price_structure_position"), dict) else {}
        timing = context.get("timing_quality", {}) if isinstance(context.get("timing_quality"), dict) else {}
        day = context.get("day_context", {}) if isinstance(context.get("day_context"), dict) else {}
        return {
            "proposed_direction": context.get("proposed_direction"),
            "h4_structure": htf.get("h4_structure"),
            "d1_structure": htf.get("d1_structure"),
            "directional_alignment": htf.get("directional_alignment"),
            "distance_to_d1_support": as_float(position.get("distance_to_d1_support")),
            "distance_to_d1_resistance": as_float(position.get("distance_to_d1_resistance")),
            "position_in_d1_range": as_float(position.get("position_in_d1_range")),
            "near_key_level": str(position.get("near_key_level")).lower(),
            "active_session": timing.get("active_session") or snapshot.active_session,
            "daily_atr_consumed_pct": as_float(timing.get("daily_atr_consumed_pct")),
            "available_range_to_next_level": as_float(timing.get("available_range_to_next_level")),
            "h4_candle_pattern": timing.get("h4_candle_pattern"),
            "day_of_week": day.get("day_of_week"),
            "d1_volatility_vs_20d_avg": as_float(day.get("d1_volatility_vs_20d_avg")),
            "current_d1_range_vs_atr": as_float(day.get("current_d1_range_vs_atr")),
        }

    def load_model(self) -> Any:
        if self.model is not None:
            return self.model
        if self._model_load_error:
            raise RuntimeError(self._model_load_error)
        if not self.model_path.exists():
            self._model_load_error = f"Gaspar model not found: {self.model_path}"
            raise RuntimeError(self._model_load_error)
        try:
            import joblib  # type: ignore
        except ImportError as exc:
            self._model_load_error = "Python package joblib is not installed; install gaspar_training_v1 requirements."
            raise RuntimeError(self._model_load_error) from exc
        try:
            self.model = joblib.load(self.model_path)
        except Exception as exc:  # noqa: BLE001
            self._model_load_error = f"Could not load Gaspar model {self.model_path}: {exc}"
            raise RuntimeError(self._model_load_error) from exc
        return self.model

    def predict(self, model: Any, row: dict[str, Any]) -> tuple[str, float]:
        frame = self.to_model_frame(row)
        prediction = model.predict(frame)[0]
        quality = str(prediction).upper()
        if quality not in {"GOOD", "FAIR", "POOR"}:
            raise ValueError(f"Gaspar model returned unsupported quality: {prediction}")
        confidence = 1.0
        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(frame)[0]
            confidence = float(max(probabilities)) if len(probabilities) else 0.0
        return quality, confidence

    def to_model_frame(self, row: dict[str, Any]) -> Any:
        try:
            import pandas as pd  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Python package pandas is not installed; install gaspar_training_v1 requirements.") from exc
        return pd.DataFrame([{column: row[column] for column in GASPAR_FEATURE_COLUMNS}])

    def detect_context_leakage(self, context: dict[str, Any]) -> list[str]:
        keys = set()

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                for key, nested in value.items():
                    keys.add(str(key).lower())
                    walk(nested)
            elif isinstance(value, list):
                for nested in value:
                    walk(nested)

        walk(context)
        return sorted(keys.intersection(GASPAR_FORBIDDEN_LEAKAGE_COLUMNS))

    def directional_alignment(self, proposed_direction: str, h4_structure: str, d1_structure: str) -> str:
        if proposed_direction == "BUY" and d1_structure == "bullish" and h4_structure != "bearish":
            return "aligned"
        if proposed_direction == "SELL" and d1_structure == "bearish" and h4_structure != "bullish":
            return "aligned"
        if proposed_direction == "NEUTRAL":
            return "neutral"
        return "contradictory"

    def safe_poor(self, snapshot: Snapshot, reason: str) -> MageVote:
        return MageVote(
            schema_version="mage_vote_v1",
            snapshot_id=snapshot.snapshot_id,
            agent="GASPAR",
            agent_version=self.version,
            vote=None,
            direction=None,
            quality="POOR",
            confidence=0.0,
            risk_flag="HIGH",
            context_tag="gaspar_real_safe_poor",
            features_used=GASPAR_FEATURE_COLUMNS.copy(),
            reason=reason,
        )
