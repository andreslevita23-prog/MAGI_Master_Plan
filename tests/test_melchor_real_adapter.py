import unittest

from magi.adapters.melchor_real_adapter import MelchorRealAdapter
from magi.ceo_magi import CeoMagiRuleBased
from magi.contracts import MageVote
from magi.melchor import MelchorRuleBased
from simulator.loaders import snapshot_from_record
from tests.test_loaders import sample_record


def melchor_config(**overrides):
    config = {
        "version": "rule_based_v0.1",
        "real_version": "melchor_real_adapter_v0.3",
        "engine_path": "servidor-prosperity/services/melchor-risk-engine.js",
        "rules_path": "config/melchor_rules.json",
        "timeout_seconds": 10,
        "default_risk_percent": 0.1,
        "max_spread_pips": 2.0,
        "allowed_sessions": ["london", "new_york", "overlap"],
        "daily_drawdown_block_percent": 1.0,
        "strict_warn": True,
    }
    config.update(overrides)
    return config


EXECUTION_CONFIG = {
    "sl_pips": 10.0,
    "tp_rr": 2.0,
    "default_pip_size": 0.0001,
    "symbol_pip_size": {"EURUSD": 0.0001},
}


class MelchorRealAdapterTests(unittest.TestCase):
    def test_rule_based_melchor_still_works(self):
        snapshot = snapshot_from_record(sample_record())
        melchor = MelchorRuleBased(melchor_config())

        vote = melchor.evaluate(snapshot)

        self.assertIsInstance(vote, MageVote)
        self.assertEqual(vote.agent, "MELCHOR")
        self.assertIn(vote.vote, {"APPROVE", "WARN", "BLOCK"})

    def test_real_adapter_returns_valid_mage_vote(self):
        snapshot = snapshot_from_record(sample_record())
        adapter = MelchorRealAdapter(melchor_config(), EXECUTION_CONFIG)

        vote = adapter.evaluate(snapshot)

        self.assertIsInstance(vote, MageVote)
        self.assertEqual(vote.agent, "MELCHOR")
        self.assertEqual(vote.vote, "APPROVE")
        self.assertEqual(vote.agent_version, "v1.0")
        self.assertGreater(vote.confidence, 0)
        self.assertIn("Melchor", vote.reason)

    def test_real_adapter_failure_returns_clear_block_vote(self):
        snapshot = snapshot_from_record(sample_record())
        adapter = MelchorRealAdapter(
            melchor_config(engine_path="missing/melchor-risk-engine.js"),
            EXECUTION_CONFIG,
        )

        vote = adapter.evaluate(snapshot)

        self.assertEqual(vote.vote, "BLOCK")
        self.assertEqual(vote.risk_flag, "CRITICAL")
        self.assertIn("Melchor real adapter failed", vote.reason)

    def test_ceo_receives_normalized_real_melchor_vote(self):
        snapshot = snapshot_from_record(sample_record())
        adapter = MelchorRealAdapter(melchor_config(), EXECUTION_CONFIG)
        melchor_vote = adapter.evaluate(snapshot)
        baltasar_vote = MageVote("mage_vote_v1", snapshot.snapshot_id, "BALTASAR", "test", None, "BUY", None, 0.8, "LOW", "test", [], "test")
        gaspar_vote = MageVote("mage_vote_v1", snapshot.snapshot_id, "GASPAR", "test", None, None, "GOOD", 0.8, "LOW", "test", [], "test")
        ceo = CeoMagiRuleBased({"version": "test", "strict_warn": True})

        decision = ceo.decide(snapshot, melchor_vote, baltasar_vote, gaspar_vote)

        self.assertEqual(melchor_vote.vote, "APPROVE")
        self.assertEqual(decision.action, "OPEN_LONG")


if __name__ == "__main__":
    unittest.main()
