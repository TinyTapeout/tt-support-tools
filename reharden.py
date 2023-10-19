#!/usr/bin/env python3
import argparse
import csv
import datetime
import glob
import json
import logging
import os
import re
import sys
from typing import List

import git

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
PROJECTS_DIR = os.path.join(ROOT, "projects")
REHARDEN_DIR = os.path.join(ROOT, "reharden")


def load_metrics(path):
    try:
        with open(os.path.join(path, "runs/wokwi/reports/metrics.csv")) as fh:
            metrics = next(csv.DictReader(fh))
            return metrics
    except FileNotFoundError:
        logging.warning(f"no metrics found for {path}")
        return None


# get cell count from synth report
def get_cell_count_from_synth(path):
    num_cells = 0
    try:
        yosys_report = (
            f"{path}/runs/wokwi/reports/synthesis/1-synthesis.AREA_0.stat.rpt"
        )
        with open(yosys_report) as fh:
            for line in fh.readlines():
                m = re.search(r"Number of cells:\s+(\d+)", line)
                if m is not None:
                    num_cells = int(m.group(1))

    except IndexError:
        logging.warning(f"couldn't open yosys cell report for cell checking {path}")
        return 0
    except FileNotFoundError:
        logging.warning(f"no cell count found for {path}")
        return 0

    return num_cells


def get_cell_counts_from_gl(path):
    cell_count = {}
    total = 0

    try:
        gl_path = glob.glob(
            os.path.join(path, "runs/wokwi/results/final/verilog/gl/*.nl.v")
        )[0]
    except IndexError:
        logging.warning("no gl cell count found")
        return 0
    with open(gl_path) as fh:
        for line in fh.readlines():
            m = re.search(r"sky130_(\S+)__(\S+)_(\d+)", line)
            if m is not None:
                total += 1
                cell_lib = m.group(1)
                cell_name = m.group(2)
                cell_drive = m.group(3)
                assert cell_lib in ["fd_sc_hd", "ef_sc_hd"]
                assert int(cell_drive) > 0
                try:
                    cell_count[cell_name] += 1
                except KeyError:
                    cell_count[cell_name] = 1
    return cell_count


def build_metrics(shuttle_index):
    total_seconds = 0
    total_wire_length = 0
    total_wires_count = 0
    total_physical_cells = 0
    max_cells = 0
    min_cells = 1000
    max_cell_project = None
    max_util = 0
    min_util = 100
    max_util_project = None

    for project in shuttle_index["mux"]:
        macro: str = shuttle_index["mux"][project]["macro"]
        repo_dir = os.path.join(REHARDEN_DIR, macro)
        metrics = load_metrics(repo_dir)
        if metrics is None:
            continue

        try:
            dt = datetime.datetime.strptime(metrics["total_runtime"][:-3], "%Hh%Mm%Ss")
        except KeyError:
            continue

        delt = datetime.timedelta(hours=dt.hour, minutes=dt.minute, seconds=dt.second)
        total_seconds += delt.total_seconds()

        total_wire_length += int(metrics["wire_length"])
        total_wires_count += int(metrics["wires_count"])
        util = float(metrics["OpenDP_Util"])
        num_cells = get_cell_count_from_synth(repo_dir)
        total_physical_cells += num_cells

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TT reharden tool")
    parser.add_argument(
        "--debug",
        help="debug logging",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
    )
    parser.add_argument(
        "--clone", help="clone the repos", action="store_const", const=True
    )
    parser.add_argument(
        "--harden", help="harden the projects", action="store_const", const=True
    )
    parser.add_argument("--start-from", help="start from", type=int, default=0)
    parser.add_argument("--end-at", help="end at", type=int, default=100000)
    parser.add_argument("--build-metrics", action="store_const", const=True)

    args = parser.parse_args()

    # setup log
    log_format = logging.Formatter(
        "%(asctime)s - %(module)-10s - %(levelname)-8s - %(message)s"
    )
    # configure the client logging
    log = logging.getLogger("")
    # has to be set to debug as is the root logger
    log.setLevel(args.loglevel)

    # create console handler and set level to info
    ch = logging.StreamHandler(sys.stdout)
    # create formatter for console
    ch.setFormatter(log_format)
    log.addHandler(ch)

    shuttle_index = json.load(open("shuttle_index.json"))
    differences: List[str] = []
    for number, project in enumerate(shuttle_index["mux"]):
        if number < args.start_from:
            continue
        if number > args.end_at:
            continue

        repo = shuttle_index["mux"][project]["repo"]
        commit = shuttle_index["mux"][project]["commit"]
        macro = shuttle_index["mux"][project]["macro"]
        repo_dir = os.path.join(REHARDEN_DIR, macro)

        if args.clone:
            if not os.path.exists(repo_dir):
                logging.info(f"cloning {number :03} {repo}")
                git.Repo.clone_from(repo, repo_dir)
                cloned_repo = git.Repo(repo_dir)
                cloned_repo.git.submodule("update", "--init")
                cloned_repo.git.checkout(commit)

            # get tt tools setup.
            # can't run tt from another directory because gitpython fails
            # can't run symlinked because openlane fails
            # simple copy won't work because of tt is a submodule and not a standalone repo.
            tt_tools_path = os.path.join(repo_dir, "tt")
            if not os.path.exists(tt_tools_path):
                logging.info(f"cloning tt to {tt_tools_path}")
                git.Repo.clone_from("tt", tt_tools_path, depth=1)

        if args.harden:
            logging.info(f"hardening {number :03} {repo_dir}")
            cwd = os.getcwd()
            os.chdir(repo_dir)
            new_gds = f"runs/wokwi/results/final/gds/{macro}.gds"
            prev_commit = None
            if os.path.isfile("commit.txt"):
                with open("commit.txt", "r") as f:
                    prev_commit = f.read().strip()
            if not os.path.exists(new_gds) or prev_commit != commit:
                os.system(f"tt/tt_tool.py --create-user-config > reharden.log")
                res = os.system(f"tt/tt_tool.py --harden --debug >> reharden.log")
                if res != 0:
                    logging.warning(f"failed to harden {macro}")
                else:
                    with open("commit.txt", "w") as f:
                        f.write(commit)
            orig_gds = os.path.join(PROJECTS_DIR, f"{macro}/{macro}.gds")
            logging.info(f"Comparing {orig_gds} with {new_gds}")
            res = os.system(
                f"klayout -b -r tt/gds_compare.py -rd 'gds1={orig_gds}' -rd 'gds2={new_gds}'"
            )
            if res != 0:
                logging.warning(f"GDS compare failed for {macro}")
                differences.append(macro)
            os.chdir(cwd)

    if args.harden:
        print(f"Found total of {len(differences)} different projects: ")
        for diff in differences:
            print("- ", diff)

    if args.build_metrics:
        build_metrics(shuttle_index)
