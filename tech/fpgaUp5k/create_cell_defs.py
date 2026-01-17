import glob
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


def create_cell_defs():
    json_files = glob.glob("sky130_fd_sc_hd/latest/cells/*/definition.json")
    definitions: Dict[str, Sky130Cell] = {}
    for json_file in json_files:
        with open(json_file) as fh:
            definition: Sky130Cell = json.load(fh)
            definitions[definition["name"]] = definition

    script_dir = os.path.dirname(os.path.realpath(__file__))
    with open(f"{script_dir}/cells.json", "w") as fh:
        json.dump(definitions, fh)


if __name__ == "__main__":
    create_cell_defs()
