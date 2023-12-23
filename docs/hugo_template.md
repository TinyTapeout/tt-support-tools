---
hidden: true
title: "{mux_address} {title}"
weight: {weight}
---

## {mux_address} : {title}

* Author: {author}
* Description: {description}
* [GitHub repository]({git_url})
* [GDS submitted]({git_action})
* {project_type} project
* [Extra docs]({doc_link})
* Clock: {clock_hz} Hz

{user_docs}

### IO

| # | Input          | Output         | Bidirectional   |
| - | -------------- | -------------- | --------------- |
| 0 | {pinout.ui[0]} | {pinout.uo[0]} | {pinout.uio[0]} |
| 1 | {pinout.ui[1]} | {pinout.uo[1]} | {pinout.uio[1]} |
| 2 | {pinout.ui[2]} | {pinout.uo[2]} | {pinout.uio[2]} |
| 3 | {pinout.ui[3]} | {pinout.uo[3]} | {pinout.uio[3]} |
| 4 | {pinout.ui[4]} | {pinout.uo[4]} | {pinout.uio[4]} |
| 5 | {pinout.ui[5]} | {pinout.uo[5]} | {pinout.uio[5]} |
| 6 | {pinout.ui[6]} | {pinout.uo[6]} | {pinout.uio[6]} |
| 7 | {pinout.ui[7]} | {pinout.uo[7]} | {pinout.uio[7]} |

### Chip location

{{{{< shuttle-map "{shuttle_id}" "{mux_address}" >}}}}
