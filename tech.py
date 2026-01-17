import json
import os
from typing import Dict, List, Literal, Pattern, Protocol, Tuple, TypedDict, Union

TechName = Literal["sky130A", "ihp-sg13g2", "gf180mcuD", "fpgaUp5k"]


class CellDefinition(TypedDict):
    url: str
    description: str


class PDKVersionInfo(TypedDict):
    source: str
    version: str


class Tech(Protocol):
    def_suffix: str
    librelane_pdk_args: str
    tt_corner: str
    cell_regexp: str
    netlist_type: Literal["pnl", "nl"]
    project_top_metal_layer: str

    """ Extra PDK-specific configuration for LibreLane """
    librelane_config: Dict[
        str, Union[bool, int, float, str, List[str], Dict[str, List[str]]]
    ]
    """ These layers will be removed from the SVG render of the layout """
    label_layers: List[Tuple[int, int]]
    """ These layers are hardly visible and will also be removed from the SVG render of the layout """
    buried_layers: List[Tuple[int, int]]
    """ Cells with names matching this regex will have their layers shuffled in the SVG render """
    scramble_cells: None | str | Pattern
    """ Default name of the mux config YAML file. """
    mux_config_yaml_name: str
    """ Lists all of the analog switch / power gate macros that need to be copied to the tt_top directory. """
    mux_macros: List[str]
    """ Lists all of the extra logo macros that need to be copied to the tt_top directory. """
    extra_logo_macros: List[str]
    """ GDS layer/datatype for the place&route boundary marker layer """
    prboundary_layer: Tuple[int, int]
    """ GDS layer/datatype for the metal layer used in the logo """
    logo_layer: Tuple[int, int]
    """ LEF layer name for the metal layer used in the logo """
    logo_layer_name: str
    """ Logo pixel size in microns """
    logo_pixel_size: float

    def read_pdk_version(self, pdk_root: str) -> PDKVersionInfo:
        raise NotImplementedError()

    def load_cell_definitions(self) -> Dict[str, CellDefinition]:
        raise NotImplementedError()


def parse_openpdks_pdk_version(
    sources_file: str, expected_source: str = "open_pdks"
) -> PDKVersionInfo:
    with open(sources_file) as f:
        pdk_source, pdk_version = f.read().strip().split(" ")
        assert pdk_source == expected_source
        return PDKVersionInfo(source=pdk_source, version=pdk_version)


class Sky130Tech(Tech):
    def_suffix = "pg"
    librelane_pdk_args = ""
    tt_corner = "nom_tt_025C_1v80"
    cell_regexp = (
        r"^\s*sky130_(?P<cell_lib>\S+)__(?P<cell_name>\S+)_(?P<cell_drive>\d+)"
    )
    netlist_type = "pnl"
    project_top_metal_layer = "met4"
    librelane_config = {}
    label_layers = [
        (64, 59),  # pwell.label
        (64, 5),  # nwell.label
        (67, 5),  # li1.label
        (68, 5),  # met1.label
        (69, 5),  # met2.label
        (70, 5),  # met3.label
        (71, 5),  # met4.label
    ]
    buried_layers = [
        (64, 16),  # nwell.pin
        (65, 44),  # tap.drawing
        (68, 16),  # met1.pin
        (68, 44),  # via.drawing
        (81, 4),  # areaid.standardc
        (70, 20),  # met3.drawing
    ]
    scramble_cells = None
    mux_config_yaml_name = "sky130.yaml"
    mux_macros = [
        "pg/sky130/tt_pg_1v8_hp_1",
        "pg/sky130/tt_pg_1v8_hp_2",
        "pg/sky130/tt_pg_1v8_hp_4",
        "pg/sky130/tt_pg_1v8_ll_1",
        "pg/sky130/tt_pg_1v8_ll_2",
        "pg/sky130/tt_pg_1v8_ll_4",
        "pg/sky130/tt_pg_3v3_2",
        "asw/sky130/tt_asw_3v3",
    ]
    extra_logo_macros = []
    prboundary_layer = (235, 4)  # prBoundary.boundary
    logo_layer = (71, 20)  # met4.drawing
    logo_layer_name = "met4"
    logo_pixel_size = 0.5  # um

    def read_pdk_version(self, pdk_root: str) -> PDKVersionInfo:
        pdk_sources_file = os.path.join(pdk_root, "sky130A", "SOURCES")
        return parse_openpdks_pdk_version(pdk_sources_file)

    def load_cell_definitions(self) -> Dict[str, CellDefinition]:
        URL_FORMAT = "https://skywater-pdk.readthedocs.io/en/main/contents/libraries/sky130_fd_sc_hd/cells/{name}/README.html"
        script_dir = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(script_dir, "tech/sky130A/cells.json")) as fh:
            cells = json.load(fh)
        for name, cell in cells.items():
            cell["url"] = URL_FORMAT.format(name=name)
        return cells


class IHPTech(Tech):
    def_suffix = "pgvdd"
    librelane_pdk_args = "--pdk ihp-sg13g2"
    tt_corner = "nom_typ_1p20V_25C"
    cell_regexp = r"^\s*sg13g2_(?P<cell_name>\S+)_(?P<cell_drive>\d+)"
    netlist_type = "nl"
    project_top_metal_layer = "TopMetal1"
    librelane_config = {}
    label_layers = [
        (8, 1),  # Metal1.label
        (8, 25),  # Metal1.text
        (67, 25),  # Metal5.text
        (126, 25),  # TopMetal1.text
    ]
    buried_layers = [
        (6, 0),  # Cont.drawing
        (8, 2),  # Metal1.pin
        (19, 0),  # Via1.drawing
        (51, 0),  # HeatTrans.drawing
        (189, 4),  # prBoundary.boundary
    ]
    scramble_cells = "sg13g2_"
    mux_config_yaml_name = "ihp-sg13g2.yaml"
    mux_macros = [
        "pg/ihp-sg13g2/tt_pg_1v5_hp_1",
        "pg/ihp-sg13g2/tt_pg_1v5_hp_2",
        "pg/ihp-sg13g2/tt_pg_1v5_hp_4",
        "pg/ihp-sg13g2/tt_pg_1v5_ll_1",
        "pg/ihp-sg13g2/tt_pg_1v5_ll_2",
        "pg/ihp-sg13g2/tt_pg_1v5_ll_4",
    ]
    extra_logo_macros = [
        "tech/ihp-sg13g2/tt_logo_corner",
    ]
    prboundary_layer = (189, 4)  # prBoundary.boundary
    logo_layer = (67, 0)  # Metal5.drawing
    logo_layer_name = "Metal5"
    logo_pixel_size = 0.25  # um

    def read_pdk_version(self, pdk_root: str) -> PDKVersionInfo:
        pdk_sources_file = os.path.join(pdk_root, "ihp-sg13g2", "SOURCES")
        return parse_openpdks_pdk_version(pdk_sources_file, "IHP-Open-PDK")

    def load_cell_definitions(self) -> Dict[str, CellDefinition]:
        URL_FORMAT = "https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/refs/heads/main/ihp-sg13g2/libs.ref/sg13g2_stdcell/doc/sg13g2_stdcell_typ_1p20V_25C.pdf#{ref}"
        script_dir = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(script_dir, "tech/ihp-sg13g2/cells.json")) as fh:
            cells = json.load(fh)
        for cell in cells.values():
            cell["url"] = URL_FORMAT.format(ref=cell["doc_ref"])
        return cells


class GF180MCUDTech(Tech):
    def_suffix = "pgvdd"
    librelane_pdk_args = "--pdk gf180mcuD"
    tt_corner = "nom_tt_025C_3v30"
    cell_regexp = (
        r"^\s*gf180mcu_(?P<cell_lib>\S+)__(?P<cell_name>\S+)_(?P<cell_drive>\d+)"
    )
    netlist_type = "pnl"
    project_top_metal_layer = "Metal4"
    librelane_config = {
        # The default configuration is for a 5V supply, but TT targets a 3.3V supply,
        # so we need to adjust the library paths to use the 3.3V libraries.
        "VDD_PIN_VOLTAGE": 3.3,
        "LIB_SYNTH": "pdk_dir::libs.ref/gf180mcu_fd_sc_mcu7t5v0/lib/gf180mcu_fd_sc_mcu7t5v0__tt_025C_3v30.lib",
        "LIB_FASTEST": "pdk_dir::libs.ref/gf180mcu_fd_sc_mcu7t5v0/lib/gf180mcu_fd_sc_mcu7t5v0__ff_n40C_3v60.lib",
        "LIB_SLOWEST": "pdk_dir::libs.ref/gf180mcu_fd_sc_mcu7t5v0/lib/gf180mcu_fd_sc_mcu7t5v0__ss_125C_3v00.lib",
        "DEFAULT_CORNER": "nom_tt_025C_3v30",
        "STA_CORNERS": [
            "nom_tt_025C_3v30",
            "nom_ss_125C_3v00",
            "nom_ff_n40C_3v60",
            "min_tt_025C_3v30",
            "min_ss_125C_3v00",
            "min_ff_n40C_3v60",
            "max_tt_025C_3v30",
            "max_ss_125C_3v00",
            "max_ff_n40C_3v60",
        ],
        "LIB": {
            "*_tt_025C_3v30": [
                "pdk_dir::libs.ref/gf180mcu_fd_sc_mcu7t5v0/lib/gf180mcu_fd_sc_mcu7t5v0__tt_025C_3v30.lib"
            ],
            "*_ss_125C_3v00": [
                "pdk_dir::libs.ref/gf180mcu_fd_sc_mcu7t5v0/lib/gf180mcu_fd_sc_mcu7t5v0__ss_125C_3v00.lib"
            ],
            "*_ff_n40C_3v60": [
                "pdk_dir::libs.ref/gf180mcu_fd_sc_mcu7t5v0/lib/gf180mcu_fd_sc_mcu7t5v0__ff_n40C_3v60.lib"
            ],
        },
    }
    label_layers = [
        # TODO: add label layers
    ]
    buried_layers = [
        # TODO: add buried layers
    ]
    scramble_cells = "gf180mcu_fd_sc_"
    mux_config_yaml_name = "gf180mcuD.yaml"
    mux_macros = [
        # Currently none
    ]
    extra_logo_macros = []
    prboundary_layer = (0, 0)  # PR_bndry
    logo_layer = (46, 0)  # Metal4
    logo_layer_name = "Metal4"
    logo_pixel_size = 0.325  # um

    def read_pdk_version(self, pdk_root: str) -> PDKVersionInfo:
        pdk_sources_file = os.path.join(pdk_root, "gf180mcuD", "SOURCES")
        return parse_openpdks_pdk_version(pdk_sources_file)

    def load_cell_definitions(self) -> Dict[str, CellDefinition]:
        URL_FORMAT = "https://gf180mcu-pdk.readthedocs.io/en/latest/digital/standard_cells/gf180mcu_fd_sc_mcu7t5v0/cells/{name}/gf180mcu_fd_sc_mcu7t5v0__{name}{variant}.html"
        script_dir = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(script_dir, "tech/gf180mcuD/cells.json")) as fh:
            cells = json.load(fh)
        for name, cell in cells.items():
            variant = cell["variants"][0] if cell["variants"] else ""
            cell["url"] = URL_FORMAT.format(name=name, variant=variant)
        return cells


tech_map: dict[TechName, Tech] = {
    "ihp-sg13g2": IHPTech(),
    "gf180mcuD": GF180MCUDTech(),
    "sky130A": Sky130Tech(),
    "fpgaUp5k": Sky130Tech(),  # don't need this
}
