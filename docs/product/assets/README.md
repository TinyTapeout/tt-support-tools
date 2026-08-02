# Datasheet assets

Files here are embedded as data URIs by `build.py`, so the generated HTML is
self-contained. Swap any of them by dropping in a replacement and updating the
`assets:` block in `datasheet.yaml`.

| File | Source | Licence |
| ---- | ------ | ------- |
| `archivo.woff2` | [Archivo](https://github.com/Omnibus-Type/Archivo) via Google Fonts, latin subset, variable weight 100–900 | SIL Open Font License 1.1 — see `OFL.txt` |
| `demoboard.jpg` | Tiny Tapeout ETR demoboard quickstart guide, downscaled to 1000px | © 2024 Pat Deegan, psychogenic.com — **not** covered by this repo's Apache-2.0 licence |
| `supporters/*` | Logos from [tinytapeout.com/credits](https://tinytapeout.com/credits/) | Trademarks of their respective owners |

The demoboard photo carries an embedded copyright of © 2024 Pat Deegan. **Matt
has permission from Pat to use it**, so it needs no on-sheet credit — the
datasheet caption that previously carried one has been removed. It remains
outside this repo's Apache-2.0 licence: don't reuse it elsewhere without asking.

The supporter logos are only rendered when the `supporters:` block in
`datasheet.yaml` is uncommented, which it currently is not.
