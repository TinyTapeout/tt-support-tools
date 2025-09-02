from typing import Any, Dict, List, Optional

YAML_VERSION = 6


class ProjectYamlError(Exception):
    pass


class PinoutSection:
    def __init__(self, yaml_data: Dict[str, Any]):
        self.__nonEmptyPins = 0
        yaml_data = yaml_data.copy()
        self.ui = self._pins(yaml_data, "ui", 8)
        self.uo = self._pins(yaml_data, "uo", 8)
        self.uio = self._pins(yaml_data, "uio", 8)
        self.ua = self._pins(yaml_data, "ua", 6, True)
        if self.__nonEmptyPins == 0:
            raise ProjectYamlError("Please fill in the 'pinout' section")
        if len(yaml_data) > 0:
            raise ProjectYamlError(
                f"Invalid keys {list(yaml_data.keys())} in 'pinout' section. Please remove them."
            )

    def _pins(
        self, yaml_data: Dict[str, Any], name: str, count: int, optional: bool = False
    ) -> List[str]:
        result: List[str] = []
        for i in range(count):
            key = f"{name}[{i}]"
            pin = yaml_data.get(key)
            if pin is None:
                if optional and i == 0:
                    break
                raise ProjectYamlError(f"Missing '{name}[{i}]' in 'pinout' section")
            if pin != "":
                self.__nonEmptyPins += 1
            result.append(pin)
            del yaml_data[key]
        return result


class ProjectInfo:
    top_module: str
    source_files: List[str]

    def __init__(self, yaml_data: Dict[str, Any], tile_sizes: Dict[str, str]):
        # Validate Version
        yaml_version = yaml_data.get("yaml_version")
        if yaml_version is None:
            raise ProjectYamlError("Missing 'yaml_version'")
        if yaml_version != YAML_VERSION:
            raise ProjectYamlError(
                f"Unsupported YAML version: {yaml_data['yaml_version']}, expected {YAML_VERSION}"
            )

        # Read "project" Section
        project_section: Optional[Dict[str, Any]] = yaml_data.get("project")
        if project_section is None:
            raise ProjectYamlError("Missing 'project' section")

        title = project_section.get("title")
        if title is None:
            raise ProjectYamlError("Missing key 'title' in 'project' section")
        if title == "":
            raise ProjectYamlError("Project title cannot be empty")
        self.title: str = title

        author = project_section.get("author")
        if author is None:
            raise ProjectYamlError("Missing key 'author' in 'project' section")
        if author == "":
            raise ProjectYamlError("Project author cannot be empty")
        self.author: str = author

        description = project_section.get("description")
        if description is None:
            raise ProjectYamlError("Missing key 'description' in 'project' section")
        if description == "":
            raise ProjectYamlError("Project description cannot be empty")
        self.description: str = description

        tiles = project_section.get("tiles")
        if tiles is None:
            raise ProjectYamlError("Missing key 'tiles' in 'project' section")
        if tiles not in tile_sizes.keys():
            raise ProjectYamlError(
                f"Invalid value for 'tiles' in 'project' section: {tiles}"
            )
        self.tiles: str = tiles

        analog_pins = project_section.get("analog_pins", 0)
        if not isinstance(analog_pins, int):
            raise ProjectYamlError(
                "Invalid value for 'analog_pins' in 'project' section, must be an integer"
            )
        if analog_pins < 0 or analog_pins > 6:
            raise ProjectYamlError(
                "Invalid value for 'analog_pins' in 'project' section, must be between 0 and 6"
            )
        self.analog_pins: int = analog_pins
        self.is_analog: bool = self.analog_pins > 0

        self.uses_3v3: bool = project_section.get("uses_3v3", False)
        if self.uses_3v3 and not self.is_analog:
            raise ProjectYamlError(
                "Projects with 3v3 power need at least one analog pin"
            )

        language = project_section.get("language")
        if language is None:
            raise ProjectYamlError("Missing key 'language' in 'project' section")
        if language == "":
            raise ProjectYamlError("Project language cannot be empty")
        self.language: str = language

        if language == "Wokwi":
            wokwi_id = project_section.get("wokwi_id")
            if wokwi_id is None:
                raise ProjectYamlError("Missing key 'wokwi_id' in 'project' section")
            if wokwi_id == "" or wokwi_id == "0":
                raise ProjectYamlError("Please provide a valid Wokwi project ID")
            self.wokwi_id: Optional[int] = wokwi_id
            self.top_module = f"tt_um_wokwi_{wokwi_id}"
            self.source_files = [f"tt_um_wokwi_{self.wokwi_id}.v", f"cells.v"]
        else:
            top_module = project_section.get("top_module")
            if top_module is None:
                raise ProjectYamlError("Missing key 'top_module' in 'project' section")
            if not top_module.startswith("tt_um_"):
                raise ProjectYamlError(
                    "Top module must start with 'tt_um_' (e.g. tt_um_my_project)"
                )
            self.top_module = top_module

            if "source_files" not in project_section:
                raise ProjectYamlError(
                    "Missing key 'source_files' in 'project' section"
                )
            if len(project_section["source_files"]) == 0:
                raise ProjectYamlError("No source files specified")
            self.source_files = project_section["source_files"]

        if "clock_hz" not in project_section:
            raise ProjectYamlError("Missing key 'clock_hz' in 'project' section")
        if not isinstance(project_section["clock_hz"], int):
            raise ProjectYamlError(
                "Invalid value for 'clock_hz' in 'project' section, must be an integer"
            )
        self.clock_hz: int = project_section["clock_hz"]

        if "pinout" not in yaml_data:
            raise ProjectYamlError("Missing 'pinout' section")
        self.pinout = PinoutSection(yaml_data["pinout"])

        self.discord: Optional[str] = project_section.get("discord")
        self.doc_link: Optional[str] = project_section.get("doc_link")
