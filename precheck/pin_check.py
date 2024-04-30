import logging
import re

import gdstk
from precheck_failure import PrecheckFailure


def parsefp3(value: str):
    # parse fixed-point numbers with 3 digits after the decimal point
    # e.g. '20.470' to 20470
    ip, fp = value.split(".")
    mul = ip + fp[:3].rjust(3, "0")
    return int(mul)


def pin_check(gds: str, lef: str, template_def: str, toplevel: str):
    logging.info("Running pin check...")

    # parse pins from template def

    diearea_re = re.compile(r"DIEAREA \( (\S+) (\S+) \) \( (\S+) (\S+) \) ;")
    pins_re = re.compile(r"PINS (\d+) ;")
    pin_re = re.compile(r" *- (\S+) \+ NET (\S+) \+ DIRECTION (\S+) \+ USE (\S+)")
    layer_re = re.compile(r" *\+ LAYER (\S+) \( (\S+) (\S+) \) \( (\S+) (\S+) \)")
    placed_re = re.compile(r" *\+ PLACED \( (\S+) (\S+) \) (\S+) ;")

    def_pins = {}
    die_width = 0
    die_height = 0

    with open(template_def) as f:
        for line in f:
            if line.startswith("DIEAREA "):
                match = diearea_re.match(line)
                lx, by, rx, ty = map(int, match.groups())
                if (lx, by) != (0, 0):
                    raise PrecheckFailure("Wrong die origin in template DEF")
                die_width = rx
                die_height = ty
            elif line.startswith("PINS "):
                match = pins_re.match(line)
                pin_count = int(match.group(1))
                break

        for i in range(pin_count):
            line = next(f)
            match = pin_re.match(line)
            pin_name, net_name, direction, use = match.groups()
            if pin_name != net_name:
                raise PrecheckFailure(
                    "Inconsistent pin name and net name in template DEF"
                )

            line = next(f)
            if not line.strip().startswith("+ PORT"):
                raise PrecheckFailure("Unexpected token in template DEF")

            line = next(f)
            match = layer_re.match(line)
            layer, lx, by, rx, ty = match.groups()
            lx, by, rx, ty = map(int, (lx, by, rx, ty))

            line = next(f)
            match = placed_re.match(line)
            ox, oy, direction = match.groups()
            ox, oy = map(int, (ox, oy))

            if pin_name in def_pins:
                raise PrecheckFailure("Duplicate pin in template DEF")

            def_pins[pin_name] = (layer, ox + lx, oy + by, ox + rx, oy + ty)

        line = next(f)
        if not line.startswith("END PINS"):
            raise PrecheckFailure("Unexpected token in template DEF")

    # parse pins from user lef

    origin_re = re.compile(r"ORIGIN (\S+) (\S+) ;")
    size_re = re.compile(r"SIZE (\S+) BY (\S+) ;")
    layer_re = re.compile(r"LAYER (\S+) ;")
    rect_re = re.compile(r"RECT (\S+) (\S+) (\S+) (\S+) ;")

    macro_active = False
    pins_expected = set(def_pins).union({"VPWR", "VGND"})
    pins_seen = set()
    current_pin = None
    pin_rects = 0
    lef_errors = 0
    lef_ports = {}

    with open(lef) as f:
        for line in f:
            line = line.strip()
            if line.startswith("MACRO "):
                if line == "MACRO " + toplevel:
                    macro_active = True
                else:
                    macro_active = False
            elif macro_active:
                if line.startswith("ORIGIN "):
                    match = origin_re.match(line)
                    lx, by = map(parsefp3, match.groups())
                    if lx != 0 or by != 0:
                        raise PrecheckFailure("Wrong die origin in LEF")
                elif line.startswith("SIZE "):
                    match = size_re.match(line)
                    rx, ty = map(parsefp3, match.groups())
                    if (rx, ty) != (die_width, die_height):
                        raise PrecheckFailure(
                            f"Inconsistent die area between LEF and template DEF: ({rx}, {ty}) != ({die_width}, {die_height})"
                        )
                elif line.startswith("PIN "):
                    if current_pin is not None:
                        raise PrecheckFailure("Unexpected token in LEF")
                    current_pin = line.removeprefix("PIN ")
                    pins_seen.add(current_pin)
                    if current_pin not in pins_expected:
                        logging.error(f"Unexpected pin {current_pin} in {lef}")
                        lef_errors += 1
                    pin_rects = 0
                elif line == "PORT":
                    if current_pin is None:
                        raise PrecheckFailure("Unexpected token in LEF")
                    line = next(f).strip()
                    while line.startswith("LAYER "):
                        match = layer_re.match(line)
                        layer = match.group(1)
                        line = next(f).strip()
                        while line.startswith("RECT "):
                            match = rect_re.match(line)
                            lx, by, rx, ty = map(parsefp3, match.groups())
                            pin_rects += 1
                            if current_pin not in lef_ports:
                                lef_ports[current_pin] = []
                            lef_ports[current_pin].append((layer, lx, by, rx, ty))
                            line = next(f).strip()
                    if line != "END":
                        raise PrecheckFailure("Unexpected token in LEF")
                elif current_pin is not None and line.startswith("END " + current_pin):
                    if pin_rects < 1:
                        logging.error(f"No ports for pin {current_pin} in {lef}")
                        lef_errors += 1
                    current_pin = None

    for current_pin in def_pins:
        if current_pin not in lef_ports:
            logging.error(f"Pin {current_pin} not found in {lef}")
            lef_errors += 1
        else:
            if len(lef_ports[current_pin]) > 1:
                logging.error(f"Too many rectangles for pin {current_pin} in {lef}")
                lef_errors += 1
            lef_layer, *lef_rect = lef_ports[current_pin][0]
            def_layer, *def_rect = def_pins[current_pin]
            if lef_layer != def_layer:
                logging.error(
                    f"Port {current_pin} on layer {lef_layer} in {lef} but on layer {def_layer} in {template_def}"
                )
                lef_errors += 1
            elif lef_rect != def_rect:
                logging.error(
                    f"Port {current_pin} has different dimensions in {lef} and {template_def}"
                )
                lef_errors += 1

    pin_widths = {}
    for current_pin in ("VPWR", "VGND"):
        if current_pin not in lef_ports:
            logging.error(f"Pin {current_pin} not found in {lef}")
            lef_errors += 1
        else:
            for layer, lx, by, rx, ty in lef_ports[current_pin]:
                width, height = rx - lx, ty - by
                if current_pin in pin_widths:
                    if pin_widths[current_pin] != width:
                        logging.error(
                            f"Multiple {current_pin} rectangles with different widths in {lef}: {pin_widths[current_pin]/1000} != {width/1000} um"
                        )
                        lef_errors += 1
                pin_widths[current_pin] = width
                if layer != "met4":
                    logging.error(
                        f"Port {current_pin} has wrong layer in {lef}: {layer} != met4"
                    )
                    lef_errors += 1
                if width < 1200:
                    logging.error(
                        f"Port {current_pin} has too small width in {lef}: {width/1000} < 1.2 um"
                    )
                    lef_errors += 1
                if width > 2000:
                    logging.error(
                        f"Port {current_pin} has too large width in {lef}: {width/1000} > 2.0 um"
                    )
                    lef_errors += 1
                if height < die_height * 0.95:
                    logging.error(
                        f"Port {current_pin} has too small height in {lef}: {height/1000} < {die_height*0.95/1000} um"
                    )
                    lef_errors += 1
                if lx < 0 or rx > die_width or by < 0 or ty > die_height:
                    logging.error(
                        f"Port {current_pin} not entirely within project area in {lef}"
                    )
                    lef_errors += 1

    if (
        "VPWR" in pin_widths
        and "VGND" in pin_widths
        and pin_widths["VPWR"] != pin_widths["VGND"]
    ):
        vpwr_width = pin_widths["VPWR"]
        vgnd_width = pin_widths["VGND"]
        logging.error(
            f"VPWR and VGND have different widths in {lef}: {vpwr_width/1000} != {vgnd_width/1000} um"
        )
        lef_errors += 1

    # check gds for the ports being present

    lib = gdstk.read_gds(gds)
    top = [cell for cell in lib.top_level() if cell.name == toplevel]
    if not top:
        raise PrecheckFailure("Wrong cell at GDS top-level")
    top = top[0]

    gds_layers = {
        "met1.pin": (68, 16),
        "met2.pin": (69, 16),
        "met3.pin": (70, 16),
        "met4.pin": (71, 16),
    }

    gds_errors = 0
    for current_pin, lef_rects in sorted(lef_ports.items()):
        for layer, lx, by, rx, ty in lef_rects:
            assert layer + ".pin" in gds_layers, "Unexpected port layer in LEF"
            pin_layer = gds_layers[layer + ".pin"]

            pin_ok = False
            for poly in top.polygons:
                poly_layer = (poly.layer, poly.datatype)
                if poly.contain_all(
                    ((lx + 1) / 1000, (by + 1) / 1000),
                    ((rx - 1) / 1000, (by + 1) / 1000),
                    ((lx + 1) / 1000, (ty - 1) / 1000),
                    ((rx - 1) / 1000, (ty - 1) / 1000),
                ):
                    if poly_layer == pin_layer:
                        pin_ok = True

            if not pin_ok:
                logging.error(
                    f"Port {current_pin} missing from layer {layer}.pin in {gds}"
                )
                gds_errors += 1

    if lef_errors > 0 or gds_errors > 0:
        err_list = []
        if lef_errors > 0:
            err_list.append(f"{lef_errors} LEF error" + ("s" if lef_errors > 1 else ""))
        if gds_errors > 0:
            err_list.append(f"{gds_errors} GDS error" + ("s" if gds_errors > 1 else ""))
        err_desc = " and ".join(err_list)
        raise PrecheckFailure(
            f"Some ports are missing or have wrong dimensions, see {err_desc} above"
        )
