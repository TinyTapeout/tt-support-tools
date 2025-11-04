import logging
import os
import random
import re
import subprocess

import cairosvg  # type: ignore
import gdstk  # type: ignore


# Custom exception for convert_svg_to_png()
class SVGTooComplexError(Exception):
    pass


# Helper function to randomize layer order of polygons in a subcell in a deterministic way
def scramble_polygons(polygons, seed):
    # group polygons by layer/datatype
    groups: dict[tuple[int, int], list] = {}
    for p in polygons:
        groups.setdefault((p.layer, p.datatype), []).append(p)
    # shuffle the layer list
    layers = sorted(groups)
    random.Random(seed).shuffle(layers)
    # return polygons according to the shuffled layer order
    return [p for layer in layers for p in groups[layer]]


# SVG render of the GDS
def render_svg(
    gds,
    svg="gds_render.svg",
    pad="5%",
    filter_text=False,
    filter_layers=None,
    scramble_cells=None,
):
    library = gdstk.read_gds(gds)
    top_cells = library.top_level()
    assert len(top_cells) == 1
    top_cell = top_cells[0]
    assert isinstance(top_cell, gdstk.Cell)
    cells = [top_cell] + [
        cell for cell in top_cell.dependencies(True) if isinstance(cell, gdstk.Cell)
    ]
    for cell in cells:
        if filter_text:
            cell.remove(*cell.labels)
        if filter_layers:
            cell.filter(filter_layers)
        if scramble_cells is not None:
            if re.match(scramble_cells, cell.name):
                polygons = cell.polygons
                paths = cell.paths
                cell.remove(*polygons, *paths)
                path_polygons = [pp for p in paths for pp in p.to_polygons()]
                cell.add(*scramble_polygons(polygons, cell.name))
                cell.add(*scramble_polygons(path_polygons, cell.name))
    top_cell.write_svg(svg, pad=pad)


# Convert SVG to PNG using rsvg-convert or cairosvg
def convert_svg_to_png(svg, png, force_cairo=False):
    if force_cairo:
        logging.warning("Falling back to cairosvg. This might take a while...")
        cairosvg.svg2png(url=svg, write_to=png)
    else:
        cmd = f"rsvg-convert --unlimited {svg} -o {png} --no-keep-image-data"
        logging.debug(cmd)
        p = subprocess.run(cmd, shell=True, capture_output=True)
        if p.returncode == 127:
            logging.warning(
                'rsvg-convert not found; is package "librsvg2-bin" installed?'
            )
            # fall back to cairosvg
            convert_svg_to_png(svg, png, force_cairo=True)
        elif p.returncode != 0:
            if b"cannot load more than" in p.stderr:
                logging.warning(
                    f'Too many SVG elements ("{p.stderr.decode().strip()}")'
                )
                raise SVGTooComplexError()
            else:
                logging.warning(
                    f'rsvg-convert returned an error ("{p.stderr.decode().strip()}")'
                )
                # fall back to cairosvg
                convert_svg_to_png(svg, png, force_cairo=True)


# Try various QUICK methods to create a more-compressed PNG render of the GDS,
# and fall back to cairosvg if it doesn't work. This is designed for speed,
# and in particular for use by the GitHub Actions.
# For more info, see:
# https://github.com/TinyTapeout/tt-gds-action/issues/8
def render_png(
    gds,
    svg="gds_render_preview.svg",
    svg_alt="gds_render_preview_alt.svg",
    png="gds_render_preview.png",
    final_png="gds_render.png",
    scramble_cells=None,
    buried_layers=None,
    quality="0-30",
):
    logging.info(f"Rendering SVG without text labels: {svg}")
    render_svg(gds=gds, svg=svg, pad=0, filter_text=True, scramble_cells=scramble_cells)
    try:
        logging.info(f"Converting to PNG using rsvg-convert: {png}")
        convert_svg_to_png(svg, png)
    except SVGTooComplexError:
        logging.info(f"Rendering SVG without text labels or buried layers: {svg_alt}")
        render_svg(
            gds=gds,
            svg=svg_alt,
            pad=0,
            filter_text=True,
            filter_layers=buried_layers,
            scramble_cells=scramble_cells,
        )
        try:
            logging.info(f"Converting to PNG using rsvg-convert: {png}")
            convert_svg_to_png(svg_alt, png)
        except SVGTooComplexError:
            # Fall back to cairosvg, and since we're doing that, might as well use the original full-detail SVG anyway:
            convert_svg_to_png(svg, png, force_cairo=True)

    # By now we should have gds_render_preview.png

    # Compress with pngquant:
    logging.info(f"Compressing PNG further with pngquant to: {final_png}")

    cmd = f"pngquant --quality {quality} --speed 1 --nofs --strip --force --output {final_png} {png}"
    logging.debug(cmd)
    p = subprocess.run(cmd, shell=True, capture_output=True)

    if p.returncode == 127:
        logging.warning(
            'pngquant not found; is package "pngquant" installed? Using intermediate (uncompressed) PNG file'
        )
        os.rename(png, final_png)
    elif p.returncode != 0:
        logging.warning(
            f'pngquant error {p.returncode} ("{p.stderr.decode().strip()}"). Using intermediate (uncompressed) PNG file'
        )
        os.rename(png, final_png)
    logging.info(f"Final PNG is {final_png} ({os.path.getsize(final_png):,} bytes)")
