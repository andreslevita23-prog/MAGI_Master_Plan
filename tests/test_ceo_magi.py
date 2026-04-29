import unittest

from magi.ceo_magi import CeoMagiRuleBased
from magi.contracts import MageVote
from simulator.loaders import snapshot_from_record
from tests.test_loaders import sample_record


def vote(agent, vote=None, direction=None, quality=None):
    return MageVote("mage_vote_v1", "s1", agent, "test", vote, direction, quality, 0.8, "LOW", "test", [], "test")


class CeoMagiTests(unittest.TestCase):
    def test_ceo_opens_long_when_agents_align(self):
        snapshot = snapshot_from_record(sample_record())
        ceo = CeoMagiRuleBased({"version": "test", "strict_warn": True})

        decision = ceo.decide(snapshot, vote("MELCHOR", vote="APPROVE"), vote("BALTASAR", direction="BUY"), vote("GASPAR", quality="GOOD"))

        self.assertEqual(decision.action, "OPEN_LONG")
        self.assertEqual(decision.direction, "LONG")


    def test_ceo_blocks_when_melchor_blocks(self):
        snapshot = snapshot_from_record(sample_record())
        ceo = CeoMagiRuleBased({"version": "test", "strict_warn": True})

        decision = ceo.decide(snapshot, vote("MELCHOR", vote="BLOCK"), vote("BALTASAR", direction="BUY"), vote("GASPAR", quality="GOOD"))

        self.assertEqual(decision.action, "NO_TRADE")
        self.assertEqual(decision.decision_rule, "melchor_block")


if __name__ == "__main__":
    unittest.main()
