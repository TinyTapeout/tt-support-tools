from typing import List, Literal, TypedDict

from tech import TechName


class ArtworkEntryType(TypedDict):
    """TypedDict for artwork, used by `config.DatasheetConfig`"""

    id: str
    rotate: str


class DatasheetConfig(TypedDict):
    """TypedDict for the datasheet config within Tiny Tapeout's config.yaml file"""

    pinout: Literal["caravel", "openframe"]
    theme_override_colour: str
    show_chip_viewer: bool
    link_disable_colour: bool
    link_override_colour: str
    qrcode_follows_theme: bool
    include: List[str]
    disabled: List[str]
    artwork: List[ArtworkEntryType]


class Config(TypedDict):
    """TypedDict for Tiny Tapeout's config.yaml file."""

    id: str
    name: str
    project_dir: str
    end_date: str
    top_level_macro: str
    powered_netlists: bool
    no_power_gating: bool
    pdk: TechName
    datasheet_config: DatasheetConfig
    openframe: bool
