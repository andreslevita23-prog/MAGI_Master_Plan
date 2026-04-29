import unittest

from magi.ceo_magi import CeoMagiRuleBased
from magi.contracts import MageVote
from magi.gaspar import GasparRuleBased
from magi.adapters.gaspar_real_adapter import (
    GASPAR_FEATURE_COLUMNS,
    GASPAR_FORBIDDEN_LEAKAGE_COLUMNS,
    GasparRealAdapter,
)
from simulator.loaders import snapshot_from_record
from tests.test_loaders import sample_record


class FakeGasparModel:
    classes_ = ["FAIR", "GOOD", "POOR"]

    def predict(self, frame):
        return ["GOOD"]

    def predict_proba(self, frame):
        return [[0.2, 0.7, 0.1]]


def gaspar_context():
    return {
        "schema_version": "1.0",
        "module": "GASPAR",
        "role": "opportunity_quality",
        "symbol": "EURUSD",
        "timestamp": "2026-01-01T12:00:00Z",
        "proposed_direction": "NEUTRAL",
        "higher_timeframe_confluence": {
            "h4_structure": "bullish",
            "d1_structure": "bullish",
            "directional_alignment": "neutral",
        },
        "price_structure_position": {
            "distance_to_d1_support": 0.0012,
            "distance_to_d1_resistance": 0.0048,
            "position_in_d1_range": 0.25,
            "near_key_level": True,
        },
        "timing_quality": {
            "active_session": "london",
            "daily_atr_consumed_pct": 0.42,
            "available_range_to_next_level": 0.0036,
            "h4_candle_pattern": "rejection",
        },
        "day_context": {
            "day_of_week": "tuesday",
            "d1_volatility_vs_20d_avg": 1.05,
            "current_d1_range_vs_atr": 0.58,
        },
    }


def gaspar_record(**overrides):
    record = sample_record()
    record["gaspar_context"] = gaspar_context()
    record.update(overrides)
    return record


def baltasar_vote(direction="BUY"):
    return MageVote("mage_vote_v1", "s1", "BALTASAR", "test", None, direction, None, 0.8, "LOW", "test", [], "test")


def adapter_with_fake_model():
    adapter = GasparRealAdapter(
        {
            "real_version": "gaspar_real_adapter_v0.5",
            "model_path": "gaspar_training_v1/artifacts/models/gaspar_baseline.joblib",
            "_model": FakeGasparModel(),
        }
    )
    adapter.to_model_frame = lambda row: [{column: row[column] for column in GASPAR_FEATURE_COLUMNS}]
    return adapter


class GasparRealAdapterTests(unittest.TestCase):
    def test_rule_based_gaspar_still_works(self):
        snapshot = snapshot_from_record(gaspar_record())
        gaspar = GasparRuleBased({"version": "rule_based_v0.1"})

        vote = gaspar.evaluate(snapshot)

        self.assertEqual(vote.agent, "GASPAR")
        self.assertIn(vote.quality, {"GOOD", "FAIR", "POOR"})

    def test_real_adapter_returns_valid_mage_vote(self):
        snapshot = snapshot_from_record(gaspar_record())
        adapter = adapter_with_fake_model()

        vote = adapter.evaluate(snapshot, baltasar_vote("BUY"))

        self.assertEqual(vote.agent, "GASPAR")
        self.assertEqual(vote.quality, "GOOD")
        self.assertAlmostEqual(vote.confidence, 0.7)
        self.assertEqual(vote.agent_version, "gaspar_real_adapter_v0.5")

    def test_real_adapter_handles_missing_baltasar_vote(self):
        snapshot = snapshot_from_record(gaspar_record())
        adapter = adapter_with_fake_model()

        vote = adapter.evaluate(snapshot, None)

        self.assertEqual(vote.agent, "GASPAR")
        self.assertIn(vote.quality, {"GOOD", "FAIR", "POOR"})

    def test_real_adapter_uses_baltasar_direction(self):
        snapshot = snapshot_from_record(gaspar_record())
        adapter = adapter_with_fake_model()

        context = adapter.context_with_baltasar_direction(snapshot, baltasar_vote("BUY"))
        row = adapter.snapshot_to_gaspar_row(snapshot, context)

        self.assertEqual(row["proposed_direction"], "BUY")
        self.assertEqual(row["directional_alignment"], "aligned")

    def test_real_adapter_blocks_leakage_columns(self):
        context = gaspar_context()
        context["rsi_14"] = 55
        snapshot = snapshot_from_record(gaspar_record(gaspar_context=context))
        adapter = adapter_with_fake_model()

        vote = adapter.evaluate(snapshot, baltasar_vote("BUY"))

        self.assertEqual(vote.quality, "POOR")
        self.assertIn("leakage", vote.reason.lower())
        self.assertTrue("rsi_14" in GASPAR_FORBIDDEN_LEAKAGE_COLUMNS)

    def test_ceo_accepts_normalized_gaspar_vote(self):
        snapshot = snapshot_from_record(gaspar_record())
        adapter = adapter_with_fake_model()
        melchor_vote = MageVote("mage_vote_v1", snapshot.snapshot_id, "MELCHOR", "test", "APPROVE", None, None, 0.8, "LOW", "test", [], "test")
        b_vote = baltasar_vote("BUY")
        g_vote = adapter.evaluate(snapshot, b_vote)
        ceo = CeoMagiRuleBased({"version": "test", "strict_warn": True})

        decision = ceo.decide(snapshot, melchor_vote, b_vote, g_vote)

        self.assertEqual(decision.action, "OPEN_LONG")


if __name__ == "__main__":
    unittest.main()
