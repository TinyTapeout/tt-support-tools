#!/usr/bin/env python3
import argparse
import logging
import os
import subprocess
import time
import traceback
import xml.etree.ElementTree as ET

import gdstk
import klayout.db as pya
import klayout.rdb as rdb
import yaml
from klayout_tools import parse_lyp_layers
from pin_check import pin_check
from precheck_failure import PrecheckFailure

PDK_ROOT = os.getenv("PDK_ROOT")
PDK_NAME = os.getenv("PDK_NAME") or "sky130A"
LYP_FILE = f"{PDK_ROOT}/{PDK_NAME}/libs.tech/klayout/tech/{PDK_NAME}.lyp"
REPORTS_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "reports")

if not PDK_ROOT:
    logging.error("PDK_ROOT environment variable not set")
    exit(1)


def has_sky130_devices(gds: str):
    for cell_name in gdstk.read_rawcells(gds):
        if cell_name.startswith("sky130_fd_"):
            return True
    return False


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
        if not has_sky130_devices(gds):
            logging.warning("No sky130 devices present - was the design flattened?")
        raise PrecheckFailure("Magic DRC failed")


def klayout_drc(gds: str, check: str, script=f"{PDK_NAME}_mr.drc"):
    logging.info(f"Running klayout {check} on {gds}")
    report_file = f"{REPORTS_PATH}/drc_{check}.xml"
    klayout = subprocess.run(
        [
            "klayout",
            "-b",
            "-r",
            f"tech-files/{script}",
            "-rd",
            f"{check}=true",
            "-rd",
            f"input={gds}",
            "-rd",
            f"report={report_file}",
        ],
    )
    if klayout.returncode != 0:
        raise PrecheckFailure(f"Klayout {check} failed")

    report = rdb.ReportDatabase("DRC")
    report.load(report_file)

    if report.num_items() > 0:
        raise PrecheckFailure(
            f"Klayout {check} failed with {report.num_items()} DRC violations"
        )


def klayout_zero_area(gds: str):
    return klayout_drc(gds, "zero_area", "zeroarea.rb.drc")


def klayout_checks(gds: str):
    layout = pya.Layout()
    layout.read(gds)
    layers = parse_lyp_layers(LYP_FILE)

    logging.info("Running top macro name check...")
    top_cell = layout.top_cell()
    expected_name = os.path.splitext(os.path.basename(gds))[0]
    if top_cell.name != expected_name:
        raise PrecheckFailure(
            f"Top macro name mismatch: expected {expected_name}, got {top_cell.name}"
        )

    logging.info("Running forbidden layer check...")
    forbidden_layers = [
        "met5.drawing",
        "met5.pin",
        "met5.label",
    ]

    for layer in forbidden_layers:
        layer_info = layers[layer]
        logging.info(f"* Checking {layer_info.name}")
        layer_index = layout.find_layer(layer_info.layer, layer_info.data_type)
        if layer_index is not None:
            raise PrecheckFailure(f"Forbidden layer {layer} found in {gds}")

    logging.info("Running prBoundary check...")
    layer_info = layers["prBoundary.boundary"]
    layer_index = layout.find_layer(layer_info.layer, layer_info.data_type)
    if layer_index is None:
        calma_index = f"{layer_info.layer}/{layer_info.data_type}"
        raise PrecheckFailure(
            f"prBoundary.boundary ({calma_index}) layer not found in {gds}"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gds", required=True)
    parser.add_argument("--lef", required=False)
    parser.add_argument("--template-def", required=False)
    parser.add_argument("--top-module", required=False)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logging.info(f"PDK_ROOT: {PDK_ROOT}")

    if args.top_module:
        top_module = args.top_module
    else:
        top_module = os.path.splitext(os.path.basename(args.gds))[0]

    if args.lef:
        lef = args.lef
    else:
        lef = os.path.splitext(args.gds)[0] + ".lef"

    if args.template_def:
        template_def = args.template_def
    else:
        yaml_dir = os.path.dirname(args.gds)
        while not os.path.exists(f"{yaml_dir}/info.yaml"):
            yaml_dir = os.path.dirname(yaml_dir)
            if yaml_dir == "/":
                raise PrecheckFailure("info.yaml not found")
        yaml_file = f"{yaml_dir}/info.yaml"
        yaml_data = yaml.safe_load(open(yaml_file))
        logging.info("info.yaml data:" + str(yaml_data))
        tiles = yaml_data.get("project", {}).get("tiles", "1x1")
        is_analog = yaml_data.get("project", {}).get("analog_pins", 0) > 0
        uses_3v3 = bool(yaml_data.get("project", {}).get("uses_3v3", False))
        if uses_3v3 and not is_analog:
            raise PrecheckFailure(
                "Projects with 3v3 power need at least one analog pin"
            )
        if is_analog:
            if uses_3v3:
                template_def = f"../def/analog/tt_analog_{tiles}_3v3.def"
            else:
                template_def = f"../def/analog/tt_analog_{tiles}.def"
        else:
            template_def = f"../def/tt_block_{tiles}_pg.def"
        logging.info(f"using def template {template_def}")

    checks = [
        ["Magic DRC", lambda: magic_drc(args.gds, top_module)],
        ["KLayout FEOL", lambda: klayout_drc(args.gds, "feol")],
        ["KLayout BEOL", lambda: klayout_drc(args.gds, "beol")],
        ["KLayout offgrid", lambda: klayout_drc(args.gds, "offgrid")],
        [
            "KLayout pin label overlapping drawing",
            lambda: klayout_drc(
                args.gds,
                "pin_label_purposes_overlapping_drawing",
                "pin_label_purposes_overlapping_drawing.rb.drc",
            ),
        ],
        ["KLayout zero area", lambda: klayout_zero_area(args.gds)],
        ["KLayout Checks", lambda: klayout_checks(args.gds)],
        [
            "Pin check",
            lambda: pin_check(args.gds, lef, template_def, top_module, uses_3v3),
        ],
    ]

    testsuite = ET.Element("testsuite", name="Tiny Tapeout Prechecks")
    error_count = 0
    markdown_table = "# Tiny Tapeout Precheck Results\n\n"
    markdown_table += "| Check | Result |\n|-----------|--------|\n"
    for [name, check] in checks:
        start_time = time.time()
        test_case = ET.SubElement(testsuite, "testcase", name=name)
        try:
            check()
            elapsed_time = time.time() - start_time
            markdown_table += f"| {name} | ✅ |\n"
            test_case.set("time", str(round(elapsed_time, 2)))
        except Exception as e:
            error_count += 1
            elapsed_time = time.time() - start_time
            markdown_table += f"| {name} | ❌ Fail: {str(e)} |\n"
            test_case.set("time", str(round(elapsed_time, 2)))
            error = ET.SubElement(test_case, "error", message=str(e))
            error.text = traceback.format_exc()
    markdown_table += "\n"
    markdown_table += "In case of failure, please reach out on [discord](https://tinytapeout.com/discord) for assistance."

    testsuites = ET.Element("testsuites")
    testsuites.append(testsuite)
    xunit_report = ET.ElementTree(testsuites)
    ET.indent(xunit_report, space="  ", level=0)
    xunit_report.write(f"{REPORTS_PATH}/results.xml", encoding="unicode")

    with open(f"{REPORTS_PATH}/results.md", "w") as f:
        f.write(markdown_table)

    if error_count > 0:
        logging.error(f"Precheck failed for {args.gds}! 😭")
        logging.error(f"See {REPORTS_PATH} for more details")
        logging.error(f"Markdown report:\n{markdown_table}")
        exit(1)
    else:
        logging.info(f"Precheck passed for {args.gds}! 🎉")


if __name__ == "__main__":
    main()
