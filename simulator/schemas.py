from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def parse_timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def timestamp_to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def as_float(value: Any, default: float | None = None) -> float | None:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "ok"}


def serialize_dataclass(value: Any) -> dict[str, Any]:
    data = asdict(value)
    for key, item in list(data.items()):
        if isinstance(item, datetime):
            data[key] = timestamp_to_iso(item)
    return data


@dataclass(frozen=True)
class Snapshot:
    schema_version: str
    snapshot_id: str
    run_id: str | None
    symbol: str
    timestamp: datetime
    anchor_bar_timestamp: datetime
    timeframe: str | None
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    current_price: float | None
    spread_pips: float | None
    active_session: str | None
    features: dict[str, Any] = field(default_factory=dict)
    gaspar_context: dict[str, Any] = field(default_factory=dict)
    account: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)
    source_file: str | None = None
    source_line: int | None = None


@dataclass(frozen=True)
class ValidationIssue:
    snapshot_id: str
    severity: str
    code: str
    message: str


@dataclass(frozen=True)
class DataQualityReport:
    total_snapshots: int
    valid_snapshots: int
    invalid_snapshots: int
    duplicate_snapshot_ids: int
    parse_errors: list[dict[str, Any]]
    issues_by_code: dict[str, int]
    symbols: dict[str, int]
    first_timestamp: str | None
    last_timestamp: str | None
    source_files: list[str]
    issues: list[dict[str, Any]]


@dataclass(frozen=True)
class SimulationConfig:
    schema_version: str
    input_path: str
    output_root: str
    input_format: str
    run_name: str
    melchor_mode: str
    baltasar_mode: str
    gaspar_mode: str
    filters: dict[str, Any]
    melchor: dict[str, Any]
    baltasar: dict[str, Any]
    gaspar: dict[str, Any]
    ceo_magi: dict[str, Any]
    ceo_training_mode: bool = False
    horizons_bars: list[int] = field(default_factory=lambda: [12, 48, 96, 288])
    output_ceo_training_path: str = "data/output/ceo_training"
    flat_threshold_pips: float = 3.0
    execution: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimulatedTrade:
    schema_version: str
    trade_id: str
    decision_id: str
    snapshot_id: str
    symbol: str
    direction: str
    entry_timestamp: datetime
    entry_price: float
    sl: float
    tp: float
    initial_risk_price: float
    timeout_snapshots: int
    snapshots_held: int = 0
    status: str = "OPEN"


@dataclass(frozen=True)
class TradeResult:
    schema_version: str
    trade_id: str
    decision_id: str
    entry_snapshot_id: str
    exit_snapshot_id: str
    symbol: str
    direction: str
    entry_timestamp: datetime
    exit_timestamp: datetime
    entry_price: float
    exit_price: float
    sl: float
    tp: float
    exit_reason: str
    pnl_r: float
    snapshots_held: int
    ambiguous_intrabar: bool


@dataclass(frozen=True)
class EquityPoint:
    timestamp: datetime
    snapshot_id: str
    closed_trades: int
    equity_r: float
    drawdown_r: float
