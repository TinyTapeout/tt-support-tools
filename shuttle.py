import glob
import json
import logging
import os
import shutil
from typing import List, Set

import git
import yaml

from config import Config
from project import Project
from shuttle_index import ShuttleIndex, ShuttleIndexLayout, ShuttleIndexProject


def copy_print(src: str, dest: str):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    logging.info(f"  -> {dest}")
    shutil.copy2(src, dest)


def copy_print_glob(pattern: str, dest_dir: str):
    for file in glob.glob(pattern):
        copy_print(file, os.path.join(dest_dir, os.path.basename(file)))


class ShuttleConfig:
    def __init__(self, config: Config, projects: List[Project], modules_yaml_name: str):
        self.config = config
        self.projects = projects
        self.script_dir = os.path.dirname(os.path.realpath(__file__))
        self.modules_yaml_name = modules_yaml_name
        self.mux_config_yaml_name = os.environ.get("TT_CONFIG", "sky130.yaml")
        self.tt_top_macro = config.get("top_level_macro", "openframe_project_wrapper")

        self.read_mux_config_file()
        total_rows: int = self.mux_config["tt"]["grid"]["y"]
        total_mux_rows = total_rows // 2
        self.layout: ShuttleIndexLayout = {
            "muxes": [["digital"] * total_mux_rows, ["digital"] * total_mux_rows]
        }
        for item in self.mux_config["tt"]["analog"]:
            mux_id: int
            for mux_id in item["mux_id"]:
                x = (mux_id >> 1) & 1
                y = (
                    total_mux_rows // 2
                    - (2 * (mux_id & 1) - 1) * (mux_id >> 2)
                    - (mux_id & 1)
                )
                self.layout["muxes"][x][y] = "analog"

    def read_mux_config_file(self):
        with open(
            f"tt-multiplexer/cfg/{self.mux_config_yaml_name}", "r"
        ) as mux_config_file:
            self.mux_config = yaml.safe_load(mux_config_file)

    def configure_mux(self):
        with open(self.modules_yaml_name, "r") as modules_file:
            module_config = yaml.safe_load(modules_file)
            configured_macros: Set[str] = set(
                map(lambda mod: mod["name"], module_config["modules"])
            )
            logging.info(
                f"found {len(configured_macros)} preconfigured macros: {configured_macros}"
            )
            for project in self.projects:
                tiles = project.info.tiles
                width, height = map(int, tiles.split("x"))
                if project.unprefixed_name not in configured_macros:
                    module_entry = {
                        "name": project.unprefixed_name,
                        "width": width,
                        "height": height,
                        "analog": {i: None for i in range(project.info.analog_pins)},
                        "pg_vaa": project.info.uses_3v3,
                    }
                    module_config["modules"].append(module_entry)

        with open("tt-multiplexer/cfg/modules.yaml", "w") as mux_modules_file:
            yaml.dump(module_config, mux_modules_file)

        res = os.system("make -C tt-multiplexer clean gensrc")
        if res != 0:
            logging.error("Failed to generate multiplexer placement configuration")
            exit(1)

        project_index: List[ShuttleIndexProject] = []
        mux_index_reverse = {}
        with open("tt-multiplexer/cfg/modules_placed.yaml") as placed_modules_file:
            placed_modules = yaml.safe_load(placed_modules_file)
            for module in placed_modules["modules"]:
                mux_address = (module["mux_id"] << 5) | module["blk_id"]
                module_name = "tt_um_" + module["name"]
                project = next(
                    p for p in self.projects if p.info.top_module == module_name
                )
                project.mux_address = mux_address
                project_info: ShuttleIndexProject = {
                    "macro": module_name,
                    "address": mux_address,
                    "x": module["x"],
                    "y": module["y"],
                    "tiles": f"{module['width']}x{module['height']}",
                    "repo": project.git_url,
                    "commit": project.commit_id,
                }

                assert list(module["analog"].keys()) == list(
                    range(len(module["analog"]))
                ), f"analog pins are not contiguous for {module_name}"

                project.analog_pins = tuple(module["analog"].values())
                if len(module["analog"]) > 0:
                    project_info["analog_pins"] = project.analog_pins

                project_index.append(project_info)
                mux_index_reverse[module_name] = mux_address

        for project in self.projects:
            if project.info.top_module not in mux_index_reverse:
                logging.error(f"no placement found for {project}!")
                exit(1)

        repo = git.Repo(".")

        shuttle_index_data: ShuttleIndex = {
            "name": self.config["name"],
            "repo": list(repo.remotes[0].urls)[0],
            "commit": repo.commit().hexsha,
            "commit_date": repo.commit().committed_date,
            "layout": self.layout,
            "version": 3,
            "projects": project_index,
        }

        with open("shuttle_index.json", "w") as shuttle_index_file:
            json.dump(shuttle_index_data, shuttle_index_file, indent=2)

        with open("verilog/includes/includes.gl.user_projects", "w") as includes_file:
            for project in self.projects:
                if project.is_chip_rom():
                    continue
                includes_file.write(
                    f"$(USER_PROJECT_VERILOG)/../projects/{project.info.top_module}/{project.info.top_module}.v\n"
                )

    def list(self):
        for project in self.projects:
            logging.info(project)

    def find_last_run(self, macro: str):
        runs = f"tt-multiplexer/ol2/{macro}/runs/"
        if macro == "tt_um_chip_rom":
            runs = "tt/rom/runs/"
        runlist = sorted(
            [
                r
                for r in os.listdir(runs)
                if r.startswith("RUN_") and os.path.isdir(os.path.join(runs, r))
            ]
        )
        if len(runlist) == 0:
            print(f"Error: no runs found for {macro}")
            exit(1)

        return os.path.join(runs, runlist[-1])

    def copy_mux_macro(self, source_dir: str, name: str):
        copy_print(
            f"tt-multiplexer/{source_dir}/gds/{name}.gds",
            f"tt-multiplexer/ol2/tt_top/gds/{name}.gds",
        )
        copy_print(
            f"tt-multiplexer/{source_dir}/lef/{name}.lef",
            f"tt-multiplexer/ol2/tt_top/lef/{name}.lef",
        )
        copy_print(
            f"tt-multiplexer/{source_dir}/src/{name}.v",
            f"tt-multiplexer/ol2/tt_top/verilog/{name}.v",
        )

    def copy_macros(self):
        logging.info("copying macros to tt_top:")
        copy_print_glob("projects/*/*.gds", "tt-multiplexer/ol2/tt_top/gds")
        copy_print_glob("projects/*/*.lef", "tt-multiplexer/ol2/tt_top/lef")
        copy_print_glob("projects/*/*.v", "tt-multiplexer/ol2/tt_top/verilog")
        macros = ["tt_um_chip_rom", "tt_ctrl", "tt_mux"]
        for macro in macros:
            lastrun = self.find_last_run(macro)
            copy_print(
                f"{lastrun}/final/gds/{macro}.gds",
                f"tt-multiplexer/ol2/tt_top/gds/{macro}.gds",
            )
            copy_print(
                f"{lastrun}/final/lef/{macro}.lef",
                f"tt-multiplexer/ol2/tt_top/lef/{macro}.lef",
            )
            copy_print(
                f"{lastrun}/final/pnl/{macro}.pnl.v",
                f"tt-multiplexer/ol2/tt_top/verilog/{macro}.v",
            )
            copy_print_glob(
                f"{lastrun}/final/spef/*/*.spef", "tt-multiplexer/ol2/tt_top/spef"
            )

        # Copy power gate / analog switch macros:
        self.copy_mux_macro("pg/tt_pg_1v8_1", "tt_pg_1v8_1")
        self.copy_mux_macro("pg/tt_pg_1v8_2", "tt_pg_1v8_2")
        self.copy_mux_macro("pg/tt_pg_1v8_4", "tt_pg_1v8_4")
        self.copy_mux_macro("pg/tt_pg_3v3_2", "tt_pg_3v3_2")
        self.copy_mux_macro("asw/tt_asw_3v3", "tt_asw_3v3")

    def copy_final_results(self):
        macros = ["tt_um_chip_rom", "tt_ctrl", "tt_mux", "tt_top"]

        logging.info("copying final results:")
        for macro in macros:
            lastrun = self.find_last_run(macro)
            macro_name = macro if macro != "tt_top" else self.tt_top_macro
            logging.info(f"** {macro_name} **")
            logging.info(f"  FROM {lastrun}")
            copy_print(f"{lastrun}/final/gds/{macro_name}.gds", f"gds/{macro_name}.gds")
            if macro != "tt_top":
                copy_print(
                    f"{lastrun}/final/lef/{macro_name}.lef", f"lef/{macro_name}.lef"
                )
            copy_print(
                f"{lastrun}/final/pnl/{macro_name}.pnl.v", f"verilog/gl/{macro_name}.v"
            )
            copy_print(
                f"{lastrun}/final/nl/{macro_name}.nl.v", f"verilog/gl/{macro_name}.nl.v"
            )
            shutil.copytree(
                f"{lastrun}/final/spef",
                f"spef/",
                copy_function=copy_print,
                dirs_exist_ok=True,
            )
        # Copy power gate macros:
        for macro in ["tt_pg_1v8_1", "tt_pg_1v8_2", "tt_pg_1v8_4", "tt_pg_3v3_2"]:
            copy_print(
                f"tt-multiplexer/pg/{macro}/gds/{macro}.gds",
                f"gds/{macro}.gds",
            )
            copy_print(
                f"tt-multiplexer/pg/{macro}/lef/{macro}.lef",
                f"lef/{macro}.lef",
            )
            copy_print(
                f"tt-multiplexer/pg/{macro}/src/{macro}.v",
                f"verilog/gl/{macro}.v",
            )

    def create_efabless_submission(self):
        logging.info("creating efabless submission directory:")
        lastrun = self.find_last_run("tt_top")
        copy_print("shuttle_index.md", "efabless/README.md")
        copy_print("shuttle_index.json", "efabless/shuttle_index.json")
        copy_print("verilog/rtl/user_defines.v", "efabless/verilog/rtl/user_defines.v")
        copy_print(
            f"{lastrun}/final/pnl/{self.tt_top_macro}.pnl.v",
            f"efabless/verilog/gl/{self.tt_top_macro}.v",
        )
        copy_print(
            f"{lastrun}/final/gds/{self.tt_top_macro}.gds",
            f"efabless/gds/{self.tt_top_macro}.gds",
        )
