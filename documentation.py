import json
import logging
import os
import shutil
import subprocess

import frontmatter  # type: ignore
import git

from config import Config
from git_utils import get_first_remote
from markdown_utils import latex_centered_image, rewrite_image_paths


class Docs:
    def __init__(self, config: Config, projects, args):
        self.config = config
        self.projects = projects
        self.args = args
        self.script_dir = os.path.dirname(os.path.realpath(__file__))

    # stuff related to docs
    def build_index(self):
        logging.info("building doc index")
        repo = git.Repo(".")
        readme = self.load_doc_template("README_init.md")
        with open("README.md", "w") as fh:
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

    # create a json file of all the project info, this is then used by tinytapeout.com to show projects
    def dump_json(self):
        designs = []
        for project in self.projects:
            design = project.get_yaml()
            designs.append(design)

        with open(self.args.dump_json, "w") as fh:
            fh.write(json.dumps(designs, indent=4))
        logging.info(f"wrote json to {self.args.dump_json}")

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

    def dump_markdown(self):
        doc_header = self.load_doc_template("doc_header.md")
        doc_chip_map = self.load_doc_template("../../docs/chip_map.md")
        doc_template = self.load_doc_template("doc_template.md")
        doc_pinout = self.load_doc_template("PINOUT.md")
        doc_info = self.load_doc_template("../../tt-multiplexer/docs/INFO.md")
        doc_credits = self.load_doc_template("CREDITS.md")

        with open(self.args.dump_markdown, "w") as fh:
            repo = git.Repo(".")
            fh.write(
                doc_header.format(name=self.config["name"], repo=get_first_remote(repo))
            )
            fh.write(doc_chip_map)
            fh.write("# Projects\n")

            self.projects.sort(key=lambda x: x.mux_address)

            for project in self.projects:
                yaml_data = project.get_project_doc_yaml()

                yaml_data["mux_address"] = project.mux_address

                logging.info(f"building datasheet for {project}")
                # handle pictures
                yaml_data["picture_link"] = ""
                if yaml_data["picture"]:
                    extension = os.path.splitext(yaml_data["picture"])[1]
                    picture_path = os.path.join(
                        project.local_dir, f"picture{extension}"
                    )
                    if os.path.exists(picture_path):
                        yaml_data["picture_link"] = latex_centered_image(picture_path)
                    else:
                        logging.warning(f"picture {picture_path} not found, skipping")

                # ensure there are no LaTeX escape sequences in various fields, and that optional fields are set
                for key in [
                    "author",
                    "description",
                    "how_it_works",
                    "how_to_test",
                    "external_hw",
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

                # many people remove unused pins in input / output / bidirectional
                for key in ["inputs", "outputs", "bidirectional"]:
                    if not yaml_data[key]:
                        yaml_data[key] = []
                    yaml_data[key].extend((8 - len(yaml_data[key])) * ["n/a"])

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

        logging.info(f"wrote markdown to {self.args.dump_markdown}")

        if self.args.dump_pdf:
            pdf_cmd = f"pandoc --toc --toc-depth 2 --pdf-engine=xelatex -i {self.args.dump_markdown} -o {self.args.dump_pdf}"
            logging.info(pdf_cmd)
            p = subprocess.run(pdf_cmd, shell=True)
            if p.returncode != 0:
                logging.error("pdf command failed")

    def build_hugo_content(self) -> None:
        hugo_root = self.args.build_hugo_content
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
        with open(os.path.join(hugo_root, "_index.md"), "w") as fh:
            fh.write(index_template)
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
                yaml_data = project.get_project_doc_yaml()
                yaml_data["mux_address"] = project.mux_address
                if '""' in yaml_data["title"]:
                    yaml_data["title"] = yaml_data["title"].replace('""', "")

                yaml_data["index"] = project.index
                yaml_data["weight"] = project.index + 1
                yaml_data["git_action"] = project.get_workflow_url_when_submitted()
                for key in "external_hw", "clock_hz":
                    if key not in yaml_data:
                        yaml_data[key] = ""

                # many people remove unused pins in input / output / bidirectional
                for key in ["inputs", "outputs", "bidirectional"]:
                    yaml_data[key].extend((8 - len(yaml_data[key])) * ["n/a"])

                yaml_data["picture_link"] = ""
                if yaml_data["picture"]:
                    extension = os.path.splitext(yaml_data["picture"])[1]
                    picture_path = os.path.join(
                        project.local_dir, f"picture{extension}"
                    )
                    picture_basename = os.path.basename(picture_path)
                    try:
                        shutil.copyfile(
                            picture_path,
                            os.path.join(project_image_dir, picture_basename),
                        )
                        yaml_data[
                            "picture_link"
                        ] = f"![picture](images/{picture_basename})"
                        logging.warning(f"picture found {picture_path}")
                    except FileNotFoundError:
                        logging.warning(f"picture not found {picture_path}")
                        yaml_data["picture_link"] = "Image path is broken"
                doc = doc_template.format(**yaml_data)
                with open(os.path.join(project_dir, "_index.md"), "w") as pfh:
                    pfh.write(doc)
