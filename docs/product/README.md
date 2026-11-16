# Product datasheets

Two-page datasheets for Tiny Tapeout: `datasheet.yaml` (individuals) and
`datasheet-universities.yaml` (departments buying for a cohort).

```sh
pip install -r docs/product/requirements.txt
python3 docs/product/build.py --pdf
python3 docs/product/build.py --pdf --config docs/product/datasheet-universities.yaml \
                              --out docs/product/tt-datasheet-universities.html
python3 docs/product/build.py --facts     # every number and where it comes from
```

Numbers in the YAML are `{{placeholders}}`, filled by `facts.py` from their
golden references: this repo, the calculator (the private
`TinyTapeout/tinytapeout-app` repo, so the build needs `GH_TOKEN` or a
`gh auth login` that can read it) and the website. `facts.yaml` holds the few
values with no other source. In CI the token comes from the
`TT_APP_READ_TOKEN` secret.

## Open questions

Inconsistencies found while moving the numbers to their sources. The datasheet
currently keeps the values shown in the "Datasheet" column.

| # | Item | Datasheet | Source says | Where |
|---|------|-----------|-------------|-------|
| 1 | sky130A pad-to-tile round-trip latency | 17 ns | 20 ns worst case, measured on TT3.5 silicon | website `content/specs/gpio` |
| 2 | sky130A I/O supply voltage | 3.30/5.00 V | 1.71–5.5 V pad rating; the demoboard supplies 3.3 V and inputs are not 5 V tolerant | website `content/specs/gpio` |
| 3 | VAPWR analog supply | 3.3 V, adjustable up to VIO | 3.3 V analog supply rail | website `content/specs/analog` |
| 4 | Analog pin price "varies by process, see calculator" | — | All three processes have identical analog pin prices (€40 for the first 2, then €100) | calculator `src/model/invoice.ts` |
| 5 | Launch demoboard price "for the first 80 people" | 80 | Only ttsky26d subsidises 80 boards; ttsky26e has none and the GF shuttles (ttgf26c, ttgf26d, ttboat26) have 200. The sheet follows `launch_offer_shuttle` in `facts.yaml`, which must be updated when the shuttle changes | calculator `src/config/shuttle.ts` |
| 6 | Analog series resistance, capacitance and current | Shown as general specs | The website gives these for sky130A only | website `content/specs/analog` |
| 7 | ihp-sg13g2 project sizes | Not listed | `tile_sizes.yaml` allows 2×1, 3×1, 4×1, 6×1 and 8×1, but there are no `tt_block_*x1` DEF templates for them | repo `tech/ihp-sg13g2/` |

When one is resolved, fix the source (or `facts.yaml`) and remove the row.
