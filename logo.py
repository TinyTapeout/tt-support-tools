#!/usr/bin/env python3

import sys

import gdstk
from git.repo import Repo
from PIL import Image, ImageDraw, ImageFont

from config import Config


class LogoGenerator:
    def __init__(self, tt_dir, config: Config | None = None):
        self.tt_dir = tt_dir
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

            img = Image.new("L", (200, 200), (0,))
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
            draw.text((2, shuttle_y_offset), shuttle, fill=255, font=font(shuttle_font_size))
            draw.text((2, 68), commit[:8], fill=255, font=font(44))
            draw.text((2, 107), commit[8:18], fill=255, font=font(35))
            draw.text((1, 137), commit[18:29], fill=255, font=font(32))
            draw.text((1, 165), commit[29:], fill=255, font=font(32))

        PRBOUNDARY_LAYER = 235
        PRBOUNDARY_DATATYPE = 4
        MET4_LAYER = 71
        DRAWING_DATATYPE = 20
        PIXEL_SIZE = 0.5  # um

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


if __name__ == "__main__":

    try:
        if sys.argv[1] == "--top":
            LogoGenerator(".").gen_logo("top", "logo/tt_logo_top.gds")

        elif sys.argv[1] == "--bottom":
            shuttle = sys.argv[2]  # e.g. "tt10"
            commit = sys.argv[3]  # e.g. "0123456789abcdef0123456789abcdef01234567"
            LogoGenerator(".").gen_logo(
                "bottom", "logo/tt_logo_bottom.gds", shuttle, commit
            )

    except IndexError:
        print(
            f"Usage:\n  {sys.argv[0]} --top\n  {sys.argv[0]} --bottom <shuttle> <commit>",
            file=sys.stderr,
        )
