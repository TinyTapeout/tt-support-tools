import json
import os
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


def read_config(
    basename: str, formats: Iterable[str] = ("json",), design_dir: str | None = None
):
    for fmt in formats:
        file = f"{basename}.{fmt}"
        if os.path.exists(file):
            if fmt == "json":
                return read_json_config(file)
            elif fmt == "yaml":
                return read_yaml_config(file)
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


def write_config(config: dict, basename: str, formats: Iterable[str] = ("json",)):
    for fmt in formats:
        file = f"{basename}.{fmt}"
        if fmt == "json":
            write_json_config(config, file)
        elif fmt == "yaml":
            write_yaml_config(config, file)
        else:
            raise ConfigFileError("Unexpected configuration file format: {fmt}")
