import logging
import os
import shutil
import subprocess
from typing import List, Optional

import frontmatter  # type: ignore
import git  # type: ignore

from config import Config
from git_utils import get_first_remote
from markdown_utils import rewrite_image_paths, rewrite_image_paths_for_website
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
        readme = self.load_doc_template("shuttle_index_header.md")
        with open(filename, "w") as fh:
            fh.write(
                readme.format(
                    name=self.config["name"],
                    git_repo=get_first_remote(repo),
                    git_commit=repo.head.commit.hexsha,
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
        doc_header = self.load_doc_template("doc_header.md")
        doc_template = self.load_doc_template("doc_template.md")
        doc_pinout = self.load_doc_template("PINOUT.md")
        doc_info = self.load_doc_template("../../tt-multiplexer/docs/INFO.md")
        doc_credits = self.load_doc_template("CREDITS.md")

        with open(markdown_file, "w") as fh:
            repo = git.Repo(".")
            fh.write(
                doc_header.format(name=self.config["name"], repo=get_first_remote(repo))
            )

            self.projects.sort(key=lambda x: x.mux_address)

            for project in self.projects:
                yaml_data = project.get_project_docs_dict()
                yaml_data["user_docs"] = rewrite_image_paths(
                    yaml_data["user_docs"], f"projects/{project.get_macro_name()}/docs"
                )
                yaml_data["mux_address"] = project.mux_address

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
                    doc = (
                        doc_template.replace("__git_url__", "{git_url}")
                        .replace("__doc_link__", "{doc_link}")
                        .format(**yaml_data)
                    )
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
                logging.error("pdf command failed")

    def build_hugo_content(self, hugo_root: str) -> None:
        hugo_images = os.path.join(hugo_root, "images")
        shutil.rmtree(hugo_root)
        os.makedirs(hugo_root)
        os.makedirs(hugo_images)

        with open(os.path.join(self.script_dir, "docs", "hugo_template.md")) as fh:
            doc_template = fh.read()

        with open(
            os.path.join(self.script_dir, "docs", "hugo_index_template.md")
        ) as fh:
            index_template = fh.read()

        # copy image
        # TODO, need to get image from somewhere
        # shutil.copyfile(
        #    "tt/docs/pics/tinytapeout_numbered.png",
        #    os.path.join(hugo_images, f'tinytapeout-{self.config["id"]}.png'),
        # )

        # index page
        logging.info("building pages")
        shuttle_info = {
            "shuttle_name": self.config["name"],
            "shuttle_id": self.config["id"],
            "project_count": len(self.projects),
            "end_date": self.config["end_date"],
        }
        with open(os.path.join(hugo_root, "_index.md"), "w") as fh:
            fh.write(index_template.format(**shuttle_info))
            fh.write("# All projects\n")
            fh.write("| Index | Title | Author |\n")
            fh.write("| ----- | ----- | -------|\n")
            self.projects.sort(key=lambda x: x.mux_address)
            for project in self.projects:
                logging.info(project)
                fh.write(project.get_hugo_row())

                project_dir = os.path.join(hugo_root, f"{project.mux_address :03}")
                project_image_dir = os.path.join(project_dir, "images")
                os.makedirs(project_dir)
                os.makedirs(project_image_dir)
                yaml_data = project.get_project_docs_dict()
                yaml_data["mux_address"] = project.mux_address
                yaml_data["index"] = project.index
                yaml_data["weight"] = project.index + 1
                yaml_data["git_action"] = project.get_workflow_url_when_submitted()
                yaml_data["shuttle_id"] = self.config["id"]
                yaml_data["user_docs"] = rewrite_image_paths_for_website(
                    yaml_data["user_docs"],
                    os.path.join(project.src_dir, "docs"),
                    project_image_dir,
                )

                doc = doc_template.format(**yaml_data)
                with open(os.path.join(project_dir, "_index.md"), "w") as pfh:
                    pfh.write(doc)
