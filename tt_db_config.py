#!/usr/bin/env python3
"""

TT config.ini manager

# global defaults
python tt_db_config.py --project tt_um_factory_test  --mode ASIC_MANUAL_INPUTS


# project specific
python tt_db_config.py --name tt_um_factory_test project --clockrate 100

"""
import argparse
import logging
import os
import subprocess
import sys
import tempfile

from configupdater import ConfigUpdater

DefaultPort = "/dev/ttyACM0"
CommandProject = "project"
CommandDefault = "default"


def getParser():
    parser = argparse.ArgumentParser(
        description="TT Demoboard Configuration Tool",
        # formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Global options (available to all subcommands)

    parser.add_argument(
        "--port",
        help=f"port for connection to DB [{DefaultPort}]",
        required=False,
        default=DefaultPort,
    )

    parser.add_argument("--name", help="project/section name", required=False)

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

    defaults = subparsers.add_parser(CommandDefault, help="Default settings")

    defaults.add_argument(
        "--project",
        metavar="PROJNAME",
        type=str,
        help="Set the default project on boot",
    )

    defaults.add_argument(
        "--mode",
        metavar="I/O MODE",
        type=str,
        choices=["SAFE", "ASIC_RP_CONTROL", "ASIC_MANUAL_INPUTS"],
    )

    project = subparsers.add_parser(CommandProject, help="Project overrides")

    project.add_argument(
        "--clockrate",
        metavar="RATE",
        type=int,
        help="Clock rate in Hz",
    )
    project.add_argument(
        "--set-default",
        action="store_true",
        help="set this project as the default on startup",
    )

    return parser


class ConfigFile:

    def __init__(self, filepath: str):
        self.filepath = filepath

        self.updater = ConfigUpdater()
        self.updater.read(filepath)
        return

    def save(self):
        with open(self.filepath, "w") as f:
            self.updater.write(f)

    def set_default_project(self, name: str):
        self.updater["DEFAULT"]["project"] = name

    def set_default_mode(self, mode: str):
        self.updater["DEFAULT"]["mode"] = mode

    def set_project_clockrate(self, name: str, rate: int):
        if name not in self.updater:
            self.updater.add_section(name)

        self.updater[name]["clock_frequency"] = int(rate)


class TTDBConfig:

    def __init__(self, port: str = DefaultPort):
        self.port = port

    @classmethod
    def get_temp_file(cls, prefix="ttconf-", suffix=".tmp", dir=None, mode="wb"):
        # path is tmp.name
        tmp = tempfile.NamedTemporaryFile(
            mode=mode,  # text mode + read/write
            delete=False,  # ← keep file after closing
            suffix=suffix,  # optional but recommended
            prefix=prefix,
            dir=dir,  # None = system temp dir
        )
        return tmp

    @classmethod
    def get_temp_filename(cls, prefix="ttconf-", suffix=".tmp", dir=None):
        tmp = cls.get_temp_file(prefix, suffix, dir)
        tmp.close()
        return tmp.name

    def reset(self):
        commands = ["connect", self.port, "+", "reset"]
        subprocess.run(["mpremote", *commands], check=False)

    def deploy(self, files: list, destination_dir: str, do_reset: bool = True):
        commands = ["connect", self.port]

        if isinstance(files, str):
            files = [files]

        for f in files:
            bname = os.path.basename(f)
            commands += ["+", "cp", f, f":{destination_dir}/{bname}"]

        if do_reset:
            commands += ["+", "reset"]

        subprocess.run(["mpremote", *commands], check=True)

    def write_file(
        self, local_filepath: str, remote_filepath: str, do_reset: bool = False
    ):
        commands = [
            "connect",
            self.port,
            "+",
            "cp",
            local_filepath,
            f":{remote_filepath}",
        ]

        if do_reset:
            commands += ["+", "reset"]

        subprocess.run(["mpremote", *commands], check=False)

    def fetch_safe(self, remote_filepath: str):
        tmp_filepath = self.get_temp_filename()

        commands = ["connect", self.port]
        commands += ["+", "cp", f":{remote_filepath}", tmp_filepath]

        subprocess.run(["mpremote", *commands], check=True)
        return tmp_filepath

    def fetch(self, files: list, destination_dir: str = "."):
        commands = ["connect", self.port]

        if isinstance(files, str):
            files = [files]

        for f in files:
            bname = os.path.basename(f)
            commands += ["+", "cp", f":{f}", f"{destination_dir}/{bname}"]

        subprocess.run(["mpremote", *commands], check=True)

    def get_config_ini(self) -> ConfigUpdater:
        tmpfile = self.fetch_safe("/config.ini")
        return ConfigFile(tmpfile)

    def upload_config_ini(self, local_filepath: str, do_reset: bool = True):
        self.write_file(local_filepath, "/config.ini", do_reset)


if __name__ == "__main__":

    parser = getParser()
    args = parser.parse_args()
    ttconf = TTDBConfig()

    cnf = None
    if args.command == CommandDefault:
        cnf = ttconf.get_config_ini()
        if args.project:
            cnf.set_default_project(args.project)
        if args.mode:
            cnf.set_default_mode(args.mode)

    elif args.command == CommandProject:
        if not args.name:
            parser.print_help()
            print("MUST specify NAME of project this applies to using --name")
            sys.exit(1)

        cnf = ttconf.get_config_ini()
        if args.clockrate:
            cnf.set_project_clockrate(args.name, args.clockrate)

        if args.set_default:
            cnf.set_default_project(args.name)

    if cnf is not None:
        cnf.save()
        ttconf.upload_config_ini(cnf.filepath, do_reset=False)
        ttconf.reset()
