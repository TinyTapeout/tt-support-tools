"""Collect the datasheet's facts from their golden references.

Every number the datasheet quotes comes from one of four places, in this order
of preference:

    repo        this repository: tile sizes, DEF templates, tech.py, project_info.py
    calculator  the app's pricing source (private repo, read via the GitHub API)
    website     tinytapeout.com's source (public repo, read raw from GitHub)
    config      facts.yaml, for the few things nothing else records

collect() returns a nested dict for the templates plus the source of each
value, so `build.py --facts` can show where every number came from. A value in
facts.yaml that another source also provides is an error, not an override.
"""

import html
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

import yaml

HERE = Path(__file__).parent
ROOT = HERE.parent.parent

APP_REPO = "TinyTapeout/tinytapeout-app"
WEBSITE_RAW = "https://raw.githubusercontent.com/TinyTapeout/tinytapeout_www/main/"

NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven"]

# Pins on the package, in pin-map order. ena is internal, so it is not listed;
# uio counts once even though the template splits it into in/out/oe.
GPIO_SIGNALS = {
    "clk": "clk",
    "rst_n": "rst_n",
    "ui_in": "ui_in",
    "uo_out": "uo_out",
    "uio": "uio_in",
}


class FactError(SystemExit):
    pass


class Facts:
    """A nested dict of values, with the source of each recorded alongside."""

    def __init__(self) -> None:
        self.values: dict[str, Any] = {}
        self.sources: dict[str, str] = {}

    def set(self, key: str, value: Any, source: str) -> None:
        if key in self.sources:
            raise FactError(
                f"{key} is set by both {self.sources[key]} and {source} — "
                "remove it from facts.yaml, the other source is authoritative"
            )
        self.sources[key] = source
        node = self.values
        *parents, leaf = key.split(".")
        for part in parents:
            node = node.setdefault(part, {})
        node[leaf] = value


# --------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------


def github_token() -> str:
    for var in ("GH_TOKEN", "GITHUB_TOKEN"):
        if os.environ.get(var):
            return os.environ[var]
    try:
        return subprocess.run(
            ["gh", "auth", "token"], check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        raise FactError(
            f"reading prices needs access to {APP_REPO} (a private repo): set "
            "GH_TOKEN to a token that can read it, or log in with `gh auth login`"
        )


def fetch(url: str, headers: dict[str, str] | None = None) -> str:
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        hint = ""
        if error.code == 404 and "api.github.com" in url:
            hint = f" — does the token have read access to {APP_REPO}?"
        raise FactError(f"fetching {url}: HTTP {error.code}{hint}")
    except urllib.error.URLError as error:
        raise FactError(f"fetching {url}: {error.reason}")


def fetch_app_file(path: str) -> str:
    return fetch(
        f"https://api.github.com/repos/{APP_REPO}/contents/{path}",
        {
            "Accept": "application/vnd.github.raw",
            "Authorization": f"Bearer {github_token()}",
        },
    )


def fetch_website_file(path: str) -> str:
    return fetch(WEBSITE_RAW + path)


def need(pattern: str, text: str, what: str, flags: int = 0) -> re.Match:
    """re.search that fails loudly: a moved source must break the build."""
    found = re.search(pattern, text, flags)
    if not found:
        raise FactError(f"could not find {what} — has the source changed format?")
    return found


# --------------------------------------------------------------------------
# Repo
# --------------------------------------------------------------------------


def repo_pdks() -> list[str]:
    return sorted(p.parent.name for p in (ROOT / "tech").glob("*/tile_sizes.yaml"))


def size_key(size: str) -> tuple[int, int]:
    width, height = size.split("x")
    return int(width), int(height)


def collect_repo(facts: Facts, pdks: list[str]) -> None:
    sys.path.insert(0, str(ROOT))
    from project_info import MAX_ANALOG_PINS
    from tech import tech_map

    src_tiles = "repo: tech/{}/tile_sizes.yaml"
    max_blocks: dict[str, str] = {}
    analog_heights: set[int] = set()

    for pdk in pdks:
        tech_dir = ROOT / "tech" / pdk
        with open(tech_dir / "tile_sizes.yaml") as fh:
            sizes: dict[str, str] = yaml.safe_load(fh)

        _, _, width, height = sizes["1x1"].split()
        facts.set(
            f"pdk.{pdk}.tile_1x1", f"{width} × {height} µm", src_tiles.format(pdk)
        )

        largest = max(sizes, key=lambda s: size_key(s)[0] * size_key(s)[1])
        max_blocks[pdk] = largest.replace("x", "×")
        facts.set(f"pdk.{pdk}.max_block", max_blocks[pdk], src_tiles.format(pdk))

        corner = tech_map[pdk].tt_corner  # type: ignore[index]
        volts = need(r"_(\d)[vp](\d\d)", corner, f"a voltage in {pdk}'s tt_corner")
        facts.set(
            f"pdk.{pdk}.core_voltage",
            f"{volts[1]}.{volts[2]}",
            f"repo: tech.py tt_corner {corner}",
        )

        for path in (tech_dir / "def" / "analog").glob("tt_analog_*.def"):
            analog_heights.add(int(need(r"_\d+x(\d+)", path.name, path.name)[1]))

    # "up to <b>8×4</b> on sky130A and ihp-sg13g2 and up to <b>4×4</b> on gf180mcuD"
    groups: dict[str, list[str]] = {}
    for pdk in pdks:
        groups.setdefault(max_blocks[pdk], []).append(pdk)
    facts.set(
        "blocks.max_summary",
        " and up to ".join(
            f"<b>{size}</b> on {join_and(names)}" for size, names in groups.items()
        ),
        "repo: tech/*/tile_sizes.yaml",
    )
    facts.set("analog.min_height", min(analog_heights), "repo: tech/*/def/analog/*.def")

    facts.set("analog.max_pins", MAX_ANALOG_PINS, "repo: project_info.MAX_ANALOG_PINS")
    facts.set(
        "analog.pins",
        f"ua[0:{MAX_ANALOG_PINS - 1}]",
        "repo: project_info.MAX_ANALOG_PINS",
    )

    collect_gpio(facts, pdks)


def def_pin_widths(path: Path) -> dict[str, int]:
    widths: dict[str, int] = {}
    pins = need(
        r"^PINS \d+ ;(.*?)^END PINS", path.read_text(), f"PINS in {path}", re.M | re.S
    )
    for name, index in re.findall(r"^\s*- (\w+)(?:\[(\d+)\])?", pins[1], re.M):
        widths[name] = max(widths.get(name, 0), int(index or 0) + 1)
    return widths


def collect_gpio(facts: Facts, pdks: list[str]) -> None:
    """Pin widths from the 1×1 digital template; every PDK must agree."""
    per_pdk = {}
    for pdk in pdks:
        template = next((ROOT / "tech" / pdk / "def").glob("tt_block_1x1_*.def"))
        widths = def_pin_widths(template)
        per_pdk[pdk] = {name: widths[pin] for name, pin in GPIO_SIGNALS.items()}
    first = per_pdk[pdks[0]]
    for pdk, widths in per_pdk.items():
        if widths != first:
            raise FactError(
                f"GPIO pins differ between {pdks[0]} and {pdk}: {first} vs {widths}"
            )

    source = "repo: tech/*/def/tt_block_1x1_*.def"
    for name, width in first.items():
        facts.set(f"gpio.{name}", width, source)
    facts.set("gpio.total", sum(first.values()), source)


# --------------------------------------------------------------------------
# Calculator
# --------------------------------------------------------------------------


def parse_ts_object(body: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key, raw in re.findall(r"^\s*(\w+):\s*([^,\n]+),", body, re.M):
        raw = raw.strip()
        if raw in ("true", "false"):
            values[key] = raw == "true"
        elif re.fullmatch(r"\d+", raw):
            values[key] = int(raw)
        else:
            values[key] = raw.strip("'\"")
    return values


def collect_calculator(facts: Facts, config: dict, pdks: list[str]) -> None:
    invoice = fetch_app_file("src/model/invoice.ts")
    objects = {
        name: parse_ts_object(body)
        for name, body in re.findall(
            r"export const (\w+): IShuttlePrices = \{(.*?)\n\};", invoice, re.S
        )
    }
    record = need(
        r"shuttlePrices: Record<ShuttleType, IShuttlePrices> = \{(.*?)\};",
        invoice,
        "shuttlePrices in invoice.ts",
        re.S,
    )
    by_type = {
        key: objects[name] for key, name in re.findall(r"(\w+): (\w+),", record[1])
    }

    prices = []
    for pdk in pdks:
        shuttle_type = config["pdks"][pdk]["calculator"]
        if shuttle_type not in by_type:
            raise FactError(
                f"facts.yaml: {pdk} calculator '{shuttle_type}' is not one of "
                f"{', '.join(by_type)} in invoice.ts"
            )
        prices.append(by_type[shuttle_type])
    for p in prices:
        if p["currency"] != "EUR":
            raise FactError(f"invoice.ts: expected EUR prices, found {p['currency']}")

    # The datasheet quotes "from" prices, so take the cheapest across PDKs.
    src = "calculator: invoice.ts"
    fields = {
        "tile": "tile",
        "board": "pcb",
        "board_launch": "pcbDiscount",
        "analog_pin": "analogPin",
        "analog_pin_discounted": "analogPinDiscount",
        "analog_pins_discounted": "discountedAnalogPins",
        "postage": "shipping",
    }
    for key, field in fields.items():
        facts.set(f"price.{key}", min(p[field] for p in prices), f"{src} {field}")

    shuttles = fetch_app_file("src/config/shuttle.ts")
    slug = config["launch_offer_shuttle"]
    block = need(
        rf"slug: '{re.escape(slug)}',(.*?)\n  \}}",
        shuttles,
        f"shuttle '{slug}' in shuttle.ts",
        re.S,
    )
    count = int(
        need(r"subsidizedPCBs: (\d+)", block[1], f"subsidizedPCBs for {slug}")[1]
    )
    if count == 0:
        raise FactError(
            f"shuttle.ts: {slug} has no subsidised boards — pick another launch_offer_shuttle"
        )
    facts.set(
        "price.board_launch_count",
        count,
        f"calculator: shuttle.ts {slug} subsidizedPCBs",
    )


# --------------------------------------------------------------------------
# Website
# --------------------------------------------------------------------------


def md_table_value(text: str, label: str) -> str:
    return need(
        rf"^\|\s*{re.escape(label)}\s*\|\s*([^|]+?)\s*\|", text, f"'{label}' row", re.M
    )[1]


def number_with_unit(value: str, unit: str, what: str) -> int:
    found = need(rf"^(\d+)\s*{unit}$", value, f"{what} in {unit} (got '{value}')")
    return int(found[1])


def collect_website(facts: Facts) -> None:
    gpio_path = "content/specs/gpio/_index.md"
    gpio = fetch_website_file(gpio_path)
    src = f"website: {gpio_path}"
    # The website's GPIO specs are for the sky130 pads only.
    facts.set(
        "pdk.sky130A.input_freq",
        number_with_unit(
            md_table_value(gpio, "Maximum input frequency"), "MHz", "input frequency"
        ),
        src,
    )
    facts.set(
        "pdk.sky130A.output_freq",
        number_with_unit(
            md_table_value(gpio, "Maximum output frequency"), "MHz", "output frequency"
        ),
        src,
    )
    facts.set(
        "pdk.sky130A.drive",
        number_with_unit(
            md_table_value(gpio, "Drive strength (source/sink)"), "mA", "drive strength"
        ),
        src,
    )
    variance = need(
        r"variance between different IO pins has been measured at less than (\d+) ?ns",
        gpio,
        "pin delay variance",
    )
    facts.set("pdk.sky130A.variance", int(variance[1]), src)

    analog_path = "content/specs/analog/_index.md"
    analog = fetch_website_file(analog_path)
    section = need(
        r"## Specifications and limitations - sky130A(.*?)\n## ",
        analog,
        "sky130A analog specs",
        re.S,
    )[1]
    src = f"website: {analog_path}"
    resistance = need(
        r"Resistance:\s*<\s*(\d+)\s*ohm", section, "analog resistance", re.I
    )
    capacitance = need(
        r"Capacitance:\s*<\s*(\d+)\s*pf", section, "analog capacitance", re.I
    )
    current = need(r"Max current:\s*(\d+)\s*mA", section, "analog max current", re.I)
    facts.set("analog.resistance", f"&lt; {resistance[1]} Ω", src)
    facts.set("analog.capacitance", f"&lt; {capacitance[1]} pF", src)
    facts.set("analog.current", f"{current[1]} mA", src)

    faq_path = "content/faq/_index.en.md"
    faq = fetch_website_file(faq_path)
    months = need(
        r"taking between (\d+) and (\d+) months to manufacture",
        faq,
        "fabrication lead time",
    )
    facts.set("schedule.lead_time", f"{months[1]}–{months[2]}", f"website: {faq_path}")


# --------------------------------------------------------------------------
# Config, and values derived from the others
# --------------------------------------------------------------------------


def collect_config(facts: Facts, config: dict, pdks: list[str]) -> None:
    src = "config: facts.yaml"
    for pdk in pdks:
        for key, value in config["pdks"][pdk].items():
            if key != "calculator":
                facts.set(f"pdk.{pdk}.{key}", escape(value), src)
    facts.set(
        "price.volume_discount_percent", config["volume_discount"]["percent"], src
    )
    facts.set(
        "price.volume_discount_threshold", config["volume_discount"]["threshold"], src
    )
    facts.set("tile.cells", config["cells_per_tile"], src)
    facts.set("schedule.shuttles_per_year", escape(config["shuttles_per_year"]), src)
    facts.set("analog.vapwr", escape(config["vapwr"]), src)
    facts.set("uni.students", config["university_example"]["students"], src)
    facts.set("uni.boards", config["university_example"]["boards"], src)


def derive(facts: Facts, pdks: list[str]) -> None:
    v = facts.values
    price, uni = v["price"], v["uni"]
    src = "derived"

    facts.set(
        "price.headline",
        price["tile"] + price["board_launch"] + price["postage"],
        f"{src}: tile + board_launch + postage",
    )

    tiles_cost = uni["students"] * price["tile"]
    boards_cost = uni["boards"] * price["board"]
    postage_cost = uni["boards"] * price["postage"]
    total = tiles_cost + boards_cost + postage_cost
    facts.set("uni.tiles_cost", tiles_cost, f"{src}: students × tile")
    facts.set("uni.boards_cost", boards_cost, f"{src}: boards × board")
    facts.set("uni.postage_cost", postage_cost, f"{src}: boards × postage")
    facts.set("uni.total", total, f"{src}: sum of the above")
    facts.set(
        "uni.per_student", round(total / uni["students"]), f"{src}: total ÷ students"
    )

    facts.set("pdks.slash", " / ".join(pdks), f"{src}: PDK list")
    facts.set("pdks.and", join_and(pdks), f"{src}: PDK list")
    facts.set("pdks.count", len(pdks), f"{src}: PDK list")
    facts.set("pdks.count_word", NUMBER_WORDS[len(pdks)], f"{src}: PDK list")
    facts.set(
        "pdks.count_Word", NUMBER_WORDS[len(pdks)].capitalize(), f"{src}: PDK list"
    )

    for pdk in pdks:
        facts.set(f"pdk.{pdk}.name", pdk, f"{src}: PDK list")


def join_and(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def escape(value: Any) -> Any:
    return html.escape(value, quote=False) if isinstance(value, str) else value


def collect(config_path: Path = HERE / "facts.yaml") -> tuple[dict, dict[str, str]]:
    with open(config_path, encoding="utf-8") as fh:
        config = yaml.safe_load(fh)

    pdks = list(config["pdks"])
    if sorted(pdks) != repo_pdks():
        raise FactError(
            f"facts.yaml lists PDKs {sorted(pdks)} but the repo has {repo_pdks()} — "
            "add or remove entries under pdks:"
        )

    facts = Facts()
    steps: list[Callable[[], None]] = [
        lambda: collect_repo(facts, pdks),
        lambda: collect_calculator(facts, config, pdks),
        lambda: collect_website(facts),
        lambda: collect_config(facts, config, pdks),
        lambda: derive(facts, pdks),
    ]
    for step in steps:
        step()
    facts.values["pdk_order"] = pdks
    return facts.values, facts.sources


if __name__ == "__main__":
    values, sources = collect()
    print(json.dumps(values, indent=2, ensure_ascii=False))
