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

        if (
            name is not None
            and name.text is not None
            and source is not None
            and source.text is not None
        ):
            name_key = name.text.split("-")[0].strip()
            layer, data_type = source.text.split("@")[0].split("/")
            # Add the 'source' text as the value in the dictionary
            layers_dict[name_key] = LayerInfo(
                name=name.text,
                source=source.text,
                layer=int(layer),
                data_type=int(data_type),
            )

    return layers_dict
