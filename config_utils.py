import json
import logging
import os
import subprocess
from collections.abc import Iterable

import yaml


class ConfigFileError(Exception):
    pass


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
            if fmt == "json":
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
            if type(value) is str:
                value = value.replace("dir::", "$(DESIGN_HOME)/")
            print(f"export {key} = {value}", file=f)


def write_config(config: dict, basename: str, formats: Iterable[str]):
    for fmt in formats:
        file = f"{basename}.{fmt}"
        if fmt == "json":
            write_json_config(config, file)
        elif fmt == "yaml":
            write_yaml_config(config, file)
        elif fmt == "mk":
            write_mk_config(config, file)
        else:
            raise ConfigFileError("Unexpected configuration file format: {fmt}")
