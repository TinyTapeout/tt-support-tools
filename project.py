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
import yaml
from git.repo import Repo

import git_utils
from cells import Cell, load_cells
from markdown_utils import limit_markdown_headings
from project_info import ProjectInfo, ProjectYamlError

CELL_URL = "https://skywater-pdk.readthedocs.io/en/main/contents/libraries/sky130_fd_sc_hd/cells/"

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


with open(os.path.join(os.path.dirname(__file__), "tile_sizes.yaml"), "r") as stream:
    tile_sizes = yaml.safe_load(stream)


class Args:
    openlane2: bool
    print_cell_summary: bool
    print_cell_category: bool


class Project:
    top_verilog_filename: str
    mux_address: int
    commit_id: str
    sort_id: int

    def __init__(
        self,
        index: int,
        git_url: str,
        local_dir: str,
        args: Args,
        is_user_project: bool,
    ):
        self.git_url = git_url
        self.args = args
        self.index = index
        self.local_dir = local_dir
        self.is_user_project = is_user_project
        self.src_dir = (
            os.path.join(self.local_dir, "src")
            if self.is_user_project
            else self.local_dir
        )

        yaml_path = os.path.join(self.local_dir, "info.yaml")
        try:
            with open(yaml_path) as fh:
                self.info = ProjectInfo(yaml.safe_load(fh))
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
                self.check_sources()
                self.top_verilog_filename = self.find_top_verilog()
        else:
            self.sources = [self.get_gl_verilog_filename()]

    def post_clone_setup(self):
        self.load_metrics()

    def load_metrics(self):
        try:
            with open(self.get_metrics_path()) as fh:
                self.metrics = next(csv.DictReader(fh))
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
        if self.is_analog_design():
            required_ports += [
                ["inout", "ua", 8],
            ]
        if include_power_ports:
            required_ports += [
                ["input", "VGND", 1],
                ["input", "VPWR", 1],
            ]
        for direction, port, bits in required_ports:
            if port not in module_ports:
                logging.error(f"{self} port '{port}' missing from top module ('{top}')")
                exit(1)
            actual_direction = module_ports[port]["direction"]
            if actual_direction != direction:
                logging.error(
                    f"{self} incorrect direction for port '{port}' in module '{top}': {direction} required, {actual_direction} found"
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

    def get_hugo_row(self) -> str:
        return f"| {self.mux_address} | [{self.info.title}]({self.mux_address :03}) | {self.info.author}|\n"

    # docs stuff for index on README.md
    def get_index_row(self):
        return f"| {self.mux_address} | {self.info.author} | {self.info.title} | {self.get_project_type_string()} | {self.git_url} |\n"

    def get_project_type_string(self):
        if self.is_wokwi():
            return f"[Wokwi]({self.get_wokwi_url()})"
        elif self.is_analog_design():
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
        for src in self.info.source_files:
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

    def is_analog_design(self) -> bool:
        return len(self.info.pinout.ua) > 0

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
            if self.args.openlane2:
                return os.path.join(self.local_dir, "runs/wokwi/final/metrics.csv")
            else:
                return os.path.join(self.local_dir, "runs/wokwi/reports/metrics.csv")
        else:
            return os.path.join(self.local_dir, "stats/metrics.csv")

    def get_gl_path(self):
        if self.is_user_project:
            if self.args.openlane2:
                return glob.glob(
                    os.path.join(self.local_dir, "runs/wokwi/final/nl/*.nl.v")
                )[0]
            else:
                return glob.glob(
                    os.path.join(
                        self.local_dir, "runs/wokwi/results/final/verilog/gl/*.nl.v"
                    )
                )[0]
        else:
            return os.path.join(self.local_dir, f"{self.info.top_module}.v")

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
            git_utils.fetch_file(url, os.path.join(self.src_dir, truthtable_file))
            logging.info(
                f"Wokwi project {self.info.wokwi_id} has a truthtable included, will test!"
            )
            self.install_wokwi_testing()
        except FileNotFoundError:
            pass

    def install_wokwi_testing(
        self, destination_dir: str = "src", resource_dir: typing.Optional[str] = None
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

    def create_user_config(self):
        if self.is_wokwi():
            self.fetch_wokwi_files()
        self.check_ports()
        logging.info("creating include file")
        filename = "user_config.tcl"
        with open(os.path.join(self.src_dir, filename), "w") as fh:
            fh.write("set ::env(DESIGN_NAME) {}\n".format(self.info.top_module))
            fh.write('set ::env(VERILOG_FILES) "\\\n')
            for line, source in enumerate(self.sources):
                fh.write("    $::env(DESIGN_DIR)/" + source)
                if line != len(self.sources) - 1:
                    fh.write(" \\\n")
            fh.write('"\n\n')
            tiles = self.info.tiles
            die_area = tile_sizes[tiles]
            fh.write(f"# Project area: {tiles} tiles\n")
            fh.write(f'set ::env(DIE_AREA) "{die_area}"\n')
            fh.write(
                f'set ::env(FP_DEF_TEMPLATE) "$::env(DESIGN_DIR)/../tt/def/tt_block_{tiles}_pg.def"\n'
            )

    def golden_harden(self):
        logging.info(f"hardening {self}")
        shutil.copyfile("golden_config.tcl", os.path.join(self.src_dir, "config.tcl"))
        self.harden()

    def harden(self):
        cwd = os.getcwd()
        os.chdir(self.local_dir)

        repo = self.get_git_remote()
        commit_hash = self.get_git_commit_hash()
        tt_version = self.get_tt_tools_version()
        workflow_url = self.get_workflow_url()

        if self.args.openlane2:
            if not os.path.exists("runs/wokwi"):
                print(
                    "OpenLane 2 harden not supported yet, please run OpenLane 2 manually"
                )
                exit(1)
            print(
                "Writing commit information on top of the existing OpenLane 2 run (runs/wokwi)"
            )
        else:
            # requires PDK, PDK_ROOT, OPENLANE_ROOT & OPENLANE_IMAGE_NAME to be set in local environment
            harden_cmd = 'docker run --rm -v $OPENLANE_ROOT:/openlane -v $PDK_ROOT:$PDK_ROOT -v $(pwd):/work -e PDK=$PDK -e PDK_ROOT=$PDK_ROOT -u $(id -u $USER):$(id -g $USER) $OPENLANE_IMAGE_NAME /bin/bash -c "./flow.tcl -overwrite -design /work/src -run_path /work/runs -tag wokwi"'
            logging.debug(harden_cmd)
            env = os.environ.copy()
            p = subprocess.run(harden_cmd, shell=True, env=env)
            if p.returncode != 0:
                logging.error("harden failed")
                exit(1)

        # Write commit information
        commit_id_json_path = "runs/wokwi/results/final/commit_id.json"
        if self.args.openlane2:
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

        os.chdir(cwd)

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
            logging.error("Missing 'How to use' section in docs/info.md")
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
            }
        )

        logging.info("Creating PDF")
        script_dir = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(script_dir, "docs/project_header.md")) as fh:
            doc_header = fh.read()
        with open(os.path.join(script_dir, "docs/project_preview.md.mustache")) as fh:
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
                fh.write("\n\\pagebreak\n")
            except IndexError:
                logging.warning("missing pins in info.yaml, skipping")

        pdf_cmd = "pandoc --pdf-engine=xelatex --resource-path=docs -i datasheet.md -o datasheet.pdf"
        logging.info(pdf_cmd)
        p = subprocess.run(pdf_cmd, shell=True)
        if p.returncode != 0:
            logging.error("pdf command failed")

    # Read and return top-level GDS data from the final GDS file, using gdstk:
    def get_final_gds_top_cells(self):
        if "GDS_PATH" in os.environ:
            gds_path = os.environ["GDS_PATH"]
        elif self.args.openlane2:
            gds_path = glob.glob(
                os.path.join(self.local_dir, "runs/wokwi/final/gds/*.gds")
            )[0]
        else:
            gds_path = glob.glob(
                os.path.join(self.local_dir, "runs/wokwi/results/final/gds/*.gds")
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
        sky130_label_layers = [
            (64, 59),  # 64/59 - pwell.label
            (64, 5),  # 64/5  - nwell.label
            (67, 5),  # 67/5  - li1.label
            (68, 5),  # 68/5  - met1.label
            (69, 5),  # 69/5  - met2.label
            (70, 5),  # 70/5  - met3.label
            (71, 5),  # 71/5  - met4.label
        ]
        top_cells.filter(sky130_label_layers)
        for subcell in top_cells.dependencies(True):
            subcell.filter(sky130_label_layers)
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
            sky130_buried_layers = [
                (64, 16),  # 64/16 - nwell.pin
                (65, 44),  # 65/44 - tap.drawing
                (68, 16),  # 68/16 - met1.pin
                (68, 44),  # 68/44 - via.drawing
                (81, 4),  # 81/4  - areaid.standardc
                (70, 20),  # 70/20 - met3.drawing
                # Important:
                # (68,20), # 68/20 - met1.drawing
                # Less important, but keep for now:
                # (69,20), # 69/20 - met2.drawing
            ]
            top_cells.filter(sky130_buried_layers)
            for subcell in top_cells.dependencies(True):
                subcell.filter(sky130_buried_layers)
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

        synth_log = "runs/wokwi/logs/synthesis/1-synthesis.log"
        if self.args.openlane2:
            synth_log = "runs/wokwi/05-yosys-synthesis/yosys-synthesis.log"
        with open(os.path.join(self.local_dir, synth_log)) as f:
            for line in f.readlines():
                if line.startswith("Warning:"):
                    # bogus warning https://github.com/YosysHQ/yosys/commit/bfacaddca8a2e113e4bc3d6177612ccdba1555c8
                    if "WIDTHLABEL" not in line:
                        warnings.append(line.strip())

        sta_report_glob = (
            "runs/wokwi/reports/signoff/*-sta-rcx_nom/multi_corner_sta.checks.rpt"
        )

        if self.args.openlane2:
            sta_report_glob = (
                "runs/wokwi/*-openroad-stapostpnr/nom_tt_025C_1v80/checks.rpt"
            )
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
        print("# Routing stats")
        print()
        print("| Utilisation (%) | Wire length (um) |")
        print("|-------------|------------------|")
        print(
            "| {} | {} |".format(
                self.metrics["OpenDP_Util"], self.metrics["wire_length"]
            )
        )

    # Print the summaries
    def summarize(self):
        cell_count = self.get_cell_counts_from_gl()
        script_dir = os.path.dirname(os.path.realpath(__file__))

        Categories = typing.TypedDict(
            "Categories", {"categories": typing.List[str], "map": typing.Dict[str, int]}
        )
        with open(os.path.join(script_dir, "categories.json")) as fh:
            categories: Categories = json.load(fh)

        defs = load_cells()

        # print all used cells, sorted by frequency
        total = 0
        if self.args.print_cell_summary:
            print("# Cell usage")
            print()
            print("| Cell Name | Description | Count |")
            print("|-----------|-------------|-------|")
            for name, count in sorted(
                cell_count.items(), key=lambda item: item[1], reverse=True
            ):
                if count > 0:
                    total += count
                    cell_link = f"{CELL_URL}{name}"
                    print(
                        f'| [{name}]({cell_link}) | {defs[name]["description"]} |{count} |'
                    )

            print(f"| | Total | {total} |")

        if self.args.print_cell_category:
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
                cell_links = [
                    f"[{name}]({CELL_URL}{name})" for name in cat_dict["examples"]
                ]
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

    # Parse the lib, cell and drive strength an OpenLane gate-level Verilog file
    def get_cell_counts_from_gl(self):
        cell_count: typing.Dict[str, int] = {}
        total = 0
        with open(self.get_gl_path()) as fh:
            for line in fh.readlines():
                m = re.search(r"sky130_(\S+)__(\S+)_(\d+)", line)
                if m is not None:
                    total += 1
                    cell_lib = m.group(1)
                    cell_name = m.group(2)
                    assert cell_lib in ["fd_sc_hd", "ef_sc_hd"]
                    try:
                        cell_count[cell_name] += 1
                    except KeyError:
                        cell_count[cell_name] = 1
        return cell_count

    # Load all the json defs and combine into one big dict, keyed by cellname
    # Needs access to the PDK
    def create_defs(self):
        # replace this with a find
        json_files = glob.glob("sky130_fd_sc_hd/latest/cells/*/definition.json")
        definitions: typing.Dict[str, Cell] = {}
        for json_file in json_files:
            with open(json_file) as fh:
                definition: Cell = json.load(fh)
                definitions[definition["name"]] = definition

        with open("cells.json", "w") as fh:
            json.dump(definitions, fh)
