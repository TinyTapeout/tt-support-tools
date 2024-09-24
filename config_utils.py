import json
import logging
import os
import re
import subprocess
import tkinter
from collections.abc import Iterable

import yaml


class ConfigFileError(Exception):
    pass


def read_tcl_config(file: str, design_dir: str | None = None):
    logging.warning(
        "Support for TCL configuration files is deprecated and will be removed"
    )
    if design_dir is None:
        design_dir = os.path.dirname(file)
    design_dir = os.path.realpath(design_dir)
    tcl_code = open(file).read()
    interp = tkinter.Tcl()
    interp.eval("array unset ::env")
    interp.setvar("env(DESIGN_DIR)", design_dir)
    config = {}
    env_rx = re.compile(r"(?:\:\:)?env\((\w+)\)")

    def py_set(key: str, value: str | None = None):
        if match := env_rx.fullmatch(key):
            if value is not None:
                value = value.replace(design_dir, "dir::")
                value = value.replace("dir::/", "dir::")
                config[match.group(1)] = value

    py_set_name = interp.register(py_set)
    interp.call("rename", py_set_name, "_py_set")
    interp.call("rename", "set", "_orig_set")
    interp.eval("proc set args { _py_set {*}$args; tailcall _orig_set {*}$args; }")
    interp.eval(tcl_code)
    return config


def read_json_config(file: str):
    config = json.load(open(file))
    config.pop("//", None)
    return config


def read_yaml_config(file: str):
    return yaml.safe_load(open(file))


def read_mk_config(file: str, design_dir: str | None = None):
    logging.warning(
        "Reading Makefile configuration files is an experimental feature and could be removed"
    )
    env_pre = {} if design_dir is None else {"DESIGN_HOME": design_dir}
    mk_cg = "all:\n\t@env"
    mk_tg = f"-include {file}\n{mk_cg}"
    env_cg = subprocess.run(
        "make -f -",
        shell=True,
        env=env_pre,
        input=mk_cg,
        capture_output=True,
        text=True,
    ).stdout.strip()
    env_tg = subprocess.run(
        "make -f -",
        shell=True,
        env=env_pre,
        input=mk_tg,
        capture_output=True,
        text=True,
    ).stdout.strip()
    env_diff = set(env_tg.split("\n")) - set(env_cg.split("\n"))
    config = dict(i.split("=", 1) for i in env_diff)
    return config


def read_config(basename: str, formats: Iterable[str], design_dir: str | None = None):
    for fmt in formats:
        file = f"{basename}.{fmt}"
        if os.path.exists(file):
            if fmt == "tcl":
                return read_tcl_config(file, design_dir)
            elif fmt == "json":
                return read_json_config(file)
            elif fmt == "yaml":
                return read_yaml_config(file)
            elif fmt == "mk":
                return read_mk_config(file)
            else:
                raise ConfigFileError(f"Unexpected configuration file format: {fmt}")
    raise ConfigFileError(
        f"Could not file configuration file {basename}.{{{'|'.join(formats)}}}"
    )


def write_tcl_config(config: dict, file: str):
    logging.warning(
        "Support for TCL configuration files is deprecated and will be removed"
    )
    with open(file, "w") as f:
        for key, value in config.items():
            if type(value) in (list, tuple):
                value = " ".join(value)
            if type(value) == str:
                value = value.replace("dir::", "$::env(DESIGN_DIR)/")
            print(f'set ::env({key}) "{value}"', file=f)


def write_json_config(config: dict, file: str):
    with open(file, "w") as f:
        json.dump(config, f, indent=2)


def write_yaml_config(config: dict, file: str):
    with open(file, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)


def write_mk_config(config: dict, file: str):
    with open(file, "w") as f:
        for key, value in config.items():
            if type(value) in (list, tuple):
                value = " ".join(value)
            if type(value) == str:
                value = value.replace("dir::", "$(DESIGN_HOME)/")
            print(f"export {key} = {value}", file=f)


def write_config(config: dict, basename: str, formats: Iterable[str]):
    for fmt in formats:
        file = f"{basename}.{fmt}"
        if fmt == "tcl":
            write_tcl_config(config, file)
        elif fmt == "json":
            write_json_config(config, file)
        elif fmt == "yaml":
            write_yaml_config(config, file)
        elif fmt == "mk":
            write_mk_config(config, file)
        else:
            raise ConfigFileError("Unexpected configuration file format: {fmt}")
