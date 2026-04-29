from __future__ import annotations

import json
import atexit
import shutil
import subprocess
from pathlib import Path
from typing import Any

from magi.contracts import MageVote
from simulator.schemas import Snapshot, timestamp_to_iso


class MelchorRealAdapter:
    """Adapter from simulator snapshots to the real Node.js Melchor risk engine."""

    def __init__(self, config: dict[str, Any], execution_config: dict[str, Any] | None = None):
        self.config = config
        self.execution_config = execution_config or {}
        self.version = str(config.get("real_version") or config.get("version") or "melchor_real_adapter_v0.3")
        self.node_path = str(config.get("node_path") or _default_node_path())
        self.engine_path = Path(config.get("engine_path", "servidor-prosperity/services/melchor-risk-engine.js"))
        self.rules_path = Path(config.get("rules_path", "config/melchor_rules.json"))
        self.timeout_seconds = float(config.get("timeout_seconds", 10.0))
        self.persistent_process = bool(config.get("persistent_process", True))
        self._process: subprocess.Popen[str] | None = None
        if self.persistent_process:
            atexit.register(self.close)

    def evaluate(self, snapshot: Snapshot) -> MageVote:
        try:
            payload = {
                "snapshot": self.to_melchor_snapshot(snapshot),
                "options": {
                    "candidateTrade": self.to_candidate_trade(snapshot),
                    "accountContext": self.account_context(snapshot),
                    "now": timestamp_to_iso(snapshot.timestamp),
                    "rulesPath": str(self.rules_path.resolve()),
                },
            }
            raw_vote = self.run_melchor(payload)
            return self.to_mage_vote(snapshot, raw_vote)
        except Exception as exc:  # noqa: BLE001 - adapter must fail safely in simulations
            return self.failure_vote(snapshot, exc)

    def to_melchor_snapshot(self, snapshot: Snapshot) -> dict[str, Any]:
        raw = snapshot.raw or {}
        position = raw.get("position") if isinstance(raw.get("position"), dict) else {}
        allowed_actions = raw.get("allowed_actions")
        if not isinstance(allowed_actions, list):
            allowed_actions = ["open", "hold"]

        return {
            "snapshot_id": snapshot.snapshot_id,
            "symbol": snapshot.symbol,
            "timestamp": timestamp_to_iso(snapshot.timestamp),
            "market": {
                "price": snapshot.current_price,
                "session": snapshot.active_session,
                "spread_pips": snapshot.spread_pips,
                "allowed_actions": allowed_actions,
            },
            "position": {
                "has_open_position": bool(position.get("has_open_position", False)),
                "open_positions_count": int(position.get("open_positions_count") or 0),
                "profit_progress_to_tp": position.get("profit_progress_to_tp", 0),
            },
            "validation": snapshot.validation or {"is_valid": True, "issues": []},
            "account": self.account_context(snapshot),
            "news": raw.get("news") if isinstance(raw.get("news"), list) else [],
        }

    def to_candidate_trade(self, snapshot: Snapshot) -> dict[str, Any]:
        entry = float(snapshot.current_price or 0.0)
        pip_size = self.pip_size(snapshot.symbol)
        sl_pips = float(self.execution_config.get("sl_pips", self.config.get("sl_pips", 10.0)))
        tp_rr = float(self.execution_config.get("tp_rr", self.config.get("tp_rr", 2.0)))
        risk = sl_pips * pip_size
        direction = self.proposed_direction(snapshot)
        if direction == "SELL":
            stop_loss = entry + risk
            take_profit = entry - risk * tp_rr
        else:
            stop_loss = entry - risk
            take_profit = entry + risk * tp_rr

        account = self.account_context(snapshot)
        return {
            "action": "open",
            "entry_price": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_percent": account.get("risk_percent_per_trade", self.config.get("default_risk_percent", 0.1)),
            "spread_pips": snapshot.spread_pips,
        }

    def account_context(self, snapshot: Snapshot) -> dict[str, Any]:
        account = dict(snapshot.account or {})
        if "daily_drawdown_percent" not in account:
            account["daily_drawdown_percent"] = 0
        if "risk_percent_per_trade" not in account or account.get("risk_percent_per_trade") in (None, ""):
            account["risk_percent_per_trade"] = self.config.get("default_risk_percent", 0.1)
        if not account.get("risk_percent_per_trade"):
            account["risk_percent_per_trade"] = self.config.get("default_risk_percent", 0.1)
        account.setdefault("consecutive_losses", 0)
        return account

    def run_melchor(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.persistent_process:
            return self.run_melchor_persistent(payload)
        return self.run_melchor_subprocess(payload)

    def run_melchor_subprocess(self, payload: dict[str, Any]) -> dict[str, Any]:
        engine_path = self.engine_path.resolve()
        if not engine_path.exists():
            raise FileNotFoundError(f"Melchor real engine not found: {engine_path}")

        script = f"""
import {{ evaluateMelchorRisk }} from {json.dumps(engine_path.as_uri())};

let input = "";
for await (const chunk of process.stdin) {{
  input += chunk;
}}
const payload = JSON.parse(input);
if (payload.options?.now) {{
  payload.options.now = new Date(payload.options.now);
}}
const vote = evaluateMelchorRisk(payload.snapshot, payload.options || {{}});
process.stdout.write(JSON.stringify(vote));
"""
        completed = subprocess.run(
            [self.node_path, "--input-type=module", "--eval", script],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or f"exit code {completed.returncode}"
            raise RuntimeError(f"Melchor real process failed: {detail}")
        try:
            parsed = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Melchor real returned invalid JSON: {completed.stdout[:500]}") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("Melchor real returned a non-object JSON payload")
        return parsed

    def run_melchor_persistent(self, payload: dict[str, Any]) -> dict[str, Any]:
        process = self.ensure_process()
        if process.stdin is None or process.stdout is None:
            raise RuntimeError("Melchor persistent process pipes are not available")
        process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        process.stdin.flush()
        line = process.stdout.readline()
        if not line:
            stderr = process.stderr.read() if process.stderr else ""
            self.close()
            raise RuntimeError(f"Melchor persistent process returned no output: {stderr[:500]}")
        parsed = json.loads(line)
        if isinstance(parsed, dict) and parsed.get("__error__"):
            raise RuntimeError(f"Melchor persistent process failed: {parsed.get('error')}")
        if not isinstance(parsed, dict):
            raise RuntimeError("Melchor real returned a non-object JSON payload")
        return parsed

    def ensure_process(self) -> subprocess.Popen[str]:
        if self._process is not None and self._process.poll() is None:
            return self._process
        engine_path = self.engine_path.resolve()
        if not engine_path.exists():
            raise FileNotFoundError(f"Melchor real engine not found: {engine_path}")
        script = f"""
import {{ evaluateMelchorRisk }} from {json.dumps(engine_path.as_uri())};
import readline from "node:readline";

const rl = readline.createInterface({{ input: process.stdin, crlfDelay: Infinity }});
for await (const line of rl) {{
  if (!line.trim()) {{
    continue;
  }}
  try {{
    const payload = JSON.parse(line);
    if (payload.options?.now) {{
      payload.options.now = new Date(payload.options.now);
    }}
    const vote = evaluateMelchorRisk(payload.snapshot, payload.options || {{}});
    process.stdout.write(JSON.stringify(vote) + "\\n");
  }} catch (error) {{
    process.stdout.write(JSON.stringify({{ __error__: true, error: String(error?.stack || error) }}) + "\\n");
  }}
}}
"""
        self._process = subprocess.Popen(
            [self.node_path, "--input-type=module", "--eval", script],
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
        )
        return self._process

    def close(self) -> None:
        if self._process is None:
            return
        process = self._process
        self._process = None
        try:
            if process.stdin:
                process.stdin.close()
            process.terminate()
            process.wait(timeout=2)
        except Exception:  # noqa: BLE001
            process.kill()

    def to_mage_vote(self, snapshot: Snapshot, raw_vote: dict[str, Any]) -> MageVote:
        native_vote = str(raw_vote.get("vote", "")).upper()
        normalized_vote = {
            "ALLOW": "APPROVE",
            "NOTIFY": "WARN",
            "PROTECT": "WARN",
            "BLOCK": "BLOCK",
            "CLOSE": "BLOCK",
        }.get(native_vote, "BLOCK")
        risk_flag = str(raw_vote.get("risk_level") or "HIGH").upper()
        rules = raw_vote.get("rules_triggered")
        features_used = ["melchor_real_engine", "candidateTrade", "market", "account", "position", "validation"]
        if isinstance(rules, list):
            features_used.extend(f"rule:{rule}" for rule in rules)

        return MageVote(
            schema_version="mage_vote_v1",
            snapshot_id=snapshot.snapshot_id,
            agent="MELCHOR",
            agent_version=str(raw_vote.get("version") or self.version),
            vote=normalized_vote,
            direction=None,
            quality=None,
            confidence=float(raw_vote.get("confidence", 1.0) or 0.0),
            risk_flag=risk_flag,
            context_tag=native_vote.lower() or "melchor_real",
            features_used=features_used,
            reason=str(raw_vote.get("reason") or "Melchor real returned no reason."),
        )

    def failure_vote(self, snapshot: Snapshot, exc: Exception) -> MageVote:
        return MageVote(
            schema_version="mage_vote_v1",
            snapshot_id=snapshot.snapshot_id,
            agent="MELCHOR",
            agent_version=self.version,
            vote="BLOCK",
            direction=None,
            quality=None,
            confidence=0.0,
            risk_flag="CRITICAL",
            context_tag="melchor_real_error",
            features_used=["melchor_real_engine", "adapter_error"],
            reason=f"Melchor real adapter failed: {exc}",
        )

    def proposed_direction(self, snapshot: Snapshot) -> str:
        gaspar_direction = snapshot.gaspar_context.get("proposed_direction") if snapshot.gaspar_context else None
        if gaspar_direction in {"BUY", "SELL"}:
            return str(gaspar_direction)
        structure = str(snapshot.raw.get("structure_direction", "")).lower()
        if structure == "bearish":
            return "SELL"
        return "BUY"

    def pip_size(self, symbol: str) -> float:
        symbol_pip_size = self.execution_config.get("symbol_pip_size", {})
        if symbol in symbol_pip_size:
            return float(symbol_pip_size[symbol])
        if "JPY" in symbol.upper():
            return 0.01
        if "XAU" in symbol.upper():
            return 0.1
        return float(self.execution_config.get("default_pip_size", 0.0001))


def _default_node_path() -> str:
    bundled = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "node" / "bin" / "node.exe"
    if bundled.exists():
        return str(bundled)
    return shutil.which("node") or "node"
