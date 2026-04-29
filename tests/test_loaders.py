import csv
import json
import shutil
import unittest
from uuid import uuid4
from pathlib import Path

from simulator.loaders import load_csv, load_jsonl


def sample_record(snapshot_id="s1"):
    return {
        "snapshot_id": snapshot_id,
        "symbol": "EURUSD",
        "timestamp": "2026-01-01T12:00:00Z",
        "anchor_bar_timestamp": "2026-01-01T11:55:00Z",
        "anchor_open": 1.1,
        "anchor_high": 1.2,
        "anchor_low": 1.0,
        "anchor_close": 1.15,
        "current_price": 1.15,
        "spread_pips": 0.8,
        "features": {"rsi_14": 60, "momentum": "bullish"},
        "gaspar_context": {"timing_quality": {"active_session": "london"}},
        "validation": {"is_valid": True, "issues": []},
    }


class LoaderTests(unittest.TestCase):
    def test_loader_jsonl_reads_snapshots(self):
        with workspace_tempdir() as temp_dir:
            path = Path(temp_dir) / "sample.jsonl"
            path.write_text(json.dumps(sample_record()) + "\n", encoding="utf-8")

            snapshots, errors = load_jsonl(path)

        self.assertEqual(errors, [])
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].snapshot_id, "s1")
        self.assertIsNotNone(snapshots[0].timestamp.tzinfo)


    def test_loader_csv_reads_snapshots(self):
        with workspace_tempdir() as temp_dir:
            path = Path(temp_dir) / "sample.csv"
            row = sample_record()
            row["features_json"] = json.dumps(row.pop("features"))
            row["validation_is_valid"] = "true"
            row.pop("gaspar_context")
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
                writer.writeheader()
                writer.writerow(row)

            snapshots, errors = load_csv(path)

        self.assertEqual(errors, [])
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].features["rsi_14"], 60)


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
