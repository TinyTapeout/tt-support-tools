from typing import TypedDict


class Config(TypedDict):
    """TypedDict for Tiny Tapeout's config.yaml file."""

    id: str
    name: str
    project_dir: str
    start_date: str
