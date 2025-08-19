from typing import TypedDict


class Config(TypedDict):
    """TypedDict for Tiny Tapeout's config.yaml file."""

    id: str
    name: str
    project_dir: str
    end_date: str
    top_level_macro: str
    powered_netlists: bool
    no_power_gating: bool
    pdk: str
