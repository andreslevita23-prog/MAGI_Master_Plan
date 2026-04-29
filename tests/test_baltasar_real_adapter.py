import unittest

from magi.adapters.baltasar_real_adapter import (
    BaltasarRealAdapter,
    COMPACT_FEATURE_COLUMNS,
    FORBIDDEN_LEAKAGE_COLUMNS,
)
from magi.baltasar import BaltasarRuleBased
from magi.ceo_magi import CeoMagiRuleBased
from magi.contracts import MageVote
from simulator.loaders import snapshot_from_record
from tests.test_loaders import sample_record


class FakeBaltasarModel:
    classes_ = ["SELL", "NEUTRAL", "BUY"]

    def predict(self, frame):
        return ["BUY"]

    def predict_proba(self, frame):
        return [[0.1, 0.2, 0.7]]


def baltasar_record(**overrides):
    record = sample_record()
    record.update(
        {
            "market_structure": "trend",
            "structure_direction": "bullish",
            "ema_20": 1.1010,
            "ema_50": 1.1000,
            "ema_200": 1.0950,
            "rsi_14": 58.0,
            "momentum": "bullish",
            "recent_range": 0.0012,
            "current_price": 1.1020,
            "anchor_open": 1.1000,
            "anchor_high": 1.1030,
            "anchor_low": 1.0990,
            "anchor_close": 1.1020,
            "position": {"has_open_position": False, "open_positions_count": 0},
        }
    )
    record.update(overrides)
    return record


def adapter_with_fake_model():
    adapter = BaltasarRealAdapter(
        {
            "real_version": "baltasar_real_adapter_v0.4",
            "model_path": "baltasar_training_v1/artifacts/models/candidate_target_compact_features__random_forest.joblib",
            "_model": FakeBaltasarModel(),
        }
    )
    adapter.to_model_frame = lambda features: [{column: features[column] for column in COMPACT_FEATURE_COLUMNS}]
    return adapter


class BaltasarRealAdapterTests(unittest.TestCase):
    def test_rule_based_baltasar_still_works(self):
        snapshot = snapshot_from_record(baltasar_record())
        baltasar = BaltasarRuleBased({"version": "rule_based_v0.1"})

        vote = baltasar.evaluate(snapshot)

        self.assertIsInstance(vote, MageVote)
        self.assertEqual(vote.agent, "BALTASAR")
        self.assertIn(vote.direction, {"BUY", "SELL", "NEUTRAL"})

    def test_real_adapter_returns_valid_mage_vote(self):
        snapshot = snapshot_from_record(baltasar_record())
        adapter = adapter_with_fake_model()

        vote = adapter.evaluate(snapshot)

        self.assertIsInstance(vote, MageVote)
        self.assertEqual(vote.agent, "BALTASAR")
        self.assertEqual(vote.direction, "BUY")
        self.assertEqual(vote.agent_version, "baltasar_real_adapter_v0.4")
        self.assertAlmostEqual(vote.confidence, 0.7)

    def test_missing_features_returns_safe_neutral(self):
        record = baltasar_record()
        record.pop("ema_20")
        snapshot = snapshot_from_record(record)
        adapter = adapter_with_fake_model()

        vote = adapter.evaluate(snapshot)

        self.assertEqual(vote.direction, "NEUTRAL")
        self.assertEqual(vote.risk_flag, "HIGH")
        self.assertIn("missing required columns", vote.reason)

    def test_ceo_accepts_normalized_baltasar_vote(self):
        snapshot = snapshot_from_record(baltasar_record())
        adapter = adapter_with_fake_model()
        melchor_vote = MageVote("mage_vote_v1", snapshot.snapshot_id, "MELCHOR", "test", "APPROVE", None, None, 0.8, "LOW", "test", [], "test")
        baltasar_vote = adapter.evaluate(snapshot)
        gaspar_vote = MageVote("mage_vote_v1", snapshot.snapshot_id, "GASPAR", "test", None, None, "GOOD", 0.8, "LOW", "test", [], "test")
        ceo = CeoMagiRuleBased({"version": "test", "strict_warn": True})

        decision = ceo.decide(snapshot, melchor_vote, baltasar_vote, gaspar_vote)

        self.assertEqual(decision.action, "OPEN_LONG")

    def test_compact_features_do_not_include_obvious_leakage_columns(self):
        snapshot = snapshot_from_record(baltasar_record())
        adapter = adapter_with_fake_model()

        features = adapter.build_compact_features(adapter.snapshot_to_training_row(snapshot))

        self.assertEqual(set(features), set(COMPACT_FEATURE_COLUMNS))
        self.assertTrue(set(features).isdisjoint(FORBIDDEN_LEAKAGE_COLUMNS))


if __name__ == "__main__":
    unittest.main()
