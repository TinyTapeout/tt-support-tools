import logging
import re
from collections.abc import Iterable
from itertools import combinations
from numbers import Real

import gdstk
from precheck_failure import PrecheckFailure


def canonicalize_rectangles(
    rects: Iterable[Iterable[Real]],
) -> Iterable[Iterable[Real]]:
    # lists all maximal rectangles covered by the union of input rectangles

    sweep_events = {}
    for lx, by, rx, ty in rects:
        sweep_events[by] = sweep_events.get(by, {})
        sweep_events[by][lx] = sweep_events[by].get(lx, 0) + 1
        sweep_events[by][rx] = sweep_events[by].get(rx, 0) - 1
        sweep_events[ty] = sweep_events.get(ty, {})
        sweep_events[ty][lx] = sweep_events[ty].get(lx, 0) - 1
        sweep_events[ty][rx] = sweep_events[ty].get(rx, 0) + 1

    closed_rects = []
    open_rects = {}
    cross_section_events = {}
    for y, sweep_line_events in sorted(sweep_events.items()):
        old_multiplicity = 0
        new_multiplicity = 0
        is_covered, covered_intervals, covered_start = False, [], None
        is_removed, removed_intervals, removed_start = False, [], None
        for x in sorted(set(cross_section_events).union(sweep_line_events)):
            old_delta = cross_section_events.get(x, 0)
            new_delta = sweep_line_events.get(x, 0) + old_delta
            old_multiplicity += old_delta
            new_multiplicity += new_delta
            assert old_multiplicity >= 0
            assert new_multiplicity >= 0
            was_covered, was_removed = is_covered, is_removed
            is_covered = new_multiplicity > 0
            is_removed = old_multiplicity > 0 and new_multiplicity == 0
            if was_covered and not is_covered:
                assert covered_start is not None
                covered_intervals.append((covered_start, x))
                covered_start = None
            if was_removed and not is_removed:
                assert removed_start is not None
                removed_intervals.append((removed_start, x))
                removed_start = None
            if is_covered and not was_covered:
                assert covered_start is None
                covered_start = x
            if is_removed and not was_removed:
                assert removed_start is None
                removed_start = x

        for x, m in sorted(sweep_line_events.items()):
            cross_section_events[x] = cross_section_events.get(x, 0) + m
            if cross_section_events[x] == 0:
                del cross_section_events[x]

        for (lx, rx), by in open_rects.items():
            closed = False
            for ix, jx in removed_intervals:
                if ix < rx and lx < jx:
                    closed = True
            if closed:
                closed_rects.append((lx, by, rx, y))

        kept_intervals = [
            (b, c)
            for ((a, b), (c, d)) in zip(
                [(None, None)] + removed_intervals, removed_intervals + [(None, None)]
            )
        ]
        open_rects_new = {}
        for ix, jx in covered_intervals:
            open_rects_new[(ix, jx)] = y
        for (lx, rx), by in open_rects.items():
            for ix, jx in kept_intervals:
                if (ix is None or ix < rx) and (jx is None or lx < jx):
                    clx = lx if ix is None else max(lx, ix)
                    crx = rx if jx is None else min(rx, jx)
                    open_rects_new[(clx, crx)] = min(
                        open_rects_new.get((clx, crx), by), by
                    )
        open_rects = open_rects_new

    return sorted(set(closed_rects))


def parsefp3(value: str):
    # parse fixed-point numbers with 3 digits after the decimal point
    # e.g. '20.470' to 20470
    ip, fp = value.split(".")
    mul = ip + fp[:3].rjust(3, "0")
    return int(mul)


def pin_check(gds: str, lef: str, template_def: str, toplevel: str, uses_3v3: bool):
    logging.info("Running pin check...")
    logging.info(f"* gds: {gds}")
    logging.info(f"* lef: {lef}")
    logging.info(f"* template_def: {template_def}")
    logging.info(f"* toplevel: {toplevel}")
    logging.info(f"* uses_3v3: {uses_3v3}")

    # parse pins from template def
    # def syntax: https://coriolis.lip6.fr/doc/lefdef/lefdefref/DEFSyntax.html

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
                    raise PrecheckFailure(
                        "Wrong die origin in template DEF, expecting (0, 0)"
                    )
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
                    f"Inconsistent pin name and net name in template DEF: {pin_name} vs {net_name}"
                )

            line = next(f)
            if not line.strip().startswith("+ PORT"):
                raise PrecheckFailure(
                    "Unexpected token in template DEF: PINS not followed by PORT"
                )

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
            raise PrecheckFailure(
                f"Unexpected token in template DEF: PINS {pin_count} section does not end after {pin_count} pins"
            )

    # parse pins from user lef
    # lef syntax: https://coriolis.lip6.fr/doc/lefdef/lefdefref/LEFSyntax.html

    origin_re = re.compile(r"ORIGIN (\S+) (\S+) ;")
    size_re = re.compile(r"SIZE (\S+) BY (\S+) ;")
    layer_re = re.compile(r"LAYER (\S+) ;")
    rect_re = re.compile(r"RECT (\S+) (\S+) (\S+) (\S+) ;")

    power_pins = ["VGND", "VDPWR"]
    if uses_3v3:
        power_pins.append("VAPWR")
    compat_pins = {"VPWR": "VDPWR"}

    macro_active = False
    pins_expected = set(def_pins).union(power_pins).union(compat_pins)
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
                        raise PrecheckFailure(
                            "Wrong die origin in LEF, expecting (0, 0)"
                        )
                elif line.startswith("SIZE "):
                    match = size_re.match(line)
                    rx, ty = map(parsefp3, match.groups())
                    if (rx, ty) != (die_width, die_height):
                        raise PrecheckFailure(
                            f"Inconsistent die area between LEF and template DEF: ({rx}, {ty}) != ({die_width}, {die_height})"
                        )
                elif line.startswith("PIN "):
                    if current_pin is not None:
                        new_pin = line.removeprefix("PIN ")
                        raise PrecheckFailure(
                            f"Unexpected token in LEF: pin {new_pin} starts without ending previous pin {current_pin}"
                        )
                    current_pin = line.removeprefix("PIN ")
                    pins_seen.add(current_pin)
                    if current_pin not in pins_expected:
                        logging.error(f"Unexpected pin {current_pin} in {lef}")
                        lef_errors += 1
                    pin_rects = 0
                elif line == "PORT":
                    if current_pin is None:
                        raise PrecheckFailure(
                            "Unexpected token in LEF: PORT outside of PIN"
                        )
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
                        raise PrecheckFailure(
                            "Unexpected token in LEF: LAYER within PORT should be followed by RECT or LAYER lines until END of port"
                        )
                elif current_pin is not None and line.startswith("END " + current_pin):
                    if pin_rects < 1:
                        logging.error(f"No ports for pin {current_pin} in {lef}")
                        lef_errors += 1
                    current_pin = None

    lef_ports_orig = lef_ports
    lef_ports = {}
    for current_pin, ports_orig in lef_ports_orig.items():
        ports_by_layers = {}
        for layer, lx, by, rx, ty in ports_orig:
            if layer not in ports_by_layers:
                ports_by_layers[layer] = []
            ports_by_layers[layer].append((lx, by, rx, ty))
        ports = []
        for layer, rects in sorted(ports_by_layers.items()):
            for lx, by, rx, ty in canonicalize_rectangles(rects):
                ports.append((layer, lx, by, rx, ty))
        lef_ports[current_pin] = ports

    for old_pin, new_pin in compat_pins.items():
        if old_pin in lef_ports:
            if new_pin in lef_ports:
                logging.error(f"Both {old_pin} and {new_pin} ports appear in {lef}")
                lef_errors += 1
            else:
                lef_ports[new_pin] = []
            lef_ports[new_pin].extend(lef_ports[old_pin])
            del lef_ports[old_pin]

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

    for current_pin in power_pins:
        if current_pin not in lef_ports:
            logging.error(f"Pin {current_pin} not found in {lef}")
            lef_errors += 1
        else:
            for layer, lx, by, rx, ty in lef_ports[current_pin]:
                width = rx - lx
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
                if by > 10000:
                    logging.error(
                        f"Port {current_pin} is too far from bottom edge of module: {by/1000} > 10 um"
                    )
                    lef_errors += 1
                if die_height - ty > 10000:
                    logging.error(
                        f"Port {current_pin} is too far from top edge of module: {(die_height-ty)/1000} > 10 um"
                    )
                    lef_errors += 1
                if lx < 0 or rx > die_width or by < 0 or ty > die_height:
                    logging.error(
                        f"Port {current_pin} not entirely within project area in {lef}"
                    )
                    lef_errors += 1

    # check for overlapping pins

    for (pin1, rects1), (pin2, rects2) in combinations(sorted(lef_ports.items()), 2):
        for layer1, lx1, by1, rx1, ty1 in rects1:
            for layer2, lx2, by2, rx2, ty2 in rects2:
                if layer1 != layer2:
                    continue
                if rx1 < lx2 or rx2 < lx1:
                    continue
                if ty1 < by2 or ty2 < by1:
                    continue
                logging.error(
                    f"Overlapping pins in {lef}: {pin1} and {pin2}."
                    "All exported pins have to be separate, and must not overlap or abut."
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

    gds_layer_lookup = {j: i for i, j in gds_layers.items()}
    polygon_list = {layer: [] for layer in gds_layers}
    for poly in top.polygons:
        poly_layer = (poly.layer, poly.datatype)
        layer_name = gds_layer_lookup.get(poly_layer, None)
        if layer_name is not None:
            polygon_list[layer_name].append(poly)
    merged_layers = {}
    for layer in gds_layers:
        merged_layers[layer] = gdstk.boolean(polygon_list[layer], [], "or")

    gds_errors = 0
    for current_pin, lef_rects in sorted(lef_ports_orig.items()):
        for layer, lx, by, rx, ty in lef_rects:
            if layer + ".pin" not in gds_layers:
                raise PrecheckFailure(
                    f"Unexpected port layer in LEF: {current_pin} is on layer {layer}"
                )

            pin_ok = False
            for poly in merged_layers[layer + ".pin"]:
                if poly.contain_all(
                    ((lx + 1) / 1000, (by + 1) / 1000),
                    ((rx - 1) / 1000, (by + 1) / 1000),
                    ((lx + 1) / 1000, (ty - 1) / 1000),
                    ((rx - 1) / 1000, (ty - 1) / 1000),
                ):
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
