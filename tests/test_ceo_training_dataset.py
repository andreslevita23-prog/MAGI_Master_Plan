import json
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from magi.contracts import MageVote
from simulator.ceo_training_dataset import (
    build_ceo_training_records,
    calculate_future_outcomes,
    features_at_decision_time,
)
from simulator.loaders import snapshot_from_record
from simulator.reporting import write_jsonl
from tests.test_loaders import sample_record


class StaticMage:
    def __init__(self, agent, *, vote=None, direction=None, quality=None):
        self.agent = agent
        self.vote = vote
        self.direction = direction
        self.quality = quality

    def evaluate(self, snapshot, *_args):
        return MageVote(
            schema_version="mage_vote_v1",
            snapshot_id=snapshot.snapshot_id,
            agent=self.agent,
            agent_version="test",
            vote=self.vote,
            direction=self.direction,
            quality=self.quality,
            confidence=0.8,
            risk_flag="LOW",
            context_tag="test",
            features_used=["fixture"],
            reason="fixture",
        )


def market_snapshot(index, price, *, high=None, low=None, symbol="EURUSD", extra=None):
    record = sample_record(f"s{index}")
    record["symbol"] = symbol
    record["timestamp"] = f"2026-01-01T12:{index:02d}:00Z"
    record["anchor_bar_timestamp"] = f"2026-01-01T12:{index:02d}:00Z"
    record["current_price"] = price
    record["anchor_open"] = price
    record["anchor_high"] = high if high is not None else price
    record["anchor_low"] = low if low is not None else price
    record["anchor_close"] = price
    if extra:
        record.update(extra)
    return snapshot_from_record(record)


class CeoTrainingDatasetTests(unittest.TestCase):
    def test_calculates_future_return_for_buy(self):
        snapshots = [
            market_snapshot(0, 1.1000),
            market_snapshot(1, 1.1010),
            market_snapshot(2, 1.1020),
        ]

        outcomes = calculate_future_outcomes(snapshots, 0, [2], "BUY", flat_threshold_pips=3.0)

        self.assertEqual(outcomes["2"]["real_direction"], "BUY")
        self.assertAlmostEqual(outcomes["2"]["future_return_pips"], 20.0)
        self.assertAlmostEqual(outcomes["2"]["max_favorable_excursion"], 20.0)

    def test_calculates_future_return_for_sell(self):
        snapshots = [
            market_snapshot(0, 1.1000),
            market_snapshot(1, 1.0990),
            market_snapshot(2, 1.0980),
        ]

        outcomes = calculate_future_outcomes(snapshots, 0, [2], "SELL", flat_threshold_pips=3.0)

        self.assertEqual(outcomes["2"]["real_direction"], "SELL")
        self.assertAlmostEqual(outcomes["2"]["future_return_pips"], -20.0)
        self.assertAlmostEqual(outcomes["2"]["max_favorable_excursion"], 20.0)

    def test_calculates_mfe_and_mae_for_buy(self):
        snapshots = [
            market_snapshot(0, 1.1000),
            market_snapshot(1, 1.1010, high=1.1030, low=1.0990),
            market_snapshot(2, 1.1020, high=1.1025, low=1.1005),
        ]

        outcomes = calculate_future_outcomes(snapshots, 0, [2], "BUY", flat_threshold_pips=3.0)

        self.assertAlmostEqual(outcomes["2"]["reached_up_pips"], 30.0)
        self.assertAlmostEqual(outcomes["2"]["reached_down_pips"], 10.0)
        self.assertAlmostEqual(outcomes["2"]["max_favorable_excursion"], 30.0)
        self.assertAlmostEqual(outcomes["2"]["max_adverse_excursion"], -10.0)

    def test_reached_down_does_not_go_negative_when_price_only_rises(self):
        snapshots = [
            market_snapshot(0, 1.1000),
            market_snapshot(1, 1.1010, high=1.1030, low=1.1005),
            market_snapshot(2, 1.1020, high=1.1025, low=1.1007),
        ]

        outcomes = calculate_future_outcomes(snapshots, 0, [2], "BUY", flat_threshold_pips=3.0)

        self.assertAlmostEqual(outcomes["2"]["reached_down_pips"], 0.0)
        self.assertAlmostEqual(outcomes["2"]["max_adverse_excursion"], -0.0)

    def test_does_not_generate_outcome_without_future_bars(self):
        snapshots = [market_snapshot(0, 1.1000), market_snapshot(1, 1.1010)]

        outcomes = calculate_future_outcomes(snapshots, 0, [2], "BUY", flat_threshold_pips=3.0)

        self.assertEqual(outcomes, {})

    def test_features_do_not_include_leakage_columns(self):
        snapshot = market_snapshot(
            0,
            1.1000,
            extra={
                "future_return": 0.01,
                "target_label": "BUY",
                "features": {"rsi_14": 55, "hit_tp": True, "nested": {"mae_pips": -5}},
            },
        )

        features = features_at_decision_time(snapshot)
        encoded = json.dumps(features)

        self.assertIn("rsi_14", encoded)
        self.assertNotIn("future_return", encoded)
        self.assertNotIn("target_label", encoded)
        self.assertNotIn("hit_tp", encoded)
        self.assertNotIn("mae_pips", encoded)

    def test_generates_valid_jsonl(self):
        snapshots = [
            market_snapshot(0, 1.1000),
            market_snapshot(1, 1.1010),
            market_snapshot(2, 1.1020),
        ]
        records, summary = build_ceo_training_records(
            snapshots=snapshots,
            melchor=StaticMage("MELCHOR", vote="APPROVE"),
            baltasar=StaticMage("BALTASAR", direction="BUY"),
            gaspar=StaticMage("GASPAR", quality="GOOD"),
            horizons_bars=[2],
            flat_threshold_pips=3.0,
        )

        with workspace_tempdir() as temp_dir:
            path = Path(temp_dir) / "ceo_training_records.jsonl"
            write_jsonl(path, records)
            loaded = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(summary["records_generated"], 1)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["schema_version"], "ceo_training_record_v0.1")
        self.assertIn("2", loaded[0]["future_outcomes"])


class workspace_tempdir:
    def __enter__(self):
        root = Path("data") / "output" / "test_tmp"
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / f"test_{uuid4().hex}"
        self.path.mkdir()
        return self.path

    def __exit__(self, exc_type, exc, tb):
        shutil.rmtree(self.path, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
