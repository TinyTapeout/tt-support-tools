import json
import os
from typing import Dict, List, Optional, TypedDict


class Port(TypedDict):
    kind: str
    name: str
    direction: str
    description: str


class Cell(TypedDict):
    description: str
    file_prefix: str
    library: str
    name: str
    parameters: List[str]
    ports: List[Port]
    type: str
    verilog_name: str
    equation: Optional[str]


Cells = Dict[str, Cell]


def load_cells() -> Cells:
    script_dir = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(script_dir, "cells.json")) as fh:
        return json.load(fh)
