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


def load_config(path: Path) -> dict:
    """Parse the content YAML, reporting syntax errors against the offending line."""
    text = path.read_text(encoding="utf-8")
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        detail = getattr(error, "problem", str(error))
        if mark is None:
            raise SystemExit(f"{path}: {detail}")
        line = (
            text.splitlines()[mark.line] if mark.line < len(text.splitlines()) else ""
        )
        raise SystemExit(
            f"{path}:{mark.line + 1}: {detail}\n"
            f"  {line.strip()}\n"
            '  hint: inside a "quoted" value, HTML quotes must be escaped as \\"'
        )


def walk_strings(node, path: str = ""):
    """Yield (dotted-path, text) for every string in the loaded config."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from walk_strings(value, f"{path}.{key}" if path else str(key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk_strings(value, f"{path}[{index}]")
    elif isinstance(node, str):
        yield path, node


def validate_markup(content: dict) -> None:
    """Catch the two easy ways to write broken HTML in the config.

    YAML only processes \\" as an escape inside "quoted" values. In a >- folded
    or plain value the backslash survives into the page and breaks the markup,
    so a loaded string should never still contain one.
    """
    problems = []
    for path, text in walk_strings(content):
        if '\\"' in text:
            problems.append(
                f'{path}: contains a literal \\" — in a >- or plain value write '
                "the quote on its own, with no backslash"
            )
        for tag in ("b", "a", "span"):
            opened = len(re.findall(rf"<{tag}\b", text))
            closed = len(re.findall(rf"</{tag}>", text))
            if opened != closed:
                problems.append(
                    f"{path}: {opened} <{tag}> but {closed} </{tag}> — unbalanced tag"
                )
        # An unterminated href swallows the rest of the tag, which still leaves
        # <a> and </a> balanced, so check the attribute closes its own quotes.
        if len(re.findall(r"href=", text)) != len(re.findall(r'href="[^"]*"', text)):
            problems.append(
                f'{path}: malformed link — href="..." is missing its closing quote'
            )
    if problems:
        raise SystemExit("\n".join(f"{p}" for p in problems))


MIME_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def as_data_uri_payload(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"missing asset: {path}")
    return base64.b64encode(path.read_bytes()).decode()


def prepare_supporters(supporters: dict, assets: Path) -> None:
    """Inline each supporter logo and work out its per-item sizing."""
    height = supporters.get("logo_height", "8.5mm")
    for item in supporters.get("items") or []:
        path = assets / "supporters" / item["file"]
        suffix = path.suffix.lower()
        if suffix not in MIME_TYPES:
            raise SystemExit(f"{path}: expected one of {', '.join(MIME_TYPES)}")
        item["data_uri"] = (
            f"data:{MIME_TYPES[suffix]};base64,{as_data_uri_payload(path)}"
        )
        scale = item.get("scale", 1)
        item["style"] = f"height: calc({height} * {scale})"


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
    # Deliberately no --user-data-dir: combined with --print-to-pdf, Chrome
    # writes the PDF correctly and then never exits.
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
        timeout=120,
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
        # Fail closed: reporting success without having measured anything is how
        # clipped content ships unnoticed.
        logging.error(
            "could not measure sheet fit — Chrome returned no report. "
            "Re-run, or pass --no-check to build without verifying the fit"
        )
        return False

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

    content = load_config(args.config)
    validate_markup(content)

    for key in TABLE_KEYS:
        if key not in content:
            raise SystemExit(f"{args.config}: missing '{key}' section")
        prepare_table(key, content[key])

    assets = HERE / "assets"
    content["font_b64"] = as_data_uri_payload(assets / content["assets"]["font"])
    content["photo_b64"] = as_data_uri_payload(assets / content["assets"]["photo"])
    if "supporters" in content:
        prepare_supporters(content["supporters"], assets)

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
