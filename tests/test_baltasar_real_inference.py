import unittest
from pathlib import Path

from magi.adapters.baltasar_real_adapter import BaltasarRealAdapter
from simulator.loaders import snapshot_from_record
from tests.test_baltasar_real_adapter import baltasar_record


class BaltasarRealInferenceTests(unittest.TestCase):
    def test_baltasar_real_joblib_inference_returns_direction(self):
        model_path = Path("baltasar_training_v1/artifacts/models/candidate_target_compact_features__random_forest.joblib")
        self.assertTrue(model_path.exists(), f"Missing Baltasar model: {model_path}")

        snapshot = snapshot_from_record(baltasar_record())
        adapter = BaltasarRealAdapter(
            {
                "real_version": "baltasar_real_adapter_v0.4",
                "model_path": str(model_path),
                "feature_variant": "compact",
            }
        )

        vote = adapter.evaluate(snapshot)

        self.assertEqual(vote.agent, "BALTASAR")
        self.assertIn(vote.direction, {"BUY", "SELL", "NEUTRAL"})
        self.assertGreater(vote.confidence, 0.0)
        self.assertNotIn("adapter failed", vote.reason.lower())


if __name__ == "__main__":
    unittest.main()
