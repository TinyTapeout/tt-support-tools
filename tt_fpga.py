#!/usr/bin/env python3
"""
    tt_fpga -- FPGA breakout management tool
    @author: Pat Deegan

    In a project based on a TT template, with a configured info.yaml, all you need
    is to run

      python tt/tt_fpga.py harden

    to generate a bitstream in build/.  Then

      python tt/tt_fpga.py configure --upload

    will make the bitstream available through the tt.shuttle object in the DB REPL.

    You may also set this as the default project to load on startup and/or set the
    auto-clocking rate through the configure command, e.g.

      python tt/tt_fpga.py configure --upload --set-default --clockrate 1000

    to do all three at once.


    If you have no info.yaml template, the script will work anyway.  But you'll need
    to specify more command line arguments.

    See
        python tt/tt_fpga.py harden --help
    and
        python tt/tt_fpga.py configure --help

"""


import argparse
import logging
import os
import subprocess
import sys

from project import SCRIPT_DIR, Project
from tt_db_config import DefaultPort, TTDBConfig
from tt_logging import setup_logging

CommandHarden = "harden"
CommandConfig = "configure"


def getParser():
    parser = argparse.ArgumentParser(
        description="TT FPGA tool",
        # formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--project-dir", help="location of the project", default=".")
    # parser.add_argument("--yaml", help="the project's yaml configuration file", default="info.yaml")

    # Global options (available to all subcommands)
    parser.add_argument(
        "--debug",
        metavar="LEVEL",
        help="debug logging",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
    )

    # Create subparsers
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,  # make subcommand mandatory
        help="Available commands",
    )

    # ----------------------
    # Subcommand: hardening
    # ----------------------
    harden = subparsers.add_parser(CommandHarden, help="Run hardening process")

    harden.add_argument(
        "--name",
        metavar="FILE",
        help="Output file and project name (default: top_module name)",
        default="",
    )

    harden.add_argument(
        "--breakout-target",
        help="Select target breakout: classic (TT04), fabricfox (TT ETR db) default: fabricfox",
        choices=["classic", "fabricfox"],
        default="fabricfox",
    )

    harden.add_argument(
        "--source_dir",
        metavar="DIR",
        help="Directory containing source verilog files (default from info.yaml)",
    )

    harden.add_argument(
        "--source",
        action="append",
        metavar="FILE",
        help="Source file(s) to harden (specify multiple times for multiple source files, default from info.yaml)",
    )

    harden.add_argument(
        "--top_module",
        metavar="TOP",
        help="Name of the top module (default from info.yaml)",
    )

    # ----------------------
    # Subcommand: configuration
    # ----------------------
    config = subparsers.add_parser(
        CommandConfig, help="Upload bitstream and manage configuration"
    )
    config.add_argument(
        "--port",
        metavar="COMPORT",
        type=str,
        default=DefaultPort,
        help=f"Port for uploads (default: {DefaultPort})",
    )

    config.add_argument(
        "--set-default",
        action="store_true",
        help="set this     project as the default on startup",
    )
    config.add_argument(
        "--upload", action="store_true", help="upload the bitstream.bin from build/"
    )
    config.add_argument(
        "--clockrate",
        metavar="RATE",
        type=int,
        help="Clock rate in Hz",
    )

    config.add_argument(
        "--name",
        metavar="FILE",
        help="Output file and project name (default: top_module name)",
        default="",
    )

    return parser


def die_with_error(msg):
    print(msg)
    sys.exit(2)


class TTFPGA:

    def __init__(self, proj: Project | None, args):
        self.project = proj
        self.args = args

    def get_name(self):
        base_name = self.args.name
        if not len(base_name):
            if (
                "top_module" in self.args
                and self.args.top_module is not None
                and len(self.args.top_module)
            ):
                return self.args.top_module
            if self.project is not None:
                base_name = self.project.info.top_module

            if not len(base_name):  # shouldn't happen
                base_name = "tt_fpga_project"

        return base_name

    @property
    def bitstream_filename(self):
        return f"{self.get_name()}.bin"

    @property
    def top_module(self):
        if "top_module" in self.args and self.args.top_module:
            # command line overrides yaml
            return self.args.top_module

        if self.project is not None:
            return self.project.info.top_module

        if "top_module" in self.args:
            if not self.args.top_module:
                die_with_error("No project yaml, must specify top_module")
        else:
            return None
        return self.args.top_module

    @property
    def source_dir(self):

        if self.args.source_dir:
            # command line overrides yaml
            return self.args.source_dir

        if self.project is not None:
            return self.project.src_dir
        if not self.args.source_dir:
            die_with_error("No project yaml, must specify source_dir")
        return self.args.source_dir

    @property
    def local_dir(self):

        if self.project is not None:
            return self.project.local_dir

        return os.path.realpath(self.args.project_dir)

    @property
    def sources(self):

        if self.args.source and len(self.args.source):
            # command line overrides yaml
            return self.args.source

        if self.project is not None:
            return self.project.sources

        if not self.args.source:
            die_with_error(
                "No project yaml, must specify --source A.v --source B.v ..."
            )

        # print(self.args.source)
        return self.args.source

    def create_fpga_bitstream(self):
        logging.info(f"Creating FPGA bitstream for {self.project}")

        target_map = {
            "classic": {
                "pcf": "tt_fpga_top.pcf",
            },
            "fabricfox": {
                "pcf": "tt_fpga_fabricfoxv2.pcf",
            },
        }
        args = self.args

        pcf_file = target_map[args.breakout_target]["pcf"]

        base_name = self.get_name()

        with open(os.path.join(SCRIPT_DIR, "fpga/tt_fpga_top.v"), "r") as f:
            top_module_template = f.read()

        with open(os.path.join(self.source_dir, "_tt_fpga_top.v"), "w") as f:
            f.write(top_module_template.replace("__tt_um_placeholder", self.top_module))

        build_dir = os.path.join(self.local_dir, "build")
        os.makedirs(build_dir, exist_ok=True)

        sources = [os.path.join(self.source_dir, src) for src in self.sources]
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


def yaml_file_exists(args):
    return os.path.exists(os.path.join(os.path.realpath(args.project_dir), "info.yaml"))


def main():

    parser = getParser()

    args = parser.parse_args()

    setup_logging(args.loglevel)

    if args.command != CommandHarden and args.command != CommandConfig:
        parser.print_help()
        sys.exit(1)

    project = None
    if yaml_file_exists(args):
        project = Project(
            0, "unknown", args.project_dir, pdk="fpgaUp5k", is_user_project=True
        )
        project.post_clone_setup()

    fpga = TTFPGA(project, args)

    if args.command == CommandHarden:
        fpga.create_fpga_bitstream()
    elif args.command == CommandConfig:
        proj_name = fpga.get_name()
        bitstream_name = f"{proj_name}.bin"
        fname = f"build/{bitstream_name}"
        if not os.path.exists(fname):
            print(f"Can't find {fname}")
            sys.exit(3)
        ttdbconf = TTDBConfig(args.port)
        if args.upload:
            print(f"Uploading {fname}")
            ttdbconf.write_file(fname, f"/bitstreams/{bitstream_name}")
        if args.set_default or args.clockrate is not None:
            cnf = ttdbconf.get_config_ini()
            if args.set_default:
                cnf.set_default_project(proj_name)
            if args.clockrate is not None:
                cnf.set_project_clockrate(proj_name, args.clockrate)

            cnf.save()  # save local file
            # upload that config.ini
            ttdbconf.upload_config_ini(cnf.filepath, do_reset=False)
            ttdbconf.reset()  # restart

        if not (args.upload or args.set_default or args.clockrate):
            print(
                "Did nothing.  Use configure with --upload, --set-default and/or --clockrate"
            )


if __name__ == "__main__":
    main()
