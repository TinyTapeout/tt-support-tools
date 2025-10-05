import logging
import os
import re
import subprocess
from typing import Optional

import chevron
import matplotlib as mpl


class DocsHelper:
    @staticmethod
    def pretty_address(address: int, subtile_address: Optional[int] = None) -> str:
        """
        Format the address and subtile address (if applicable) into an nice string for the typst template
        """
        content = str(address).rjust(4, "-")
        if subtile_address is not None:
            content += f"/{subtile_address}"
        return content

    @staticmethod
    def pretty_clock(clock: int) -> str:
        """
        Format the clock with engineering notation
        """
        if clock == 0:
            return "No Clock"
        else:
            formatter = mpl.ticker.EngFormatter(sep=" ")
            # [clock, SI suffix]
            hz_as_eng = formatter(clock).split(" ")

        if len(hz_as_eng) == 2:
            return f"{hz_as_eng[0]} {hz_as_eng[1]}Hz"
        elif len(hz_as_eng) == 1:
            return f"{hz_as_eng[0]} Hz"
        else:
            raise RuntimeError(
                "unexpected amount of entries when formatting clock for datasheet"
            )

    @staticmethod
    def format_authors(authors: str) -> str:
        """
        Format the authors properly

        Split the authors with a set of delimiters, then repackage as a typst array for the template
        """
        split_authors = re.split(r"[,|;|+]| and | & ", authors)
        formatted_authors = []
        for author in split_authors:
            stripped = author.strip()
            if stripped == "":
                continue

            # typst needs a trailing comma if len(array) == 1, so that it doesn't interpret it as an expression
            # https://typst.app/docs/reference/foundations/array/
            formatted_authors.append(f'"{stripped}",')
        return "".join(formatted_authors)

    @staticmethod
    def _escape_characters_in_content(text: str) -> str:
        """
        Helper function to escape certain characters in content blocks
        """
        return text.replace("[", "\\[").replace("]", "\\]").replace("/", "\\/")

    @staticmethod
    def format_digital_pins(pins: dict) -> str:
        """
        Iterate through and create the digital pin table as a string
        """
        pin_table = ""
        for pin in pins:
            ui_text = DocsHelper._escape_characters_in_content(pin["ui"])
            uo_text = DocsHelper._escape_characters_in_content(pin["uo"])
            uio_text = DocsHelper._escape_characters_in_content(pin["uio"])
            pin_table += (
                f"[`{pin['pin_index']}`], [{ui_text}], [{uo_text}], [{uio_text}],\n"
            )

        return pin_table

    @staticmethod
    def format_analog_pins(pins: dict):
        """
        Iterate through and create the analog pin table as a string
        """
        pin_table = ""
        for pin in pins:
            desc_text = DocsHelper._escape_characters_in_content(pin["desc"])
            pin_table += (
                f"[`{pin['ua_index']}`], [`{pin['analog_index']}`], [{desc_text}],\n"
            )
        return pin_table

    @staticmethod
    def get_docs_as_typst(path: str) -> str:
        """
        Run pandoc to convert a given file to typst
        """
        pandoc_command = [
            "pandoc",
            path,
            "--shift-heading-level-by=-1",
            "-f",
            "markdown-auto_identifiers",
            "-t",
            "typst",
            "--columns=120",
        ]
        logging.info(pandoc_command)

        result = subprocess.run(pandoc_command, capture_output=True)

        if result.stderr != b"":
            logging.warning(result.stderr.decode())

        return result.stdout.decode()

    @staticmethod
    def get_project_type(language: str, is_wokwi: bool, is_analog: bool) -> str:
        if is_wokwi:
            return "Wokwi"
        elif is_analog:
            return "Analog"
        else:
            return "HDL"

    @staticmethod
    def format_project_info(yaml_info: dict, index_info: dict) -> dict:
        """
        Merge two sources of project information into one dictionary

        Accepts `info.yaml` from the project root, and project information from the tapeout index.
        Using these two sources, the function will pick and merge the required information for the datasheet.
        """
        info = {
            "title": yaml_info["project"]["title"],
            "author": yaml_info["project"]["author"],
            "description": yaml_info["project"]["description"],
            "address": index_info["address"],
            "clock_hz": index_info["clock_hz"],
            "git_url": index_info["repo"],
            "language": yaml_info["project"]["language"],
            "macro": index_info["macro"],
            "is_analog": len(index_info["analog_pins"]) > 0,
            "is_wokwi": True if "wokwi_id" in yaml_info["project"] else False,
            "type": "project",
        }

        if info["is_wokwi"]:
            info["wokwi_id"] = yaml_info["project"]["wokwi_id"]

        try:
            info["pins"] = [
                {
                    "pin_index": str(i),
                    "ui": index_info["pinout"][f"ui[{i}]"],
                    "uo": index_info["pinout"][f"uo[{i}]"],
                    "uio": index_info["pinout"][f"uio[{i}]"],
                }
                for i in range(8)
            ]
        except KeyError as e:
            logging.info(
                f"project is missing a pin entry ({e}), falling back to info.yaml (is this a subtile?)"
            )

            info["pins"] = [
                {
                    "pin_index": str(i),
                    "ui": yaml_info["pinout"][f"ui[{i}]"],
                    "uo": yaml_info["pinout"][f"uo[{i}]"],
                    "uio": yaml_info["pinout"][f"uio[{i}]"],
                }
                for i in range(8)
            ]

        if info["is_analog"]:
            info["analog_pins"] = [
                {
                    "ua_index": str(i),
                    "analog_index": index_info["analog_pins"][i],
                    "desc": index_info["pinout"][f"ua[{i}]"],
                }
                for i in range(len(index_info["analog_pins"]))
            ]

        if "type" in index_info:
            if index_info["type"] == "subtile":
                info["type"] = "subtile"
                info["subtile_addr"] = index_info["subtile_addr"]
                info["subtile_group"] = index_info["subtile_group"]
            elif index_info["type"] == "group":
                info["type"] = "group"

        return info

    @staticmethod
    def normalise_project_info(project) -> dict:
        """
        Similar to `DocHelper.format_project_info`, but this accepts a `Project` object and attempts to
        normalise it to the tapeout index format that is expected by the `Docs.build_datasheet()` function.

        To help visualise it, the output of this function would be fed to the `index_info` parameter of
        the `DocsHelper.format_project_info()`.
        """
        info = {
            "title": project.info.title,
            "author": project.info.author,
            "description": project.info.description,
            "address": project.mux_address,
            "clock_hz": project.info.clock_hz,
            "repo": project.git_url,
            "language": project.info.language,
            "macro": project.info.top_module,
            "is_analog": project.info.is_analog,
            "is_wokwi": project.is_wokwi(),
            "type": "project",
        }

        if project.is_wokwi():
            info["wokwi_id"] = project.info.wokwi_id

        info["pinout"] = {}
        for i in range(8):
            info["pinout"].update({f"ui[{i}]": project.info.pinout.ui[i]})
            info["pinout"].update({f"uo[{i}]": project.info.pinout.uo[i]})
            info["pinout"].update({f"uio[{i}]": project.info.pinout.uio[i]})

        if project.info.is_analog:
            info["analog_pins"] = project.analog_pins
            for i, desc in enumerate(project.info.pinout.ua):
                info["pinout"].update({f"ua[{i}]": desc})
        else:
            info["analog_pins"] = []

        return info

    @staticmethod
    def write_doc(path: str, template: str, content: dict) -> None:
        try:
            with open(path, "w") as f:
                f.write(chevron.render(template, content))
        except FileNotFoundError:
            logging.warning(
                f"unable to write to {path}... the project exists in tapeout index, but not in local directory? skipping"
            )

    @staticmethod
    def populate_template_tags(
        info: dict, danger_info: dict, docs: str, template_version="1.0.0"
    ) -> dict:
        """
        Populate the required template fields given information about the project and its danger level
        """
        content = {
            "template-version": template_version,
            "project-title": info["title"].replace('"', '\\"'),
            "project-author": f"({DocsHelper.format_authors(info['author'])})",
            "project-repo-link": info["git_url"],
            "project-description": info["description"],
            "project-address": DocsHelper.pretty_address(info["address"]),
            "project-clock": DocsHelper.pretty_clock(info["clock_hz"]),
            "project-type": DocsHelper.get_project_type(
                info["language"], info["is_wokwi"], info["is_analog"]
            ),
            "project-doc-body": docs,
            "digital-pins": DocsHelper.format_digital_pins(info["pins"]),
        }

        if info["macro"] in danger_info:
            content["is-dangerous"] = True
            content["project-danger-level"] = danger_info[info["macro"]]["level"]
            content["project-danger-reason"] = danger_info[info["macro"]]["reason"]

        if info["type"] == "subtile":
            content["project-address"] = DocsHelper.pretty_address(
                info["address"], info["subtile_addr"]
            )

        if info["is_wokwi"]:
            content["is-wokwi"] = True
            content["project-wokwi-id"] = info["wokwi_id"]

        return content

    @staticmethod
    def configure_datasheet(
        shuttle_config: dict, datasheet_template: str, template_version: str = "1.0.0"
    ) -> None:
        """
        Prepare the datasheet.typ file with info from `config.yaml`

        The following keys can be used to configure the datasheet:
        - `pinout`: set what pinout table is shown in multiplexer chapter (caravel or openframe)
        - `theme_override_colour`: set a custom colour for the datasheet (rgb object)
        - `show_chip_viewer`*: toggle the chip viewer QR code (boolean)
        - `link_disable_colour`: disable link colouring (boolean)
        - `link_override_colour`: set a custom link colour (rgb object)
        - `qrcode_follows_theme`: colour template-generated QR codes with the main theme colour (boolean)
        - `include`*: a list of additional `.typ` files to include - they are copied into the body of `datasheet.typ`

        The keys correspond to the arguments available in the template, except those marked with an asterisk.

        Example usage (in `config.yaml`):
        ```yaml
        datasheet_config:
            pinout: caravel
            theme_override_colour: tt.colours.THEME_TT06_PINK
            link_override_colour: rgb("#a5415c")
            include:
                - doc/chip_map.typ
                - doc/funding.typ
        ```

        There are other keys which are *not* used to configure the datasheet, but instead control the content of it:
        - `disabled`: a list of projects which are excluded from the datasheet, mainly due to compilation issues
        - `artwork`: a list of key pairs that specify which artwork is added in the projects section (order sensitive)

        The `artwork` key pairs consist of an `ID` and a `rotate` value that specify which image to use and its rotation:
        ```yaml
        datasheet_config:
            disabled:
                - tt_um_project_1
                - tt_um_project_2
            artwork:
                - {id: photo1, rotate: 90deg}
                - {id: photo2, rotate: -90deg}
        ```
        """
        logging.info("configuring datasheet.typ")
        content = {
            "template-version": template_version,
            # the template already prefixes "Tiny Tapeout" to shuttle name, so remove it here
            "shuttle-pretty-name": shuttle_config["name"].replace("Tiny Tapeout ", ""),
            "shuttle-id": shuttle_config["id"],
            "if-chip-viewer": True,
            # themeing
            "qrcode-follows-theme": "false",
            "link-disable-colour": "false",
        }

        # get repo link
        git_repo_link_cmd = ["git", "config", "--get", "remote.origin.url"]
        logging.info(git_repo_link_cmd)
        result = subprocess.run(git_repo_link_cmd, capture_output=True)
        git_repo_link = result.stdout.decode().strip()
        content["repo-link"] = git_repo_link

        if "datasheet_config" in shuttle_config:
            datasheet_config = shuttle_config["datasheet_config"]

            if datasheet_config is None:
                logging.warning(
                    "datasheet config specified in config.yaml but has no entries"
                )
            else:

                if "pinout" in datasheet_config:
                    content["if-pinout"] = True
                    content["pinout"] = shuttle_config["datasheet_config"]["pinout"]

                if "theme_override_colour" in datasheet_config:
                    content["if-theme-override-colour"] = True
                    content["theme-override-colour"] = datasheet_config[
                        "theme_override_colour"
                    ]

                if "show_chip_viewer" in datasheet_config:
                    content["if-chip-viewer"] = datasheet_config["show_chip_viewer"]

                if "link_disable_colour" in datasheet_config:
                    # convert to string and lowercase because python "False" != typst "false"
                    content["link-disable-colour"] = str(
                        datasheet_config["link_disable_colour"]
                    ).lower()

                if "link_override_colour" in datasheet_config:
                    content["if-link-override-colour"] = True
                    content["link-override-colour"] = datasheet_config[
                        "link_override_colour"
                    ]

                if "qrcode_follows_theme" in datasheet_config:
                    content["qrcode-follows-theme"] = str(
                        datasheet_config["qrcode_follows_theme"]
                    ).lower()

                if "include" in datasheet_config:
                    doc_body = []
                    for path in datasheet_config["include"]:
                        logging.info(f"including {os.path.abspath(path)}")

                        with open(os.path.abspath(path)) as f:
                            doc_body.append(f.read())

                    content["datasheet-body"] = "\n".join(doc_body)

        with open("datasheet.typ", "w") as f:
            logging.info("writing datasheet.typ")
            f.write(chevron.render(datasheet_template, content))
