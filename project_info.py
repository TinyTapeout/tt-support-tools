from typing import Any, Dict, List, Optional

YAML_VERSION = 6


class ProjectYamlError(Exception):
    def __init__(self, errors: List[str]):
        if isinstance(errors, str):
            errors = [errors]
        self.errors = errors
        super().__init__(", ".join(errors))


class PinoutSection:
    def __init__(
        self, yaml_data: Dict[str, Any], errors: List[str], require_pinout: bool = False
    ):
        self.__nonEmptyPins = 0
        yaml_data = yaml_data.copy()
        self.ui = self._pins(yaml_data, "ui", 8, errors)
        self.uo = self._pins(yaml_data, "uo", 8, errors)
        self.uio = self._pins(yaml_data, "uio", 8, errors)
        self.ua = self._pins(yaml_data, "ua", 6, errors, True)
        if require_pinout and self.__nonEmptyPins == 0:
            errors.append("Please fill in the 'pinout' section")
        if len(yaml_data) > 0:
            errors.append(
                f"Invalid keys {list(yaml_data.keys())} in 'pinout' section. Please remove them."
            )

    def _pins(
        self,
        yaml_data: Dict[str, Any],
        name: str,
        count: int,
        errors: List[str],
        optional: bool = False,
    ) -> List[str]:
        result: List[str] = []
        for i in range(count):
            key = f"{name}[{i}]"
            pin = yaml_data.get(key)
            if pin is None:
                if optional and i == 0:
                    break
                errors.append(f"Missing '{name}[{i}]' in 'pinout' section")
                # Continue to collect more errors
                continue
            if pin != "":
                self.__nonEmptyPins += 1
            result.append(pin)
            del yaml_data[key]
        return result


class ProjectInfo:
    top_module: str
    source_files: List[str]

    def __init__(
        self,
        yaml_data: Dict[str, Any],
        tile_sizes: Dict[str, str],
        require_pinout: bool = False,
    ):
        errors: List[str] = []

        # Validate Version
        yaml_version = yaml_data.get("yaml_version")
        if yaml_version is None:
            errors.append("Missing 'yaml_version'")
        elif yaml_version != YAML_VERSION:
            errors.append(
                f"Unsupported YAML version: {yaml_data['yaml_version']}, expected {YAML_VERSION}"
            )

        # Read "project" Section
        project_section: Optional[Dict[str, Any]] = yaml_data.get("project")
        if project_section is None:
            errors.append("Missing 'project' section")
            # Can't continue without project section
            raise ProjectYamlError(errors)

        # Validate all required fields in project section
        title = project_section.get("title")
        if title is None:
            errors.append("Missing key 'title' in 'project' section")
        elif title == "":
            errors.append("Project title cannot be empty")
        else:
            self.title: str = title

        author = project_section.get("author")
        if author is None:
            errors.append("Missing key 'author' in 'project' section")
        elif author == "":
            errors.append("Project author cannot be empty")
        else:
            self.author: str = author

        description = project_section.get("description")
        if description is None:
            errors.append("Missing key 'description' in 'project' section")
        elif description == "":
            errors.append("Project description cannot be empty")
        else:
            self.description: str = description

        tiles = project_section.get("tiles")
        if tiles is None:
            errors.append("Missing key 'tiles' in 'project' section")
        elif tiles not in tile_sizes.keys():
            errors.append(f"Invalid value for 'tiles' in 'project' section: {tiles}")
        else:
            self.tiles: str = tiles

        analog_pins = project_section.get("analog_pins", 0)
        if not isinstance(analog_pins, int):
            errors.append(
                "Invalid value for 'analog_pins' in 'project' section, must be an integer"
            )
            analog_pins = 0  # Set default for further validation
        elif analog_pins < 0 or analog_pins > 6:
            errors.append(
                "Invalid value for 'analog_pins' in 'project' section, must be between 0 and 6"
            )
            analog_pins = 0  # Set default for further validation
        self.analog_pins: int = analog_pins
        self.is_analog: bool = self.analog_pins > 0

        uses_3v3: bool = project_section.get("uses_3v3", False)
        self.uses_3v3: bool = uses_3v3
        if uses_3v3 and not self.is_analog:
            errors.append("Projects with 3v3 power need at least one analog pin")

        language = project_section.get("language")
        if language is None:
            errors.append("Missing key 'language' in 'project' section")
            language = ""  # Set default for further validation
        elif language == "":
            errors.append("Project language cannot be empty")
        else:
            self.language: str = language

        # Language-specific validation
        if language == "Wokwi":
            wokwi_id = project_section.get("wokwi_id")
            if wokwi_id is None:
                errors.append("Missing key 'wokwi_id' in 'project' section")
            elif wokwi_id == "" or wokwi_id == "0":
                errors.append("Please provide a valid Wokwi project ID")
            else:
                self.wokwi_id: Optional[int] = wokwi_id
                self.top_module = f"tt_um_wokwi_{wokwi_id}"
                self.source_files = [f"tt_um_wokwi_{self.wokwi_id}.v", f"cells.v"]
        elif language != "":
            # Only validate these if language is not empty (error already added above)
            top_module = project_section.get("top_module")
            if top_module is None:
                errors.append("Missing key 'top_module' in 'project' section")
            elif not top_module.startswith("tt_um_"):
                errors.append(
                    "Top module must start with 'tt_um_' (e.g. tt_um_my_project)"
                )
            else:
                self.top_module = top_module

            if "source_files" not in project_section:
                errors.append("Missing key 'source_files' in 'project' section")
            elif len(project_section["source_files"]) == 0:
                errors.append("No source files specified")
            else:
                self.source_files = project_section["source_files"]

        # Validate clock_hz
        if "clock_hz" not in project_section:
            errors.append("Missing key 'clock_hz' in 'project' section")
        elif not isinstance(project_section["clock_hz"], int):
            errors.append(
                "Invalid value for 'clock_hz' in 'project' section, must be an integer"
            )
        else:
            self.clock_hz: int = project_section["clock_hz"]

        # Validate pinout section
        if "pinout" not in yaml_data:
            errors.append("Missing 'pinout' section")
        else:
            self.pinout = PinoutSection(yaml_data["pinout"], errors, require_pinout)

        # Optional fields
        self.discord: Optional[str] = project_section.get("discord")
        self.doc_link: Optional[str] = project_section.get("doc_link")

        # Raise all errors if any were collected
        if errors:
            raise ProjectYamlError(errors)
