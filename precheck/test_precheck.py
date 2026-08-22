import os
import subprocess
import textwrap

import klayout.db as pya
import klayout_tools
import pytest

import precheck

PDK_ROOT = os.getenv("PDK_ROOT")
PDK_NAME = os.getenv("PDK") or "sky130A"
LYP_NAME = "gf180mcu" if PDK_NAME == "gf180mcuD" else PDK_NAME
LYP_FILE = f"{PDK_ROOT}/{PDK_NAME}/libs.tech/klayout/tech/{LYP_NAME}.lyp"
gds_layers = klayout_tools.parse_lyp_layers(LYP_FILE)

sky130A_only = pytest.mark.skipif(
    PDK_NAME != "sky130A", reason="test only valid for PDK=sky130A"
)
gf180mcuD_only = pytest.mark.skipif(
    PDK_NAME != "gf180mcuD", reason="test only valid for PDK=gf180mcuD"
)


# FIXTURES


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


@pytest.fixture(scope="session")
def gds_def_boundary_ok(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS & DEF with boundary matching the project size."""
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_boundary_ok.gds"
    layout = pya.Layout()
    top_cell = layout.create_cell("TEST_boundary_ok")
    met1_info = gds_layers["met1.drawing"]
    met1 = layout.layer(met1_info.layer, met1_info.data_type)
    rect = pya.DBox(0, 0, 1, 1)
    top_cell.shapes(met1).insert(rect)
    boundary_info = gds_layers["prBoundary.boundary"]
    boundary = layout.layer(boundary_info.layer, boundary_info.data_type)
    rect = pya.DBox(0, 0, 10, 10)
    top_cell.shapes(boundary).insert(rect)
    layout.write(str(gds_file))
    def_file = tmp_path_factory.mktemp("def") / "TEST_boundary_ok.def"
    def_data = """
        VERSION 5.8 ;
        DIVIDERCHAR "/" ;
        BUSBITCHARS "[]" ;
        DESIGN tt_um_template ;
        UNITS DISTANCE MICRONS 1000 ;
        DIEAREA ( 0 0 ) ( 10000 10000 ) ;
        COMPONENTS 0 ;
        END COMPONENTS
        PINS 0 ;
        END PINS
        SPECIALNETS 0 ;
        END SPECIALNETS
        NETS 0 ;
        END NETS
        END DESIGN
    """
    open(def_file, "w").write(textwrap.dedent(def_data))
    return str(gds_file), str(def_file)


@pytest.fixture(scope="session")
def gds_def_boundary_wrong_1(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS & DEF with a bounding box smaller than the project size."""
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_boundary_wrong_1.gds"
    layout = pya.Layout()
    met1_info = gds_layers["met1.drawing"]
    met1 = layout.layer(met1_info.layer, met1_info.data_type)
    top_cell = layout.create_cell("TEST_boundary_wrong_1")
    rect = pya.DBox(0, 0, 1, 1)
    top_cell.shapes(met1).insert(rect)
    boundary_info = gds_layers["prBoundary.boundary"]
    boundary = layout.layer(boundary_info.layer, boundary_info.data_type)
    rect = pya.DBox(0, 0, 2, 2)
    top_cell.shapes(boundary).insert(rect)
    layout.write(str(gds_file))
    def_file = tmp_path_factory.mktemp("def") / "TEST_boundary_wrong_1.def"
    def_data = """
        VERSION 5.8 ;
        DIVIDERCHAR "/" ;
        BUSBITCHARS "[]" ;
        DESIGN tt_um_template ;
        UNITS DISTANCE MICRONS 1000 ;
        DIEAREA ( 0 0 ) ( 10000 10000 ) ;
        COMPONENTS 0 ;
        END COMPONENTS
        PINS 0 ;
        END PINS
        SPECIALNETS 0 ;
        END SPECIALNETS
        NETS 0 ;
        END NETS
        END DESIGN
    """
    open(def_file, "w").write(textwrap.dedent(def_data))
    return str(gds_file), str(def_file)


@pytest.fixture(scope="session")
def gds_def_boundary_wrong_2(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS & DEF where the bounding box is ok but the boundary layer is wrong."""
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_boundary_wrong_2.gds"
    layout = pya.Layout()
    met1_info = gds_layers["met1.drawing"]
    met1 = layout.layer(met1_info.layer, met1_info.data_type)
    top_cell = layout.create_cell("TEST_boundary_wrong_2")
    rect = pya.DBox(0, 0, 10, 10)
    top_cell.shapes(met1).insert(rect)
    boundary_info = gds_layers["prBoundary.boundary"]
    boundary = layout.layer(boundary_info.layer, boundary_info.data_type)
    rect = pya.DBox(0, 0, 2, 2)
    top_cell.shapes(boundary).insert(rect)
    layout.write(str(gds_file))
    def_file = tmp_path_factory.mktemp("def") / "TEST_boundary_wrong_2.def"
    def_data = """
        VERSION 5.8 ;
        DIVIDERCHAR "/" ;
        BUSBITCHARS "[]" ;
        DESIGN tt_um_template ;
        UNITS DISTANCE MICRONS 1000 ;
        DIEAREA ( 0 0 ) ( 10000 10000 ) ;
        COMPONENTS 0 ;
        END COMPONENTS
        PINS 0 ;
        END PINS
        SPECIALNETS 0 ;
        END SPECIALNETS
        NETS 0 ;
        END NETS
        END DESIGN
    """
    open(def_file, "w").write(textwrap.dedent(def_data))
    return str(gds_file), str(def_file)


@pytest.fixture(scope="session")
def gds_def_shapes_outside_area(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS & DEF with shapes outside the project area."""
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_shapes_outside_area.gds"
    layout = pya.Layout()
    top_cell = layout.create_cell("TEST_shapes_outside_area")
    met1_info = gds_layers["met1.drawing"]
    met1 = layout.layer(met1_info.layer, met1_info.data_type)
    rect = pya.DBox(-1, 0, 0, 1)
    top_cell.shapes(met1).insert(rect)
    layout.write(str(gds_file))
    def_file = tmp_path_factory.mktemp("def") / "TEST_shapes_outside_area.def"
    def_data = """
        VERSION 5.8 ;
        DIVIDERCHAR "/" ;
        BUSBITCHARS "[]" ;
        DESIGN tt_um_template ;
        UNITS DISTANCE MICRONS 1000 ;
        DIEAREA ( 0 0 ) ( 10000 10000 ) ;
        COMPONENTS 0 ;
        END COMPONENTS
        PINS 0 ;
        END PINS
        SPECIALNETS 0 ;
        END SPECIALNETS
        NETS 0 ;
        END NETS
        END DESIGN
    """
    open(def_file, "w").write(textwrap.dedent(def_data))
    return str(gds_file), str(def_file)


@pytest.fixture(scope="session")
def verilog_lef_wrong_power_pins(tmp_path_factory: pytest.TempPathFactory):
    """Creates a Verilog & LEF file with wrong power pins."""
    verilog_file = tmp_path_factory.mktemp("verilog") / "TEST_wrong_power_pins.v"
    verilog_data = """
        `default_nettype none
        module TEST_wrong_power_pins (
            input wire VGND,
            input wire VDPWR,
            input wire VAPWR
        );
        endmodule
    """
    open(verilog_file, "w").write(textwrap.dedent(verilog_data))
    lef_file = tmp_path_factory.mktemp("lef") / "TEST_wrong_power_pins.lef"
    lef_data = """
        VERSION 5.7 ;
        NOWIREEXTENSIONATPIN ON ;
        DIVIDERCHAR "/" ;
        BUSBITCHARS "[]" ;
        MACRO TEST_wrong_power_pins
        CLASS BLOCK ;
        FOREIGN TEST_wrong_power_pins ;
        ORIGIN 0.000 0.000 ;
        SIZE 161.000 BY 111.520 ;
        PIN VGND
            DIRECTION INOUT ;
            USE GROUND ;
            PORT
            LAYER met4 ;
                RECT 21.580 2.480 23.180 109.040 ;
            END
        END VGND
        PIN VDPWR
            DIRECTION INOUT ;
            USE POWER ;
            PORT
            LAYER met4 ;
                RECT 18.280 2.480 19.880 109.040 ;
            END
        END VDPWR
    """
    open(lef_file, "w").write(textwrap.dedent(lef_data))
    return str(verilog_file), str(lef_file)


@pytest.fixture(scope="session")
def verilog_lef_missing_use_power(tmp_path_factory: pytest.TempPathFactory):
    """Creates a Verilog & LEF file with wrong power pins."""
    verilog_file = tmp_path_factory.mktemp("verilog") / "TEST_missing_use_power.v"
    verilog_data = """
        `default_nettype none
        module TEST_wrong_power_pins (
            input wire VGND,
            input wire VDPWR
        );
        endmodule
    """
    open(verilog_file, "w").write(textwrap.dedent(verilog_data))
    lef_file = tmp_path_factory.mktemp("lef") / "TEST_missing_use_power.lef"
    lef_data = """
        VERSION 5.7 ;
        NOWIREEXTENSIONATPIN ON ;
        DIVIDERCHAR "/" ;
        BUSBITCHARS "[]" ;
        MACRO TEST_missing_use_power
        CLASS BLOCK ;
        FOREIGN TEST_missing_use_power ;
        ORIGIN 0.000 0.000 ;
        SIZE 161.000 BY 111.520 ;
        PIN VGND
            DIRECTION INOUT ;
            USE GROUND ;
            PORT
            LAYER met4 ;
                RECT 21.580 2.480 23.180 109.040 ;
            END
        END VGND
        PIN VDPWR
            DIRECTION INOUT ;
            PORT
            LAYER met4 ;
                RECT 18.280 2.480 19.880 109.040 ;
            END
        END VDPWR
    """
    open(lef_file, "w").write(textwrap.dedent(lef_data))
    return str(verilog_file), str(lef_file)


@pytest.fixture(scope="session")
def verilog_lef_missing_use_ground(tmp_path_factory: pytest.TempPathFactory):
    """Creates a Verilog & LEF file with wrong power pins."""
    verilog_file = tmp_path_factory.mktemp("verilog") / "TEST_missing_use_ground.v"
    verilog_data = """
        `default_nettype none
        module TEST_wrong_power_pins (
            input wire VGND,
            input wire VDPWR
        );
        endmodule
    """
    open(verilog_file, "w").write(textwrap.dedent(verilog_data))
    lef_file = tmp_path_factory.mktemp("lef") / "TEST_missing_use_ground.lef"
    lef_data = """
        VERSION 5.7 ;
        NOWIREEXTENSIONATPIN ON ;
        DIVIDERCHAR "/" ;
        BUSBITCHARS "[]" ;
        MACRO TEST_missing_use_ground
        CLASS BLOCK ;
        FOREIGN TEST_missing_use_ground ;
        ORIGIN 0.000 0.000 ;
        SIZE 161.000 BY 111.520 ;
        PIN VGND
            DIRECTION INOUT ;
            PORT
            LAYER met4 ;
                RECT 21.580 2.480 23.180 109.040 ;
            END
        END VGND
        PIN VDPWR
            DIRECTION INOUT ;
            USE POWER ;
            PORT
            LAYER met4 ;
                RECT 18.280 2.480 19.880 109.040 ;
            END
        END VDPWR
    """
    open(lef_file, "w").write(textwrap.dedent(lef_data))
    return str(verilog_file), str(lef_file)


@pytest.fixture(scope="session")
def gds_invalid_layer(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS with a layer/datatype not defined in sky130."""
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_invalid_layer.gds"
    layout = pya.Layout()
    invalid_layer = layout.layer(255, 255)
    top_cell = layout.create_cell("TEST_invalid_layer")
    rect = pya.DBox(0, 0, 5, 5)
    top_cell.shapes(invalid_layer).insert(rect)
    layout.write(str(gds_file))
    return str(gds_file)


@pytest.fixture(scope="session")
def gds_invalid_cell_name(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS with a subcell having a '#' in its name."""
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_invalid_cell_name.gds"
    layout = pya.Layout()
    top_cell = layout.create_cell("TEST_invalid_cell_name")
    subcell = layout.create_cell("subcell#")
    subcell_instance = pya.CellInstArray(subcell, pya.Trans())
    top_cell.insert(subcell_instance)
    layout.write(str(gds_file))
    return str(gds_file)


@pytest.fixture(scope="session")
def gds_urpm_nwell_too_close(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS with a subcell having a '#' in its name."""
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_urpm_nwell_too_close.gds"
    layout = pya.Layout()
    nwell_info = gds_layers["nwell.drawing"]
    nwell = layout.layer(nwell_info.layer, nwell_info.data_type)
    urpm = layout.layer(79, 20)
    # Hardcoding "urpm" layer/datatype because the .lyp file on the PDK version
    # we use on GitHub Actions doesn't have it yet. Once we upgrade it, we can
    # replace the line above with:
    #   urpm_info = gds_layers["urpm"]
    #   urpm = layout.layer(urpm_info.layer, urpm_info.data_type)
    top_cell = layout.create_cell("TEST_urpm_nwell_too_close")
    nwell_rect = pya.DBox(0, 0, 5, 5)
    top_cell.shapes(nwell).insert(nwell_rect)
    urpm_rect = pya.DBox(5, 0, 10, 5)
    top_cell.shapes(urpm).insert(urpm_rect)
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
            def read ../tech/{PDK_NAME}/def/analog/tt_analog_1x2.def
            cellname rename tt_um_template {toplevel}
            """
        )
        for port in extra_ports:
            for rect in port.rects:
                tcl_append(
                    f"""
                    box {rect.lx} {rect.by} {rect.rx} {rect.ty}
                    paint {rect.layer}
                    """
                )
                if port.name:
                    tcl_append(
                        f"""
                        label {port.name} FreeSans {rect.layer}
                        """
                    )
            if port.name:
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
    """Creates a GDS and LEF using the 1x2 analog template using 3v3 power."""
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


@pytest.fixture(scope="session")
def gds_lef_analog_pin_example(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS and LEF using the 1x2 analog template with 2 analog pins used."""
    tcl_file = tmp_path_factory.mktemp("tcl") / "TEST_analog_pin_example.tcl"
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_analog_pin_example.gds"
    lef_file = tmp_path_factory.mktemp("lef") / "TEST_analog_pin_example.lef"

    generate_analog_example(
        str(tcl_file),
        str(gds_file),
        str(lef_file),
        "TEST_analog_example",
        [
            SimplePort("VDPWR", "met4", (100, 500), (250, 22076)),
            SimplePort("VGND", "met4", (4900, 500), (5050, 22076)),
            SimplePort("", "via3", (15200, 30), (15250, 80)),
            SimplePort("", "via3", (13270, 30), (13320, 80)),
        ],
    )
    return str(gds_file), str(lef_file)


@pytest.fixture(scope="session")
def gds_lef_analog_unused_pins(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS and LEF using the 1x2 analog template with no analog pins connected."""
    tcl_file = tmp_path_factory.mktemp("tcl") / "TEST_analog_unused_pins.tcl"
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_analog_unused_pins.gds"
    lef_file = tmp_path_factory.mktemp("lef") / "TEST_analog_unused_pins.lef"

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
def gds_lef_analog_bridged_unused_pins(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS and LEF using the 1x2 analog template with 2 analog pins used and the rest bridged together with a path."""
    tcl_file = tmp_path_factory.mktemp("tcl") / "TEST_analog_bridged_unused_pins.tcl"
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_analog_bridged_unused_pins.gds"
    lef_file = tmp_path_factory.mktemp("lef") / "TEST_analog_bridged_unused_pins.lef"

    generate_analog_example(
        str(tcl_file),
        str(gds_file),
        str(lef_file),
        "TEST_analog_bridged_unused_pins",
        [
            SimplePort("", "via3", (15200, 30), (15250, 80)),
            SimplePort("", "via3", (13270, 30), (13320, 80)),
        ],
    )

    # add a GDSII path object using klayout
    layout = pya.Layout()
    layout.read(str(gds_file))
    top = layout.top_cell()
    layer = layout.layer(71, 20)  # sky130 metal4
    points = [
        pya.DPoint(16.57, 0.5),
        pya.DPoint(114.07, 0.5),
        pya.DPoint(114.07, 0.5),
    ]
    path = pya.DPath(points, 0.3)
    top.shapes(layer).insert(path)
    layout.write(str(gds_file))

    return str(gds_file), str(lef_file)


@pytest.fixture(scope="session")
def gds_lef_analog_incorrect_pin_connected(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS and LEF using the 1x2 analog template with the incorrect analog pin wired up."""
    tcl_file = (
        tmp_path_factory.mktemp("tcl") / "TEST_analog_incorrect_pin_connected.tcl"
    )
    gds_file = (
        tmp_path_factory.mktemp("gds") / "TEST_analog_incorrect_pin_connected.gds"
    )
    lef_file = (
        tmp_path_factory.mktemp("lef") / "TEST_analog_incorrect_pin_connected.lef"
    )

    generate_analog_example(
        str(tcl_file),
        str(gds_file),
        str(lef_file),
        "TEST_analog_incorrect_pin_connected",
        [
            SimplePort(
                "", "via3", (13270, 30), (13320, 80)
            ),  # connect to ua[1] instead of ua[0]
        ],
    )
    return str(gds_file), str(lef_file)


@pytest.fixture(scope="session")
def verilog_syntax_ok(tmp_path_factory: pytest.TempPathFactory):
    """Creates a Verilog file with correct syntax."""
    verilog_file = tmp_path_factory.mktemp("verilog") / "TEST_verilog_syntax_ok.v"
    verilog_data = """
        module TEST_verilog_syntax_ok ();
        endmodule
    """
    open(verilog_file, "w").write(textwrap.dedent(verilog_data))
    return str(verilog_file)


@pytest.fixture(scope="session")
def verilog_syntax_error(tmp_path_factory: pytest.TempPathFactory):
    """Creates a Verilog file with incorrect syntax."""
    verilog_file = tmp_path_factory.mktemp("verilog") / "TEST_verilog_syntax_error.v"
    verilog_data = """
        module TEST_verilog_syntax_error ();
        syntax error
        endmodule
    """
    open(verilog_file, "w").write(textwrap.dedent(verilog_data))
    return str(verilog_file)


@pytest.fixture(scope="session")
def gds_antenna_pass(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS without antenna violation."""
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_antenna_pass.gds"
    layout = pya.Layout()
    poly2_info = gds_layers["Poly2"]
    poly2 = layout.layer(poly2_info.layer, poly2_info.data_type)
    comp_info = gds_layers["COMP"]
    comp = layout.layer(comp_info.layer, comp_info.data_type)
    top_cell = layout.create_cell("TEST_antenna_pass")
    poly2_rect = pya.DBox(0, 0, 1, 3)
    top_cell.shapes(poly2).insert(poly2_rect)
    comp_rect = pya.DBox(-1, 1, 2, 2)
    top_cell.shapes(comp).insert(comp_rect)
    layout.write(str(gds_file))
    return str(gds_file)


@pytest.fixture(scope="session")
def gds_antenna_fail(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS with antenna violation."""
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_antenna_fail.gds"
    layout = pya.Layout()
    poly2_info = gds_layers["Poly2"]
    poly2 = layout.layer(poly2_info.layer, poly2_info.data_type)
    comp_info = gds_layers["COMP"]
    comp = layout.layer(comp_info.layer, comp_info.data_type)
    top_cell = layout.create_cell("TEST_antenna_fail")
    poly2_rect = pya.DBox(0, 0, 1, 500)
    top_cell.shapes(poly2).insert(poly2_rect)
    comp_rect = pya.DBox(-1, 1, 2, 2)
    top_cell.shapes(comp).insert(comp_rect)
    layout.write(str(gds_file))
    return str(gds_file)


@pytest.fixture(scope="session")
def gds_gf180_drc_pass(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS without DRC violations (density rules are not run)."""
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_gf180_drc_pass.gds"
    layout = pya.Layout()
    metal1_info = gds_layers["Metal1"]
    metal1 = layout.layer(metal1_info.layer, metal1_info.data_type)
    top_cell = layout.create_cell("TEST_gf180_drc_pass")
    # A single wide Metal1 shape: satisfies min width, area and spacing.
    top_cell.shapes(metal1).insert(pya.DBox(0, 0, 1, 1))
    layout.write(str(gds_file))
    return str(gds_file)


@pytest.fixture(scope="session")
def gds_gf180_drc_fail(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS with a Metal1 spacing violation (rule M1.2a)."""
    gds_file = tmp_path_factory.mktemp("gds") / "TEST_gf180_drc_fail.gds"
    layout = pya.Layout()
    metal1_info = gds_layers["Metal1"]
    metal1 = layout.layer(metal1_info.layer, metal1_info.data_type)
    top_cell = layout.create_cell("TEST_gf180_drc_fail")
    # Two wide Metal1 shapes spaced 0.1um apart, below the min spacing rule.
    top_cell.shapes(metal1).insert(pya.DBox(0, 0, 1, 1))
    top_cell.shapes(metal1).insert(pya.DBox(1.1, 0, 2.1, 1))
    layout.write(str(gds_file))
    return str(gds_file)


# TESTS


@sky130A_only
def test_magic_drc_pass(gds_valid: str):
    precheck.magic_drc(gds_valid, "TEST_valid")


@sky130A_only
def test_magic_drc_fail(gds_fail_met1_poly: str):
    with pytest.raises(precheck.PrecheckFailure):
        precheck.magic_drc(gds_fail_met1_poly, "TEST_met1_error")


@sky130A_only
def test_klayout_feol_pass(gds_valid: str):
    precheck.klayout_drc(gds_valid, "feol")


@sky130A_only
def test_klayout_feol_fail(gds_fail_nwell_poly: str):
    with pytest.raises(precheck.PrecheckFailure):
        precheck.klayout_drc(gds_fail_nwell_poly, "feol")


@sky130A_only
def test_klayout_beol_pass(gds_valid: str):
    precheck.klayout_drc(gds_valid, "beol")


@sky130A_only
def test_klayout_beol_fail(gds_fail_met1_poly: str):
    with pytest.raises(precheck.PrecheckFailure):
        precheck.klayout_drc(gds_fail_met1_poly, "beol")


@sky130A_only
def test_klayout_checks_pass(gds_valid: str):
    precheck.klayout_checks(gds_valid, "TEST_valid", PDK_NAME)


@sky130A_only
def test_klayout_checks_fail_metal5(gds_fail_metal5_poly: str):
    with pytest.raises(
        precheck.PrecheckFailure, match=r"Forbidden layer met5\.drawing found in .+"
    ):
        precheck.klayout_checks(gds_fail_metal5_poly, "TEST_met5_error", PDK_NAME)


@sky130A_only
def test_klayout_checks_fail_pr_boundary(gds_no_pr_boundary: str):
    with pytest.raises(
        precheck.PrecheckFailure,
        match=r"prBoundary.boundary \(235/4\) layer not found in .+",
    ):
        precheck.klayout_checks(gds_no_pr_boundary, "TEST_no_prboundary", PDK_NAME)


def test_klayout_top_module_name(gds_invalid_macro_name: str):
    with pytest.raises(
        precheck.PrecheckFailure,
        match="Top macro name mismatch: expected TEST_invalid_macro_name, got wrong_name",
    ):
        precheck.klayout_checks(
            gds_invalid_macro_name, "TEST_invalid_macro_name", PDK_NAME
        )


@sky130A_only
def test_klayout_zero_area_drc_pass(gds_valid: str):
    precheck.klayout_zero_area(gds_valid)


@sky130A_only
def test_klayout_zero_area_drc_fail(gds_zero_area: str):
    with pytest.raises(precheck.PrecheckFailure, match="Klayout zero_area failed"):
        precheck.klayout_zero_area(gds_zero_area)


@sky130A_only
def test_boundary_ok(gds_def_boundary_ok: tuple[str, str]):
    gds_boundary_ok, def_boundary_ok = gds_def_boundary_ok
    precheck.boundary_check(gds_boundary_ok, def_boundary_ok, PDK_NAME)


@sky130A_only
def test_boundary_wrong_1(gds_def_boundary_wrong_1: tuple[str, str]):
    gds_boundary_wrong_1, def_boundary_wrong_1 = gds_def_boundary_wrong_1
    with pytest.raises(
        precheck.PrecheckFailure, match="Boundary layer doesn't cover project area"
    ):
        precheck.boundary_check(gds_boundary_wrong_1, def_boundary_wrong_1, PDK_NAME)


@sky130A_only
def test_boundary_wrong_2(gds_def_boundary_wrong_2: tuple[str, str]):
    gds_boundary_wrong_2, def_boundary_wrong_2 = gds_def_boundary_wrong_2
    with pytest.raises(
        precheck.PrecheckFailure,
        match="Missing top-level prBoundary rectangle with right size",
    ):
        precheck.boundary_check(gds_boundary_wrong_2, def_boundary_wrong_2, PDK_NAME)


@sky130A_only
def test_shapes_outside_area(gds_def_shapes_outside_area: tuple[str, str]):
    gds_shapes_outside_area, def_shapes_outside_area = gds_def_shapes_outside_area
    with pytest.raises(precheck.PrecheckFailure, match="Shapes outside project area"):
        precheck.boundary_check(
            gds_shapes_outside_area, def_shapes_outside_area, PDK_NAME
        )


def test_wrong_power_pins_1(verilog_lef_wrong_power_pins: tuple[str, str]):
    verilog_file, lef_file = verilog_lef_wrong_power_pins
    with pytest.raises(precheck.PrecheckFailure, match="Verilog contains VAPWR"):
        precheck.power_pin_check(verilog_file, lef_file, uses_vapwr=False)


def test_wrong_power_pins_2(verilog_lef_wrong_power_pins: tuple[str, str]):
    verilog_file, lef_file = verilog_lef_wrong_power_pins
    with pytest.raises(precheck.PrecheckFailure, match="LEF doesn't contain VAPWR"):
        precheck.power_pin_check(verilog_file, lef_file, uses_vapwr=True)


def test_missing_use_power(verilog_lef_missing_use_power: tuple[str, str]):
    verilog_file, lef_file = verilog_lef_missing_use_power
    with pytest.raises(
        precheck.PrecheckFailure,
        match="VDPWR does not have a corresponding 'USE POWER ;'",
    ):
        precheck.power_pin_check(verilog_file, lef_file, uses_vapwr=False)


def test_missing_use_ground(verilog_lef_missing_use_ground: tuple[str, str]):
    verilog_file, lef_file = verilog_lef_missing_use_ground
    with pytest.raises(
        precheck.PrecheckFailure,
        match="VGND does not have a corresponding 'USE GROUND ;'",
    ):
        precheck.power_pin_check(verilog_file, lef_file, uses_vapwr=False)


def test_invalid_layer(gds_invalid_layer: str):
    with pytest.raises(precheck.PrecheckFailure, match="Invalid layers in GDS"):
        precheck.layer_check(gds_invalid_layer, PDK_NAME)


def test_invalid_cell_name(gds_invalid_cell_name: str):
    with pytest.raises(
        precheck.PrecheckFailure,
        match="Cell name subcell# contains invalid character '#'",
    ):
        precheck.cell_name_check(gds_invalid_cell_name)


@sky130A_only
def test_urpm_nwell_too_close(gds_urpm_nwell_too_close: str):
    with pytest.raises(
        precheck.PrecheckFailure,
        match="Klayout nwell_urpm failed with 1 DRC violations",
    ):
        precheck.urpm_nwell_check(gds_urpm_nwell_too_close, "TEST_urpm_nwell_too_close")


@sky130A_only
def test_pin_analog_example(gds_lef_analog_example: tuple[str, str]):
    gds_file, lef_file = gds_lef_analog_example
    precheck.pin_check(
        gds_file,
        lef_file,
        f"../tech/{PDK_NAME}/def/analog/tt_analog_1x2.def",
        "TEST_analog_example",
        False,
        PDK_NAME,
    )


@sky130A_only
def test_pin_analog_power_compat(gds_lef_analog_power_compat: tuple[str, str]):
    gds_file, lef_file = gds_lef_analog_power_compat
    precheck.pin_check(
        gds_file,
        lef_file,
        f"../tech/{PDK_NAME}/def/analog/tt_analog_1x2.def",
        "TEST_analog_power_compat",
        False,
        PDK_NAME,
    )


@sky130A_only
def test_pin_analog_wrong_vgnd(gds_lef_analog_wrong_vgnd: tuple[str, str]):
    with pytest.raises(
        precheck.PrecheckFailure,
        match="Some ports are missing or have wrong dimensions",
    ):
        gds_file, lef_file = gds_lef_analog_wrong_vgnd
        precheck.pin_check(
            gds_file,
            lef_file,
            f"../tech/{PDK_NAME}/def/analog/tt_analog_1x2.def",
            "TEST_analog_wrong_vgnd",
            False,
            PDK_NAME,
        )


@sky130A_only
def test_pin_analog_overlapping_vgnd(gds_lef_analog_overlapping_vgnd: tuple[str, str]):
    with pytest.raises(
        precheck.PrecheckFailure,
        match="Some ports are missing or have wrong dimensions",
    ):
        gds_file, lef_file = gds_lef_analog_overlapping_vgnd
        precheck.pin_check(
            gds_file,
            lef_file,
            f"../tech/{PDK_NAME}/def/analog/tt_analog_1x2.def",
            "TEST_analog_overlapping_vgnd",
            False,
            PDK_NAME,
        )


@sky130A_only
def test_pin_analog_compound_vgnd(gds_lef_analog_compound_vgnd: tuple[str, str]):
    gds_file, lef_file = gds_lef_analog_compound_vgnd
    precheck.pin_check(
        gds_file,
        lef_file,
        f"../tech/{PDK_NAME}/def/analog/tt_analog_1x2.def",
        "TEST_analog_compound_vgnd",
        False,
        PDK_NAME,
    )


@sky130A_only
def test_pin_analog_example_3v3(gds_lef_analog_example_3v3: tuple[str, str]):
    gds_file, lef_file = gds_lef_analog_example_3v3
    precheck.pin_check(
        gds_file,
        lef_file,
        f"../tech/{PDK_NAME}/def/analog/tt_analog_1x2.def",
        "TEST_analog_example_3v3",
        True,
        PDK_NAME,
    )


@sky130A_only
def test_pin_analog_3v3_mismatch1(gds_lef_analog_example: tuple[str, str]):
    with pytest.raises(
        precheck.PrecheckFailure,
        match="Some ports are missing or have wrong dimensions",
    ):
        gds_file, lef_file = gds_lef_analog_example
        precheck.pin_check(
            gds_file,
            lef_file,
            f"../tech/{PDK_NAME}/def/analog/tt_analog_1x2.def",
            "TEST_analog_example",
            True,
            PDK_NAME,
        )


@sky130A_only
def test_pin_analog_3v3_mismatch2(gds_lef_analog_example_3v3: tuple[str, str]):
    with pytest.raises(
        precheck.PrecheckFailure,
        match="Some ports are missing or have wrong dimensions",
    ):
        gds_file, lef_file = gds_lef_analog_example_3v3
        precheck.pin_check(
            gds_file,
            lef_file,
            f"../tech/{PDK_NAME}/def/analog/tt_analog_1x2.def",
            "TEST_analog_example_3v3",
            False,
            PDK_NAME,
        )


@sky130A_only
def test_analog_exact_pins(gds_lef_analog_pin_example: tuple[str, str]):
    gds_file, lef_file = gds_lef_analog_pin_example
    precheck.analog_pin_check(
        gds_file, PDK_NAME, True, False, 2, {"ua[0]": "x", "ua[1]": "x"}
    )


@sky130A_only
def test_analog_less_pins(gds_lef_analog_pin_example: tuple[str, str]):
    gds_file, lef_file = gds_lef_analog_pin_example
    with pytest.raises(
        precheck.PrecheckFailure,
        match="Analog pin `ua\\[1\\]` is connected to some metal but `analog_pins` is set to 1 .*",
    ):
        precheck.analog_pin_check(
            gds_file, PDK_NAME, True, False, 1, {"ua[0]": "x", "ua[1]": "x"}
        )


@sky130A_only
def test_analog_more_pins(gds_lef_analog_pin_example: tuple[str, str]):
    gds_file, lef_file = gds_lef_analog_pin_example
    with pytest.raises(
        precheck.PrecheckWarning,
        match="Analog pin `ua\\[2\\]` is not connected to any adjacent metal but `analog_pins` is set to 3 .*",
    ):
        precheck.analog_pin_check(
            gds_file, PDK_NAME, True, False, 3, {"ua[0]": "x", "ua[1]": "x"}
        )


@sky130A_only
def test_analog_less_ua_entries(gds_lef_analog_pin_example: tuple[str, str]):
    gds_file, lef_file = gds_lef_analog_pin_example
    with pytest.raises(
        precheck.PrecheckFailure,
        match="Analog pin `ua\\[1\\]` is connected to some metal but the description of `ua\\[1\\]` .*",
    ):
        precheck.analog_pin_check(gds_file, PDK_NAME, True, False, 2, {"ua[0]": "x"})


@sky130A_only
def test_analog_more_ua_entries(gds_lef_analog_pin_example: tuple[str, str]):
    gds_file, lef_file = gds_lef_analog_pin_example
    with pytest.raises(
        precheck.PrecheckWarning,
        match="Analog pin `ua\\[2\\]` is not connected to any adjacent metal but the description of `ua\\[2\\]` .*",
    ):
        precheck.analog_pin_check(
            gds_file,
            PDK_NAME,
            True,
            False,
            2,
            {"ua[0]": "x", "ua[1]": "x", "ua[2]": "x"},
        )


@sky130A_only
def test_analog_bridged_unused_pins(
    gds_lef_analog_bridged_unused_pins: tuple[str, str]
):
    gds_file, lef_file = gds_lef_analog_bridged_unused_pins
    with pytest.RaisesGroup(
        pytest.RaisesExc(
            precheck.PrecheckFailure,
            match="Analog pin `ua\\[2\\]` is connected to some metal .*",
        ),
        pytest.RaisesExc(
            precheck.PrecheckFailure,
            match="Analog pin `ua\\[3\\]` is connected to some metal .*",
        ),
        pytest.RaisesExc(
            precheck.PrecheckFailure,
            match="Analog pin `ua\\[4\\]` is connected to some metal .*",
        ),
        pytest.RaisesExc(
            precheck.PrecheckFailure,
            match="Analog pin `ua\\[5\\]` is connected to some metal .*",
        ),
        pytest.RaisesExc(
            precheck.PrecheckFailure,
            match="Analog pin `ua\\[6\\]` is connected to some metal .*",
        ),
        pytest.RaisesExc(
            precheck.PrecheckFailure,
            match="Analog pin `ua\\[7\\]` is connected to some metal .*",
        ),
        match="Analog pin check failed with 6 errors.",
    ):
        precheck.analog_pin_check(
            gds_file, PDK_NAME, True, False, 2, {"ua[0]": "x", "ua[1]": "x"}
        )


@sky130A_only
def test_analog_incorrect_wired_pin(
    gds_lef_analog_incorrect_pin_connected: tuple[str, str]
):
    gds_file, lef_file = gds_lef_analog_incorrect_pin_connected
    with pytest.RaisesGroup(
        pytest.RaisesExc(
            precheck.PrecheckFailure,
            match="Analog pin `ua\\[1\\]` is connected to some metal but `analog_pins` is set to 1 .*",
        ),
        pytest.RaisesExc(
            precheck.PrecheckWarning,
            match="Analog pin `ua\\[0\\]` is not connected to any adjacent metal but `analog_pins` is set to 1 .*",
        ),
        match="Analog pin check failed with 1 errors and 1 warnings.",
    ):
        precheck.analog_pin_check(gds_file, PDK_NAME, True, False, 1, {"ua[0]": "x"})


def test_analog_single_declared_unused_pin(gds_lef_analog_unused_pins: tuple[str, str]):
    """Test if `PrecheckWarning` is raised if `analog_pins` == 1"""
    gds_file, lef_file = gds_lef_analog_unused_pins
    with pytest.raises(
        precheck.PrecheckWarning,
        match="Analog pin `ua\\[0\\]` is not connected to any adjacent metal but `analog_pins` is set to 1 .*",
    ):
        precheck.analog_pin_check(gds_file, PDK_NAME, True, False, 1, {})


def test_analog_multiple_declared_unused_pins(
    gds_lef_analog_unused_pins: tuple[str, str]
):
    """Test if a `PrecheckWarningGroup` is raised if `analog_pins` > 1"""
    gds_file, lef_file = gds_lef_analog_unused_pins
    with pytest.RaisesGroup(
        pytest.RaisesExc(
            precheck.PrecheckWarning,
            match="Analog pin `ua\\[0\\]` is not connected to any adjacent metal but `analog_pins` is set to 2 .*",
        ),
        pytest.RaisesExc(
            precheck.PrecheckWarning,
            match="Analog pin `ua\\[1\\]` is not connected to any adjacent metal but `analog_pins` is set to 2 .*",
        ),
        match="Analog pin check succeeded with 2 warnings.",
    ):
        precheck.analog_pin_check(gds_file, PDK_NAME, True, False, 2, {})


def test_verilog_syntax_ok(verilog_syntax_ok: str):
    precheck.verilog_syntax_check(verilog_syntax_ok)


def test_verilog_syntax_error(verilog_syntax_error: str):
    with pytest.raises(
        precheck.PrecheckFailure,
        match="Verilog syntax check failed",
    ):
        precheck.verilog_syntax_check(verilog_syntax_error)


@gf180mcuD_only
def test_gf180mcuD_drc_pass(gds_gf180_drc_pass: str):
    precheck.klayout_gf180mcuD_drc(gds_gf180_drc_pass, "TEST_gf180_drc_pass")


@gf180mcuD_only
def test_gf180mcuD_drc_fail(gds_gf180_drc_fail: str):
    with pytest.raises(
        precheck.PrecheckFailure,
        match="Klayout gf180mcuD failed with 1 DRC violations",
    ):
        precheck.klayout_gf180mcuD_drc(gds_gf180_drc_fail, "TEST_gf180_drc_fail")


@gf180mcuD_only
def test_antenna_pass(gds_antenna_pass: str):
    precheck.klayout_gf180mcuD_antenna(gds_antenna_pass, "TEST_antenna_pass")


@gf180mcuD_only
def test_antenna_fail(gds_antenna_fail: str):
    with pytest.raises(
        precheck.PrecheckFailure,
        match="Klayout antenna failed with 1 DRC violations",
    ):
        precheck.klayout_gf180mcuD_antenna(gds_antenna_fail, "TEST_antenna_fail")
