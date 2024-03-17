from typing import List, NotRequired, TypedDict


class ShuttleIndexProject(TypedDict):
    macro: str
    address: int
    x: int
    y: int
    tiles: str
    repo: str
    commit: str
    analog_pins: NotRequired[List[int]]


class ShuttleIndex(TypedDict):
    """TypedDict for Tiny Tapeout's shuttle_index.json file."""

    name: str
    repo: str
    commit: str
    commit_date: int
    version: int
    projects: List[ShuttleIndexProject]
