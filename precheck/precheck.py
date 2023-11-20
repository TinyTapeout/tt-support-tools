#!/usr/bin/env python3
import argparse
import logging
import os
import subprocess

import klayout.db as pya
import klayout.rdb as rdb
from klayout_tools import parse_lyp_layers

PDK_ROOT = os.getenv("PDK_ROOT")
PDK_NAME = os.getenv("PDK_NAME") or "sky130A"
LYP_FILE = f"{PDK_ROOT}/{PDK_NAME}/libs.tech/klayout/tech/{PDK_NAME}.lyp"
REPORTS_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "reports")

if not PDK_ROOT:
    logging.error("PDK_ROOT environment variable not set")
    exit(1)


def magic_drc(gds: str, toplevel: str):
    logging.info(f"Running magic DRC on {gds} (module={toplevel})")

    magic = subprocess.run(
        [
            "magic",
            "-noconsole",
            "-dnull",
            "-rcfile",
            f"{PDK_ROOT}/{PDK_NAME}/libs.tech/magic/{PDK_NAME}.magicrc",
            "magic_drc.tcl",
            gds,
            toplevel,
            PDK_ROOT,
            f"{REPORTS_PATH}/magic_drc.txt",
            f"{REPORTS_PATH}/magic_drc.mag",
        ],
    )

    if magic.returncode != 0:
        logging.error("Magic DRC failed")
        return False

    return True


def klayout_drc(gds: str, check: str):
    logging.info(f"Running klayout {check} on {gds}")
    report_file = f"{REPORTS_PATH}/drc_{check}.xml"
    klayout = subprocess.run(
        [
            "klayout",
            "-b",
            "-r",
            f"tech-files/{PDK_NAME}_mr.drc",
            "-rd",
            f"{check}=true",
            "-rd",
            f"input={gds}",
            "-rd",
            f"report={report_file}",
        ],
    )
    if klayout.returncode != 0:
        logging.error(f"Klayout {check} failed")
        return False

    report = rdb.ReportDatabase("DRC")
    report.load(report_file)

    if report.num_items() > 0:
        logging.error(
            f"Klayout {check} failed with {report.num_items()} DRC violations"
        )
        return False

    return True


def klayout_checks(gds: str):
    layout = pya.Layout()
    layout.read(gds)
    layers = parse_lyp_layers(LYP_FILE)

    logging.info("Running forbidden layer check...")
    forbidden_layers = [
        "met5.drawing",
        "met5.pin",
        "met5.label",
    ]

    had_error = False
    for layer in forbidden_layers:
        layer_info = layers[layer]
        logging.info(f"* Checking {layer_info.name}")
        layer_index = layout.find_layer(layer_info.layer, layer_info.data_type)
        if layer_index is not None:
            logging.error(f"Forbidden layer {layer} found in {gds}")
            had_error = True

    if had_error:
        logging.error("Klayout checks failed")
    return not had_error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gds", required=True)
    parser.add_argument("--top-module", required=False)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logging.info(f"PDK_ROOT: {PDK_ROOT}")

    if args.top_module:
        top_module = args.top_module
    else:
        top_module = os.path.splitext(os.path.basename(args.gds))[0]

    assert magic_drc(args.gds, top_module)

    assert klayout_drc(args.gds, "feol")
    assert klayout_drc(args.gds, "beol")
    assert klayout_drc(args.gds, "offgrid")

    assert klayout_checks(args.gds)

    logging.info(f"Precheck passed for {args.gds}! 🎉")


if __name__ == "__main__":
    main()
