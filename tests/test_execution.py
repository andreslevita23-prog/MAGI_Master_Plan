import unittest

from magi.contracts import CeoDecision
from simulator.execution import ExecutionEngine
from simulator.loaders import snapshot_from_record
from tests.test_loaders import sample_record


def snapshot(snapshot_id, price=1.1000, high=None, low=None, timestamp="2026-01-01T12:00:00Z"):
    record = sample_record(snapshot_id)
    record["timestamp"] = timestamp
    record["anchor_bar_timestamp"] = timestamp
    record["current_price"] = price
    record["anchor_open"] = price
    record["anchor_high"] = high if high is not None else price
    record["anchor_low"] = low if low is not None else price
    record["anchor_close"] = price
    return snapshot_from_record(record)


def decision(snapshot_id, action):
    return CeoDecision(
        schema_version="ceo_decision_v1",
        snapshot_id=snapshot_id,
        decision_id=f"decision-{snapshot_id}",
        ceo_version="test",
        action=action,
        direction="LONG" if action == "OPEN_LONG" else "SHORT" if action == "OPEN_SHORT" else None,
        decision_rule="test",
        votes={},
        reason="test",
    )


NO_TRADE = decision("none", "NO_TRADE")


class ExecutionTests(unittest.TestCase):
    def engine(self, timeout=3):
        return ExecutionEngine({"sl_pips": 10, "tp_rr": 2, "timeout_snapshots": timeout, "default_pip_size": 0.0001})

    def test_opens_long_correctly(self):
        engine = self.engine()
        entry = snapshot("entry")

        engine.on_snapshot(entry, decision("entry", "OPEN_LONG"))

        self.assertIsNotNone(engine.open_trade)
        self.assertEqual(engine.open_trade.direction, "LONG")
        self.assertAlmostEqual(engine.open_trade.sl, 1.0990)
        self.assertAlmostEqual(engine.open_trade.tp, 1.1020)

    def test_opens_short_correctly(self):
        engine = self.engine()
        entry = snapshot("entry")

        engine.on_snapshot(entry, decision("entry", "OPEN_SHORT"))

        self.assertIsNotNone(engine.open_trade)
        self.assertEqual(engine.open_trade.direction, "SHORT")
        self.assertAlmostEqual(engine.open_trade.sl, 1.1010)
        self.assertAlmostEqual(engine.open_trade.tp, 1.0980)

    def test_closes_by_tp(self):
        engine = self.engine()
        engine.on_snapshot(snapshot("entry"), decision("entry", "OPEN_LONG"))

        engine.on_snapshot(snapshot("tp", price=1.1015, high=1.1021, low=1.1005), NO_TRADE)

        self.assertIsNone(engine.open_trade)
        self.assertEqual(engine.closed_trades[0].exit_reason, "TP")
        self.assertEqual(engine.closed_trades[0].pnl_r, 2.0)

    def test_closes_by_sl(self):
        engine = self.engine()
        engine.on_snapshot(snapshot("entry"), decision("entry", "OPEN_LONG"))

        engine.on_snapshot(snapshot("sl", price=1.0995, high=1.1005, low=1.0989), NO_TRADE)

        self.assertIsNone(engine.open_trade)
        self.assertEqual(engine.closed_trades[0].exit_reason, "SL")
        self.assertEqual(engine.closed_trades[0].pnl_r, -1.0)

    def test_closes_by_timeout(self):
        engine = self.engine(timeout=2)
        engine.on_snapshot(snapshot("entry"), decision("entry", "OPEN_LONG"))

        engine.on_snapshot(snapshot("hold1", price=1.1005, high=1.1006, low=1.0995), NO_TRADE)
        engine.on_snapshot(snapshot("hold2", price=1.1007, high=1.1008, low=1.0998), NO_TRADE)

        self.assertIsNone(engine.open_trade)
        self.assertEqual(engine.closed_trades[0].exit_reason, "TIMEOUT")
        self.assertAlmostEqual(engine.closed_trades[0].pnl_r, 0.7)

    def test_closes_by_end_of_data(self):
        engine = self.engine()
        entry = snapshot("entry")
        engine.on_snapshot(entry, decision("entry", "OPEN_LONG"))

        result = engine.close_end_of_data(entry)

        self.assertIsNotNone(result)
        self.assertIsNone(engine.open_trade)
        self.assertEqual(engine.closed_trades[0].exit_reason, "END_OF_DATA")

    def test_detects_ambiguous(self):
        engine = self.engine()
        engine.on_snapshot(snapshot("entry"), decision("entry", "OPEN_LONG"))

        engine.on_snapshot(snapshot("ambiguous", price=1.1000, high=1.1021, low=1.0989), NO_TRADE)

        self.assertEqual(engine.closed_trades[0].exit_reason, "AMBIGUOUS")
        self.assertTrue(engine.closed_trades[0].ambiguous_intrabar)

    def test_respects_one_open_trade(self):
        engine = self.engine()
        engine.on_snapshot(snapshot("entry1"), decision("entry1", "OPEN_LONG"))

        engine.on_snapshot(snapshot("entry2", price=1.1002, high=1.1003, low=1.0997), decision("entry2", "OPEN_SHORT"))

        self.assertIsNotNone(engine.open_trade)
        self.assertEqual(engine.open_trade.direction, "LONG")
        self.assertEqual(engine.trade_attempts_blocked_by_open_trade, 1)


if __name__ == "__main__":
    unittest.main()
