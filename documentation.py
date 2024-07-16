import logging
import os
import subprocess
from typing import List, Optional

import chevron
import frontmatter  # type: ignore
import git  # type: ignore

from config import Config
from git_utils import get_first_remote
from markdown_utils import rewrite_image_paths
from project import Project


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

                # ensure there are no LaTeX escape sequences in various fields, and that optional fields are set
                for key in [
                    "author",
                    "description",
                    "clock_hz",
                    "git_url",
                    "doc_link",
                ]:
                    if key in yaml_data:
                        yaml_data[key] = str(yaml_data[key]).replace(
                            "\\", "\\mbox{\\textbackslash}"
                        )
                    else:
                        yaml_data[key] = ""

                # now build the doc & print it
                try:
                    doc = chevron.render(doc_template, yaml_data)
                    fh.write(doc)
                    fh.write("\n\\clearpage\n")
                except IndexError:
                    logging.warning("missing pins in info.yaml, skipping")

            # ending
            fh.write(doc_pinout)
            fh.write("\n\\clearpage\n")
            fh.write(doc_info)
            fh.write("\n\\clearpage\n")
            fh.write(doc_credits)

        logging.info(f"wrote markdown to {markdown_file}")

        if pdf_file is not None:
            pdf_cmd = f"pandoc --toc --toc-depth 2 --pdf-engine=xelatex -i {markdown_file} -o {pdf_file}"
            logging.info(pdf_cmd)
            p = subprocess.run(pdf_cmd, shell=True)
            if p.returncode != 0:
                logging.error("pdf generation failed")
                raise RuntimeError(f"pdf generation failed with code {p.returncode}")
