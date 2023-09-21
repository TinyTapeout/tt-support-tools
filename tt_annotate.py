#!/usr/bin/env python3

from PIL import Image, ImageDraw, ImageFont

img = Image.open("pics/tinytapeout.png").convert("RGBA")
overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
draw = ImageDraw.Draw(overlay)
font = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans.ttf", 30)

# coordinate mapping
xmap = ((88, 272), (2676, 1646))  # two pairs of (chip x coord, picture x coord)
ymap = ((95, 1879), (3240, 213))  # two pairs of (chip y coord, picture y coord)
xshift, yshift = 40, -43  # text position relative to macro origin

for line in open("openlane/user_project_wrapper/macro.cfg"):
    macro, x, y, orient = line.split()
    if macro == "scan_controller":
        continue
    elif macro.startswith("scanchain_"):
        continue
    name, num = macro.rsplit("_", 1)
    num, x, y = int(num), int(x), int(y)
    x = int(
        (x - xmap[0][0]) / (xmap[1][0] - xmap[0][0]) * (xmap[1][1] - xmap[0][1])
        + xmap[0][1]
    )
    y = int(
        (y - ymap[0][0]) / (ymap[1][0] - ymap[0][0]) * (ymap[1][1] - ymap[0][1])
        + ymap[0][1]
    )
    x += xshift
    y += yshift
    msg = str(num)
    w, h = draw.textsize(msg, font=font)
    draw.text((x - w / 2, y - h / 2), msg, fill=(0, 0, 0, 255), font=font)

combined = Image.alpha_composite(img, overlay).convert("RGB")
combined.save("pics/tinytapeout_numbered.png")
