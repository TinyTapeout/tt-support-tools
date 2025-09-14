#!/usr/bin/env python3

import argparse
import sys
from typing import Dict, TypedDict

import gdstk
from git.repo import Repo
from PIL import Image, ImageDraw, ImageFont

from config import Config


class TechDef(TypedDict):
    PRBOUNDARY_LAYER: int
    PRBOUNDARY_DATATYPE: int
    LOGO_LAYER: int
    LOGO_DATATYPE: int
    OBS_LAYER_NAME: str
    PIXEL_SIZE: float


tech: Dict[str, TechDef] = {
    "sky130A": {
        "PRBOUNDARY_LAYER": 235,  # prBoundary
        "PRBOUNDARY_DATATYPE": 4,  # .boundary
        "LOGO_LAYER": 71,  # Metal4
        "LOGO_DATATYPE": 20,  # .drawing
        "OBS_LAYER_NAME": "met4",
        "PIXEL_SIZE": 0.5,  # um
    },
    "ihp-sg13g2": {
        "PRBOUNDARY_LAYER": 189,  # prBoundary
        "PRBOUNDARY_DATATYPE": 4,  # .boundary
        "LOGO_LAYER": 67,  # Metal5
        "LOGO_DATATYPE": 0,  # .drawing
        "OBS_LAYER_NAME": "Metal5",
        "PIXEL_SIZE": 0.25,  # um
    },
}

LOGO_WIDTH = 200
LOGO_HEIGHT = 200


class LogoGenerator:
    def __init__(self, tt_dir, pdk: str, config: Config | None = None):
        self.tt_dir = tt_dir
        self.pdk = pdk
        self.config = config

    def gen_logo(self, variant: str, gds_file: str, shuttle=None, commit=None):

        assert variant in ("top", "bottom")
        if variant == "top":
            # use included bitmap
            img = Image.open(f"{self.tt_dir}/logo/tt_logo.png").convert("L")

        elif variant == "bottom":
            # generate bitmap from shuttle ID & commit hash
            if shuttle is None:
                assert self.config is not None
                shuttle = self.config["id"]
            if commit is None:
                commit = Repo(".").commit().hexsha

            img = Image.new("L", (LOGO_WIDTH, LOGO_HEIGHT), (0,))
            draw = ImageDraw.Draw(img)

            font_file = f"{self.tt_dir}/logo/font/UbuntuSansMono.ttf"

            def font(size):
                f = ImageFont.truetype(font_file, size)
                f.set_variation_by_axes([700])
                return f

            shuttle_font_size = 88
            shuttle_y_offset = -15
            if len(shuttle) > 4:
                shuttle = shuttle[:-1].upper() + shuttle[-1]
                shuttle_font_size = 44
                shuttle_y_offset = 10
            draw.text(
                (2, shuttle_y_offset), shuttle, fill=255, font=font(shuttle_font_size)
            )
            draw.text((2, 68), commit[:8], fill=255, font=font(44))
            draw.text((2, 107), commit[8:18], fill=255, font=font(35))
            draw.text((1, 137), commit[18:29], fill=255, font=font(32))
            draw.text((1, 165), commit[29:], fill=255, font=font(32))

        PRBOUNDARY_LAYER = tech[self.pdk]["PRBOUNDARY_LAYER"]
        PRBOUNDARY_DATATYPE = tech[self.pdk]["PRBOUNDARY_DATATYPE"]
        MET4_LAYER = tech[self.pdk]["LOGO_LAYER"]
        DRAWING_DATATYPE = tech[self.pdk]["LOGO_DATATYPE"]
        PIXEL_SIZE = tech[self.pdk]["PIXEL_SIZE"]

        lib = gdstk.Library()
        cell = lib.new_cell(f"tt_logo_{variant}")
        boundary = gdstk.rectangle(
            (0, 0),
            (img.width * PIXEL_SIZE, img.height * PIXEL_SIZE),
            layer=PRBOUNDARY_LAYER,
            datatype=PRBOUNDARY_DATATYPE,
        )
        cell.add(boundary)

        for y in range(img.height):
            for x in range(img.width):
                color: int = img.getpixel((x, y))  # type: ignore
                if color >= 128:
                    flipped_y = img.height - y - 1  # flip vertically
                    rect = gdstk.rectangle(
                        (x * PIXEL_SIZE, flipped_y * PIXEL_SIZE),
                        ((x + 1) * PIXEL_SIZE, (flipped_y + 1) * PIXEL_SIZE),
                        layer=MET4_LAYER,
                        datatype=DRAWING_DATATYPE,
                    )
                    cell.add(rect)

        lib.write_gds(gds_file)

    def gen_lef(self, variant: str, lef_file: str):
        assert variant in ("top", "bottom")
        width = tech[self.pdk]["PIXEL_SIZE"] * LOGO_WIDTH
        height = tech[self.pdk]["PIXEL_SIZE"] * LOGO_HEIGHT
        lef_lines = [
            f"VERSION 5.7 ;",
            f"  NOWIREEXTENSIONATPIN ON ;",
            f'  DIVIDERCHAR "/" ;',
            f'  BUSBITCHARS "[]" ;',
            f"MACRO tt_logo_{variant}",
            f"  CLASS BLOCK ;",
            f"  FOREIGN tt_logo_{variant} ;",
            f"  ORIGIN 0.000 0.000 ;",
            f"  SIZE {width:.3f} BY {height:.3f} ;",
            f"  OBS",
            f'      LAYER {tech[self.pdk]["OBS_LAYER_NAME"]} ;',
            f"        RECT 0.000 0.000 {width:.3f} {height:.3f} ;",
            f"  END",
            f"END tt_logo_{variant}",
            f"END LIBRARY",
        ]

        with open(lef_file, "w") as f:
            f.write("\n".join(lef_lines) + "\n")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="TT logo generator")
    parser.add_argument(
        "--pdk", type=str, default="sky130A", choices=["sky130A", "ihp-sg13g2"]
    )
    parser.add_argument("--top", action="store_true")
    parser.add_argument("--bottom", action="store_true")
    parser.add_argument("--shuttle", type=str, default="tt10")
    parser.add_argument(
        "--commit", type=str, default="0123456789abcdef0123456789abcdef01234567"
    )
    args = parser.parse_args()

    generator = LogoGenerator(".", pdk=args.pdk)
    if args.top:
        generator.gen_logo("top", "logo/tt_logo_top.gds")
        generator.gen_lef("top", "logo/tt_logo_top.lef")
    if args.bottom:
        shuttle = args.shuttle
        commit = args.commit
        generator.gen_logo("bottom", "logo/tt_logo_bottom.gds", shuttle, commit)
        generator.gen_lef("bottom", "logo/tt_logo_bottom.lef")
    if not args.top and not args.bottom:
        print(f"Need to specify --top or --bottom", file=sys.stderr)
        parser.print_help()
        sys.exit(1)
