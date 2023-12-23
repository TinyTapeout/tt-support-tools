from typing import Dict, TypedDict


class ShuttleIndexMuxEntry(TypedDict):
    macro: str
    x: int
    y: int
    tiles: str
    repo: str
    commit: str
    features: dict[str, bool]


class ShuttleIndex(TypedDict):
    """TypedDict for Tiny Tapeout's shuttle_index.json file."""

    shuttle: str
    repo: str
    commit: str
    commit_date: int
    version: int
    mux: Dict[str, ShuttleIndexMuxEntry]
