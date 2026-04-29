import unittest
from pathlib import Path

from magi.adapters.gaspar_real_adapter import GasparRealAdapter
from simulator.loaders import snapshot_from_record
from tests.test_gaspar_real_adapter import baltasar_vote, gaspar_record


class GasparRealInferenceTests(unittest.TestCase):
    def test_gaspar_real_joblib_inference_returns_quality(self):
        model_path = Path("gaspar_training_v1/artifacts/models/gaspar_baseline.joblib")
        self.assertTrue(model_path.exists(), f"Missing Gaspar model: {model_path}")

        snapshot = snapshot_from_record(gaspar_record())
        adapter = GasparRealAdapter(
            {
                "real_version": "gaspar_real_adapter_v0.5",
                "model_path": str(model_path),
                "target_version": "v1",
            }
        )

        vote = adapter.evaluate(snapshot, baltasar_vote("BUY"))

        self.assertEqual(vote.agent, "GASPAR")
        self.assertIn(vote.quality, {"GOOD", "FAIR", "POOR"})
        self.assertGreater(vote.confidence, 0.0)
        self.assertNotIn("adapter failed", vote.reason.lower())


if __name__ == "__main__":
    unittest.main()
