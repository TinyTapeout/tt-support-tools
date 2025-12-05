import argparse
import os

import gdstk
from cairosvg import svg2png
from PIL import Image

LOGO_WIDTH = 220
LOGO_HEIGHT = 220
PIXEL_SIZE = 1

PRBOUNDARY_LAYER = (0, 0)
LOGO_LAYER = (81, 0)
NOFILL_LAYER = (152, 5)

TR_NOFILL_POLY_XY = [
    [148.226, 2.881],
    [3.652, 147.455],
    [3.652, 160.353],
    [58.538, 215.238],
    [112.790, 160.985],
    [171.735, 219.930],
    [194.395, 219.930],
    [194.430, 219.895],
    [217.290, 197.035],
    [217.290, 101.273],
    [202.873, 101.273],
    [179.863, 78.263],
    [216.499, 41.626],
    [177.755, 2.881],
]


class LogoGenerator:
    def __init__(self):
        pass

    def gen_logo(self, variant: str, gds_file: str, verilog_file: str):
        assert variant in ("tr")
        if variant == "tr":
            script_dir = os.path.dirname(os.path.abspath(__file__))
            png_file = os.path.join(script_dir, f"tt_logo_corner_{variant}.png")
            svg2png(
                url=f"{script_dir}/tt_logo_corner_{variant}.svg",
                write_to=png_file,
            )
            img = Image.open(png_file).convert("L")

        lib = gdstk.Library()
        cell_name = f"tt_logo_corner_{variant}"
        cell = lib.new_cell(cell_name)
        boundary = gdstk.rectangle(
            (0, 0),
            (img.width * PIXEL_SIZE, img.height * PIXEL_SIZE),
            layer=PRBOUNDARY_LAYER[0],
            datatype=PRBOUNDARY_LAYER[1],
        )
        cell.add(boundary)

        for y in range(img.height):
            for x in range(img.width):
                color: int = img.getpixel((x, y))  # type: ignore
                if color < 16:
                    flipped_y = img.height - y - 1  # flip vertically
                    rect = gdstk.rectangle(
                        (x * PIXEL_SIZE, flipped_y * PIXEL_SIZE),
                        ((x + 1) * PIXEL_SIZE, (flipped_y + 1) * PIXEL_SIZE),
                        layer=LOGO_LAYER[0],
                        datatype=LOGO_LAYER[1],
                    )
                    cell.add(rect)

        if variant == "tr":
            nofill_poly = gdstk.Polygon(
                TR_NOFILL_POLY_XY, layer=NOFILL_LAYER[0], datatype=NOFILL_LAYER[1]
            )
            cell.add(nofill_poly)

        lib.write_gds(gds_file)

        verilog_lines = [
            "`default_nettype none",
            "",
            f"module {cell_name} ();",
            "endmodule",
        ]

        with open(verilog_file, "w") as f:
            f.write("\n".join(verilog_lines) + "\n")

    def gen_lef(self, variant: str, lef_file: str):
        assert variant in ("tr")
        width = PIXEL_SIZE * LOGO_WIDTH
        height = PIXEL_SIZE * LOGO_HEIGHT
        lef_lines = [
            f"VERSION 5.7 ;",
            f"  NOWIREEXTENSIONATPIN ON ;",
            f'  DIVIDERCHAR "/" ;',
            f'  BUSBITCHARS "[]" ;',
            f"MACRO tt_logo_corner_{variant}",
            f"  CLASS BLOCK ;",
            f"  FOREIGN tt_logo_corner_{variant} ;",
            f"  ORIGIN 0.000 0.000 ;",
            f"  SIZE {width:.3f} BY {height:.3f} ;",
            f"END tt_logo_corner_{variant}",
            f"END LIBRARY",
        ]

        with open(lef_file, "w") as f:
            f.write("\n".join(lef_lines) + "\n")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="TT GF corner logo generator")
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory to write the logo files to",
    )
    args = parser.parse_args()
    generator = LogoGenerator()
    dir = args.output_dir
    os.makedirs(f"{dir}/gds", exist_ok=True)
    os.makedirs(f"{dir}/lef", exist_ok=True)
    os.makedirs(f"{dir}/verilog", exist_ok=True)
    generator.gen_logo(
        "tr", f"{dir}/gds/tt_logo_corner_tr.gds", f"{dir}/verilog/tt_logo_corner_tr.v"
    )
    generator.gen_lef("tr", f"{dir}/lef/tt_logo_corner_tr.lef")
