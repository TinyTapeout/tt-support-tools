import glob
import json
import logging
import os
import shutil

import git
import yaml


def copy_print(src: str, dest: str):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    logging.info(f"  -> {dest}")
    shutil.copy2(src, dest)


def copy_print_glob(pattern: str, dest_dir: str):
    for file in glob.glob(pattern):
        copy_print(file, os.path.join(dest_dir, os.path.basename(file)))


class ShuttleConfig:
    def __init__(self, config, projects, modules_yaml_name: str):
        self.config = config
        self.projects = projects
        self.script_dir = os.path.dirname(os.path.realpath(__file__))
        self.modules_yaml_name = modules_yaml_name
        if config.get("openframe", False):
            self.tt_top_macro = "openframe_project_wrapper"
        else:
            self.tt_top_macro = "user_project_wrapper"

    def configure_mux(self):
        with open(self.modules_yaml_name, "r") as modules_file:
            module_config = yaml.safe_load(modules_file)
            configured_macros = set(
                map(lambda mod: mod["name"], module_config["modules"])
            )
            logging.info(
                f"found {len(configured_macros)} preconfigured macros: {configured_macros}"
            )
            for project in self.projects:
                tiles = project.yaml["project"]["tiles"]
                width, height = map(int, tiles.split("x"))
                if project.unprefixed_name not in configured_macros:
                    module_config["modules"].append(
                        {
                            "name": project.unprefixed_name,
                            "width": width,
                            "height": height,
                            "pg_vdd": True if project.power_gated else None,
                        }
                    )

        with open("tt-multiplexer/cfg/modules.yaml", "w") as mux_modules_file:
            yaml.dump(module_config, mux_modules_file)

        res = os.system("make -C tt-multiplexer clean gensrc")
        if res != 0:
            logging.error("Failed to generate multiplexer placement configuration")
            exit(1)

        mux_index = {}
        mux_index_reverse = {}
        with open("tt-multiplexer/cfg/modules_placed.yaml") as placed_modules_file:
            placed_modules = yaml.safe_load(placed_modules_file)
            for module in placed_modules["modules"]:
                mux_address = (module["mux_id"] << 5) | module["blk_id"]
                module_name = "tt_um_" + module["name"]
                project = next(p for p in self.projects if p.top_module == module_name)
                project.mux_address = mux_address
                mux_index[mux_address] = {
                    "macro": module_name,
                    "x": module["x"],
                    "y": module["y"],
                    "tiles": f"{module['width']}x{module['height']}",
                    "repo": project.git_url,
                    "commit": project.commit_id,
                    "features": {
                        "power_switch": bool(module["pg_vdd"]),
                        "analog": module["analog"],
                    },
                }
                mux_index_reverse[module_name] = mux_address

        for project in self.projects:
            if project.top_module not in mux_index_reverse:
                logging.error(f"no placement found for {project}!")
                exit(1)
            project.mux_address = mux_index_reverse[project.top_module]

        repo = git.Repo(".")

        shuttle_index_data = {
            "shuttle": self.config["name"],
            "repo": list(repo.remotes[0].urls)[0],
            "commit": repo.commit().hexsha,
            "commit_date": repo.commit().committed_date,
            "version": 2,
            "mux": mux_index,
        }

        with open("shuttle_index.json", "w") as shuttle_index_file:
            json.dump(shuttle_index_data, shuttle_index_file, indent=2)

        with open("verilog/includes/includes.gl.user_projects", "w") as includes_file:
            for project in self.projects:
                if project.is_chip_rom():
                    continue
                includes_file.write(
                    f"$(USER_PROJECT_VERILOG)/../projects/{project.top_module}/{project.top_module}.v\n"
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
        # Copy power gate macros:
        for macro in ["tt_pg_vdd_1", "tt_pg_vdd_2"]:
            copy_print(
                f"tt-multiplexer/pg/{macro}/{macro}.gds",
                f"tt-multiplexer/ol2/tt_top/gds/{macro}.gds",
            )
            copy_print(
                f"tt-multiplexer/pg/{macro}/{macro}.lef",
                f"tt-multiplexer/ol2/tt_top/lef/{macro}.lef",
            )
            copy_print(
                f"tt-multiplexer/pg/{macro}/{macro}.v",
                f"tt-multiplexer/ol2/tt_top/verilog/{macro}.v",
            )

    def copy_final_results(self):
        macros = ["tt_um_chip_rom", "tt_ctrl", "tt_mux", "tt_top"]

        logging.info("copying final results:")
        for macro in macros:
            lastrun = self.find_last_run(macro)
            macro_name = macro if macro != "tt_top" else self.tt_top_macro
            logging.info(f"** {macro_name} **")
            logging.info(f"  FROM {lastrun}")
            copy_print(f"{lastrun}/final/gds/{macro_name}.gds", f"gds/{macro_name}.gds")
            copy_print(f"{lastrun}/final/lef/{macro_name}.lef", f"lef/{macro_name}.lef")
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
        for macro in ["tt_pg_vdd_1", "tt_pg_vdd_2"]:
            copy_print(
                f"tt-multiplexer/pg/{macro}/{macro}.gds",
                f"gds/{macro}.gds",
            )
            copy_print(
                f"tt-multiplexer/pg/{macro}/{macro}.lef",
                f"lef/{macro}.lef",
            )
            copy_print(
                f"tt-multiplexer/pg/{macro}/{macro}.v",
                f"verilog/gl/{macro}.v",
            )

    def create_efabless_submission(self):
        logging.info("creating efabless submission directory:")
        lastrun = self.find_last_run("tt_top")
        copy_print("README.md", "efabless/README.md")
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
        copy_print(
            f"{lastrun}/final/lef/{self.tt_top_macro}.lef",
            f"efabless/lef/{self.tt_top_macro}.lef",
        )
