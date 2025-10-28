import xml.etree.ElementTree as ET
from typing import Dict


class LayerInfo:
    def __init__(self, name: str, source: str, layer: int, data_type: int):
        self.name = name
        self.source = source
        self.layer = layer
        self.data_type = data_type

    def __repr__(self):
        return f"LayerInfo(name={self.name}, source={self.source}, layer={self.layer}, data_type={self.data_type})"


def parse_lyp_layers(lyp_file: str, only_valid: bool = True):
    with open(lyp_file) as f:
        xml_content = f.read()
    root = ET.fromstring(xml_content)

    layers_dict: Dict[str, LayerInfo] = {}

    for properties in root.findall("properties"):
        name = properties.find("name")
        source = properties.find("source")
        valid = properties.find("valid")

        if only_valid and valid is not None and valid.text == "false":
            continue

        if name is None or name.text is None:
            name = None
        else:
            name = name.text

        if source is None or source.text is None:
            continue

        source = source.text

        name_orig = name
        source_orig = source

        # for more details on the source field, see
        # https://www.klayout.de/doc/about/layer_sources.html
        # and klayout's src/laybasic/laybasic/layParsedLayerSource.cc

        if "@" in source:
            assert source.count("@") == 1
            source, layout_index = source.split("@")
            assert layout_index.isnumeric()
            if layout_index != "1":
                continue

        if " " in source:
            assert source.count(" ") == 1
            # sky130A and sg13g2 has the name in the "name" field
            # gf180mcuD has the name as part of the "source" field
            # if a future PDK has it in both places, we'll trigger the
            #     assertion below to decide which one has priority
            assert name is None
            name, source = source.split(" ")

        if name is None:
            name = source

        # the source field can have further transformations & filters,
        # but so far none of the PDKs use them, so we are ignoring them

        layer, data_type = source.split("/")
        assert layer.isnumeric()
        assert data_type.isnumeric()
        layer = int(layer)
        data_type = int(data_type)

        # sky130A includes an extra copy of layer & data_type
        # as part of the name, let's remove that
        name = name.split(" - ")[0]

        layers_dict[name] = LayerInfo(
            name=name_orig, source=source_orig, layer=layer, data_type=data_type
        )

    return layers_dict
