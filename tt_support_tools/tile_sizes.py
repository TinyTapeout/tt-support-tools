from os.path import dirname, join, realpath
from typing import Dict

import yaml

with open(join(dirname(realpath(__file__)), "tile_sizes.yaml")) as fh:
    tile_sizes: Dict[str, str] = yaml.safe_load(fh)
