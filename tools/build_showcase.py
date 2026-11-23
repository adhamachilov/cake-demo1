"""Build the static showcase into showcase/: the Mini App with a simulated bakery,
ready to drag onto https://app.netlify.com/drop (or any static host). No server needed.

    .venv/bin/python tools/build_showcase.py

Run it again after changing catalog.yaml, photos or the app, then upload the folder again."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from bot.catalog import CatalogError, load_catalog  # noqa: E402

OUT = ROOT / "showcase"
STATIC = ROOT / "bot" / "webapp" / "static"
MARKER = ".built-by-build_showcase"
SIZES = {520: 72, 1080: 78}  # width -> JPEG quality (cards / big photos)
FOREVER = "public, max-age=31536000, immutable"

HEADERS = f"""/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin

/
  Cache-Control: no-cache
/index.html
  Cache-Control: no-cache
/catalog.json
  Cache-Control: no-cache
/app.js
  Cache-Control: {FOREVER}
/app.css
  Cache-Control: {FOREVER}
/showcase.js
  Cache-Control: {FOREVER}
/img/*
  Cache-Control: {FOREVER}
"""


def photo_variants(src: Path) -> dict[int, str]:
    """Resized copies named after their content, so phones can cache them forever."""
    out = {}
    with Image.open(src) as im:
        im = im.convert("RGB")
        for width, quality in SIZES.items():
            copy = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS) if im.width > width else im
            tmp = OUT / "img" / "tmp.jpg"
            copy.save(tmp, "JPEG", quality=quality, optimize=True, progressive=True)
            digest = hashlib.sha256(tmp.read_bytes()).hexdigest()[:10]
            name = f"{src.stem}-{width}-{digest}.jpg"
            tmp.replace(OUT / "img" / name)
            out[width] = f"img/{name}"
    return out


def main() -> None:
    try:
        catalog = load_catalog(ROOT / "catalog.yaml")
    except CatalogError as e:
        sys.exit(f"[catalog error] {e}")

    if OUT.exists():
        if not (OUT / MARKER).exists() and any(OUT.iterdir()):
            sys.exit(f"{OUT} exists and was not made by this script; move it away first.")
        shutil.rmtree(OUT)
    (OUT / "img").mkdir(parents=True)
    (OUT / MARKER).write_text("This folder is generated. Edit catalog.yaml / bot/webapp/static and rebuild.\n")

    products = []
    for p in catalog.products.values():
        photos = photo_variants(p.photo) if p.photo else {}
        products.append({
            "id": p.id, "category": p.category, "emoji": p.emoji, "color": p.color,
            "photo": photos.get(1080), "thumb": photos.get(520),
            "name": p.name, "desc": p.description,
            "price": {lang: p.price_label(lang) for lang in ("uz", "ru")},
            "sizes": [{"id": z.id, "name": z.name, "price": z.price} for z in p.sizes],
            "fillings": [{"id": f.id, "name": f.name, "extra": f.extra} for f in p.fillings],
            "inscription": p.inscription, "photoRef": p.reference_photo, "featured": p.featured,
            "leadDays": p.lead_days,
        })
    s = catalog.shop
    data = {
        "shop": {"name": s.name, "tagline": s.tagline, "phone": s.phone, "pickup": s.pickup_address,
                 "fee": s.delivery_fee, "freeFrom": s.free_delivery_from, "slots": s.time_slots,
                 "card": s.card_number, "cardHolder": s.card_holder, "deposit": s.deposit_percent,
                 "prefix": s.order_prefix, "capacity": s.daily_capacity, "bookingDays": s.booking_days,
                 "reminder": s.reminder_time, "summary": s.summary_time,
                 "color": s.brand_color, "logo": photo_variants(s.logo)[520] if s.logo else None},
        "categories": [{"id": c.id, "emoji": c.emoji, "name": c.name} for c in catalog.categories],
        "products": products,
        "limits": {"inscription": 50, "address": 300},
    }
    (OUT / "catalog.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    for name in ("app.js", "app.css", "showcase.js"):
        shutil.copy2(STATIC / name, OUT / name)
    version = hashlib.sha256(b"".join((OUT / n).read_bytes() for n in ("app.js", "app.css", "showcase.js"))).hexdigest()[:12]
    html = (STATIC / "index.html").read_text(encoding="utf-8").replace("__V__", version)
    app_tag = f'<script src="app.js?v={version}"></script>'
    assert app_tag in html, "index.html changed: update build_showcase.py"
    html = html.replace(app_tag, f'<script src="showcase.js?v={version}"></script>\n{app_tag}')
    (OUT / "index.html").write_text(html, encoding="utf-8")
    (OUT / "_headers").write_text(HEADERS, encoding="utf-8")

    files = [f for f in OUT.rglob("*") if f.is_file()]
    size = sum(f.stat().st_size for f in files)
    print(f"Showcase built: {OUT}  ({len(files)} files, {size / 1024 / 1024:.1f} MB)")
    print("Upload it: open https://app.netlify.com/drop and drag this folder onto the page.")


if __name__ == "__main__":
    main()
