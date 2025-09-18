import json
import os
from typing import Dict, List, Literal, Protocol, Tuple, TypedDict

from git.repo import Repo

TechName = Literal["sky130A", "ihp-sg13g2"]


class CellDefinition(TypedDict):
    url: str
    description: str


class Tech(Protocol):
    def_suffix: str
    librelane_pdk_args: str
    tt_corner: str
    cell_regexp: str
    netlist_type: Literal["pnl", "nl"]

    """ These layers will be removed from the SVG render of the layout """
    label_layers: List[Tuple[int, int]]
    """ These layers are hardly visible and will also be removed from the SVG render of the layout """
    buried_layers: List[Tuple[int, int]]
    """ Default name of the mux config YAML file. """
    mux_config_yaml_name: str
    """ Lists all of the analog switch / power gate macros that need to be copied to the tt_top directory. """
    mux_macros: List[str]
    """ Lists all of the extra logo macros that need to be copied to the tt_top directory. """
    extra_logo_macros: List[str]

    def read_pdk_version(self, pdk_root: str) -> str:
        raise NotImplementedError()

    def load_cell_definitions(self) -> Dict[str, CellDefinition]:
        raise NotImplementedError()


class Sky130Tech(Tech):
    def_suffix = "pg"
    librelane_pdk_args = ""
    tt_corner = "nom_tt_025C_1v80"
    cell_regexp = r"sky130_(?P<cell_lib>\S+)__(?P<cell_name>\S+)_(?P<cell_drive>\d+)"
    netlist_type = "pnl"
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

    def read_pdk_version(self, pdk_root: str) -> str:
        pdk_sources_file = os.path.join(pdk_root, "sky130A", "SOURCES")
        with open(pdk_sources_file) as f:
            return f.read()

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
    librelane_pdk_args = "--manual-pdk --pdk ihp-sg13g2"
    tt_corner = "nom_typ_1p20V_25C"
    cell_regexp = r"sg13g2_(?P<cell_name>\S+)_(?P<cell_drive>\d+)"
    netlist_type = "nl"
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

    def read_pdk_version(self, pdk_root: str) -> str:
        pdk_repo = Repo(pdk_root)
        pdk_repo_name = list(pdk_repo.remotes[0].urls)[0].split("/")[-1]
        pdk_commit = pdk_repo.commit().hexsha
        return f"{pdk_repo_name} {pdk_commit}"

    def load_cell_definitions(self) -> Dict[str, CellDefinition]:
        URL_FORMAT = "https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/refs/heads/main/ihp-sg13g2/libs.ref/sg13g2_stdcell/doc/sg13g2_stdcell_typ_1p20V_25C.pdf#{ref}"
        script_dir = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(script_dir, "tech/ihp-sg13g2/cells.json")) as fh:
            cells = json.load(fh)
        for cell in cells.values():
            cell["url"] = URL_FORMAT.format(ref=cell["doc_ref"])
        return cells


tech_map: dict[TechName, Tech] = {
    "sky130A": Sky130Tech(),
    "ihp-sg13g2": IHPTech(),
}
