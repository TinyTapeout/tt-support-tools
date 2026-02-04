import os
import sys

from project_info import ProjectInfo, ProjectYamlError


def check_info_md(project_dir: str) -> list[str]:
    info_md = os.path.join(project_dir, "docs/info.md")
    if not os.path.exists(info_md):
        return ["Missing docs/info.md file"]

    with open(info_md) as fh:
        info_md_content = fh.read()

    errors = []
    if "# How it works\n\nExplain how your project works" in info_md_content:
        errors += ["Missing 'How it works' section in docs/info.md"]

    if "# How to test\n\nExplain how to use your project" in info_md_content:
        errors += ["Missing 'How to test' section in docs/info.md"]

    return errors


def check_info_yaml(project_dir: str, pdk: str) -> list[str]:
    import yaml

    info_yaml = os.path.join(project_dir, "info.yaml")
    if not os.path.exists(info_yaml):
        return ["Missing info.yaml file"]

    with open(info_yaml) as fh:
        try:
            yaml_data = yaml.safe_load(fh)
        except yaml.YAMLError as e:
            return [f"Error parsing info.yaml: {e}"]

    tile_sizes_yaml = f"tech/{pdk}/tile_sizes.yaml"
    tt_tools_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(tt_tools_dir, tile_sizes_yaml), "r") as f:
        tile_sizes = yaml.safe_load(f)

    try:
        _ = ProjectInfo(yaml_data, tile_sizes, require_pinout=True)
    except Exception as e:
        if isinstance(e, ProjectYamlError):
            return e.errors

    return []  # No errors


def check_project_docs(project_dir: str, pdk: str) -> None:
    info_md_errors = check_info_md(project_dir)
    info_yaml_errors = check_info_yaml(project_dir, pdk)
    errors = info_md_errors + info_yaml_errors
    if errors:
        if info_yaml_errors:
            print("## Errors in info.yaml")
            for error in info_yaml_errors:
                print(f"- {error}")
            print()
        if info_md_errors:
            print("## Errors in docs/info.md")
            for error in info_md_errors:
                print(f"- {error}")
            print()
        sys.exit(1)
    else:
        print("Documentation check passed successfully.")
