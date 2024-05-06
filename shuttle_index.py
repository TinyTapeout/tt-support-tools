from typing import List, Literal, NotRequired, TypedDict


class ShuttleIndexProject(TypedDict):
    macro: str
    address: int
    x: int
    y: int
    tiles: str
    repo: str
    commit: str
    analog_pins: NotRequired[tuple[int, ...]]


class ShuttleIndexLayout(TypedDict):
    muxes: List[List[Literal["analog", "digital"]]]


class ShuttleIndex(TypedDict):
    """TypedDict for Tiny Tapeout's shuttle_index.json file."""

    name: str
    repo: str
    commit: str
    commit_date: int
    version: int
    layout: ShuttleIndexLayout
    projects: List[ShuttleIndexProject]
