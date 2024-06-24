import os
import subprocess
import textwrap

import klayout.db as pya
import klayout_tools
import pytest

import precheck

PDK_ROOT = os.getenv("PDK_ROOT")
PDK_NAME = os.getenv("PDK_NAME") or "sky130A"
LYP_FILE = f"{PDK_ROOT}/{PDK_NAME}/libs.tech/klayout/tech/{PDK_NAME}.lyp"
gds_layers = klayout_tools.parse_lyp_layers(LYP_FILE)


@pytest.fixture(scope="session")
def gds_valid(tmp_path_factory: pytest.TempPathFactory):
    """Creates a minimal GDS that should pass DRC."""
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_valid.gds"
    layout = pya.Layout()
    top_cell = layout.create_cell("TEST_valid")
    prboundary_info = gds_layers["prBoundary.boundary"]
    prboundary = layout.layer(prboundary_info.layer, prboundary_info.data_type)
    rect = pya.DBox(0, 0, 161, 111.52)
    top_cell.shapes(prboundary).insert(rect)
    layout.write(str(gds_file))
    return str(gds_file)


@pytest.fixture(scope="session")
def gds_fail_met1_poly(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS that fails Magic DRC and BEOL because the met1 rect is too small."""
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_met1_error.gds"
    layout = pya.Layout()
    met1_info = gds_layers["met1.drawing"]
    met1 = layout.layer(met1_info.layer, met1_info.data_type)
    top_cell = layout.create_cell("TEST_met1_error")
    # Should fail "Metal1 minimum area < 0.083um^2 (met1.6)" (magic)
    # and "m1.1 : min. m1 width : 0.14um" (klayout):
    rect = pya.DBox(0, 0, 0.005, 0.005)
    top_cell.shapes(met1).insert(rect)
    layout.write(str(gds_file))
    return str(gds_file)


@pytest.fixture(scope="session")
def gds_fail_nwell_poly(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS that fails FEOL because the nwell is too small."""
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_nwell_error.gds"
    layout = pya.Layout()
    nwell_info = gds_layers["nwell.drawing"]
    nwell = layout.layer(nwell_info.layer, nwell_info.data_type)
    top_cell = layout.create_cell("TEST_nwell_error")
    # Should fail "nwell.1 : min. nwell width : 0.84um" (klayout):
    rect = pya.DBox(0, 0, 0.005, 0.005)
    top_cell.shapes(nwell).insert(rect)
    layout.write(str(gds_file))
    return str(gds_file)


@pytest.fixture(scope="session")
def gds_fail_metal5_poly(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS with drawings on layer5, should fail our precheck."""
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_met5_error.gds"
    layout = pya.Layout()
    met5_info = gds_layers["met5.drawing"]
    met5 = layout.layer(met5_info.layer, met5_info.data_type)
    top_cell = layout.create_cell("TEST_met5_error")
    rect = pya.DBox(0, 0, 5, 5)
    top_cell.shapes(met5).insert(rect)
    layout.write(str(gds_file))
    return str(gds_file)


@pytest.fixture(scope="session")
def gds_no_pr_boundary(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS without a pr boundary layer."""
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_no_prboundary.gds"
    layout = pya.Layout()
    layout.create_cell("TEST_no_prboundary")
    layout.write(str(gds_file))
    return str(gds_file)


@pytest.fixture(scope="session")
def gds_zero_area(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS with a zero-area polygon."""
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_zero_area.gds"
    layout = pya.Layout()
    top_cell = layout.create_cell("TEST_zero_area")
    met1_info = gds_layers["met1.drawing"]
    met1 = layout.layer(met1_info.layer, met1_info.data_type)
    rect = pya.DBox(0, 0, 0, 0)
    top_cell.shapes(met1).insert(rect)
    layout.write(str(gds_file))
    return str(gds_file)


@pytest.fixture(scope="session")
def gds_invalid_macro_name(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS with a top cell name that doesn't match the filename."""
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_invalid_macro_name.gds"
    layout = pya.Layout()
    layout.create_cell("wrong_name")
    layout.write(str(gds_file))
    return str(gds_file)


class PortRect:
    def __init__(
        self, layer: str, bottom_left: tuple[int, int], top_right: tuple[int, int]
    ):
        self.layer = layer
        self.lx, self.by = bottom_left
        self.rx, self.ty = top_right


class CompoundPort:
    def __init__(self, name: str, rects: list[PortRect]):
        self.name = name
        self.port_use = "ground" if name == "VGND" else "power"
        self.port_class = "bidirectional"
        self.rects = rects


class SimplePort(CompoundPort):
    def __init__(self, name: str, *rect_args: list):
        super().__init__(name, [PortRect(*rect_args)])


def generate_analog_example(
    tcl_file: str,
    gds_file: str,
    lef_file: str,
    toplevel: str,
    extra_ports: list[CompoundPort],
):
    with open(tcl_file, "w") as f:

        def tcl_append(s):
            f.write(textwrap.dedent(s))

        tcl_append(
            f"""
            def read ../def/analog/tt_analog_1x2.def
            cellname rename tt_um_template {toplevel}
            """
        )
        for port in extra_ports:
            for rect in port.rects:
                tcl_append(
                    f"""
                    box {rect.lx} {rect.by} {rect.rx} {rect.ty}
                    paint {rect.layer}
                    label {port.name} FreeSans {rect.layer}
                    """
                )
            tcl_append(
                f"""
                port {port.name} makeall n
                port {port.name} use {port.port_use}
                port {port.name} class {port.port_class}
                port conn n s e w
                """
            )
        tcl_append(
            f"""
            # Export
            gds write {gds_file}
            lef write {lef_file}
            """
        )

    magic = subprocess.run(
        [
            "magic",
            "-noconsole",
            "-dnull",
            "-rcfile",
            f"{PDK_ROOT}/{PDK_NAME}/libs.tech/magic/{PDK_NAME}.magicrc",
            tcl_file,
        ],
    )

    assert magic.returncode == 0


@pytest.fixture(scope="session")
def gds_lef_analog_example(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS and LEF using the 1x2 analog template."""
    tcl_file = tmp_path_factory.mktemp("tcl") / "TEST_analog_example.tcl"
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_analog_example.gds"
    lef_file = tmp_path_factory.mktemp("lef") / "TEST_analog_example.lef"

    generate_analog_example(
        str(tcl_file),
        str(gds_file),
        str(lef_file),
        "TEST_analog_example",
        [
            SimplePort("VDPWR", "met4", (100, 500), (250, 22076)),
            SimplePort("VGND", "met4", (4900, 500), (5050, 22076)),
        ],
    )
    return str(gds_file), str(lef_file)


@pytest.fixture(scope="session")
def gds_lef_analog_power_compat(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS and LEF using the 1x2 analog template, with VPWR instead of VDPWR."""
    tcl_file = tmp_path_factory.mktemp("tcl") / "TEST_analog_power_compat.tcl"
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_analog_power_compat.gds"
    lef_file = tmp_path_factory.mktemp("lef") / "TEST_analog_power_compat.lef"

    generate_analog_example(
        str(tcl_file),
        str(gds_file),
        str(lef_file),
        "TEST_analog_power_compat",
        [
            SimplePort("VPWR", "met4", (100, 500), (250, 22076)),
            SimplePort("VGND", "met4", (4900, 500), (5050, 22076)),
        ],
    )
    return str(gds_file), str(lef_file)


@pytest.fixture(scope="session")
def gds_lef_analog_wrong_vgnd(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS and LEF using the 1x2 analog template, with wrong VGND layer & dimensions."""
    tcl_file = tmp_path_factory.mktemp("tcl") / "TEST_analog_wrong_vgnd.tcl"
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_analog_wrong_vgnd.gds"
    lef_file = tmp_path_factory.mktemp("lef") / "TEST_analog_wrong_vgnd.lef"

    generate_analog_example(
        str(tcl_file),
        str(gds_file),
        str(lef_file),
        "TEST_analog_wrong_vgnd",
        [
            SimplePort("VDPWR", "met4", (100, 500), (250, 22076)),
            SimplePort("VGND", "met3", (4900, 500), (5250, 12076)),
        ],
    )
    return str(gds_file), str(lef_file)


@pytest.fixture(scope="session")
def gds_lef_analog_overlapping_vgnd(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS and LEF using the 1x2 analog template, with VGND overlapping uio_oe[7]"""
    tcl_file = tmp_path_factory.mktemp("tcl") / "TEST_analog_overlapping_vgnd.tcl"
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_analog_overlapping_vgnd.gds"
    lef_file = tmp_path_factory.mktemp("lef") / "TEST_analog_overlapping_vgnd.lef"

    generate_analog_example(
        str(tcl_file),
        str(gds_file),
        str(lef_file),
        "TEST_analog_overlapping_vgnd",
        [
            SimplePort("VDPWR", "met4", (100, 500), (250, 22076)),
            SimplePort("VGND", "met4", (3000, 20), (3200, 22504)),
        ],
    )
    return str(gds_file), str(lef_file)


@pytest.fixture(scope="session")
def gds_lef_analog_compound_vgnd(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS and LEF using the 1x2 analog template, with VGND consisting of two rectangles."""
    tcl_file = tmp_path_factory.mktemp("tcl") / "TEST_analog_compound_vgnd.tcl"
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_analog_compound_vgnd.gds"
    lef_file = tmp_path_factory.mktemp("lef") / "TEST_analog_compound_vgnd.lef"

    generate_analog_example(
        str(tcl_file),
        str(gds_file),
        str(lef_file),
        "TEST_analog_compound_vgnd",
        [
            SimplePort("VDPWR", "met4", (100, 500), (250, 22076)),
            CompoundPort(
                "VGND",
                [
                    PortRect("met4", (4900, 500), (5050, 12076)),
                    PortRect("met4", (4900, 12000), (5050, 22076)),
                ],
            ),
        ],
    )
    return str(gds_file), str(lef_file)


@pytest.fixture(scope="session")
def gds_lef_analog_example_3v3(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS and LEF using the 1x2 analog template."""
    tcl_file = tmp_path_factory.mktemp("tcl") / "TEST_analog_example_3v3.tcl"
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_analog_example_3v3.gds"
    lef_file = tmp_path_factory.mktemp("lef") / "TEST_analog_example_3v3.lef"

    generate_analog_example(
        str(tcl_file),
        str(gds_file),
        str(lef_file),
        "TEST_analog_example_3v3",
        [
            SimplePort("VDPWR", "met4", (100, 500), (250, 22076)),
            SimplePort("VAPWR", "met4", (2500, 500), (2650, 22076)),
            SimplePort("VGND", "met4", (4900, 500), (5050, 22076)),
        ],
    )
    return str(gds_file), str(lef_file)


def test_magic_drc_pass(gds_valid: str):
    precheck.magic_drc(gds_valid, "TEST_valid")


def test_magic_drc_fail(gds_fail_met1_poly: str):
    with pytest.raises(precheck.PrecheckFailure):
        precheck.magic_drc(gds_fail_met1_poly, "TEST_met1_error")


def test_klayout_feol_pass(gds_valid: str):
    precheck.klayout_drc(gds_valid, "feol")


def test_klayout_feol_fail(gds_fail_nwell_poly: str):
    with pytest.raises(precheck.PrecheckFailure):
        precheck.klayout_drc(gds_fail_nwell_poly, "feol")


def test_klayout_beol_pass(gds_valid: str):
    precheck.klayout_drc(gds_valid, "beol")


def test_klayout_beol_fail(gds_fail_met1_poly: str):
    with pytest.raises(precheck.PrecheckFailure):
        precheck.klayout_drc(gds_fail_met1_poly, "beol")


def test_klayout_checks_pass(gds_valid: str):
    precheck.klayout_checks(gds_valid)


def test_klayout_checks_fail_metal5(gds_fail_metal5_poly: str):
    with pytest.raises(
        precheck.PrecheckFailure, match=r"Forbidden layer met5\.drawing found in .+"
    ):
        precheck.klayout_checks(gds_fail_metal5_poly)


def test_klayout_checks_fail_pr_boundary(gds_no_pr_boundary: str):
    with pytest.raises(
        precheck.PrecheckFailure,
        match=r"prBoundary.boundary \(235/4\) layer not found in .+",
    ):
        precheck.klayout_checks(gds_no_pr_boundary)


def test_klayout_top_module_name(gds_invalid_macro_name: str):
    with pytest.raises(
        precheck.PrecheckFailure,
        match="Top macro name mismatch: expected TEST_invalid_macro_name, got wrong_name",
    ):
        precheck.klayout_checks(gds_invalid_macro_name)


def test_klayout_zero_area_drc_pass(gds_valid: str):
    precheck.klayout_zero_area(gds_valid)


def test_klayout_zero_area_drc_fail(gds_zero_area: str):
    with pytest.raises(precheck.PrecheckFailure, match="Klayout zero_area failed"):
        precheck.klayout_zero_area(gds_zero_area)


def test_pin_analog_example(gds_lef_analog_example: tuple[str, str]):
    gds_file, lef_file = gds_lef_analog_example
    precheck.pin_check(
        gds_file,
        lef_file,
        "../def/analog/tt_analog_1x2.def",
        "TEST_analog_example",
        False,
    )


def test_pin_analog_power_compat(gds_lef_analog_power_compat: tuple[str, str]):
    gds_file, lef_file = gds_lef_analog_power_compat
    precheck.pin_check(
        gds_file,
        lef_file,
        "../def/analog/tt_analog_1x2.def",
        "TEST_analog_power_compat",
        False,
    )


def test_pin_analog_wrong_vgnd(gds_lef_analog_wrong_vgnd: tuple[str, str]):
    with pytest.raises(
        precheck.PrecheckFailure,
        match="Some ports are missing or have wrong dimensions",
    ):
        gds_file, lef_file = gds_lef_analog_wrong_vgnd
        precheck.pin_check(
            gds_file,
            lef_file,
            "../def/analog/tt_analog_1x2.def",
            "TEST_analog_wrong_vgnd",
            False,
        )


def test_pin_analog_overlapping_vgnd(gds_lef_analog_overlapping_vgnd: tuple[str, str]):
    with pytest.raises(
        precheck.PrecheckFailure,
        match="Some ports are missing or have wrong dimensions",
    ):
        gds_file, lef_file = gds_lef_analog_overlapping_vgnd
        precheck.pin_check(
            gds_file,
            lef_file,
            "../def/analog/tt_analog_1x2.def",
            "TEST_analog_overlapping_vgnd",
            False,
        )


def test_pin_analog_compound_vgnd(gds_lef_analog_compound_vgnd: tuple[str, str]):
    gds_file, lef_file = gds_lef_analog_compound_vgnd
    precheck.pin_check(
        gds_file,
        lef_file,
        "../def/analog/tt_analog_1x2.def",
        "TEST_analog_compound_vgnd",
        False,
    )


def test_pin_analog_example_3v3(gds_lef_analog_example_3v3: tuple[str, str]):
    gds_file, lef_file = gds_lef_analog_example_3v3
    precheck.pin_check(
        gds_file,
        lef_file,
        "../def/analog/tt_analog_1x2.def",
        "TEST_analog_example_3v3",
        True,
    )


def test_pin_analog_3v3_mismatch1(gds_lef_analog_example: tuple[str, str]):
    with pytest.raises(
        precheck.PrecheckFailure,
        match="Some ports are missing or have wrong dimensions",
    ):
        gds_file, lef_file = gds_lef_analog_example
        precheck.pin_check(
            gds_file,
            lef_file,
            "../def/analog/tt_analog_1x2.def",
            "TEST_analog_example",
            True,
        )


def test_pin_analog_3v3_mismatch2(gds_lef_analog_example_3v3: tuple[str, str]):
    with pytest.raises(
        precheck.PrecheckFailure,
        match="Some ports are missing or have wrong dimensions",
    ):
        gds_file, lef_file = gds_lef_analog_example_3v3
        precheck.pin_check(
            gds_file,
            lef_file,
            "../def/analog/tt_analog_1x2.def",
            "TEST_analog_example_3v3",
            False,
        )
