# Create a JSON file with cell definitions from the gf180mcu_fd_sc_mcu7t5v0 standard cell library.
# To run this script, first clone the standard cell library by running:
#
#     git clone --depth 1 https://github.com/google/globalfoundries-pdk-libs-gf180mcu_fd_sc_mcu7t5v0 gf180mcu_fd_sc_mcu7t5v0

import glob
import json
import os
from typing import Dict, List, TypedDict


class GF180Cell(TypedDict):
    description: str
    file_prefix: str
    library: str
    name: str
    parameters: List[str]
    ports: List[List[str]]  # kind, name, direction, description
    type: str
    verilog_name: str
    """
    Each variant is a different drive strength (e.g. _1, _2, _4, etc.).
    Cells with a single drive strength have the empty string as variant.
    """
    variants: List[str]


def create_cell_defs():
    json_files = glob.glob("gf180mcu_fd_sc_mcu7t5v0/cells/*/definition.json")
    definitions: Dict[str, GF180Cell] = {}
    for json_file in json_files:
        with open(json_file) as fh:
            definition: GF180Cell = json.load(fh)
            definitions[definition["name"]] = definition
            variants = []
            for item in os.listdir(os.path.dirname(json_file)):
                if item.startswith(definition["file_prefix"]) and item.endswith(".gds"):
                    variants.append(item[len(definition["file_prefix"]) : -4])
            variants.sort()
            definition["variants"] = variants
            print(definition["name"], variants)

    script_dir = os.path.dirname(os.path.realpath(__file__))
    with open(f"{script_dir}/cells.json", "w") as fh:
        json.dump(definitions, fh, indent=2)


if __name__ == "__main__":
    create_cell_defs()
