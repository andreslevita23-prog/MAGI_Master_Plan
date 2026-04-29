from __future__ import annotations

from simulator.schemas import Snapshot


def sort_snapshots(snapshots: list[Snapshot]) -> list[Snapshot]:
    return sorted(snapshots, key=lambda item: (item.symbol, item.anchor_bar_timestamp, item.snapshot_id))


def iter_timeline(snapshots: list[Snapshot]):
    yield from sort_snapshots(snapshots)
