"""Draw placeholder product photos into images/ from catalog.yaml.

    python tools/make_placeholders.py            # only missing images
    python tools/make_placeholders.py --force    # redraw all

For a real bakery, put real photos in images/ instead and skip this script.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H = 1024, 768
SS = 2  # draw at 2x, then downscale for smooth edges

KIND_BY_ID = {"macarons": "macarons", "cupcakes": "cupcakes", "trifles": "trifles",
              "ny_set": "gift", "gingerbread": "trees", "bento_classic": "bento", "bento_lotus": "bento"}
KIND_BY_CATEGORY = {"cakes": "cake", "bento": "bento", "desserts": "cupcakes", "newyear": "gift"}

FONT_PATHS = [
    "/usr/share/fonts/truetype/DejaVuSans-Bold.ttf",              # openSUSE
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",       # Debian/Ubuntu
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",     # Fedora
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",                   # Arch
]


def font(size: int) -> ImageFont.FreeTypeFont:
    for p in FONT_PATHS:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size=size)


def rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, k: float):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def light(c, k=0.55):
    return mix(c, (255, 255, 255), k)


def dark(c, k=0.3):
    return mix(c, (40, 20, 20), k)


def s(*v):
    return [int(x * SS) for x in v]


# ---------------------------------------------------------------- drawings

def cake(d: ImageDraw.ImageDraw, c, cx=512, base=560, w=420, tiers=2):
    sponge, cream = light(c, 0.25), light(c, 0.8)
    y = base
    for i in range(tiers):
        tw = w - i * 130
        th = 150 - i * 25
        x0, x1 = cx - tw // 2, cx + tw // 2
        d.rectangle(s(x0, y - th, x1, y), fill=sponge)
        d.ellipse(s(x0, y - 28, x1, y + 28), fill=sponge)
        d.ellipse(s(x0, y - th - 28, x1, y - th + 28), fill=cream)
        for k in range(9):  # frosting drips
            dx = x0 + 20 + k * (tw - 40) // 8
            dh = 30 + (k * 37) % 45
            d.rounded_rectangle(s(dx - 13, y - th, dx + 13, y - th + dh), radius=13 * SS, fill=cream)
        for k in range(14):  # sprinkles
            sx = x0 + 30 + (k * 53) % (tw - 60)
            sy = y - th - 12 + (k * 17) % 22
            d.ellipse(s(sx - 5, sy - 5, sx + 5, sy + 5), fill=dark(c, 0.45) if k % 2 else (255, 255, 255))
        y -= th
    d.rectangle(s(cx - 7, y - 95, cx + 7, y - 15), fill=(250, 240, 230))  # candle
    d.ellipse(s(cx - 14, y - 135, cx + 14, y - 92), fill=(255, 190, 60))
    d.ellipse(s(cx - 7, y - 120, cx + 7, y - 100), fill=(255, 240, 170))


def bento(d, c):
    box = (250, 245, 238)
    d.rounded_rectangle(s(250, 220, 774, 330), radius=12 * SS, fill=mix(box, c, 0.12))  # open lid
    d.rectangle(s(290, 470, 734, 600), fill=box)
    cake(d, c, base=540, w=300, tiers=1)
    d.rectangle(s(290, 520, 734, 600), fill=box)
    d.rectangle(s(290, 520, 734, 530), fill=mix(box, c, 0.2))


def macarons(d, c):
    colors = [c, (183, 225, 205), (250, 214, 140), (244, 167, 195), (190, 170, 230), (250, 190, 150)]
    spots = [(330, 610), (512, 610), (694, 610), (421, 485), (603, 485), (512, 360)]  # a pyramid
    for (x, y), col in zip(spots, colors):
        x0, x1 = x - 88, x + 88
        d.rounded_rectangle(s(x0, y - 62, x1, y - 18), radius=22 * SS, fill=col)
        d.rounded_rectangle(s(x0 + 10, y - 22, x1 - 10, y - 4), radius=8 * SS, fill=(255, 248, 240))
        d.rounded_rectangle(s(x0, y - 8, x1, y + 36), radius=22 * SS, fill=col)


def cupcake(d, c, cx, base, scale=1.0):
    wrap = dark(c, 0.15)
    sw = 170 * scale
    d.polygon(s(cx - sw / 2, base - 150 * scale, cx + sw / 2, base - 150 * scale,
                cx + sw / 2.6, base, cx - sw / 2.6, base), fill=wrap)
    for k in range(-3, 4):
        d.line(s(cx + k * sw / 8, base - 150 * scale, cx + k * sw / 10.5, base), fill=light(wrap, 0.3), width=5 * SS)
    cream = light(c, 0.7)
    for i, (rw, rh) in enumerate([(210, 80), (165, 70), (110, 60)]):
        y = base - 150 * scale - i * 50 * scale
        d.ellipse(s(cx - rw * scale / 2, y - rh * scale / 2 - 20, cx + rw * scale / 2, y + rh * scale / 2 - 20), fill=cream)
    top = base - 150 * scale - 150 * scale
    d.ellipse(s(cx - 22 * scale, top - 30 * scale, cx + 22 * scale, top + 14 * scale), fill=(214, 40, 60))


def cupcakes(d, c):
    cupcake(d, c, 330, 620, 0.85)
    cupcake(d, c, 694, 620, 0.85)
    cupcake(d, c, 512, 650, 1.0)


def trifles(d, c):
    layers = [light(c, 0.1), (250, 240, 225), dark(c, 0.2), (250, 240, 225)]
    for i, cx in enumerate((340, 512, 684)):
        x0, x1, bottom = cx - 70, cx + 70, 640 - (30 if i == 1 else 0)
        y = bottom
        for k, col in enumerate(layers):
            h = 70 if k % 2 == 0 else 45
            d.rectangle(s(x0, y - h, x1, y), fill=col)
            y -= h
        d.ellipse(s(x0 - 5, y - 40, x1 + 5, y + 25), fill=(255, 252, 248))
        d.ellipse(s(cx - 18, y - 60, cx + 18, y - 24), fill=(200, 30, 60))
        d.rectangle(s(x0 - 8, y - 10, x0, bottom), fill=(255, 255, 255))
        d.rectangle(s(x1, y - 10, x1 + 8, bottom), fill=(255, 255, 255))


def gift(d, c):
    cake(d, c, cx=380, base=620, w=300, tiers=1)
    red, ribbon = (205, 60, 60), (250, 215, 110)
    d.rectangle(s(560, 380, 800, 620), fill=red)
    d.rectangle(s(545, 340, 815, 400), fill=dark(red, 0.1))
    d.rectangle(s(665, 340, 695, 620), fill=ribbon)
    d.ellipse(s(610, 290, 680, 350), outline=ribbon, width=14 * SS)
    d.ellipse(s(680, 290, 750, 350), outline=ribbon, width=14 * SS)


def trees(d, c):
    dough, icing = (196, 135, 80), (255, 255, 255)
    for i, (cx, base, k) in enumerate([(330, 640, 0.8), (694, 640, 0.8), (512, 660, 1.0)]):
        for j in range(3):
            tw, top = (260 - j * 60) * k, base - (100 + j * 90) * k
            d.polygon(s(cx - tw / 2, top + 110 * k, cx + tw / 2, top + 110 * k, cx, top - 40 * k), fill=dough)
            d.line(s(cx - tw / 2 + 20, top + 95 * k, cx + tw / 2 - 20, top + 95 * k), fill=icing, width=6 * SS)
        d.rectangle(s(cx - 22 * k, base, cx + 22 * k, base + 40 * k), fill=dark(dough, 0.2))
        for j in range(5):
            dx, dy = cx + ((j * 47) % 90 - 45) * k, base - (60 + j * 55) * k
            d.ellipse(s(dx - 9, dy - 9, dx + 9, dy + 9), fill=(220, 50, 60) if j % 2 else (255, 215, 90))


DRAW = {"cake": cake, "bento": bento, "macarons": macarons, "cupcakes": cupcakes,
        "trifles": trifles, "gift": gift, "trees": trees}


def render(product: dict, shop_name: str) -> Image.Image:
    c = rgb(product.get("color", "#f4a7c3"))
    img = Image.new("RGB", (W * SS, H * SS))
    top, bottom = light(c, 0.82), light(c, 0.55)
    grad = ImageDraw.Draw(img)
    for y in range(H * SS):
        grad.line([(0, y), (W * SS, y)], fill=mix(top, bottom, y / (H * SS)))

    shadow = Image.new("L", img.size, 0)
    ImageDraw.Draw(shadow).ellipse(s(200, 600, 824, 690), fill=90)
    shadow = shadow.filter(ImageFilter.GaussianBlur(18 * SS))
    img.paste(dark(c, 0.5), mask=shadow)

    d = ImageDraw.Draw(img)
    kind = KIND_BY_ID.get(product["id"]) or KIND_BY_CATEGORY.get(product["category"], "cake")
    DRAW[kind](d, c)

    # a small corner mark so nobody mistakes a placeholder for a real product photo
    tag = "demo"
    f_small = font(18 * SS)
    tw = d.textlength(tag, font=f_small)
    d.text((W * SS - tw - 28 * SS, (H - 44) * SS), tag, font=f_small, fill=dark(c, 0.15))
    return img.resize((W, H), Image.LANCZOS)


def main() -> None:
    force = "--force" in sys.argv
    catalog = yaml.safe_load((ROOT / "catalog.yaml").read_text(encoding="utf-8"))
    shop = catalog["shop"]["name"]
    for p in catalog["products"]:
        if not p.get("photo"):
            continue
        out = ROOT / p["photo"]
        if out.exists() and not force:
            print(f"skip   {out.relative_to(ROOT)} (exists)")
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        render(p, shop).save(out, optimize=True)
        print(f"drawn  {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
