import json
import logging
import math
import os
import subprocess
from pathlib import Path
from typing import List

import chevron
import frontmatter  # type: ignore
import git  # type: ignore
import yaml

from config import Config
from doc_utils import DocsHelper
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

    def build_datasheet(
        self,
        template_version: str,
        tapeout_index_path: str,
    ):
        logging.info(f"building datasheet with version {template_version}")

        tapeout_index = None
        # if given a path but the file doesn't exist
        if tapeout_index_path is not None and not os.path.isfile(tapeout_index_path):
            raise FileNotFoundError("unable to find tapeout index at given path")
        # if given a path but it does exist
        elif tapeout_index_path is not None:
            with open(os.path.abspath(tapeout_index_path), "r") as f:
                index = json.load(f)

            tapeout_index = sorted(
                index["projects"], key=lambda project: project["address"]
            )
        elif tapeout_index_path is None:
            logging.warning("tapeout index not provided, using project list")
            self.projects.sort(key=lambda x: x.mux_address)
            tapeout_index = map(DocsHelper.normalise_project_info, self.projects)

        datasheet_content_config = None
        if "datasheet_config" in self.config:
            logging.info("using datasheet config in config.yaml")
            datasheet_content_config = self.config["datasheet_config"]

        with open(os.path.join(self.script_dir, "docs/datasheet.typ.mustache")) as f:
            datasheet_template = f.read()

        DocsHelper.configure_datasheet(
            self.config, datasheet_template, template_version
        )

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

        datasheet_manifest = [f'#import "/tt/docs/typst/src/tt.typ" as tt\n']

        # handle art
        current_project = 0
        art_index = 0
        total_available_art = None
        if (
            datasheet_content_config is not None
            and "artwork" in datasheet_content_config
        ):
            total_available_art = len(datasheet_content_config["artwork"])

        if total_available_art is not None:
            if total_available_art > 0:
                insert_art_after = max(
                    1, math.floor(len(self.projects) / total_available_art)
                )

        temp_subtile_projects = {}
        for project in tapeout_index:

            logging.info(
                f"processing datasheet for [{project['address']} : {project['repo']}]"
            )

            # fetch info.yaml
            yaml_path = os.path.abspath(f"./projects/{project['macro']}/info.yaml")
            if "type" in project:
                if project["type"] == "subtile":
                    yaml_path = os.path.abspath(
                        f"./projects/{project['subtile_group']}/docs/{project['macro']}/info.yaml"
                    )

            try:
                with open(yaml_path, "r") as f:
                    yaml_info = yaml.safe_load(f)
            except FileNotFoundError:
                logging.warning(
                    f"unable to read {yaml_path}... project exists in tapeout index but not in local directory? skipping"
                )
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
                        template_version=template_version,
                    ),
                )

                # add group doc to manifest
                include_str = f'#include "{group_typ_path}"\n'
                if (
                    datasheet_content_config is not None
                    and "disabled" in datasheet_content_config
                ):
                    if info["macro"] in datasheet_content_config["disabled"]:
                        logging.warning(
                            f"datasheet disabled for [{info['address']} : {info['git_url']}"
                        )
                        include_str = "// " + include_str
                datasheet_manifest.append(include_str)

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
                            template_version=template_version,
                        ),
                    )

                    # add subtile doc to manifest
                    include_str = f'#include "{typ_path}"\n'
                    if DocsHelper.project_is_disabled(
                        datasheet_content_config, subtile_info["macro"]
                    ):
                        logging.warning(
                            f"datasheet disabled for [{subtile_info['address']} : {subtile_info['git_url']}]"
                        )
                        include_str = "// " + include_str
                    datasheet_manifest.append(include_str)

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
                        template_version=template_version,
                    ),
                )

                # add project doc to manifest
                include_str = f'#include "{project_typ_path}"\n'
                if DocsHelper.project_is_disabled(
                    datasheet_content_config, info["macro"]
                ):
                    logging.warning(
                        f"datasheet disabled for [{info['address']} : {info['git_url']}]"
                    )
                    include_str = "// " + include_str
                datasheet_manifest.append(include_str)

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
                            f"#tt.datasheet.art(\"{details['id']}\", rot:{details['rotate']})\n"
                        )
                        art_index += 1

        with open("datasheet_manifest.typ", "w") as f:
            f.writelines(datasheet_manifest)

        DocsHelper.compile()


def interactive_doc_checker():
    """
    Launch the interactive document checker.

    This will go through every project and display the project's documentation (`info.md`) in `nano`, prompting you to
    either leave or remove the project datasheet from the shuttle datasheet after closing the `nano` editor.

    There are some commands which you can use:
        - "y": remove the project from the datasheet
        - "n" (default): leave the project in the datasheet
        - "e"/"end": save progress to return to later

    The results are saved into a separate file (`doc_check.yaml`) - copy the `datasheet_config.disabled` array over to
    `config.yaml`. This file does not need to be commited to the repo and can be deleted after.

    If `doc_check.yaml` exists, and a `_skip_to_project` key is present, the function will attempt to skip over all
    the projects until it encounters the one specified by `_skip_to_project` - this allows for easy resuming and does
    not require you to audit every project immediately.
    """

    docs = []
    skip_projects = False
    skip_to = None
    # check if we have saved progress
    if Path("doc_check.yaml").is_file():
        with open("doc_check.yaml", "r") as f:
            tmp = yaml.safe_load(f)

        if "_skip_to_project" in tmp:
            skip_to = tmp["_skip_to_project"]
            skip_projects = True

        # get in-progress list of disabled projects
        docs += tmp["datasheet_config"]["disabled"]

    with open("config.yaml") as f:
        shuttle_config = yaml.safe_load(f)

    if "datasheet_config" in shuttle_config:
        if "disabled" in shuttle_config["datasheet_config"]:
            docs += shuttle_config["datasheet_config"]["disabled"]

    for project in Path("projects").glob("*/docs/info.md"):
        name = project.parts[1]

        if name in docs:
            logging.info(f"skipping {name} (already disabled)")
            continue

        if skip_projects:
            if name != skip_to:
                continue
            else:
                skip_projects = False

        # inspect docs with nano in read-only mode
        subprocess.call(["nano", "-v", project])

        while True:
            decision = str(input(f"\nremove {name} (y/N)? ")).lower()

            if decision == "y":
                logging.info(f"removing {name}")
                docs.append(name)
                break
            elif (decision == "n") or (decision == ""):
                logging.info(f"not removing {name}")
                break
            elif (decision == "e") or (decision == "end"):
                break

        # break out of both loops and save progress
        if decision == "end":
            skip_to = name
            break

    if len(docs) == 0:
        logging.info("no projects disabled, nothing written")
        return

    # mock yaml structure (see comment below re intermediate file)
    tmp_yaml: dict[str, dict[str, list] | str] = {
        "datasheet_config": {"disabled": docs}
    }

    # save progress for next time
    if decision == "end":
        tmp_yaml["_skip_to_project"] = name

    # NOTE: have to use an intermediate file since writing back to config.yaml would wreck the existing formatting
    # a potential upgrade: https://pypi.org/project/ruamel.yaml/
    with open("doc_check.yaml", "w+") as f:
        logging.info(
            "writing to doc_check.yaml -- please copy list of disabled projects to config.yaml"
        )
        yaml.safe_dump(tmp_yaml, f, default_flow_style=False)
