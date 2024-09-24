import json
import os
from typing import Dict, List, Optional, TypedDict


class Port(TypedDict):
    kind: str
    name: str
    direction: str
    description: str


class Sky130Cell(TypedDict):
    description: str
    file_prefix: str
    library: str
    name: str
    parameters: List[str]
    ports: List[Port]
    type: str
    verilog_name: str
    equation: Optional[str]


class IHPCell(TypedDict):
    description: str
    doc_name: str
    doc_ref: int


Sky130Cells = Dict[str, Sky130Cell]
IHPCells = Dict[str, IHPCell]


def load_sky130_cells() -> Sky130Cells:
    script_dir = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(script_dir, "cells.json")) as fh:
        return json.load(fh)


def load_ihp_cells() -> IHPCells:
    script_dir = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(script_dir, "ihp/cells.json")) as fh:
        return json.load(fh)
