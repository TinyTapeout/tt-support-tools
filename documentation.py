import logging
import os
import subprocess
import json
import math
from typing import List, Optional

import chevron
import frontmatter  # type: ignore
import git  # type: ignore
import yaml

from config import Config
from git_utils import get_first_remote
from markdown_utils import rewrite_image_paths
from project import Project
from doc_utils import DocsHelper

class Docs:
    def __init__(self, config: Config, projects: List[Project]):
        self.config = config
        self.projects = projects
        self.script_dir = os.path.dirname(os.path.realpath(__file__))

    # stuff related to docs
    def build_index(self, filename: str = "shuttle_index.md"):
        logging.info(f"building {filename}")
        repo = git.Repo(".")
        readme = self.load_doc_template("shuttle_index_header.md.mustache")
        with open(filename, "w") as fh:
            fh.write(
                chevron.render(
                    readme,
                    {
                        "name": self.config["name"],
                        "git_repo": get_first_remote(repo),
                        "git_commit": repo.head.commit.hexsha,
                    },
                )
            )
            fh.write("| Address | Author | Title | Type | Git Repo |\n")
            fh.write("| ------- | ------ | ------| -----| ---------|\n")
            self.projects.sort(key=lambda x: x.mux_address)
            for project in self.projects:
                fh.write(project.get_index_row())

    def update_image(self):
        ruby = os.path.join(self.script_dir, "caravel_template", "dump_pic.rb")
        klayoutrc = os.path.join(self.script_dir, "caravel_template", "klayoutrc")
        lyp = os.path.join(self.script_dir, "caravel_template", "caravel.lyp")
        cmd = f"klayout -l {lyp} gds/user_project_wrapper.gds* -r {ruby} -c {klayoutrc}"
        logging.info(cmd)
        os.system(cmd)

    def load_doc_template(self, name: str) -> str:
        root = os.path.join(self.script_dir, "docs")
        doc_path = os.path.join(root, name)
        image_root = os.path.relpath(os.path.dirname(doc_path), ".")
        doc = frontmatter.load(doc_path)
        doc.content = rewrite_image_paths(doc.content, image_root)
        if "title" in doc:
            doc["title"] = rewrite_image_paths(doc["title"], image_root)
        if len(doc.keys()) > 0:
            return frontmatter.dumps(doc) + "\n"
        else:
            return doc.content + "\n"

    def write_datasheet(self, markdown_file: str, pdf_file: Optional[str] = None):
        doc_header = self.load_doc_template("doc_header.md.mustache")
        doc_chip_map = self.load_doc_template("../../docs/chip_map.md")
        doc_template = self.load_doc_template("doc_template.md.mustache")
        doc_pinout = self.load_doc_template("PINOUT.md")
        doc_info = self.load_doc_template("../../tt-multiplexer/docs/INFO.md")
        doc_credits = self.load_doc_template("CREDITS.md")

        with open(markdown_file, "w") as fh:
            repo = git.Repo(".")
            fh.write(
                chevron.render(
                    doc_header,
                    {
                        "name": self.config["name"],
                        "repo": get_first_remote(repo),
                    },
                )
            )
            fh.write(doc_chip_map)
            fh.write("# Projects\n")

            self.projects.sort(key=lambda x: x.mux_address)

            for project in self.projects:
                yaml_data = project.get_project_docs_dict()
                analog_pins = project.info.analog_pins
                yaml_data.update(
                    {
                        "user_docs": rewrite_image_paths(
                            yaml_data["user_docs"],
                            f"projects/{project.get_macro_name()}/docs",
                        ),
                        "mux_address": project.mux_address,
                        "pins": [
                            {
                                "pin_index": str(i),
                                "ui": project.info.pinout.ui[i],
                                "uo": project.info.pinout.uo[i],
                                "uio": project.info.pinout.uio[i],
                            }
                            for i in range(8)
                        ],
                        "analog_pins": [
                            {
                                "ua_index": str(i),
                                "analog_index": str(project.analog_pins[i]),
                                "desc": desc,
                            }
                            for i, desc in enumerate(
                                project.info.pinout.ua[:analog_pins]
                            )
                        ],
                        "is_analog": analog_pins > 0,
                    }
                )

                logging.info(f"building datasheet for {project}")

                # ensure that optional fields are set
                for key in [
                    "author",
                    "description",
                    "clock_hz",
                    "git_url",
                    "doc_link",
                ]:
                    if key not in yaml_data:
                        yaml_data[key] = ""

                # now build the doc & print it
                try:
                    doc = chevron.render(doc_template, yaml_data)
                    fh.write(doc)
                    fh.write("\n```{=latex}\n\\clearpage\n```\n")
                except IndexError:
                    logging.warning("missing pins in info.yaml, skipping")

            # ending
            fh.write(doc_pinout)
            fh.write("\n```{=latex}\n\\clearpage\n```\n")
            fh.write(doc_info)
            fh.write("\n```{=latex}\n\\clearpage\n```\n")
            fh.write(doc_credits)

        logging.info(f"wrote markdown to {markdown_file}")

        if pdf_file is not None:
            pdf_cmd = f"pandoc --toc --toc-depth 2 --pdf-engine=xelatex -i {markdown_file} -o {pdf_file} --from gfm+raw_attribute+smart+attributes"
            logging.info(pdf_cmd)
            p = subprocess.run(pdf_cmd, shell=True)
            if p.returncode != 0:
                logging.error("pdf generation failed")
                raise RuntimeError(f"pdf generation failed with code {p.returncode}")
            
    def build_datasheet(self, template_version: str, tapeout_index_path: str, datasheet_content_config_path: str):
        self.projects.sort(key=lambda x: x.mux_address)

        logging.info(f"building datasheet with version {template_version}")
        logging.info(f"tapeout index available? {True if tapeout_index_path != None else False}")
        logging.info(f"content config available? {True if datasheet_content_config_path != None else False}")

        tapeout_index = None
        # if given a path but the file doesn't exist
        if tapeout_index_path != None and not os.path.isfile(tapeout_index_path):
            raise FileNotFoundError("unable to find tapeout index at given path")
        # if given a path but it does exist
        elif tapeout_index_path != None:
            with open(os.path.abspath(tapeout_index_path), "r") as f:
                tapeout_index = json.load(f)

        datasheet_content_config = None
        if datasheet_content_config_path != None and not os.path.isfile(datasheet_content_config_path):
            raise FileNotFoundError("unable to find datasheet content config at given path")
        elif datasheet_content_config_path != None:
            with open(os.path.abspath(datasheet_content_config_path), "r") as f:
                datasheet_content_config = json.load(f)

        if not os.path.isfile("datasheet.typ"):
            raise FileNotFoundError("datasheet.typ not found in the root, cannot compile datasheet")

        danger_info = {}
        if not os.path.isfile("./projects/danger_level.yaml"):
            logging.warning("danger_level.yaml not found")
        else:
            with open(os.path.abspath("./projects/danger_level.yaml"), "r") as f:
                content = yaml.safe_load(f)
                # yaml.safe_load() returns None for an empty file
                # check before overwriting since we rely on danger_info being a dict later
                if content != None:
                    danger_info = content
        
        with open(os.path.join(self.script_dir, "docs/user_project.typ.mustache")) as f:
            project_template = f.read()

        datasheet_manifest = [
            f"#import \"@local/tt-datasheet:{template_version}\" as tt\n"
        ]

        # handle art
        current_project = 0
        art_index = 0
        total_available_art = None
        if datasheet_content_config != None and "artwork" in datasheet_content_config:
            total_available_art = len(datasheet_content_config["artwork"])

        if total_available_art != None:
            if total_available_art > 0:
                insert_art_after = math.floor(len(self.projects) / total_available_art)

        for project in self.projects:           
            yaml_data = project.get_project_docs_dict()
            analog_pins = project.info.analog_pins
            yaml_data.update(
                    {
                        "user_docs": rewrite_image_paths(
                            yaml_data["user_docs"],
                            f"projects/{project.get_macro_name()}/docs",
                        ),
                        "mux_address": project.mux_address,
                        "pins": [
                            {
                                "pin_index": str(i),
                                "ui": project.info.pinout.ui[i],
                                "uo": project.info.pinout.uo[i],
                                "uio": project.info.pinout.uio[i],
                            }
                            for i in range(8)
                        ],
                        "analog_pins": [
                            {
                                "ua_index": str(i),
                                "analog_index": str(project.analog_pins[i]),
                                "desc": desc,
                            }
                            for i, desc in enumerate(
                                project.info.pinout.ua[:analog_pins]
                            )
                        ],
                        "is_analog": analog_pins > 0,
                    }
                )

            logging.info(f"building datasheet for {project}")
            result = DocsHelper.get_docs_as_typst(f"projects/{project.get_macro_name()}/docs/info.md")

            if result.stderr != b'':
                logging.warning(result.stderr.decode())

            include_proj_str = f"#include \"projects/{project.get_macro_name()}/docs/doc.typ\"\n"
            if datasheet_content_config != None and project.get_macro_name() in datasheet_content_config["disabled"]:
                logging.warning(f"datasheet disabled for {project}")
                datasheet_manifest.append("// " + include_proj_str)
            else:
                datasheet_manifest.append(include_proj_str)

            # insert artwork
            current_project += 1
            if total_available_art != None:
                if not (art_index >= len(datasheet_content_config["artwork"])):
                    if current_project % insert_art_after == 0:
                        details = datasheet_content_config["artwork"][art_index]
                        datasheet_manifest.append(
                            f"#tt.art(\"{details["id"]}\", rot:{details["rotate"]})\n"
                        )                
                        art_index += 1
        
            content = {
                "template-version": template_version,
                "project-title": yaml_data["title"].replace('"', '\\"'),
                "project-author": f"({DocsHelper.format_authors(yaml_data["author"])})",
                "project-repo-link": yaml_data["git_url"],
                "project-description": yaml_data["description"],
                "project-address": DocsHelper.pretty_address(project.mux_address),
                "project-clock": DocsHelper.pretty_clock(project.info.clock_hz),
                "project-type": DocsHelper.get_project_type(yaml_data["language"], project.is_wokwi(), yaml_data["is_analog"]),
                "project-doc-body": result.stdout.decode(),
                "digital-pins": DocsHelper.format_digital_pins(yaml_data["pins"]),
            }

            if project.is_wokwi():
                content["is-wokwi"] = True
                content["project-wokwi-id"] = project.info.wokwi_id

            if project.get_macro_name() in danger_info:
                content["is-dangerous"] = True
                content["project-danger-level"] = danger_info[project.get_macro_name()]["level"]
                content["project-danger-reason"] = danger_info[project.get_macro_name()]["reason"]

            if yaml_data["is_analog"]:
                content["is-analog"] = True
                content["analog-pins"] = DocsHelper.format_analog_pins(yaml_data["analog_pins"])

            with open(os.path.abspath(f"./projects/{project.get_macro_name()}/docs/doc.typ"), "w") as f:
                f.write(chevron.render(project_template, content))

        with open("datasheet_manifest.typ", "w") as f:
            f.writelines(datasheet_manifest)
            