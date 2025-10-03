import pytest
import yaml

from project_info import YAML_VERSION, ProjectInfo, ProjectYamlError


@pytest.fixture
def valid_yaml_data():
    """Base valid YAML data for testing"""
    return {
        "yaml_version": YAML_VERSION,
        "project": {
            "title": "Test Project",
            "author": "Test Author",
            "description": "Test Description",
            "tiles": "1x1",
            "analog_pins": 0,
            "uses_3v3": False,
            "language": "Verilog",
            "top_module": "tt_um_test_project",
            "source_files": ["test.v"],
            "clock_hz": 10000000,
        },
        "pinout": {
            "ui[0]": "input_0",
            "ui[1]": "input_1",
            "ui[2]": "input_2",
            "ui[3]": "input_3",
            "ui[4]": "input_4",
            "ui[5]": "input_5",
            "ui[6]": "input_6",
            "ui[7]": "input_7",
            "uo[0]": "output_0",
            "uo[1]": "output_1",
            "uo[2]": "output_2",
            "uo[3]": "output_3",
            "uo[4]": "output_4",
            "uo[5]": "output_5",
            "uo[6]": "output_6",
            "uo[7]": "output_7",
            "uio[0]": "bidir_0",
            "uio[1]": "bidir_1",
            "uio[2]": "bidir_2",
            "uio[3]": "bidir_3",
            "uio[4]": "bidir_4",
            "uio[5]": "bidir_5",
            "uio[6]": "bidir_6",
            "uio[7]": "bidir_7",
        },
    }


@pytest.fixture
def tile_sizes():
    """Valid tile sizes for testing"""
    return {
        "1x1": "0 0 161 111.52",
        "1x2": "0 0 161 225.76",
        "2x2": "0 0 322 225.76",
        "8x2": "0 0 1292 225.76",
    }


class TestProjectInfoYamlVersion:
    """Test YAML version validation"""

    def test_missing_yaml_version(self, valid_yaml_data, tile_sizes):
        del valid_yaml_data["yaml_version"]
        with pytest.raises(ProjectYamlError, match="Missing 'yaml_version'"):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_wrong_yaml_version(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["yaml_version"] = YAML_VERSION - 1
        with pytest.raises(
            ProjectYamlError,
            match=f"Unsupported YAML version: {YAML_VERSION - 1}, expected {YAML_VERSION}",
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_valid_yaml_version(self, valid_yaml_data, tile_sizes):
        project_info = ProjectInfo(valid_yaml_data, tile_sizes)
        assert project_info is not None


class TestProjectInfoProjectSection:
    """Test project section validation"""

    def test_missing_project_section(self, valid_yaml_data, tile_sizes):
        del valid_yaml_data["project"]
        with pytest.raises(ProjectYamlError, match="Missing 'project' section"):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_missing_title(self, valid_yaml_data, tile_sizes):
        del valid_yaml_data["project"]["title"]
        with pytest.raises(
            ProjectYamlError, match="Missing key 'title' in 'project' section"
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_empty_title(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["title"] = ""
        with pytest.raises(ProjectYamlError, match="Project title cannot be empty"):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_missing_author(self, valid_yaml_data, tile_sizes):
        del valid_yaml_data["project"]["author"]
        with pytest.raises(
            ProjectYamlError, match="Missing key 'author' in 'project' section"
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_empty_author(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["author"] = ""
        with pytest.raises(ProjectYamlError, match="Project author cannot be empty"):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_missing_description(self, valid_yaml_data, tile_sizes):
        del valid_yaml_data["project"]["description"]
        with pytest.raises(
            ProjectYamlError, match="Missing key 'description' in 'project' section"
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_empty_description(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["description"] = ""
        with pytest.raises(
            ProjectYamlError, match="Project description cannot be empty"
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_missing_tiles(self, valid_yaml_data, tile_sizes):
        del valid_yaml_data["project"]["tiles"]
        with pytest.raises(
            ProjectYamlError, match="Missing key 'tiles' in 'project' section"
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_invalid_tiles(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["tiles"] = "invalid_size"
        with pytest.raises(
            ProjectYamlError,
            match="Invalid value for 'tiles' in 'project' section: invalid_size",
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_analog_pins_not_integer(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["analog_pins"] = "not_int"
        with pytest.raises(
            ProjectYamlError,
            match="Invalid value for 'analog_pins' in 'project' section, must be an integer",
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_analog_pins_negative(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["analog_pins"] = -1
        with pytest.raises(
            ProjectYamlError,
            match="Invalid value for 'analog_pins' in 'project' section, must be between 0 and 6",
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_analog_pins_too_high(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["analog_pins"] = 7
        with pytest.raises(
            ProjectYamlError,
            match="Invalid value for 'analog_pins' in 'project' section, must be between 0 and 6",
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_uses_3v3_without_analog_pins(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["uses_3v3"] = True
        valid_yaml_data["project"]["analog_pins"] = 0
        with pytest.raises(
            ProjectYamlError,
            match="Projects with 3v3 power need at least one analog pin",
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_missing_language(self, valid_yaml_data, tile_sizes):
        del valid_yaml_data["project"]["language"]
        with pytest.raises(
            ProjectYamlError, match="Missing key 'language' in 'project' section"
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_empty_language(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["language"] = ""
        with pytest.raises(ProjectYamlError, match="Project language cannot be empty"):
            ProjectInfo(valid_yaml_data, tile_sizes)


class TestProjectInfoWokwiLanguage:
    """Test Wokwi language specific validation"""

    def test_wokwi_missing_wokwi_id(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["language"] = "Wokwi"
        del valid_yaml_data["project"]["top_module"]
        del valid_yaml_data["project"]["source_files"]
        with pytest.raises(
            ProjectYamlError, match="Missing key 'wokwi_id' in 'project' section"
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_wokwi_empty_wokwi_id(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["language"] = "Wokwi"
        valid_yaml_data["project"]["wokwi_id"] = ""
        del valid_yaml_data["project"]["top_module"]
        del valid_yaml_data["project"]["source_files"]
        with pytest.raises(
            ProjectYamlError, match="Please provide a valid Wokwi project ID"
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_wokwi_zero_wokwi_id(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["language"] = "Wokwi"
        valid_yaml_data["project"]["wokwi_id"] = "0"
        del valid_yaml_data["project"]["top_module"]
        del valid_yaml_data["project"]["source_files"]
        with pytest.raises(
            ProjectYamlError, match="Please provide a valid Wokwi project ID"
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_wokwi_valid(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["language"] = "Wokwi"
        valid_yaml_data["project"]["wokwi_id"] = 123456789
        del valid_yaml_data["project"]["top_module"]
        del valid_yaml_data["project"]["source_files"]
        project_info = ProjectInfo(valid_yaml_data, tile_sizes)
        assert project_info.top_module == "tt_um_wokwi_123456789"
        assert project_info.source_files == ["tt_um_wokwi_123456789.v", "cells.v"]


class TestProjectInfoNonWokwiLanguage:
    """Test non-Wokwi language validation"""

    def test_missing_top_module(self, valid_yaml_data, tile_sizes):
        del valid_yaml_data["project"]["top_module"]
        with pytest.raises(
            ProjectYamlError, match="Missing key 'top_module' in 'project' section"
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_top_module_without_tt_um_prefix(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["top_module"] = "invalid_module"
        with pytest.raises(
            ProjectYamlError, match="Top module must start with 'tt_um_'"
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_missing_source_files(self, valid_yaml_data, tile_sizes):
        del valid_yaml_data["project"]["source_files"]
        with pytest.raises(
            ProjectYamlError, match="Missing key 'source_files' in 'project' section"
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_empty_source_files(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["source_files"] = []
        with pytest.raises(ProjectYamlError, match="No source files specified"):
            ProjectInfo(valid_yaml_data, tile_sizes)


class TestProjectInfoClockHz:
    """Test clock_hz validation"""

    def test_missing_clock_hz(self, valid_yaml_data, tile_sizes):
        del valid_yaml_data["project"]["clock_hz"]
        with pytest.raises(
            ProjectYamlError, match="Missing key 'clock_hz' in 'project' section"
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_clock_hz_not_integer(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["clock_hz"] = "not_int"
        with pytest.raises(
            ProjectYamlError,
            match="Invalid value for 'clock_hz' in 'project' section, must be an integer",
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)


class TestProjectInfoPinoutSection:
    """Test pinout section validation"""

    def test_missing_pinout_section(self, valid_yaml_data, tile_sizes):
        del valid_yaml_data["pinout"]
        with pytest.raises(ProjectYamlError, match="Missing 'pinout' section"):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_missing_ui_pin(self, valid_yaml_data, tile_sizes):
        del valid_yaml_data["pinout"]["ui[0]"]
        with pytest.raises(
            ProjectYamlError, match="Missing 'ui\\[0\\]' in 'pinout' section"
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_missing_uo_pin(self, valid_yaml_data, tile_sizes):
        del valid_yaml_data["pinout"]["uo[3]"]
        with pytest.raises(
            ProjectYamlError, match="Missing 'uo\\[3\\]' in 'pinout' section"
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_missing_uio_pin(self, valid_yaml_data, tile_sizes):
        del valid_yaml_data["pinout"]["uio[7]"]
        with pytest.raises(
            ProjectYamlError, match="Missing 'uio\\[7\\]' in 'pinout' section"
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_all_empty_pinout(self, valid_yaml_data, tile_sizes):
        for pin in valid_yaml_data["pinout"]:
            valid_yaml_data["pinout"][pin] = ""
        with pytest.raises(
            ProjectYamlError, match="Please fill in the 'pinout' section"
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_invalid_pinout_keys(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["pinout"]["invalid_key"] = "value"
        with pytest.raises(
            ProjectYamlError,
            match="Invalid keys \\['invalid_key'\\] in 'pinout' section. Please remove them.",
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_ua_pins_optional_when_not_analog(self, valid_yaml_data, tile_sizes):
        # ua pins should be optional when analog_pins is 0
        project_info = ProjectInfo(valid_yaml_data, tile_sizes)
        assert project_info.pinout.ua == []

    def test_ua_pins_required_when_analog(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["analog_pins"] = 2
        pinout = valid_yaml_data["pinout"]
        pinout["ua[0]"] = "analog_0"
        pinout["ua[1]"] = "analog_1"
        pinout["ua[2]"] = ""
        pinout["ua[3]"] = ""
        pinout["ua[4]"] = ""
        pinout["ua[5]"] = ""

        project_info = ProjectInfo(valid_yaml_data, tile_sizes)
        expected_ua = ["analog_0", "analog_1", "", "", "", ""]
        assert project_info.pinout.ua == expected_ua

    def test_missing_ua_pin_when_analog(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["analog_pins"] = 1
        # If ua[0] is present, but ua[1] is missing, it should fail
        valid_yaml_data["pinout"]["ua[0]"] = "analog_0"
        # Missing ua[1] should fail since ua[0] exists
        with pytest.raises(
            ProjectYamlError, match="Missing 'ua\\[1\\]' in 'pinout' section"
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_ua_pins_completely_optional(self, valid_yaml_data, tile_sizes):
        # If no ua[0] is present, then ua pins are completely optional
        valid_yaml_data["project"]["analog_pins"] = 2  # Even with analog_pins > 0
        project_info = ProjectInfo(valid_yaml_data, tile_sizes)
        assert project_info.pinout.ua == []


class TestProjectInfoValidCombinations:
    """Test valid combinations and edge cases"""

    def test_valid_analog_project(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["analog_pins"] = 2
        valid_yaml_data["project"]["uses_3v3"] = True
        # Include all required ua pins
        for i in range(6):
            valid_yaml_data["pinout"][f"ua[{i}]"] = f"analog_{i}" if i < 2 else ""

        project_info = ProjectInfo(valid_yaml_data, tile_sizes)
        assert project_info.analog_pins == 2
        assert project_info.is_analog is True
        assert project_info.uses_3v3 is True

    def test_valid_digital_project(self, valid_yaml_data, tile_sizes):
        project_info = ProjectInfo(valid_yaml_data, tile_sizes)
        assert project_info.analog_pins == 0
        assert project_info.is_analog is False
        assert project_info.uses_3v3 is False

    def test_optional_fields(self, valid_yaml_data, tile_sizes):
        # Test that optional fields work
        valid_yaml_data["project"]["discord"] = "test_discord"
        valid_yaml_data["project"]["doc_link"] = "https://example.com"

        project_info = ProjectInfo(valid_yaml_data, tile_sizes)
        assert project_info.discord == "test_discord"
        assert project_info.doc_link == "https://example.com"

    def test_default_analog_pins(self, valid_yaml_data, tile_sizes):
        # Test that analog_pins defaults to 0 when not specified
        del valid_yaml_data["project"]["analog_pins"]
        project_info = ProjectInfo(valid_yaml_data, tile_sizes)
        assert project_info.analog_pins == 0

    def test_default_uses_3v3(self, valid_yaml_data, tile_sizes):
        # Test that uses_3v3 defaults to False when not specified
        del valid_yaml_data["project"]["uses_3v3"]
        project_info = ProjectInfo(valid_yaml_data, tile_sizes)
        assert project_info.uses_3v3 is False

    def test_all_tile_sizes(self, valid_yaml_data, tile_sizes):
        # Test all valid tile sizes
        for tile_size in tile_sizes.keys():
            valid_yaml_data["project"]["tiles"] = tile_size
            project_info = ProjectInfo(valid_yaml_data, tile_sizes)
            assert project_info.tiles == tile_size

    def test_empty_pinout_descriptions_allowed(self, valid_yaml_data, tile_sizes):
        # Some pins can be empty (just not ALL pins)
        valid_yaml_data["pinout"]["ui[0]"] = ""
        valid_yaml_data["pinout"]["uo[0]"] = ""
        valid_yaml_data["pinout"]["uio[0]"] = ""

        project_info = ProjectInfo(valid_yaml_data, tile_sizes)
        assert project_info.pinout.ui[0] == ""
        assert project_info.pinout.uo[0] == ""
        assert project_info.pinout.uio[0] == ""


class TestProjectInfoIntegration:
    """Integration tests with real YAML files"""

    def test_load_from_yaml_string(self, tile_sizes):
        yaml_content = f"""
yaml_version: {YAML_VERSION}
project:
  title: "Integration Test"
  author: "Test Author"
  description: "Integration test description"
  tiles: "1x1"
  language: "Verilog"
  top_module: "tt_um_integration_test"
  source_files: ["integration_test.v"]
  clock_hz: 25000000
pinout:
  ui[0]: "clk"
  ui[1]: "rst_n"
  ui[2]: "enable"
  ui[3]: "data_in[0]"
  ui[4]: "data_in[1]"
  ui[5]: "data_in[2]"
  ui[6]: "data_in[3]"
  ui[7]: "unused"
  uo[0]: "data_out[0]"
  uo[1]: "data_out[1]"
  uo[2]: "data_out[2]"
  uo[3]: "data_out[3]"
  uo[4]: "valid"
  uo[5]: "ready"
  uo[6]: "error"
  uo[7]: "unused"
  uio[0]: "sda"
  uio[1]: "scl"
  uio[2]: "cs"
  uio[3]: "mosi"
  uio[4]: "miso"
  uio[5]: "sck"
  uio[6]: "interrupt"
  uio[7]: "debug"
"""
        yaml_data = yaml.safe_load(yaml_content)
        project_info = ProjectInfo(yaml_data, tile_sizes)

        assert project_info.title == "Integration Test"
        assert project_info.top_module == "tt_um_integration_test"
        assert project_info.clock_hz == 25000000
        assert len(project_info.source_files) == 1
        assert project_info.source_files[0] == "integration_test.v"

    def test_load_wokwi_from_yaml_string(self, tile_sizes):
        yaml_content = f"""
yaml_version: {YAML_VERSION}
project:
  title: "Wokwi Integration Test"
  author: "Wokwi User"
  description: "Wokwi integration test"
  tiles: "1x1"
  language: "Wokwi"
  wokwi_id: 987654321
  clock_hz: 10000000
pinout:
  ui[0]: "button_0"
  ui[1]: "button_1"
  ui[2]: "switch_0"
  ui[3]: "switch_1"
  ui[4]: "unused"
  ui[5]: "unused"
  ui[6]: "unused"
  ui[7]: "unused"
  uo[0]: "led_0"
  uo[1]: "led_1"
  uo[2]: "led_2"
  uo[3]: "led_3"
  uo[4]: "segment_a"
  uo[5]: "segment_b"
  uo[6]: "segment_c"
  uo[7]: "segment_d"
  uio[0]: "unused"
  uio[1]: "unused"
  uio[2]: "unused"
  uio[3]: "unused"
  uio[4]: "unused"
  uio[5]: "unused"
  uio[6]: "unused"
  uio[7]: "unused"
"""
        yaml_data = yaml.safe_load(yaml_content)
        project_info = ProjectInfo(yaml_data, tile_sizes)

        assert project_info.title == "Wokwi Integration Test"
        assert project_info.top_module == "tt_um_wokwi_987654321"
        assert project_info.source_files == ["tt_um_wokwi_987654321.v", "cells.v"]
        assert hasattr(project_info, "wokwi_id")
        assert project_info.wokwi_id == 987654321
