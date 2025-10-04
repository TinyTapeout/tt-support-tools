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
        logging.info(f"building datasheet with version {template_version}")
        logging.info(f"tapeout index available? {True if tapeout_index_path is not None else False}")
        logging.info(f"content config available? {True if datasheet_content_config_path is not None else False}")

        tapeout_index = None
        # if given a path but the file doesn't exist
        if tapeout_index_path is not None and not os.path.isfile(tapeout_index_path):
            raise FileNotFoundError("unable to find tapeout index at given path")
        # if given a path but it does exist
        elif tapeout_index_path is not None:
            with open(os.path.abspath(tapeout_index_path), "r") as f:
                index = json.load(f)

            tapeout_index = sorted(index["projects"], key=lambda project: project["address"])
        elif tapeout_index_path is None:
            logging.error("a tapeout index must be specified (pass --doc-tapeout-index <path>)")
            exit(1)

        datasheet_content_config = None
        if datasheet_content_config_path is None and not os.path.isfile(datasheet_content_config_path):
            raise FileNotFoundError("unable to find datasheet content config at given path")
        elif datasheet_content_config_path is not None:
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
                if content is not None:
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
        if datasheet_content_config is not None and "artwork" in datasheet_content_config:
            total_available_art = len(datasheet_content_config["artwork"])

        if total_available_art is not None:
            if total_available_art > 0:
                insert_art_after = math.floor(len(self.projects) / total_available_art)

        temp_subtile_projects = {}
        for project in tapeout_index:

            logging.info(f"processing datasheet for [{project['address']} : {project['repo']}]")

            # fetch info.yaml
            yaml_path = os.path.abspath(f"./projects/{project['macro']}/info.yaml")
            if "type" in project:
                if project["type"] == "subtile":
                    yaml_path = os.path.abspath(f"./projects/{project['subtile_group']}/docs/{project['macro']}/info.yaml")

            try:
                with open(yaml_path, "r") as f:
                    yaml_info = yaml.safe_load(f)
            except FileNotFoundError:
                logging.warning(f"unable to read {yaml_path}... project exists in tapeout index but not in local directory? skipping")
                continue

            info = DocsHelper.format_project_info(yaml_info, project)

            # decide what to do given project type
            if info["type"] == "subtile":
                # defer for later (when we hit the group module)
                # we want the group module to appear first in the datasheet
                temp_subtile_projects[info["subtile_addr"]] = info
                continue

            elif info["type"] == "group":

                # write group doc
                group_md_path = f"projects/{info['macro']}/docs/info.md"
                group_typ_path = f"projects/{info['macro']}/docs/doc.typ"
                DocsHelper.write_doc(
                    path=os.path.abspath(group_typ_path),
                    template=project_template,
                    content=DocsHelper.populate_template_tags(
                        info=info,
                        danger_info=danger_info,
                        docs=DocsHelper.get_docs_as_typst(group_md_path),
                        template_version=template_version
                    )
                )

                # add group doc to manifest
                if datasheet_content_config is not None and info["macro"] in datasheet_content_config["disabled"]:
                    logging.warning(f"datasheet disabled for [{info['address']} : {info['git_url']}")
                    datasheet_manifest.append(f"// #include \"{group_typ_path}\"\n")
                else:
                    datasheet_manifest.append(f"#include \"{group_typ_path}\"\n")

                # write subtile doc
                for _, subtile_info in temp_subtile_projects.items():
                    partial_doc_path = f"projects/{subtile_info['subtile_group']}/docs/{subtile_info['macro']}"
                    typ_path = os.path.join(partial_doc_path, "doc.typ")
                    md_path = os.path.join(partial_doc_path, "info.md")

                    DocsHelper.write_doc(
                        path=typ_path,
                        template=project_template,
                        content=DocsHelper.populate_template_tags(
                            info=subtile_info,
                            danger_info=danger_info,
                            docs=DocsHelper.get_docs_as_typst(md_path),
                            template_version=template_version
                        )
                    )

                    # add subtile doc to manifest
                    if datasheet_content_config is not None and subtile_info["macro"] in datasheet_content_config["disabled"]:
                        logging.warning(f"datasheet disabled for [{subtile_info['address']} : {subtile_info['git_url']}")
                        datasheet_manifest.append(f"// #include \"{typ_path}\"\n")
                    else:
                        datasheet_manifest.append(f"#include \"{typ_path}\"\n")

                # clear subtiles for next group
                temp_subtile_projects = {}

            elif info["type"] == "project":
                project_md_path = f"projects/{info['macro']}/docs/info.md"
                project_typ_path = f"projects/{info['macro']}/docs/doc.typ"

                DocsHelper.write_doc(
                    path=project_typ_path,
                    template=project_template,
                    content=DocsHelper.populate_template_tags(
                        info=info,
                        danger_info=danger_info,
                        docs=DocsHelper.get_docs_as_typst(project_md_path),
                        template_version=template_version
                    )
                )

                # add project doc to manifest
                if datasheet_content_config is not None and info["macro"] in datasheet_content_config["disabled"]:
                    logging.warning(f"datasheet disabled for [{info['address']} : {info['git_url']}")
                    datasheet_manifest.append(f"// #include \"{project_typ_path}\"\n")
                else:
                    datasheet_manifest.append(f"#include \"{project_typ_path}\"\n")

            else:
                logging.error(f"unhandled project type! what is \"{info['type']}\"?")
                exit(1)

            # insert artwork
            current_project += 1
            if total_available_art is not None:
                if not (art_index >= len(datasheet_content_config["artwork"])):
                    if current_project % insert_art_after == 0:
                        details = datasheet_content_config["artwork"][art_index]
                        datasheet_manifest.append(
                            f"#tt.art(\"{details['id']}\", rot:{details['rotate']})\n"
                        )
                        art_index += 1

        with open("datasheet_manifest.typ", "w") as f:
            f.writelines(datasheet_manifest)
