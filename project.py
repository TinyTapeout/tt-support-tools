import copy
import csv
import glob
import json
import logging
import os
import re
import shutil
import subprocess
import typing

import cairosvg  # type: ignore
import chevron
import gdstk  # type: ignore
import klayout.db as pya
import yaml
from git.repo import Repo

import git_utils
from config_utils import read_config, write_config
from markdown_utils import limit_markdown_headings
from project_info import ProjectInfo, ProjectYamlError
from tech import TechName, tech_map

PINOUT_KEYS = [
    "ui[0]",
    "ui[1]",
    "ui[2]",
    "ui[3]",
    "ui[4]",
    "ui[5]",
    "ui[6]",
    "ui[7]",
    "uo[0]",
    "uo[1]",
    "uo[2]",
    "uo[3]",
    "uo[4]",
    "uo[5]",
    "uo[6]",
    "uo[7]",
    "uio[0]",
    "uio[1]",
    "uio[2]",
    "uio[3]",
    "uio[4]",
    "uio[5]",
    "uio[6]",
    "uio[7]",
]

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


class Project:
    top_verilog_filename: str
    mux_address: int
    analog_pins: tuple[int, ...]
    commit_id: str
    sort_id: int

    def __init__(
        self,
        index: int,
        git_url: str,
        local_dir: str,
        pdk: TechName,
        is_user_project: bool,
    ):
        self.git_url = git_url
        self.pdk = pdk
        self.tech = tech_map[pdk]
        self.index = index
        self.local_dir = os.path.realpath(local_dir)
        self.is_user_project = is_user_project
        self.src_dir = (
            os.path.join(self.local_dir, "src")
            if self.is_user_project
            else self.local_dir
        )
        self.test_dir = (
            os.path.join(self.local_dir, "test")
            if self.is_user_project
            else self.local_dir
        )

        yaml_path = os.path.join(self.local_dir, "info.yaml")
        try:
            with open(yaml_path) as fh:
                self.info = ProjectInfo(yaml.safe_load(fh), self.get_tile_sizes())
        except FileNotFoundError:
            logging.error(
                f"yaml file not found for {self} - do you need to --clone the project repos?"
            )
            exit(1)
        except ProjectYamlError as e:
            logging.error(f"Error loading {yaml_path}: {e}")
            exit(1)
        self.unprefixed_name = re.sub("^tt_um_", "", self.info.top_module)

        if self.is_user_project:
            self.sources = self.info.source_files
            if self.is_wokwi():
                self.top_verilog_filename = self.sources[0]
            else:
                if any(s.endswith(".vhdl") for s in self.sources):
                    self.transpile_vhdl()
                self.check_sources()
                self.top_verilog_filename = self.find_top_verilog()
        else:
            self.sources = [self.get_gl_verilog_filename()]

    def post_clone_setup(self):
        self.load_metrics()

    def load_metrics(self):
        try:
            with open(self.get_metrics_path()) as fh:
                self.metrics = dict(csv.reader(fh))
        except FileNotFoundError:
            self.metrics = {}

    def is_chip_rom(self):
        return self.get_macro_name() == "tt_um_chip_rom"

    def is_wokwi(self) -> bool:
        return hasattr(self.info, "wokwi_id")

    def is_hdl(self):
        return not self.is_wokwi()

    def check_sources(self):
        for filename in self.sources:
            if "*" in filename:
                logging.error("* not allowed, please specify each file")
                exit(1)
            if not os.path.exists(os.path.join(self.src_dir, filename)):
                logging.error(f"{filename} doesn't exist in the repo")
                exit(1)

    def run_yosys(self, command: str, no_output: bool = False):
        env = os.environ.copy()
        env["YOSYS_CMD"] = command
        yosys_cmd = 'yowasp-yosys -qp "$YOSYS_CMD"'
        return subprocess.run(yosys_cmd, shell=True, env=env, capture_output=no_output)

    def check_ports(self, include_power_ports: bool = False):
        top = self.get_macro_name()
        if not self.is_user_project and self.is_chip_rom():
            return  # Chip ROM is auto generated, so we don't have the verilog yet
        sources = [os.path.join(self.src_dir, src) for src in self.sources]
        source_list = " ".join(sources)

        json_file = "ports.json"

        # Heuristic - try reading just the first source file, if that fails, try all of them
        p = self.run_yosys(
            f"read_verilog -lib -sv {sources[0]}; hierarchy -top {top} ; proc; write_json {json_file}",
            True,
        )
        if p.returncode != 0:
            p = self.run_yosys(
                f"read_verilog -lib -sv {source_list}; hierarchy -top {top} ; proc; write_json {json_file}"
            )
        if p.returncode != 0:
            logging.error(f"yosys port read failed for {self}")
            exit(1)

        with open(json_file) as fh:
            ports = json.load(fh)
        os.unlink(json_file)

        module_ports = ports["modules"][top]["ports"]
        if "VPWR" in module_ports:
            if "VDPWR" in module_ports:
                logging.error(
                    f"{self} top module '{top}' uses both VPWR and VDPWR ports"
                )
                exit(1)
            else:
                logging.info(
                    f"{self} top module '{top}' uses VPWR port, substituting VDPWR"
                )
                module_ports["VDPWR"] = module_ports["VPWR"]
                del module_ports["VPWR"]

        required_ports = [
            ["input", "clk", 1],
            ["input", "ena", 1],
            ["input", "rst_n", 1],
            ["input", "ui_in", 8],
            ["input", "uio_in", 8],
            ["output", "uio_oe", 8],
            ["output", "uio_out", 8],
            ["output", "uo_out", 8],
        ]
        if self.info.is_analog:
            required_ports += [
                ["inout", "ua", 8],
            ]
        if include_power_ports:
            required_ports += [
                [("input", "inout"), "VGND", 1],
                [("input", "inout"), "VDPWR", 1],
            ]
            if self.info.uses_3v3:
                required_ports += [
                    [("input", "inout"), "VAPWR", 1],
                ]
        for valid_directions, port, bits in required_ports:
            if port not in module_ports:
                logging.error(f"{self} port '{port}' missing from top module ('{top}')")
                exit(1)
            actual_direction = module_ports[port]["direction"]
            if type(valid_directions) is tuple:
                valid_directions_tuple = valid_directions
            else:
                valid_directions_tuple = (valid_directions,)
            if actual_direction not in valid_directions_tuple:
                logging.error(
                    f"{self} incorrect direction for port '{port}' in module '{top}': {valid_directions_tuple} required, {actual_direction} found"
                )
                exit(1)
            actual_bits = len(module_ports[port]["bits"])
            if actual_bits != bits:
                logging.error(
                    f"{self} incorrect width for port '{port}' in module '{top}': {bits} bits required, {actual_bits} found"
                )
                exit(1)
            del module_ports[port]
        if len(module_ports):
            logging.error(
                f"{self} module '{top}' has unsupported extra ports: {', '.join(module_ports.keys())}"
            )
            exit(1)

    def check_num_cells(self):
        num_cells = self.get_cell_count_from_synth()
        if self.is_hdl():
            if num_cells < 20:
                logging.warning(f"{self} only has {num_cells} cells")
        else:
            if num_cells < 11:
                logging.warning(f"{self} only has {num_cells} cells")

    # docs stuff for index on README.md
    def get_index_row(self):
        return f"| {self.mux_address} | {self.info.author} | {self.info.title} | {self.get_project_type_string()} | {self.git_url} |\n"

    def get_project_type_string(self):
        if self.is_wokwi():
            return f"[Wokwi]({self.get_wokwi_url()})"
        elif self.info.is_analog:
            return "Analog"
        else:
            return "HDL"

    def get_project_docs_dict(self):
        docs = self.info.__dict__.copy()
        docs["project_type"] = self.get_project_type_string()
        docs["git_url"] = self.git_url
        with open(os.path.join(self.local_dir, "docs/info.md")) as fh:
            docs["user_docs"] = limit_markdown_headings(fh.read(), min_level=3)
        return docs

    def get_wokwi_url(self):
        return f"https://wokwi.com/projects/{self.info.wokwi_id}"

    # top module name is defined in one of the source files, which one?
    def find_top_verilog(self):
        rgx_mod = re.compile(r"(?:^|[\s])module[\s]{1,}([\w]+)")
        top_verilog: typing.List[str] = []
        top_module = self.info.top_module
        for src in self.sources:
            with open(os.path.join(self.src_dir, src)) as fh:
                for line in fh.readlines():
                    for match in rgx_mod.finditer(line):
                        if match.group(1) == top_module:
                            top_verilog.append(src)
        if len(top_verilog) == 0:
            logging.error(
                f"Couldn't find verilog module '{top_module}' in any of the project's source files"
            )
            exit(1)
        if len(top_verilog) > 1:
            logging.error(
                f"Top verilog module '{top_module}' found in multiple source files: {', '.join(top_verilog)}"
            )
            exit(1)
        return top_verilog[0]

    def get_git_remote(self):
        return list(Repo(self.local_dir).remotes[0].urls)[0]

    def get_git_commit_hash(self):
        return Repo(self.local_dir).commit().hexsha

    def get_tt_tools_version(self):
        repo = Repo(os.path.join(self.local_dir, "tt"))
        return f"{repo.active_branch.name} {repo.commit().hexsha[:8]}"

    def read_commit_info_json(self) -> typing.Dict[str, typing.Any]:
        json_file = os.path.join(self.local_dir, "commit_id.json")
        with open(json_file) as fh:
            return json.load(fh)

    def get_workflow_url_when_submitted(self) -> str:
        commit_info = self.read_commit_info_json()
        return commit_info["workflow_url"]

    def get_workflow_url(self):
        GITHUB_SERVER_URL = os.getenv("GITHUB_SERVER_URL")
        GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
        GITHUB_RUN_ID = os.getenv("GITHUB_RUN_ID")
        if GITHUB_SERVER_URL and GITHUB_REPOSITORY and GITHUB_RUN_ID:
            return (
                f"{GITHUB_SERVER_URL}/{GITHUB_REPOSITORY}/actions/runs/{GITHUB_RUN_ID}"
            )

    def __str__(self):
        return f"[{self.index:03} : {self.git_url}]"

    def get_latest_action_url(self):
        return git_utils.get_latest_action_url(self.git_url)

    def get_macro_name(self):
        return self.info.top_module

    # unique id
    def get_index(self):
        return self.index

    # metrics
    def get_metrics_path(self):
        if self.is_user_project:
            return os.path.join(self.local_dir, "runs/wokwi/final/metrics.csv")
        else:
            return os.path.join(self.local_dir, "stats/metrics.csv")

    def get_gl_path(self):
        if self.is_user_project:
            return glob.glob(
                os.path.join(self.local_dir, "runs/wokwi/final/nl/*.nl.v")
            )[0]
        else:
            return os.path.join(self.local_dir, f"{self.info.top_module}.v")

    def get_tile_sizes(self):
        tile_sizes_yaml = f"tech/{self.pdk}/tile_sizes.yaml"
        with open(
            os.path.join(os.path.dirname(__file__), tile_sizes_yaml), "r"
        ) as stream:
            tile_sizes = yaml.safe_load(stream)
        return tile_sizes

    # name of the gds file
    def get_macro_gds_filename(self):
        return f"{self.info.top_module}.gds"

    def get_macro_info_filename(self):
        return f"{self.info.top_module}.info.json"

    def get_macro_lef_filename(self):
        return f"{self.info.top_module}.lef"

    def get_macro_spef_filename(self):
        return f"{self.info.top_module}.spef"

    # for GL sims & blackboxing
    def get_gl_verilog_filename(self):
        return f"{self.info.top_module}.v"

    # for simulations
    def get_top_verilog_filename(self):
        if self.is_hdl():
            # make sure it's unique & without leading directories
            # a few people use 'top.v', which is OK as long as the top module is called something more unique
            # but then it needs to be made unique so the source can be found
            filename = os.path.basename(self.top_verilog_filename)
            return f"{self.index :03}_{filename}"
        else:
            return self.top_verilog_filename

    def get_git_url(self):
        return self.git_url

    def print_wokwi_id(self):
        print(self.info.wokwi_id)

    def print_top_module(self):
        print(self.info.top_module)

    def fetch_wokwi_files(self):
        logging.info("fetching wokwi files")
        src_file = self.info.source_files[0]
        url = f"https://wokwi.com/api/projects/{self.info.wokwi_id}/verilog"
        git_utils.fetch_file(url, os.path.join(self.src_dir, src_file))

        # also fetch the wokwi diagram
        url = f"https://wokwi.com/api/projects/{self.info.wokwi_id}/diagram.json"
        diagram_file = "wokwi_diagram.json"
        git_utils.fetch_file(url, os.path.join(self.src_dir, diagram_file))

        # attempt to download the *optional* truthtable for the project
        truthtable_file = "truthtable.md"
        url = f"https://wokwi.com/api/projects/{self.info.wokwi_id}/{truthtable_file}"
        try:
            git_utils.fetch_file(url, os.path.join(self.test_dir, truthtable_file))
            logging.info(
                f"Wokwi project {self.info.wokwi_id} has a truthtable included, will test!"
            )
            self.install_wokwi_testing()
        except FileNotFoundError:
            pass

    def install_wokwi_testing(
        self, destination_dir: str = "test", resource_dir: typing.Optional[str] = None
    ):
        if resource_dir is None or not len(resource_dir):
            resource_dir = os.path.join(os.path.dirname(__file__), "testing")

        # directories in testing/lib to copy over
        pyLibsDir = os.path.join(resource_dir, "lib")

        # src template dir
        srcTplDir = os.path.join(resource_dir, "src-tpl")

        for libfullpath in glob.glob(os.path.join(pyLibsDir, "*")):
            logging.info(f"Copying {libfullpath} to {destination_dir}")
            shutil.copytree(
                libfullpath,
                os.path.join(destination_dir, os.path.basename(libfullpath)),
                dirs_exist_ok=True,
            )

        for srcTemplate in glob.glob(os.path.join(srcTplDir, "*")):
            with open(srcTemplate, "r") as f:
                contents = f.read()
                customizedContents = re.sub(
                    "WOKWI_ID", str(self.info.wokwi_id), contents
                )
                outputFname = os.path.basename(srcTemplate)
                with open(os.path.join(destination_dir, outputFname), "w") as outf:
                    logging.info(f"writing src tpl to {outputFname}")
                    outf.write(customizedContents)
                    outf.close()

    def transpile_vhdl(self):
        # logging.info("transpiling vhdl sources")
        new_sources = []
        for s in self.sources:
            if s.endswith(".vhdl"):
                # logging.info(f"running ghdl on {s}")
                t = "generated/" + s.replace(".vhdl", ".v")
                s_full = os.path.join(self.src_dir, s)
                t_full = os.path.join(self.src_dir, t)
                os.makedirs(os.path.dirname(t_full), exist_ok=True)
                transpile_cmd = f"ghdl synth -Wno-binding --std=08 --out=verilog {s_full} -e > {t_full}"
                p = subprocess.run(transpile_cmd, shell=True)
                if p.returncode != 0:
                    logging.error("transpile failed")
                    exit(1)
                new_sources.append(t)
            else:
                new_sources.append(s)
        self.sources = new_sources

    def create_merged_config(self):
        config = read_config("src/config")
        user_config = read_config("src/user_config")
        config.update(user_config)
        write_config(config, "src/config_merged")

    def create_user_config(self):
        if self.is_wokwi():
            self.fetch_wokwi_files()
        self.check_ports()
        logging.info("creating include file")
        tiles = self.info.tiles
        tile_sizes = self.get_tile_sizes()
        die_area = tile_sizes[tiles]
        def_suffix = self.tech.def_suffix
        def_template = (
            f"dir::../tt/tech/{self.pdk}/def/tt_block_{tiles}_{def_suffix}.def"
        )
        config = {
            "DESIGN_NAME": self.info.top_module,
            "VERILOG_FILES": [f"dir::{src}" for src in self.sources],
            "DIE_AREA": die_area,
            "FP_DEF_TEMPLATE": def_template,
            "VDD_PIN": "VPWR",
            "GND_PIN": "VGND",
            "RT_MAX_LAYER": self.tech.project_top_metal_layer,
        }
        write_config(config, os.path.join(self.src_dir, "user_config"), ("json",))
        self.create_merged_config()

    def golden_harden(self):
        logging.info(f"hardening {self}")
        shutil.copyfile("golden_config.json", os.path.join(self.src_dir, "config.json"))
        self.harden()

    def harden(self):
        cwd = os.getcwd()
        os.chdir(self.local_dir)

        repo = self.get_git_remote()
        commit_hash = self.get_git_commit_hash()
        tt_version = self.get_tt_tools_version()
        workflow_url = self.get_workflow_url()

        self.create_merged_config()
        shutil.rmtree("runs/wokwi", ignore_errors=True)
        os.makedirs("runs/wokwi", exist_ok=True)
        arg_progress = "--hide-progress-bar" if "CI" in os.environ else ""
        arg_pdk_root = '--pdk-root "$PDK_ROOT"' if "PDK_ROOT" in os.environ else ""
        arg_pdk = self.tech.librelane_pdk_args
        harden_cmd = f"python -m librelane {arg_pdk_root} --docker-no-tty --dockerized {arg_pdk_root} {arg_pdk} --run-tag wokwi --force-run-dir runs/wokwi {arg_progress} src/config_merged.json"
        env = os.environ.copy()
        logging.debug(harden_cmd)
        p = subprocess.run(harden_cmd, shell=True, env=env)
        if p.returncode != 0:
            logging.error("harden failed")
            exit(1)

        # Write commit information
        commit_id_json_path = "runs/wokwi/final/commit_id.json"
        with open(os.path.join(self.local_dir, commit_id_json_path), "w") as f:
            json.dump(
                {
                    "app": f"Tiny Tapeout {tt_version}",
                    "repo": repo,
                    "commit": commit_hash,
                    "workflow_url": workflow_url,
                },
                f,
                indent=2,
            )
            f.write("\n")
        run_dir = os.path.join(self.local_dir, "runs/wokwi")
        with open(os.path.join(run_dir, "resolved.json"), "r") as f:
            ll_config = json.load(f)
        librelane_version = ll_config["meta"]["librelane_version"]
        with open(os.path.join(run_dir, "pdk.json"), "w") as f:
            pdk_version_info = self.tech.read_pdk_version(ll_config["PDK_ROOT"])
            pdk_json = {
                "FLOW_NAME": "LibreLane",
                "FLOW_VERSION": librelane_version,
                "PDK": ll_config["PDK"],
                "PDK_SOURCE": pdk_version_info["source"],
                "PDK_VERSION": pdk_version_info["version"],
            }
            json.dump(pdk_json, f, indent=2)

        os.chdir(cwd)

    def create_tt_submission(self):
        top_module = self.get_macro_name()
        logging.info(f"Creating TT submission for {top_module}")
        tt_submission_dir = os.path.join(self.local_dir, "tt_submission")
        shutil.rmtree(tt_submission_dir, ignore_errors=True)
        stats_dir = os.path.join(tt_submission_dir, "stats")
        os.makedirs(stats_dir, exist_ok=True)
        run_dir = os.path.join(self.local_dir, "runs/wokwi")
        final_dir = os.path.join(run_dir, "final")

        # Convert to OAS:
        # strm2oas tt_submission/${TOP_MODULE}.gds tt_submission/${TOP_MODULE}.oas
        oas_file = os.path.join("tt_submission", f"{top_module}.oas")
        gds_file = os.path.join(final_dir, "gds", f"{top_module}.gds")
        layout = pya.Layout()
        layout.read(gds_file)
        layout.set_property("TT_PDK", self.pdk)
        layout.write(oas_file)

        files_to_copy = [
            os.path.join(run_dir, "pdk.json"),
            os.path.join(run_dir, "resolved.json"),
            os.path.join(final_dir, "commit_id.json"),
            os.path.join(final_dir, "gds", f"{top_module}.gds"),
            os.path.join(final_dir, "lef", f"{top_module}.lef"),
            *glob.glob(os.path.join(final_dir, "spef/*/*.spef")),
        ]
        for file in files_to_copy:
            shutil.copyfile(
                file, os.path.join(tt_submission_dir, os.path.basename(file))
            )

        # GL netlist
        gl_type = self.tech.netlist_type
        gl_file = os.path.join(final_dir, gl_type, f"{top_module}.{gl_type}.v")
        shutil.copyfile(gl_file, os.path.join(tt_submission_dir, f"{top_module}.v"))

        # Stats:
        shutil.copyfile(
            os.path.join(final_dir, "metrics.csv"),
            os.path.join(stats_dir, "metrics.csv"),
        )
        (yosys_synth_dir,) = glob.glob(os.path.join(run_dir, "*yosys-synthesis"))
        shutil.copyfile(
            os.path.join(yosys_synth_dir, "reports", "stat.rpt"),
            os.path.join(stats_dir, "synthesis-stats.txt"),
        )

    def create_fpga_bitstream(self, args):
        logging.info(f"Creating FPGA bitstream for {self}")

        target_map = {
            "classic": {
                "pcf": "tt_fpga_top.pcf",
                "def_name": "tt_fpga",
            },
            "fabricfox": {"pcf": "tt_fpga_fabricfox.pcf", "def_name": "tt_ff_fpga"},
        }
        pcf_file = target_map[args.fpga_breakout_target]["pcf"]

        base_name = args.fpga_bitstream_name
        if not len(base_name):
            base_name = target_map[args.fpga_breakout_target]["def_name"]

        with open(os.path.join(SCRIPT_DIR, "fpga/tt_fpga_top.v"), "r") as f:
            top_module_template = f.read()

        with open(os.path.join(self.src_dir, "_tt_fpga_top.v"), "w") as f:
            f.write(
                top_module_template.replace("__tt_um_placeholder", self.info.top_module)
            )

        build_dir = os.path.join(self.local_dir, "build")
        os.makedirs(build_dir, exist_ok=True)

        sources = [os.path.join(self.src_dir, src) for src in self.sources]
        source_list = " ".join(sources)

        yosys_cmd = f"yosys -l {build_dir}/01-synth.log -DSYNTH -p 'synth_ice40 -top tt_fpga_top -json {build_dir}/{base_name}.json' src/_tt_fpga_top.v {source_list}"
        logging.debug(yosys_cmd)
        p = subprocess.run(yosys_cmd, shell=True)
        if p.returncode != 0:
            logging.error("synthesis failed")
            exit(1)

        seed = os.getenv("TT_FPGA_SEED", "10")
        freq = os.getenv("TT_FPGA_FREQ", "12")

        nextpnr_cmd = f"nextpnr-ice40 -l {build_dir}/02-nextpnr.log --pcf-allow-unconstrained --seed {seed} --freq {freq} --package sg48 --up5k --asc {build_dir}/{base_name}.asc --pcf {SCRIPT_DIR}/fpga/{pcf_file} --json {build_dir}/{base_name}.json"
        logging.debug(nextpnr_cmd)
        p = subprocess.run(nextpnr_cmd, shell=True)
        if p.returncode != 0:
            logging.error("placement failed")
            exit(1)

        icepack_cmd = f"icepack {build_dir}/{base_name}.asc {build_dir}/{base_name}.bin"
        logging.debug(icepack_cmd)
        p = subprocess.run(icepack_cmd, shell=True)
        if p.returncode != 0:
            logging.error("bitstream creation failed failed")
            exit(1)

        logging.info(f"Bitstream created successfully: {build_dir}/{base_name}.bin")

    # doc check
    # makes sure that the basic info is present
    def check_docs(self):
        info_md = os.path.join(self.local_dir, "docs/info.md")
        if not os.path.exists(info_md):
            logging.error("Missing docs/info.md file")
            exit(1)

        with open(info_md) as fh:
            info_md_content = fh.read()

        if "# How it works\n\nExplain how your project works" in info_md_content:
            logging.error("Missing 'How it works' section in docs/info.md")
            exit(1)

        if "# How to test\n\nExplain how to use your project" in info_md_content:
            logging.error("Missing 'How to test' section in docs/info.md")
            exit(1)

    # use pandoc to create a single page PDF preview
    def create_pdf(self):
        template_args = copy.deepcopy(self.info.__dict__)
        template_args.update(
            {
                "pins": [
                    {
                        "pin_index": str(i),
                        "ui": self.info.pinout.ui[i],
                        "uo": self.info.pinout.uo[i],
                        "uio": self.info.pinout.uio[i],
                    }
                    for i in range(8)
                ],
                "analog_pins": [
                    {
                        "ua_index": str(i),
                        "analog_index": "?",
                        "desc": desc,
                    }
                    for i, desc in enumerate(self.info.pinout.ua)
                ],
                "is_analog": self.info.is_analog,
                "uses_3v3": self.info.uses_3v3,
            }
        )

        logging.info("Creating PDF")
        with open(os.path.join(SCRIPT_DIR, "docs/project_header.md")) as fh:
            doc_header = fh.read()
        with open(os.path.join(SCRIPT_DIR, "docs/project_preview.md.mustache")) as fh:
            doc_template = fh.read()
        info_md = os.path.join(self.local_dir, "docs/info.md")
        with open(info_md) as fh:
            template_args["info"] = fh.read()

        with open("datasheet.md", "w") as fh:
            fh.write(doc_header)

            # now build the doc & print it
            try:
                doc = chevron.render(doc_template, template_args)
                fh.write(doc)
                fh.write("\n```{=latex}\n\\pagebreak\n```\n")
            except IndexError:
                logging.warning("missing pins in info.yaml, skipping")

        pdf_cmd = "pandoc --pdf-engine=xelatex --resource-path=docs -i datasheet.md -o datasheet.pdf --from gfm+raw_attribute+smart+attributes"
        logging.info(pdf_cmd)
        p = subprocess.run(pdf_cmd, shell=True)
        if p.returncode != 0:
            logging.error("pdf generation failed")
            raise RuntimeError(f"pdf generation failed with code {p.returncode}")

    # Read and return top-level GDS data from the final GDS file, using gdstk:
    def get_final_gds_top_cells(self):
        if "GDS_PATH" in os.environ:
            gds_path = os.environ["GDS_PATH"]
        else:
            gds_path = glob.glob(
                os.path.join(self.local_dir, "runs/wokwi/final/gds/*.gds")
            )[0]
        library = gdstk.read_gds(gds_path)
        top_cells = library.top_level()
        return top_cells[0]

    # SVG render of the GDS.
    # NOTE: This includes all standard GDS layers inc. text labels.
    def create_svg(self):
        top_cells = self.get_final_gds_top_cells()
        top_cells.write_svg("gds_render.svg")

    # Try various QUICK methods to create a more-compressed PNG render of the GDS,
    # and fall back to cairosvg if it doesn't work. This is designed for speed,
    # and in particular for use by the GitHub Actions.
    # For more info, see:
    # https://github.com/TinyTapeout/tt-gds-action/issues/8
    def create_png(self):
        logging.info("Loading GDS data...")
        top_cells = self.get_final_gds_top_cells()

        # Remove label layers (i.e. delete text), then generate SVG:
        label_layers = self.tech.label_layers
        top_cells.filter(label_layers)
        for subcell in top_cells.dependencies(True):
            subcell.filter(label_layers)
        svg = "gds_render_preview.svg"
        logging.info("Rendering SVG without text label layers: {}".format(svg))
        top_cells.write_svg(svg, pad=0)
        # We should now have gds_render_preview.svg

        # Try converting using 'rsvg-convert' command-line utility.
        # This should create gds_render_preview.png
        png = "gds_render_preview.png"
        logging.info("Converting to PNG using rsvg-convert: {}".format(png))

        cmd = "rsvg-convert --unlimited {} -o {} --no-keep-image-data".format(svg, png)
        logging.debug(cmd)
        p = subprocess.run(cmd, shell=True, capture_output=True)

        if p.returncode == 127:
            logging.warning(
                'rsvg-convert not found; is package "librsvg2-bin" installed? Falling back to cairosvg. This might take a while...'
            )
            # Fall back to cairosvg:
            cairosvg.svg2png(url=svg, write_to=png)

        elif p.returncode != 0 and b"cannot load more than" in p.stderr:
            logging.warning(
                'Too many SVG elements ("{}"). Reducing complexity...'.format(
                    p.stderr.decode().strip()
                )
            )

            # Remove more layers that are hardly visible anyway:
            buried_layers = self.tech.buried_layers
            top_cells.filter(buried_layers)
            for subcell in top_cells.dependencies(True):
                subcell.filter(buried_layers)
            svg_alt = "gds_render_preview_alt.svg"
            logging.info("Rendering SVG with more layers removed: {}".format(svg_alt))
            top_cells.write_svg(svg_alt, pad=0)
            logging.info("Converting to PNG using rsvg-convert: {}".format(png))

            cmd = "rsvg-convert --unlimited {} -o {} --no-keep-image-data".format(
                svg_alt, png
            )
            logging.debug(cmd)
            p = subprocess.run(cmd, shell=True, capture_output=True)

            if p.returncode != 0:
                logging.warning(
                    'Still cannot convert to SVG ("{}"). Falling back to cairosvg. This might take a while...'.format(
                        p.stderr.decode().strip()
                    )
                )

                # Fall back to cairosvg, and since we're doing that, might as well use the original full-detail SVG anyway:
                cairosvg.svg2png(url=svg, write_to=png)

        # By now we should have gds_render_preview.png

        # Compress with pngquant:
        final_png = "gds_render.png"
        if self.info.tiles == "8x2":
            quality = "0-10"  # Compress more for 8x2 tiles.
        else:
            quality = "0-30"
        logging.info("Compressing PNG further with pngquant to: {}".format(final_png))

        cmd = "pngquant --quality {} --speed 1 --nofs --strip --force --output {} {}".format(
            quality, final_png, png
        )
        logging.debug(cmd)
        p = subprocess.run(cmd, shell=True, capture_output=True)

        if p.returncode == 127:
            logging.warning(
                'pngquant not found; is package "pngquant" installed? Using intermediate (uncompressed) PNG file'
            )
            os.rename(png, final_png)
        elif p.returncode != 0:
            logging.warning(
                'pngquant error {} ("{}"). Using intermediate (uncompressed) PNG file'.format(
                    p.returncode, p.stderr.decode().strip()
                )
            )
            os.rename(png, final_png)
        logging.info(
            "Final PNG is {} ({:,} bytes)".format(final_png, os.path.getsize(final_png))
        )

    def print_warnings(self):
        warnings: typing.List[str] = []

        synth_log_glob = "runs/wokwi/*-yosys-synthesis/yosys-synthesis.log"
        synth_log = glob.glob(os.path.join(self.local_dir, synth_log_glob))[0]
        with open(os.path.join(self.local_dir, synth_log)) as f:
            for line in f.readlines():
                if line.startswith("Warning:"):
                    # bogus warning https://github.com/YosysHQ/yosys/commit/bfacaddca8a2e113e4bc3d6177612ccdba1555c8
                    if "WIDTHLABEL" not in line:
                        warnings.append(line.strip())

        tt_corner = self.tech.tt_corner
        sta_report_glob = f"runs/wokwi/*-openroad-stapostpnr/{tt_corner}/checks.rpt"
        sta_report = glob.glob(os.path.join(self.local_dir, sta_report_glob))[0]
        with open(os.path.join(self.local_dir, sta_report)) as f:
            for line in f.readlines():
                if line.startswith("Warning:") and "clock" in line:
                    warnings.append(line.strip())

        if len(warnings):
            print("# Synthesis warnings")
            print()
            for warning in warnings:
                print(f"* {warning}")

    def print_stats(self):
        util_glob = "runs/wokwi/*-openroad-globalplacement/openroad-globalplacement.log"
        util_log = glob.glob(os.path.join(self.local_dir, util_glob))[0]
        util_regexp = r"^\[INFO GPL-0019\] (Util|Utilization):"
        util_line = next(line for line in open(util_log) if re.match(util_regexp, line))
        util = re.sub(util_regexp, "", util_line).strip()

        try:
            wire_length = self.metrics["route__wirelength"]  # OpenROAD #2047
        except KeyError:
            wire_length = self.metrics["detailedroute__route__wirelength"]

        print("# Routing stats")
        print()
        print("| Utilisation (%) | Wire length (um) |")
        print("|-------------|------------------|")
        print("| {} | {} |".format(util, wire_length))

    # Print the summaries
    def summarize(self, print_cell_category: bool, print_cell_summary: bool):
        cell_count = self.get_cell_counts_from_gl()

        Categories = typing.TypedDict(
            "Categories", {"categories": typing.List[str], "map": typing.Dict[str, int]}
        )
        categories_file = f"tech/{self.pdk}/categories.json"
        with open(os.path.join(SCRIPT_DIR, categories_file)) as fh:
            categories: Categories = json.load(fh)

        cell_defs = self.tech.load_cell_definitions()

        # print all used cells, sorted by frequency
        total = 0
        if print_cell_summary:
            print("# Cell usage")
            print()
            print("| Cell Name | Description | Count |")
            print("|-----------|-------------|-------|")
            for name, count in sorted(
                cell_count.items(), key=lambda item: item[1], reverse=True
            ):
                if count > 0:
                    total += count
                    cell_def = cell_defs.get(name)
                    if cell_def is not None:
                        cell_link = cell_def["url"]
                        description = cell_def["description"]
                        print(f"| [{name}]({cell_link}) | {description} |{count} |")
                    else:
                        print(f"| {name} | (unknown) | {count} |")

            print(f"| | Total | {total} |")

        if print_cell_category:
            CategoryInfo = typing.TypedDict(
                "CategoryInfo", {"count": int, "examples": typing.List[str]}
            )
            by_category: typing.Dict[str, CategoryInfo] = {}
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

                if cat_name not in ["Fill", "Tap"]:
                    total += cell_count[cell_name]

            print("# Cell usage by Category")
            print()
            print("| Category | Cells | Count |")
            print("|---------------|----------|-------|")
            for cat_name, cat_dict in sorted(
                by_category.items(), key=lambda x: x[1]["count"], reverse=True
            ):
                cell_links = []
                for name in cat_dict["examples"]:
                    cell_def = cell_defs.get(name)
                    if cell_def is not None:
                        cell_links.append(f"[{name}]({cell_def['url']})")
                    else:
                        cell_links.append(name)

                print(f'|{cat_name} | {" ".join(cell_links)} | {cat_dict["count"]}|')

            print(f"## {total} total cells (excluding fill and tap cells)")

    # get cell count from synth report
    def get_cell_count_from_synth(self):
        num_cells = 0
        try:
            yosys_report = f"{self.local_dir}/stats/synthesis-stats.txt"
            with open(yosys_report) as fh:
                for line in fh.readlines():
                    m = re.search(r"Number of cells:\s+(\d+)", line)
                    if m is not None:
                        num_cells = int(m.group(1))

        except (IndexError, FileNotFoundError):
            logging.warning(f"couldn't open yosys cell report for cell checking {self}")

        return num_cells

    # Parse the lib, cell and drive strength an LibreLane gate-level Verilog file
    def get_cell_counts_from_gl(self):
        cell_count: typing.Dict[str, int] = {}
        total = 0
        with open(self.get_gl_path()) as fh:
            for line in fh.readlines():
                m = re.search(self.tech.cell_regexp, line)
                if m is not None:
                    total += 1
                    gd = m.groupdict()
                    cell_lib = gd.get("cell_lib", "")
                    cell_name = gd["cell_name"]
                    assert cell_lib in ["fd_sc_hd", "ef_sc_hd", ""]
                    try:
                        cell_count[cell_name] += 1
                    except KeyError:
                        cell_count[cell_name] = 1
        return cell_count
