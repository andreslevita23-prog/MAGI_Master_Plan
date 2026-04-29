import unittest

from tests.test_loaders import sample_record
from simulator.loaders import snapshot_from_record
from simulator.validation import validate_snapshot


class ValidationTests(unittest.TestCase):
    def test_validation_accepts_minimal_valid_snapshot(self):
        snapshot = snapshot_from_record(sample_record())

        issues = validate_snapshot(snapshot)

        self.assertTrue(all(issue.severity != "error" for issue in issues))


    def test_validation_rejects_negative_spread(self):
        record = sample_record()
        record["spread_pips"] = -1
        snapshot = snapshot_from_record(record)

        issues = validate_snapshot(snapshot)

        self.assertTrue(any(issue.code == "negative_spread" for issue in issues))


if __name__ == "__main__":
    unittest.main()
