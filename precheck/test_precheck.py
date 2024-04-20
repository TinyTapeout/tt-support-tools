import os

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
    gds_file = tmp_path_factory.mktemp("gds") / "gds_valid.gds"
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
    gds_file = tmp_path_factory.mktemp("gds") / "gds_met1_fail.gds"
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
    gds_file = tmp_path_factory.mktemp("gds") / "gds_nwell_fail.gds"
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
    gds_file = tmp_path_factory.mktemp("gds") / "gds_metal5_fail.gds"
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
    gds_file = tmp_path_factory.mktemp("gds") / "gds_no_pr_boundary.gds"
    layout = pya.Layout()
    layout.create_cell("TEST_no_prboundary")
    layout.write(str(gds_file))
    return str(gds_file)


@pytest.fixture(scope="session")
def gds_zero_area(tmp_path_factory: pytest.TempPathFactory):
    """Creates a GDS with a zero-area polygon."""
    gds_file = tmp_path_factory.mktemp("gds") / "gds_zero_area.gds"
    layout = pya.Layout()
    top_cell = layout.create_cell("TEST_zero_area")
    met1_info = gds_layers["met1.drawing"]
    met1 = layout.layer(met1_info.layer, met1_info.data_type)
    rect = pya.DBox(0, 0, 0, 0)
    top_cell.shapes(met1).insert(rect)
    layout.write(str(gds_file))
    return str(gds_file)


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
    with pytest.raises(precheck.PrecheckFailure):
        precheck.klayout_checks(gds_fail_metal5_poly)


def test_klayout_checks_fail_pr_boundary(gds_no_pr_boundary: str):
    with pytest.raises(precheck.PrecheckFailure):
        precheck.klayout_checks(gds_no_pr_boundary)


def test_klayout_zero_area_drc_pass(gds_valid: str):
    precheck.klayout_zero_area(gds_valid)


def test_klayout_zero_area_drc_fail(gds_zero_area: str):
    with pytest.raises(precheck.PrecheckFailure):
        precheck.klayout_zero_area(gds_zero_area)
