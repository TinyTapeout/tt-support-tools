import argparse
import os

import gdstk
from cairosvg import svg2png
from PIL import Image

PRBOUNDARY_LAYER = (0, 0)
LOGO_LAYER = (81, 0)
NOFILL_LAYER = (152, 5)

TR_NOFILL_POLY_XY = [
    [121.76, 5.27],
    [121.76, 28.54],
    [96.94, 28.54],
    [96.94, 51.80],
    [78.02, 51.80],
    [78.02, 75.38],
    [57.85, 75.38],
    [57.85, 96.16],
    [38.93, 96.16],
    [38.93, 119.12],
    [17.84, 119.12],
    [17.84, 205.36],
    [101.90, 205.36],
    [101.90, 175.89],
    [123.93, 175.89],
    [123.93, 160.62],
    [150.29, 160.62],
    [150.29, 201.63],
    [166.43, 201.63],
    [166.43, 219.63],
    [216.39, 219.63],
    [216.39, 98.09],
    [192.48, 98.09],
    [192.48, 5.27],
]


class LogoGenerator:
    def __init__(self, variant: str):
        assert variant in ("tr", "tl")
        self.variant = variant
        self.macro_name = f"tt_logo_corner_{variant}"
        script_dir = os.path.dirname(os.path.abspath(__file__))
        png_file = os.path.join(script_dir, f"tt_logo_corner_{variant}.png")
        svg2png(
            url=f"{script_dir}/tt_logo_corner_{variant}.svg",
            write_to=png_file,
        )
        self.img = Image.open(png_file).convert("L")
        self.pixel_size = 1
        if variant == "tl":
            self.pixel_size = 0.82  # 164 um
        self.width = self.img.width * self.pixel_size
        self.height = self.img.height * self.pixel_size

    def gen_gds(self, gds_file: str):
        lib = gdstk.Library()
        cell = lib.new_cell(self.macro_name)
        boundary = gdstk.rectangle(
            (0, 0),
            (self.width, self.height),
            layer=PRBOUNDARY_LAYER[0],
            datatype=PRBOUNDARY_LAYER[1],
        )
        cell.add(boundary)

        img = self.img
        for y in range(img.height):
            for x in range(img.width):
                color: int = img.getpixel((x, y))  # type: ignore
                if color < 16:
                    flipped_y = img.height - y - 1  # flip vertically
                    rect = gdstk.rectangle(
                        (x * self.pixel_size, flipped_y * self.pixel_size),
                        ((x + 1) * self.pixel_size, (flipped_y + 1) * self.pixel_size),
                        layer=LOGO_LAYER[0],
                        datatype=LOGO_LAYER[1],
                    )
                    cell.add(rect)

        if self.variant == "tr":
            nofill_poly = gdstk.Polygon(
                TR_NOFILL_POLY_XY, layer=NOFILL_LAYER[0], datatype=NOFILL_LAYER[1]
            )
            cell.add(nofill_poly)
        else:
            nofill_rect = gdstk.rectangle(
                (0, 0),
                (self.width, self.height),
                layer=NOFILL_LAYER[0],
                datatype=NOFILL_LAYER[1],
            )
            cell.add(nofill_rect)

        lib.write_gds(gds_file)

    def gen_verilog(self, verilog_file: str):
        verilog_lines = [
            "`default_nettype none",
            "",
            f"module {self.macro_name} ();",
            "endmodule",
        ]

        with open(verilog_file, "w") as f:
            f.write("\n".join(verilog_lines) + "\n")

    def gen_lef(self, lef_file: str):
        lef_lines = [
            f"VERSION 5.7 ;",
            f"  NOWIREEXTENSIONATPIN ON ;",
            f'  DIVIDERCHAR "/" ;',
            f'  BUSBITCHARS "[]" ;',
            f"MACRO {self.macro_name}",
            f"  CLASS BLOCK ;",
            f"  FOREIGN {self.macro_name} ;",
            f"  ORIGIN 0.000 0.000 ;",
            f"  SIZE {self.width:.3f} BY {self.height:.3f} ;",
            f"END {self.macro_name}",
            f"END LIBRARY",
        ]

        with open(lef_file, "w") as f:
            f.write("\n".join(lef_lines) + "\n")

    def gen_logo(self, dir):
        self.gen_gds(f"{dir}/gds/{self.macro_name}.gds")
        self.gen_lef(f"{dir}/lef/{self.macro_name}.lef")
        self.gen_verilog(f"{dir}/verilog/{self.macro_name}.v")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="TT GF corner logo generator")
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory to write the logo files to",
    )
    args = parser.parse_args()
    dir = args.output_dir
    os.makedirs(f"{dir}/gds", exist_ok=True)
    os.makedirs(f"{dir}/lef", exist_ok=True)
    os.makedirs(f"{dir}/verilog", exist_ok=True)
    LogoGenerator("tr").gen_logo(dir)
    LogoGenerator("tl").gen_logo(dir)
