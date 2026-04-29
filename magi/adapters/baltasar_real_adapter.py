from __future__ import annotations

from pathlib import Path
from typing import Any

from magi.contracts import MageVote
from simulator.schemas import Snapshot, as_bool, as_float, timestamp_to_iso


BALTASAR_REQUIRED_COLUMNS = [
    "snapshot_id",
    "symbol",
    "anchor_bar_timestamp",
    "current_price",
    "anchor_open",
    "anchor_high",
    "anchor_low",
    "anchor_close",
    "market_structure",
    "structure_direction",
    "ema_20",
    "ema_50",
    "ema_200",
    "rsi_14",
    "momentum",
    "recent_range",
    "validation_is_valid",
    "has_open_position",
]

COMPACT_FEATURE_COLUMNS = [
    "market_structure",
    "structure_direction",
    "momentum",
    "rsi_14",
    "has_open_position",
    "candle_body_ratio",
    "candle_range_ratio",
    "upper_wick_ratio",
    "lower_wick_ratio",
    "price_vs_ema20",
    "price_vs_ema50",
    "price_vs_ema200",
    "ema_gap_20_50",
    "ema_gap_50_200",
    "ema_gap_20_200",
    "normalized_recent_range",
]

FORBIDDEN_LEAKAGE_COLUMNS = {
    "forward_return",
    "future_price",
    "trade_result",
    "pnl",
    "pnl_r",
    "mfe",
    "mae",
    "hit_tp",
    "hit_sl",
    "outcome",
    "label",
    "target",
    "ceo_decision",
}


class BaltasarRealAdapter:
    """Adapter from simulator snapshots to Baltasar v1.2 joblib pipelines."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.version = str(config.get("real_version") or "baltasar_real_adapter_v0.4")
        self.model_path = Path(
            config.get(
                "model_path",
                "baltasar_training_v1/artifacts/models/candidate_target_compact_features__random_forest.joblib",
            )
        )
        self.feature_variant = str(config.get("feature_variant", "compact"))
        self.model: Any | None = config.get("_model")
        self._model_load_error: str | None = None

    def evaluate(self, snapshot: Snapshot) -> MageVote:
        row = self.snapshot_to_training_row(snapshot)
        missing = [column for column in BALTASAR_REQUIRED_COLUMNS if row.get(column) in (None, "")]
        if missing:
            return self.safe_neutral(snapshot, f"Baltasar real missing required columns: {', '.join(missing)}")

        features = self.build_compact_features(row)
        leakage = self.detect_leakage_columns(features)
        if leakage:
            return self.safe_neutral(snapshot, f"Baltasar real blocked leakage columns: {', '.join(leakage)}")

        try:
            model = self.load_model()
            direction, confidence = self.predict(model, features)
        except Exception as exc:  # noqa: BLE001 - adapter must fail safely
            return self.safe_neutral(snapshot, f"Baltasar real adapter failed: {exc}")

        return MageVote(
            schema_version="mage_vote_v1",
            snapshot_id=snapshot.snapshot_id,
            agent="BALTASAR",
            agent_version=self.version,
            vote=None,
            direction=direction,
            quality=None,
            confidence=confidence,
            risk_flag="LOW" if direction != "NEUTRAL" else "MEDIUM",
            context_tag=f"baltasar_{self.feature_variant}",
            features_used=COMPACT_FEATURE_COLUMNS.copy(),
            reason=f"Baltasar real {self.feature_variant} model predicted {direction}.",
        )

    def snapshot_to_training_row(self, snapshot: Snapshot) -> dict[str, Any]:
        raw = snapshot.raw or {}
        position = raw.get("position") if isinstance(raw.get("position"), dict) else {}
        validation = snapshot.validation or {}
        return {
            "snapshot_id": snapshot.snapshot_id,
            "symbol": snapshot.symbol,
            "anchor_bar_timestamp": timestamp_to_iso(snapshot.anchor_bar_timestamp),
            "current_price": snapshot.current_price,
            "anchor_open": snapshot.open,
            "anchor_high": snapshot.high,
            "anchor_low": snapshot.low,
            "anchor_close": snapshot.close,
            "market_structure": raw.get("market_structure"),
            "structure_direction": raw.get("structure_direction"),
            "ema_20": as_float(raw.get("ema_20")),
            "ema_50": as_float(raw.get("ema_50")),
            "ema_200": as_float(raw.get("ema_200")),
            "rsi_14": as_float(raw.get("rsi_14")),
            "momentum": raw.get("momentum"),
            "recent_range": as_float(raw.get("recent_range")),
            "validation_is_valid": as_bool(validation.get("is_valid"), default=True),
            "has_open_position": bool(position.get("has_open_position", raw.get("has_open_position", False))),
        }

    def build_compact_features(self, row: dict[str, Any]) -> dict[str, Any]:
        price = float(row["current_price"])
        if price == 0:
            raise ValueError("current_price cannot be zero for compact features")
        anchor_open = float(row["anchor_open"])
        anchor_high = float(row["anchor_high"])
        anchor_low = float(row["anchor_low"])
        anchor_close = float(row["anchor_close"])
        ema_20 = float(row["ema_20"])
        ema_50 = float(row["ema_50"])
        ema_200 = float(row["ema_200"])
        recent_range = float(row["recent_range"])

        return {
            "market_structure": row["market_structure"],
            "structure_direction": row["structure_direction"],
            "momentum": row["momentum"],
            "rsi_14": float(row["rsi_14"]),
            "has_open_position": bool(row["has_open_position"]),
            "candle_body_ratio": (anchor_close - anchor_open) / price,
            "candle_range_ratio": (anchor_high - anchor_low) / price,
            "upper_wick_ratio": (anchor_high - max(anchor_open, anchor_close)) / price,
            "lower_wick_ratio": (min(anchor_open, anchor_close) - anchor_low) / price,
            "price_vs_ema20": (price - ema_20) / price,
            "price_vs_ema50": (price - ema_50) / price,
            "price_vs_ema200": (price - ema_200) / price,
            "ema_gap_20_50": (ema_20 - ema_50) / price,
            "ema_gap_50_200": (ema_50 - ema_200) / price,
            "ema_gap_20_200": (ema_20 - ema_200) / price,
            "normalized_recent_range": recent_range / price,
        }

    def load_model(self) -> Any:
        if self.model is not None:
            return self.model
        if self._model_load_error:
            raise RuntimeError(self._model_load_error)
        if not self.model_path.exists():
            self._model_load_error = f"Baltasar model not found: {self.model_path}"
            raise RuntimeError(self._model_load_error)
        try:
            import joblib  # type: ignore
        except ImportError as exc:
            self._model_load_error = "Python package joblib is not installed; install baltasar_training_v1 requirements."
            raise RuntimeError(self._model_load_error) from exc
        try:
            self.model = joblib.load(self.model_path)
        except Exception as exc:  # noqa: BLE001
            self._model_load_error = f"Could not load Baltasar model {self.model_path}: {exc}"
            raise RuntimeError(self._model_load_error) from exc
        return self.model

    def predict(self, model: Any, features: dict[str, Any]) -> tuple[str, float]:
        frame = self.to_model_frame(features)
        prediction = model.predict(frame)[0]
        direction = str(prediction).upper()
        if direction not in {"BUY", "SELL", "NEUTRAL"}:
            raise ValueError(f"Baltasar model returned unsupported direction: {prediction}")
        confidence = 1.0
        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(frame)[0]
            confidence = float(max(probabilities)) if len(probabilities) else 0.0
        return direction, confidence

    def to_model_frame(self, features: dict[str, Any]) -> Any:
        try:
            import pandas as pd  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Python package pandas is not installed; install baltasar_training_v1 requirements.") from exc
        return pd.DataFrame([{column: features[column] for column in COMPACT_FEATURE_COLUMNS}])

    def detect_leakage_columns(self, features: dict[str, Any]) -> list[str]:
        lower_columns = {column.lower() for column in features}
        return sorted(lower_columns.intersection(FORBIDDEN_LEAKAGE_COLUMNS))

    def safe_neutral(self, snapshot: Snapshot, reason: str) -> MageVote:
        return MageVote(
            schema_version="mage_vote_v1",
            snapshot_id=snapshot.snapshot_id,
            agent="BALTASAR",
            agent_version=self.version,
            vote=None,
            direction="NEUTRAL",
            quality=None,
            confidence=0.0,
            risk_flag="HIGH",
            context_tag="baltasar_real_safe_neutral",
            features_used=COMPACT_FEATURE_COLUMNS.copy(),
            reason=reason,
        )
