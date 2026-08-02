#!/usr/bin/env python3
"""Build the two-page Tiny Tapeout product datasheet.

All copy, numbers and colours live in datasheet.yaml. This script renders them
through datasheet.html.mustache, inlining the font and photo as data URIs so the
result is a single self-contained file that prints to two A4 pages.

    python3 docs/product/build.py              # write tt-datasheet.html
    python3 docs/product/build.py --pdf        # also render tt-datasheet.pdf

The sheets are a fixed 297mm tall with overflow hidden, so copy that grows too
long is silently clipped rather than spilling onto a third page. Every build
therefore measures the rendered sheets in headless Chrome and fails if anything
overflows. Pass --no-check to skip that (or set CHROME if it isn't found).

Requires chevron and pyyaml, both already pinned in requirements.txt.
"""

import argparse
import base64
import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import chevron
import yaml

HERE = Path(__file__).parent

# `style` tokens in datasheet.yaml -> CSS classes in the template.
STYLE_CLASSES = {
    "name": "t-name",
    "mono": "t-mono",
    "num": "t-num",
    "price": "t-price",
    "dim": "t-dim",
    "center": "t-center",
}

# Tables are rendered through partials/table.mustache and need preparing first.
TABLE_KEYS = ["pricing", "process", "ratings", "gpio", "analog", "ordering"]

EM_DASH = "—"

CHROME_CANDIDATES = [
    os.environ.get("CHROME"),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome",
    "chromium",
]


def cell_classes(style: str, value: str) -> str:
    """Map a column's style tokens to CSS classes for one cell."""
    classes = []
    for token in style.split():
        try:
            classes.append(STYLE_CLASSES[token])
        except KeyError:
            raise SystemExit(
                f"unknown style '{token}' — expected one of {', '.join(STYLE_CLASSES)}"
            )
    # A lone em dash means "not applicable"; grey it out wherever it appears.
    if value.strip() == EM_DASH and "t-dim" not in classes:
        classes.append("t-dim")
    return " ".join(classes)


def prepare_table(name: str, table: dict) -> None:
    """Expand a table's columns and rows into what the template expects."""
    columns = table.get("columns") or []
    for column in columns:
        width = column.get("width")
        column["width_attr"] = f' style="width:{width}"' if width else ""
        column.setdefault("label", "")

    styles = [column.get("style", "") for column in columns]

    rows = []
    for index, row in enumerate(table.get("rows") or [], start=1):
        if len(row) != len(columns):
            raise SystemExit(
                f"{name}: row {index} has {len(row)} cells "
                f"but there are {len(columns)} columns"
            )
        rows.append(
            {
                "cells": [
                    {"v": value, "cls": cell_classes(style, value)}
                    for style, value in zip(styles, row)
                ]
            }
        )

    table["rows"] = rows
    table["has_note"] = bool(table.get("note"))
    table["has_footnote"] = bool(table.get("footnote"))


def as_data_uri_payload(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"missing asset: {path}")
    return base64.b64encode(path.read_bytes()).decode()


def find_chrome() -> str:
    for candidate in CHROME_CANDIDATES:
        if candidate and (Path(candidate).is_file() or shutil.which(candidate)):
            return candidate
    raise SystemExit(
        "could not find Chrome — set the CHROME environment variable to its path"
    )


MEASURE_SCRIPT = """
<div id="fit-report">pending</div>
<script>
window.addEventListener("load", () => setTimeout(() => {
  const mm = 25.4 / 96;
  const report = [...document.querySelectorAll(".sheet")].map((sheet, i) => {
    const body = sheet.querySelector(".body");
    return [i + 1, ((body.scrollHeight - body.clientHeight) * mm).toFixed(1)].join(":");
  });
  document.getElementById("fit-report").textContent = report.join(",");
}, 500));
</script>
"""


def run_chrome(*flags: str, page: Path) -> bytes:
    result = subprocess.run(
        [
            find_chrome(),
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            *flags,
            page.resolve().as_uri(),
        ],
        check=True,
        capture_output=True,
    )
    return result.stdout


def as_document(html_path: Path, extra: str = "") -> Path:
    """Chrome needs a complete document; the published artifact is wrapped for us."""
    wrapped = html_path.with_name("." + html_path.stem + ".chrome.html")
    wrapped.write_text(
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>*{margin:0;padding:0}</style></head><body>"
        + html_path.read_text(encoding="utf-8")
        + extra
        + "</body></html>",
        encoding="utf-8",
    )
    return wrapped


def check_fit(html_path: Path) -> bool:
    """Measure each sheet in Chrome; report how far any of them overflows."""
    page = as_document(html_path, MEASURE_SCRIPT)
    try:
        dom = run_chrome("--virtual-time-budget=5000", "--dump-dom", page=page)
    finally:
        page.unlink(missing_ok=True)

    found = re.search(rb'<div id="fit-report">([^<]*)</div>', dom)
    if not found or found.group(1) == b"pending":
        logging.warning("could not measure sheet fit — skipping check")
        return True

    overflowed = False
    for entry in found.group(1).decode().split(","):
        sheet, overflow = entry.split(":")
        if float(overflow) > 0:
            overflowed = True
            logging.error(
                f"page {sheet} overflows by {overflow}mm — content past the bottom "
                "of the sheet is CLIPPED, not moved to another page"
            )
        else:
            logging.info(f"page {sheet} fits")
    if overflowed:
        logging.error("trim copy in datasheet.yaml, or shorten a table")
    return not overflowed


def render_pdf(html_path: Path, pdf_path: Path) -> None:
    page = as_document(html_path)
    try:
        run_chrome("--no-pdf-header-footer", f"--print-to-pdf={pdf_path}", page=page)
    finally:
        page.unlink(missing_ok=True)
    pages = len(re.findall(rb"/Type\s*/Page[^s]", pdf_path.read_bytes()))
    logging.info(f"wrote {pdf_path} ({pages} pages)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", default=HERE / "datasheet.yaml", type=Path, help="content YAML"
    )
    parser.add_argument(
        "--out", default=HERE / "tt-datasheet.html", type=Path, help="output HTML"
    )
    parser.add_argument(
        "--pdf", action="store_true", help="also render a PDF next to the HTML"
    )
    parser.add_argument(
        "--no-check",
        dest="check",
        action="store_false",
        help="skip the headless-Chrome overflow check",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(levelname)-8s %(message)s", stream=sys.stdout
    )

    with open(args.config, encoding="utf-8") as fh:
        content = yaml.safe_load(fh)

    for key in TABLE_KEYS:
        if key not in content:
            raise SystemExit(f"{args.config}: missing '{key}' section")
        prepare_table(key, content[key])

    assets = HERE / "assets"
    content["font_b64"] = as_data_uri_payload(assets / content["assets"]["font"])
    content["photo_b64"] = as_data_uri_payload(assets / content["assets"]["photo"])

    with open(HERE / "datasheet.html.mustache", encoding="utf-8") as fh:
        rendered = chevron.render(
            fh.read(),
            content,
            partials_path=str(HERE / "partials"),
            partials_ext="mustache",
        )

    args.out.write_text(rendered, encoding="utf-8")
    logging.info(f"wrote {args.out} ({len(rendered) / 1024:.0f} KB)")

    if args.pdf:
        render_pdf(args.out, args.out.with_suffix(".pdf"))

    if args.check and not check_fit(args.out):
        sys.exit(1)


if __name__ == "__main__":
    main()
