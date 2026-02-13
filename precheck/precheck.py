#!/usr/bin/env python3
import argparse
import logging
import os
import re
import subprocess
import tempfile
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
from tech_data import (
    analog_pin_pos,
    boundary_layer,
    forbidden_layers,
    layer_map,
    lyp_filename,
    tech_names,
    valid_layers,
)

PDK_ROOT = os.getenv("PDK_ROOT")
PDK_NAME = os.getenv("PDK") or "sky130A"
LYP_DIR = f"{PDK_ROOT}/{PDK_NAME}/libs.tech/klayout/tech"
REPORTS_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "reports")

if not PDK_ROOT:
    logging.error("PDK_ROOT environment variable not set")
    exit(1)


def has_sky130_devices(gds: str):
    for cell_name in gdstk.read_rawcells(gds):
        if cell_name.startswith("sky130_fd_"):
            return True
    return False


def load_layers(tech: str, only_valid: bool = True):
    lyp_file = f"{LYP_DIR}/{lyp_filename[tech]}"
    layers = parse_lyp_layers(lyp_file, only_valid)
    return layers


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


def klayout_drc(
    gds: str,
    check: str,
    script=f"{PDK_NAME}_mr.drc",
    script_dir="tech-files",
    extra_vars=[],
):
    logging.info(f"Running klayout {check} on {gds}")
    report_file = f"{REPORTS_PATH}/drc_{check}.xml"
    script_vars = [
        f"{check}=true",
        f"input={gds}",
        f"report={report_file}",
        f"report_file={report_file}",
    ]
    klayout_args = ["klayout", "-b", "-r", f"{script_dir}/{script}"]
    for v in script_vars + extra_vars:
        klayout_args.extend(["-rd", v])
    klayout = subprocess.run(klayout_args)
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


def klayout_sg13g2(gds: str):
    return klayout_drc(gds, "sg13g2", "sg13g2_mr.lydrc", extra_vars=[f"in_gds={gds}"])


def klayout_gf180mcuD_antenna(gds: str):
    return klayout_drc(
        gds,
        "antenna",
        "antenna.drc",
        script_dir=f"{PDK_ROOT}/{PDK_NAME}/libs.tech/klayout/drc/rule_decks",
    )


def klayout_checks(gds: str, expected_name: str, tech: str):
    layout = pya.Layout()
    layout.read(gds)
    layers = load_layers(tech)

    logging.info("Running top macro name check...")
    top_cell = layout.top_cell()
    if top_cell.name != expected_name:
        raise PrecheckFailure(
            f"Top macro name mismatch: expected {expected_name}, got {top_cell.name}"
        )

    logging.info("Running forbidden layer check...")
    for layer in forbidden_layers[tech]:
        layer_info = layers[layer]
        logging.info(f"* Checking {layer_info.name}")
        layer_index = layout.find_layer(layer_info.layer, layer_info.data_type)
        if layer_index is not None:
            raise PrecheckFailure(f"Forbidden layer {layer} found in {gds}")

    logging.info("Running prBoundary check...")
    layer_name = boundary_layer[tech]
    layer_info = layers[layer_name]
    layer_index = layout.find_layer(layer_info.layer, layer_info.data_type)
    if layer_index is None:
        calma_index = f"{layer_info.layer}/{layer_info.data_type}"
        raise PrecheckFailure(f"{layer_name} ({calma_index}) layer not found in {gds}")


def boundary_check(gds: str, tech: str):
    """Ensure that there are no shapes outside the project area."""
    lib = gdstk.read_gds(gds)
    tops = lib.top_level()
    if len(tops) != 1:
        raise PrecheckFailure("GDS top level not unique")
    top = tops[0]
    boundary = top.copy("test_boundary")

    layers = load_layers(tech)
    layer_name = boundary_layer[tech]
    layer_info = layers[layer_name]
    boundary.filter([(layer_info.layer, layer_info.data_type)], False)
    if top.bounding_box() != boundary.bounding_box():
        raise PrecheckFailure("Shapes outside project area")


def power_pin_check(verilog: str, lef: str, uses_3v3: bool):
    """Ensure that VPWR / VGND are present and have USE definitions,
    and that VAPWR is present if and only if 'uses_3v3' is set."""
    verilog_s = open(verilog).read().replace("VPWR", "VDPWR")
    lef_s = open(lef).read().replace("VPWR", "VDPWR")

    # naive but good enough way to ignore comments
    verilog_s = re.sub("//.*", "", verilog_s)
    verilog_s = re.sub("/\\*.*?\\*/", "", verilog_s, flags=(re.DOTALL | re.MULTILINE))

    # this looks for a line beginning with "PIN", captures the name of the pin and the body up until its "END"
    PIN_PATTERN = re.compile(
        r"^\s*PIN (VPWR|VDPWR|VAPWR|VGND)\s*([\s\S]+?(?=^\s*END \1))",
        flags=re.MULTILINE,
    )

    for ft, s in (("Verilog", verilog_s), ("LEF", lef_s)):
        for pwr, ex in (("VGND", True), ("VDPWR", True), ("VAPWR", uses_3v3)):
            if (pwr in s) and not ex:
                raise PrecheckFailure(f"{ft} contains {pwr}")
            if not (pwr in s) and ex:
                raise PrecheckFailure(f"{ft} doesn't contain {pwr}")

    for match in PIN_PATTERN.finditer(lef_s):
        pin, definition = match.groups()

        match pin:
            case "VPWR" | "VDPWR" | "VAPWR":
                if "USE POWER" not in definition:
                    raise PrecheckFailure(
                        f"{pin} does not have a corresponding 'USE POWER ;'"
                    )

            case "VGND":
                if "USE GROUND" not in definition:
                    raise PrecheckFailure(
                        f"{pin} does not have a corresponding 'USE GROUND ;'"
                    )

            case _:
                raise PrecheckFailure(f"unhandled {pin}")


def layer_check(gds: str, tech: str):
    """Check that there are no invalid layers in the GDS file."""
    layer_definition = load_layers(tech, only_valid=False)
    lib = gdstk.read_gds(gds)
    valid_layer_list = set(
        map(
            lambda layer_name: (
                (
                    layer_definition[layer_name].layer,
                    layer_definition[layer_name].data_type,
                )
                if type(layer_name) is str
                else layer_name
            ),
            valid_layers[tech],
        )
    )
    gds_layers = lib.layers_and_datatypes().union(lib.layers_and_texttypes())
    excess = gds_layers - valid_layer_list
    if excess:
        raise PrecheckFailure(f"Invalid layers in GDS: {excess}")


def cell_name_check(gds: str):
    """Check that there are no cell names with '#' or '/' in them."""
    for cell_name in gdstk.read_rawcells(gds):
        if "#" in cell_name:
            raise PrecheckFailure(
                f"Cell name {cell_name} contains invalid character '#'"
            )
        if "/" in cell_name:
            raise PrecheckFailure(
                f"Cell_name {cell_name} contains invalid character '/'"
            )


def urpm_nwell_check(gds: str, top_module: str):
    """Run a DRC check for urpm to nwell spacing."""
    extra_vars = [f"thr={os.cpu_count()}", f"top_cell={top_module}"]
    klayout_drc(
        gds=gds, check="nwell_urpm", script="nwell_urpm.drc", extra_vars=extra_vars
    )


def analog_pin_check(
    gds: str, tech: str, is_analog: bool, uses_3v3: bool, analog_pins: int, pinout: dict
):
    """Check that every analog pin connects to a piece of metal
    if and only if the pin is used according to info.yaml."""
    if is_analog:
        lib = gdstk.read_gds(gds)
        top = lib.top_level()[0]
        met4 = top.copy("test_met4")
        met4.flatten()
        met4.filter([layer_map[tech]["met4"]], False)
        via3 = top.copy("test_via3")
        via3.flatten()
        via3.filter([layer_map[tech]["via3"]], False)

        for pin in range(8):
            x = analog_pin_pos[tech](pin, uses_3v3)
            pin_over = gdstk.rectangle((x, 0), (x + 0.9, 1.0))
            pin_around = gdstk.boolean(
                gdstk.offset(pin_over, 0.5), gdstk.offset(pin_over, 0.1), "not"
            )

            via3_over = gdstk.boolean(via3.polygons, pin_over, "and")
            met4_around = gdstk.boolean(met4.polygons, pin_around, "and")
            connected = bool(via3_over) or bool(met4_around)

            expected_pc = pin < analog_pins
            expected_pd = bool(pinout.get(f"ua[{pin}]", ""))

            if connected and not expected_pc:
                raise PrecheckFailure(
                    f"Analog pin `ua[{pin}]` is connected to some metal but `analog_pins` is set to {analog_pins} in `info.yaml`. Either increase `analog_pins` to at least {pin+1}, or remove any metal4 or via3 adjacent to `ua[{pin}]`."
                )
            elif connected and not expected_pd:
                raise PrecheckFailure(
                    f"Analog pin `ua[{pin}]` is connected to some metal but the description of `ua[{pin}]` in the pinout section of `info.yaml` is empty. Either add a description or remove any metal4 or via3 adjacent to `ua[{pin}]`."
                )
            elif not connected and expected_pc:
                raise PrecheckFailure(
                    f"Analog pin `ua[{pin}]` is not connected to any adjacent metal but `analog_pins` is set to {analog_pins} in `info.yaml`. Either wire up `ua[{pin}]` to your design using metal4 or via3, or decrease `analog_pins` to {pin}."
                )
            elif not connected and expected_pd:
                raise PrecheckFailure(
                    f"Analog pin `ua[{pin}]` is not connected to any adjacent metal but the description of `ua[{pin}]` in the pinout section of `info.yaml` is non-empty. Either wire up `ua[{pin}]` to your design using metal4 or via3, or remove the description for the disconnected pin."
                )


def main():
    default_tech = PDK_NAME
    if default_tech not in tech_names:
        default_tech = tech_names[0]

    parser = argparse.ArgumentParser()
    parser.add_argument("--gds", required=True)
    parser.add_argument(
        "--tech", required=False, default=default_tech, choices=tech_names
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logging.info(f"PDK_ROOT: {PDK_ROOT}")
    logging.info(f"Tech: {args.tech}")

    if args.gds.endswith(".gds"):
        gds_stem = args.gds.removesuffix(".gds")
        gds_temp = None
        gds_file = args.gds
    elif args.gds.endswith(".oas"):
        gds_stem = args.gds.removesuffix(".oas")
        gds_temp = tempfile.NamedTemporaryFile(suffix=".gds", delete=False)
        gds_file = gds_temp.name
        logging.info(f"Converting {args.gds} to {gds_file}")
        layout = pya.Layout()
        layout.read(args.gds)
        layout.write(gds_file)
    else:
        raise PrecheckFailure("Layout file extension is neither .gds nor .oas")

    tech = args.tech
    if tech not in tech_names:
        raise PrecheckFailure(f"Invalid tech: {tech}")

    yaml_dir = os.path.dirname(args.gds)
    while not os.path.exists(f"{yaml_dir}/info.yaml"):
        yaml_dir = os.path.dirname(yaml_dir)
        if yaml_dir in ("/", ""):
            raise PrecheckFailure("info.yaml not found")
    yaml_file = f"{yaml_dir}/info.yaml"
    yaml_data = yaml.safe_load(open(yaml_file))

    wokwi_id = yaml_data["project"].get("wokwi_id", 0)
    top_module = yaml_data["project"].get("top_module", f"tt_um_wokwi_{wokwi_id}")
    assert top_module == os.path.basename(gds_stem)

    tiles = yaml_data.get("project", {}).get("tiles", "1x1")
    analog_pins = yaml_data.get("project", {}).get("analog_pins", 0)
    is_analog = analog_pins > 0
    uses_3v3 = bool(yaml_data.get("project", {}).get("uses_3v3", False))
    pinout = yaml_data.get("pinout", {})
    if uses_3v3 and not is_analog:
        raise PrecheckFailure("Projects with 3v3 power need at least one analog pin")
    def_root = f"../tech/{tech}/def"
    if is_analog:
        if uses_3v3:
            template_def = f"{def_root}/analog/tt_analog_{tiles}_3v3.def"
        else:
            template_def = f"{def_root}/analog/tt_analog_{tiles}.def"
    elif tech == "ihp-sg13g2" or tech == "gf180mcuD":
        template_def = f"{def_root}/tt_block_{tiles}_pgvdd.def"
    else:
        template_def = f"{def_root}/tt_block_{tiles}_pg.def"
    logging.info(f"using def template {template_def}")

    gds_dir = os.path.dirname(gds_stem)
    lef_file = gds_stem + ".lef"
    lef_file_alt = os.path.join(
        gds_dir, "..", "lef", os.path.basename(gds_stem) + ".lef"
    )
    if not os.path.exists(lef_file) and os.path.exists(lef_file_alt):
        lef_file = lef_file_alt
    verilog_file = gds_stem + ".v"

    checks = [
        {
            "name": "Magic DRC",
            "check": lambda: magic_drc(gds_file, top_module),
            "techs": ["sky130A", "gf180mcuD"],
        },
        {
            "name": "KLayout FEOL",
            "check": lambda: klayout_drc(gds_file, "feol"),
            "techs": ["sky130A"],
        },
        {
            "name": "KLayout BEOL",
            "check": lambda: klayout_drc(gds_file, "beol"),
            "techs": ["sky130A"],
        },
        {
            "name": "KLayout offgrid",
            "check": lambda: klayout_drc(gds_file, "offgrid"),
            "techs": ["sky130A"],
        },
        {
            "name": "KLayout pin label overlapping drawing",
            "check": lambda: klayout_drc(
                gds_file,
                "pin_label_purposes_overlapping_drawing",
                "pin_label_purposes_overlapping_drawing.rb.drc",
            ),
        },
        {
            "name": "KLayout SG13G2 DRC",
            "check": lambda: klayout_sg13g2(gds_file),
            "techs": ["ihp-sg13g2"],
        },
        {"name": "KLayout zero area", "check": lambda: klayout_zero_area(gds_file)},
        {
            "name": "KLayout Checks",
            "check": lambda: klayout_checks(gds_file, top_module, tech),
        },
        {
            "name": "Pin check",
            "check": lambda: pin_check(
                gds_file, lef_file, template_def, top_module, uses_3v3, tech
            ),
        },
        {"name": "Boundary check", "check": lambda: boundary_check(gds_file, tech)},
        {
            "name": "Power pin check",
            "check": lambda: power_pin_check(verilog_file, lef_file, uses_3v3),
            "techs": ["sky130A", "gf180mcuD"],
        },
        {"name": "Layer check", "check": lambda: layer_check(gds_file, tech)},
        {"name": "Cell name check", "check": lambda: cell_name_check(gds_file)},
        {
            "name": "urpm/nwell check",
            "check": lambda: urpm_nwell_check(gds_file, top_module),
            "techs": ["sky130A"],
        },
        {
            "name": "Antenna check",
            "check": lambda: klayout_gf180mcuD_antenna(gds_file),
            "techs": ["gf180mcuD"],
        },
        {
            "name": "Analog pin check",
            "check": lambda: analog_pin_check(
                gds_file, tech, is_analog, uses_3v3, analog_pins, pinout
            ),
            "techs": ["sky130A"],
        },
    ]

    testsuite = ET.Element("testsuite", name="Tiny Tapeout Prechecks")
    error_count = 0
    markdown_table = "# Tiny Tapeout Precheck Results\n\n"
    markdown_table += "| Check | Result |\n|-----------|--------|\n"
    for check in checks:
        name = check["name"]
        if "techs" in check and tech not in check["techs"]:
            continue
        start_time = time.time()
        test_case = ET.SubElement(testsuite, "testcase", name=name)
        try:
            check["check"]()
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

    if gds_temp is not None:
        gds_temp.close()
        os.unlink(gds_temp.name)

    if error_count > 0:
        logging.error(f"Precheck failed for {args.gds}! 😭")
        logging.error(f"See {REPORTS_PATH} for more details")
        logging.error(f"Markdown report:\n{markdown_table}")
        exit(1)
    else:
        logging.info(f"Precheck passed for {args.gds}! 🎉")


if __name__ == "__main__":
    main()
