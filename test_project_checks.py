import pytest

from project_checks import check_info_yaml

HEADER = """\
yaml_version: 6
project:
  title: Test Project
  author: Test Author
  description: Test Description
  tiles: 1x1
  language: Verilog
  top_module: tt_um_test_project
  source_files:
    - test.v
  clock_hz: 10000000
pinout:
"""
PINS = "".join(
    f"  {prefix}[{i}]: \"{'sig' if (prefix, i) == ('ui', 0) else ''}\"\n"
    for prefix in ("ui", "uo", "uio")
    for i in range(8)
)
VALID_INFO_YAML = HEADER + PINS


def write_info_yaml(tmp_path, content):
    (tmp_path / "info.yaml").write_text(content)
    return str(tmp_path)


def test_valid_info_yaml(tmp_path):
    assert check_info_yaml(write_info_yaml(tmp_path, VALID_INFO_YAML), "sky130A") == []


def test_validation_errors_are_reported(tmp_path):
    content = VALID_INFO_YAML.replace("title: Test Project", "title: ''")
    errors = check_info_yaml(write_info_yaml(tmp_path, content), "sky130A")
    assert errors == ["Project title cannot be empty"]


@pytest.mark.parametrize(
    "content",
    [
        "",
        "- just\n- a list\n",
        VALID_INFO_YAML.replace("    - test.v\n", ""),
        VALID_INFO_YAML.replace("top_module: tt_um_test_project", "top_module: 1"),
        HEADER,
    ],
    ids=[
        "empty",
        "not-a-mapping",
        "empty-source-files",
        "top-module-int",
        "empty-pinout",
    ],
)
def test_malformed_info_yaml_is_an_error(tmp_path, content):
    errors = check_info_yaml(write_info_yaml(tmp_path, content), "sky130A")
    assert errors
