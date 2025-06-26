#!/usr/bin/env python3
import argparse
import collections
import datetime
import json
import logging
import os
import sys

# pipe handling
from signal import SIG_DFL, SIGPIPE, signal
from typing import Dict, List, TypedDict

import yaml

from config import Config
from documentation import Docs
from logo import LogoGenerator
from project import Project
from rom import ROMFile
from shuttle import ShuttleConfig

signal(SIGPIPE, SIG_DFL)


class Projects:
    def __init__(self, config: Config, args):
        self.args = args
        self.config = config
        self.project_dir = config["project_dir"]

        if not os.path.exists(self.project_dir):
            os.makedirs(self.project_dir)

        only_projects = os.getenv("TT_ONLY_PROJECTS")
        only_projects_list = only_projects.split(",") if only_projects else None

        self.projects: List[Project] = []
        project_list = [
            entry
            for entry in os.listdir(self.project_dir)
            if os.path.isdir(os.path.join(self.project_dir, entry))
        ]
        if args.test:
            project_list = ["tt_um_chip_rom", "tt_um_factory_test"]
        elif args.sta_projects:
            project_list = ["tt_um_loopback"]

        for index, project_id in enumerate(project_list):
            project_dir = os.path.join(self.project_dir, project_id)

            commit_id_file = os.path.join(project_dir, "commit_id.json")
            if not os.path.exists(commit_id_file):
                logging.warning(f"no commit_id.json in {project_dir}, skippinggi")
                continue

            commit_id_data = json.load(open(commit_id_file))
            if commit_id_data.get("skip", False):
                logging.warning(f"skipping {project_dir} (skip flag set)")
                continue

            if only_projects_list and project_id not in only_projects_list:
                continue

            project = Project(
                index,
                commit_id_data["repo"],
                project_dir,
                pdk=config["pdk"],
                is_user_project=False,
            )
            project.commit_id = commit_id_data["commit"]
            project.sort_id = commit_id_data["sort_id"]

            # projects should now be installed, so load all the data from the yaml files
            # fill projects will load from the fill project's directory
            logging.debug("post clone setup")
            project.post_clone_setup()
            logging.debug(project)

            if args.harden:
                project.create_user_config()
                project.golden_harden()

            if args.update_shuttle:
                project.check_ports(bool(config.get("powered_netlists", True)))
                project.check_num_cells()

            self.projects.append(project)

        self.projects.sort(key=lambda x: x.sort_id)

        all_macro_instances = [project.get_macro_name() for project in self.projects]
        self.assert_unique(all_macro_instances)

        all_gds_files = [project.get_macro_gds_filename() for project in self.projects]
        self.assert_unique(all_gds_files)

        logging.info(f"loaded {len(self.projects)} projects")

    def assert_unique(self, check: List[str]):
        duplicates = [
            item for item, count in collections.Counter(check).items() if count > 1
        ]
        if duplicates:
            logging.error("duplicate projects: {}".format(duplicates))
            exit(1)

    def build_metrics(self):
        total_seconds = 0.0
        total_wire_length = 0
        total_wires_count = 0
        total_physical_cells = 0
        max_cells = 0
        min_cells = 1000
        max_cell_project = None
        max_util = 0.0
        min_util = 100.0
        max_util_project = None
        languages: Dict[str, int] = {}

        for project in self.projects:
            try:
                dt = datetime.datetime.strptime(
                    project.metrics["total_runtime"][:-3], "%Hh%Mm%Ss"
                )
            except KeyError:
                continue

            if project.is_chip_rom():
                continue

            delt = datetime.timedelta(
                hours=dt.hour, minutes=dt.minute, seconds=dt.second
            )
            total_seconds += delt.total_seconds()

            cell_count = project.get_cell_counts_from_gl()
            script_dir = os.path.dirname(os.path.realpath(__file__))
            with open(os.path.join(script_dir, "categories.json")) as fh:
                categories = json.load(fh)
            CategoryInfo = TypedDict(
                "CategoryInfo", {"count": int, "examples": List[str]}
            )
            by_category: Dict[str, CategoryInfo] = {}
            total = 0
            for cell_name in cell_count:
                cat_index = categories["map"][cell_name]
                cat_name = categories["categories"][cat_index]
                if cat_name in by_category:
                    by_category[cat_name]["count"] += cell_count[cell_name]
                    by_category[cat_name]["examples"].append(cell_name)
                else:
                    by_category[cat_name] = {
                        "count": cell_count[cell_name],
                        "examples": [cell_name],
                    }

                if cat_name not in ["Fill", "Tap", "Buffer", "Misc"]:
                    total += cell_count[cell_name]

            if total < 10:
                del by_category["Fill"]
                del by_category["Tap"]
                if "Buffer" in by_category:
                    del by_category["Buffer"]
                print(project.get_macro_name(), total, by_category)

            total_wire_length += int(project.metrics["wire_length"])
            total_wires_count += int(project.metrics["wires_count"])
            util = float(project.metrics["OpenDP_Util"])
            num_cells = project.get_cell_count_from_synth()
            total_physical_cells += num_cells

            lang = project.info.language
            if lang in languages:
                languages[lang] += 1
            else:
                languages[lang] = 1

            if num_cells > max_cells:
                max_cells = num_cells
                max_cell_project = project
            if num_cells < min_cells:
                min_cells = num_cells

            if util > max_util:
                max_util = util
                max_util_project = project
            if util < min_util:
                min_util = util

        logging.info(f"build time for all projects {total_seconds / 3600} hrs")
        logging.info(f"total wire length {total_wire_length} um")
        logging.info(f"total cells {total_physical_cells}")
        logging.info(f"max cells {max_cells} for project {max_cell_project}")
        logging.info(f"min cells {min_cells}")
        logging.info(f"max util {max_util} for project {max_util_project}")
        logging.info(f"min util {min_util}")
        logging.info(f"languages {languages}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tiny Tapeout configuration and docs")

    with open("config.yaml") as fh:
        config = yaml.safe_load(fh)

    parser.add_argument(
        "--list", help="list projects", action="store_const", const=True
    )
    parser.add_argument(
        "--single", help="do action on single project", type=int, default=-1
    )
    parser.add_argument(
        "--update-shuttle",
        help="configure shuttle for build",
        action="store_const",
        const=True,
    )
    parser.add_argument(
        "--copy-macros",
        help="copy macros for building the tt_top project",
        action="store_const",
        const=True,
    )
    parser.add_argument(
        "--copy-final-results",
        help="copy final project files to gds/lef directories",
        action="store_const",
        const=True,
    )
    parser.add_argument(
        "--create-chipfoundry-submission",
        help="create ChipFoundry submission directory",
        action="store_const",
        const=True,
    )
    parser.add_argument(
        "--create-ihp-submission",
        help="create IHP submission directory",
        action="store_const",
        const=True,
    )
    parser.add_argument(
        "--harden", help="harden project", action="store_const", const=True
    )
    parser.add_argument(
        "--test", help="use test projects", action="store_const", const=True
    )
    parser.add_argument(
        "--sta-projects", help="use sta projects", action="store_const", const=True
    )
    parser.add_argument(
        "--debug",
        help="debug logging",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
    )
    parser.add_argument(
        "--log-email",
        help="print persons email in messages",
        action="store_const",
        const=True,
    )
    parser.add_argument(
        "--update-image", help="update the image", action="store_const", const=True
    )
    parser.add_argument(
        "--dump-json", help="dump json of all project data to given file"
    )
    parser.add_argument(
        "--dump-markdown", help="dump markdown of all project data to given file"
    )
    parser.add_argument("--dump-pdf", help="create pdf from the markdown")
    parser.add_argument(
        "--metrics", help="print some project metrics", action="store_const", const=True
    )

    args = parser.parse_args()

    # setup log
    log_format = logging.Formatter("%(asctime)s - %(levelname)-8s - %(message)s")
    # configure the client logging
    log = logging.getLogger("")
    # has to be set to debug as is the root logger
    log.setLevel(args.loglevel)

    # create console handler and set level to info
    ch = logging.StreamHandler(sys.stdout)
    # create formatter for console
    ch.setFormatter(log_format)
    log.addHandler(ch)

    projects = Projects(config, args)

    if args.test:
        modules_yaml_name = "modules.test.yaml"
    elif args.sta_projects:
        modules_yaml_name = "modules.sta.yaml"
    else:
        modules_yaml_name = "modules.yaml"

    docs = Docs(config, projects.projects)
    shuttle = ShuttleConfig(config, projects.projects, modules_yaml_name)
    rom = ROMFile(config)
    logo = LogoGenerator("tt", pdk=config["pdk"], config=config)

    if args.list:
        shuttle.list()

    if args.metrics:
        projects.build_metrics()

    if args.update_shuttle:
        shuttle.configure_mux()
        rom.write_rom()
        logo.gen_logo("top", "tt/logo/tt_logo_top.gds")
        logo.gen_lef("top", "tt/logo/tt_logo_top.lef")
        logo.gen_logo("bottom", "tt/logo/tt_logo_bottom.gds")
        logo.gen_lef("bottom", "tt/logo/tt_logo_bottom.lef")
        if not args.test:
            docs.build_index()

    if args.copy_macros:
        shuttle.copy_macros()

    if args.copy_final_results:
        shuttle.copy_final_results()

    if args.create_chipfoundry_submission:
        shuttle.create_foundry_submission("chipfoundry", True)

    if args.create_ihp_submission:
        shuttle.create_foundry_submission("ihp", False)

    if args.update_image:
        docs.update_image()

    if args.dump_markdown:
        shuttle.configure_mux()
        docs.write_datasheet(args.dump_markdown, args.dump_pdf)
