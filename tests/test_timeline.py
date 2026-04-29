import unittest

from tests.test_loaders import sample_record
from simulator.loaders import snapshot_from_record
from simulator.timeline import sort_snapshots


class TimelineTests(unittest.TestCase):
    def test_timeline_orders_by_symbol_anchor_timestamp_and_id(self):
        late = sample_record("b")
        late["anchor_bar_timestamp"] = "2026-01-01T12:00:00Z"
        early = sample_record("a")
        early["anchor_bar_timestamp"] = "2026-01-01T11:55:00Z"

        ordered = sort_snapshots([snapshot_from_record(late), snapshot_from_record(early)])

        self.assertEqual([snapshot.snapshot_id for snapshot in ordered], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
