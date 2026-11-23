"""The Mini App's backend, running inside the bot process.

Serves the app (static/), the product photos (images/), and a small JSON API.
Every API call carries Telegram.WebApp.initData, which is checked with the
HMAC algorithm from https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
so only real Telegram users can order, and prices are always recalculated
here from catalog.yaml, never taken from the phone. /api/admin/* answers only
the owner (OWNER_ID)."""

from __future__ import annotations

import asyncio
import calendar
import hashlib
import hmac
import json
import logging
import time
import urllib.parse
import uuid
from datetime import date, timedelta
from pathlib import Path

from aiohttp import web
from telegram import Bot

from .. import flow, ops, promo, reviews, views
from .. import status as st
from ..services import Draft, Services

log = logging.getLogger(__name__)

STATIC = Path(__file__).parent / "static"
MAX_UPLOAD = 10 * 1024 * 1024
INIT_DATA_MAX_AGE = 24 * 3600
MAX_INSCRIPTION = flow.MAX_INSCRIPTION
MAX_ADDRESS = flow.MAX_ADDRESS
FOREVER = "public, max-age=31536000, immutable"  # safe: every URL changes when its content does
COMPRESSIBLE = ("application/json", "application/javascript", "text/css", "text/html")
IMAGE_WIDTHS = {520: 72, 1080: 78}  # width -> JPEG quality; 520 for cards, 1080 for big photos


def check_init_data(init_data: str, token: str, max_age: int = INIT_DATA_MAX_AGE) -> dict | None:
    """Return the Telegram user if initData is genuine and recent, else None."""
    if not init_data:
        return None
    fields = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    received = fields.pop("hash", "")
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not received or not hmac.compare_digest(expected, received):
        return None
    if not fields.get("auth_date", "").isdigit() or time.time() - int(fields["auth_date"]) > max_age:
        return None
    try:
        user = json.loads(fields.get("user", ""))
    except ValueError:
        return None
    return user if isinstance(user, dict) and isinstance(user.get("id"), int) else None


class ApiError(Exception):
    def __init__(self, code: str, status: int = 400):
        super().__init__(code)
        self.code, self.status = code, status


class MiniAppServer:
    def __init__(self, s: Services, bot: Bot):
        self.s, self.bot = s, bot
        self.health_token = f"shirin-miniapp {int(time.time())}"  # proves a public address really leads here
        self.photos = {p.photo.name: p.photo for p in s.catalog.products.values() if p.photo}
        if s.catalog.shop.logo:
            self.photos[s.catalog.shop.logo.name] = s.catalog.shop.logo
        self.thumbs = s.cfg.db_path.parent / "thumbs"
        self.runner: web.AppRunner | None = None

        app = web.Application(client_max_size=MAX_UPLOAD, middlewares=[self._errors, self._compress])
        r = app.router
        r.add_get("/", self.index)
        r.add_get("/health", lambda req: web.Response(text=self.health_token))
        r.add_get("/app.js", self.static)
        r.add_get("/app.css", self.static)
        r.add_get("/img/{name}", self.image)
        r.add_get("/f/{name}", self.tg_file)
        # customer
        r.add_post("/api/bootstrap", self.bootstrap)
        r.add_post("/api/lang", self.set_lang)
        r.add_post("/api/phone", self.phone)
        r.add_post("/api/orders", self.orders)
        r.add_post("/api/order", self.order)
        r.add_post("/api/receipt", self.receipt)
        r.add_post("/api/review", self.review)
        # owner
        r.add_post("/api/admin/overview", self.admin_overview)
        r.add_post("/api/admin/order", self.admin_order)
        r.add_post("/api/admin/action", self.admin_action)
        r.add_post("/api/admin/calendar", self.admin_calendar)
        r.add_post("/api/admin/day", self.admin_day)
        r.add_post("/api/admin/products", self.admin_products)
        r.add_post("/api/admin/product", self.admin_product)
        r.add_post("/api/admin/settings", self.admin_settings)
        r.add_post("/api/admin/gallery", self.admin_gallery)
        r.add_post("/api/admin/broadcast", self.admin_broadcast)
        r.add_post("/api/admin/broadcasts", self.admin_broadcasts)
        # browser preview (?demo=1): catalog only, orders are checked but never placed
        r.add_get("/api/demo", self.demo_bootstrap)
        r.add_post("/api/demo/order", self.demo_order)
        self.app = app

    async def start(self, port: int) -> None:
        self.runner = web.AppRunner(self.app, access_log=None)
        await self.runner.setup()
        await web.TCPSite(self.runner, "127.0.0.1", port).start()
        log.info("Mini App server on http://127.0.0.1:%d", port)

    async def stop(self) -> None:
        if self.runner:
            await self.runner.cleanup()

    async def warm_up(self) -> None:
        """Make the photo sizes ahead of time, so the first customer doesn't wait."""
        for name in self.photos:
            for width in IMAGE_WIDTHS:
                try:
                    await asyncio.to_thread(self._variant, name, width)
                except Exception as e:  # a broken photo file must not stop the bot
                    log.warning("Photo %s could not be resized: %s", name, e)

    # ---------------------------------------------------------------- plumbing

    @web.middleware
    async def _compress(self, request: web.Request, handler):
        """gzip the app code and the JSON: 3-5x fewer bytes through the tunnel."""
        resp = await handler(request)
        if (isinstance(resp, web.Response) and resp.body is not None and len(resp.body) > 1024
                and resp.content_type in COMPRESSIBLE):
            resp.enable_compression()
        return resp

    @web.middleware
    async def _errors(self, request: web.Request, handler):
        try:
            return await handler(request)
        except ApiError as e:
            return web.json_response({"error": e.code}, status=e.status)
        except ops.OpError as e:
            return web.json_response({"error": e.code}, status=409)
        except web.HTTPException:
            raise
        except Exception:
            log.exception("Mini App request %s failed", request.path)
            return web.json_response({"error": "server"}, status=500)

    def _user(self, init_data: str) -> dict:
        user = check_init_data(init_data, self.s.cfg.token)
        if not user:
            raise ApiError("auth", 401)
        self.s.db.touch_user(user["id"], user.get("first_name"), user.get("username"))
        return user

    async def _json_user(self, request: web.Request) -> tuple[dict, dict]:
        try:
            body = await request.json()
        except ValueError:
            raise ApiError("bad_json")
        return body, self._user(str(body.get("initData", "")))

    async def _owner(self, request: web.Request) -> dict:
        body, user = await self._json_user(request)
        if user["id"] != self.s.cfg.owner_id:
            raise ApiError("forbidden", 403)
        return body

    # ---------------------------------------------------------------- pages and files

    async def index(self, request: web.Request) -> web.Response:
        # app.js/app.css are cached by the phone forever under a name that changes with their content
        version = hashlib.sha256(b"".join((STATIC / f).read_bytes() for f in ("app.js", "app.css"))).hexdigest()[:12]
        html = (STATIC / "index.html").read_text(encoding="utf-8").replace("__V__", version)
        return web.Response(text=html, content_type="text/html", headers={"Cache-Control": "no-store"})

    async def static(self, request: web.Request) -> web.Response:
        name = request.path.lstrip("/")
        return web.Response(body=(STATIC / name).read_bytes(), charset="utf-8",
                            content_type="application/javascript" if name.endswith(".js") else "text/css",
                            headers={"Cache-Control": FOREVER})

    def _variant(self, name: str, width: int) -> Path:
        """A product photo resized to `width` px (cards need far fewer bytes than the original)."""
        src = self.photos[name]
        out = self.thumbs / f"{src.stem}-{width}-{int(src.stat().st_mtime)}.jpg"
        if not out.exists():
            from PIL import Image  # Pillow is in requirements.txt

            self.thumbs.mkdir(parents=True, exist_ok=True)
            with Image.open(src) as im:
                im = im.convert("RGB")
                if im.width > width:
                    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
                # unique temp name: the warm-up and a first visitor may resize the same photo at once
                tmp = out.with_name(f"{out.name}.{uuid.uuid4().hex}.tmp")
                im.save(tmp, "JPEG", quality=IMAGE_WIDTHS[width], optimize=True, progressive=True)
                tmp.replace(out)
        return out

    async def image(self, request: web.Request) -> web.FileResponse:
        name = request.match_info["name"]
        if name not in self.photos or not self.photos[name].is_file():
            raise web.HTTPNotFound()
        width = request.query.get("w", "")
        path = self.photos[name]
        if width.isdigit() and int(width) in IMAGE_WIDTHS:
            try:
                path = await asyncio.to_thread(self._variant, name, int(width))
            except Exception as e:
                log.warning("Photo %s could not be resized: %s", name, e)
        return web.FileResponse(path, headers={"Cache-Control": FOREVER})

    async def tg_file(self, request: web.Request) -> web.FileResponse:
        q = request.query
        path = await self.s.files.path(request.match_info["name"], q.get("s", ""), q.get("id", "")) if self.s.files else None
        if not path:
            raise web.HTTPNotFound()
        return web.FileResponse(path, headers={"Cache-Control": "private, max-age=31536000, immutable"})

    # ---------------------------------------------------------------- catalog

    def _catalog(self) -> dict:
        s, shop = self.s, self.s.catalog.shop
        sold_out = s.db.sold_out()
        ratings = s.db.product_ratings()
        products = []
        for p in s.catalog.products.values():
            days = s.date_status(p)
            products.append({
                "id": p.id, "category": p.category, "emoji": p.emoji, "color": p.color,
                "photo": self._img(p, 1080), "thumb": self._img(p, 520),
                "name": p.name, "desc": p.description,
                "price": {lang: p.price_label(lang) for lang in ("uz", "ru")},
                "sizes": [{"id": z.id, "name": z.name, "price": z.price} for z in p.sizes],
                "fillings": [{"id": f.id, "name": f.name, "extra": f.extra} for f in p.fillings],
                "inscription": p.inscription, "photoRef": p.reference_photo, "featured": p.featured,
                "soldOut": p.id in sold_out,
                "rating": {"avg": ratings[p.id][0], "n": ratings[p.id][1]} if p.id in ratings else None,
                "dates": [d.isoformat() for d, why in days if not why],
                "days": [{"d": d.isoformat(), "x": why} for d, why in days],
            })
        return {
            "shop": {"name": shop.name, "tagline": shop.tagline, "phone": shop.phone,
                     "pickup": shop.pickup_address, "fee": shop.delivery_fee,
                     "freeFrom": shop.free_delivery_from, "slots": shop.time_slots,
                     "card": shop.card_number, "cardHolder": shop.card_holder, "deposit": s.deposit_percent(),
                     "color": shop.brand_color,
                     "logo": f"img/{shop.logo.name}?w=520&v={int(shop.logo.stat().st_mtime)}" if shop.logo else None},
            "gallery": self._gallery(),
            "categories": [{"id": c.id, "emoji": c.emoji, "name": c.name} for c in s.catalog.categories],
            "products": products,
            "limits": {"inscription": MAX_INSCRIPTION, "address": MAX_ADDRESS},
        }

    async def bootstrap(self, request: web.Request) -> web.Response:
        _, user = await self._json_user(request)
        uid = user["id"]
        active = sum(1 for o in self.s.db.user_orders(uid, 20) if o["status"] in st.ACTIVE)
        return web.json_response({
            "lang": self.s.lang_of(user),
            "phone": self.s.db.get_phone(uid),
            "firstName": user.get("first_name", ""),
            "activeOrders": active,
            "isOwner": uid == self.s.cfg.owner_id,
            **self._catalog(),
        })

    async def set_lang(self, request: web.Request) -> web.Response:
        body, user = await self._json_user(request)
        lang = body.get("lang")
        if lang not in ("uz", "ru"):
            raise ApiError("lang")
        self.s.db.set_lang(user["id"], lang)
        return web.json_response({"ok": True})

    async def phone(self, request: web.Request) -> web.Response:
        """After requestContact the number reaches the bot as a chat message; the app fetches it here."""
        _, user = await self._json_user(request)
        return web.json_response({"phone": self.s.db.get_phone(user["id"])})

    # ---------------------------------------------------------------- customer orders

    def _gallery(self) -> list[dict]:
        """Finished cakes for "Our works": delivered orders with a photo the owner didn't hide."""
        out = []
        for o in self.s.db.gallery():
            out.append({"photo": self.s.files.url(o["ready_photo_id"]) if self.s.files else None,
                        "stars": o["rating"], "text": o["review"],
                        "name": (o["customer_name"] or "").split(" ")[0], "names": o["names"], "date": o["delivery_date"]})
        return [g for g in out if g["photo"]]

    def _img(self, p, width: int) -> str | None:
        return f"img/{p.photo.name}?w={width}&v={int(p.photo.stat().st_mtime)}" if p and p.photo else None

    async def _order_json(self, o: dict, admin: bool = False) -> dict:
        s = self.s
        product = s.product(o["product_id"])
        out = {
            "num": o["num"], "code": s.order_code(o["num"]), "status": o["status"], "history": o["history"],
            "steps": st.steps(o), "names": o["names"], "date": o["delivery_date"], "slot": o["time_slot"],
            "method": o["method"], "address": o["address"], "lat": o["lat"], "lon": o["lon"],
            "inscription": o["inscription"], "total": o["total"], "item": o["item_price"], "fee": o["delivery_fee"],
            "deposit": o["deposit"], "paid": o["paid"], "payment": o["payment_status"],
            "courier": o["courier"], "created": o["created_at"], "gift": o["gift"],
            "rating": o["rating"], "review": o["review"],
            "photo": self._img(product, 520),
            "readyPhoto": s.files.url(o["ready_photo_id"]) if s.files else None,
        }
        if admin:
            out.update({
                "customer": {"id": o["user_id"], "name": o["customer_name"], "username": o["username"], "lang": o["lang"]},
                "phone": o["phone"], "actions": st.next_actions(o),
                "mapUrl": views.map_link(o["lat"], o["lon"]) if o["lat"] is not None else None,
                "refPhoto": s.files.url(o["photo_file_id"]) if s.files and o["photo_kind"] == "photo" else None,
                "receipt": s.files.url(o["receipt_file_id"]) if s.files else None,
                "inGallery": bool(o["in_gallery"]),
            })
        return out

    async def orders(self, request: web.Request) -> web.Response:
        _, user = await self._json_user(request)
        out = [await self._order_json(o) for o in self.s.db.user_orders(user["id"], 10)]
        return web.json_response({"orders": out})

    async def order(self, request: web.Request) -> web.Response:
        form = await request.post()
        user = self._user(str(form.get("initData", "")))
        try:
            data = json.loads(str(form.get("order", "")))
        except ValueError:
            raise ApiError("bad_json")
        photo_bytes = _image(form.get("photo"))
        draft = self._draft(user, data, photo_bytes is not None)
        if draft.photo_kind != "photo":
            photo_bytes = None  # this product takes no reference photo
        order = await flow.place_order(self.s, self.bot, draft, user["id"], photo_upload=photo_bytes, from_app=True)
        return web.json_response({"code": self.s.order_code(order["num"]), "num": order["num"]})

    async def receipt(self, request: web.Request) -> web.Response:
        """Deposit receipt uploaded from 'My orders'."""
        form = await request.post()
        user = self._user(str(form.get("initData", "")))
        num = int(form.get("num", 0) or 0)
        o = self.s.db.get_order(num)
        if not o or o["user_id"] != user["id"]:
            raise ApiError("not_found", 404)
        if o["payment_status"] != "due":
            raise ApiError("stale", 409)
        photo = _image(form.get("photo"))
        if not photo:
            raise ApiError("photo_type")
        o = await ops.submit_receipt(self.s, self.bot, o, upload=photo)
        return web.json_response({"order": await self._order_json(o)})

    async def review(self, request: web.Request) -> web.Response:
        body, user = await self._json_user(request)
        value = body.get("stars")
        if not isinstance(value, int) or not 1 <= value <= 5:
            raise ApiError("stars")
        o = await reviews.save(self.s, self.bot, int(body.get("num") or 0), user["id"], value, str(body.get("text") or ""))
        if not o:
            raise ApiError("not_found", 404)
        return web.json_response({"order": await self._order_json(o)})

    def _draft(self, user: dict, o: dict, has_photo: bool) -> Draft:
        """Check every field against the catalog, exactly like the chat form does."""
        s = self.s
        p = s.product(str(o.get("product", "")))
        if not p:
            raise ApiError("product")
        if s.is_sold_out(p.id):
            raise ApiError("sold_out")
        size = p.size(o.get("size"))
        if not size:
            raise ApiError("size")
        filling = p.filling(o.get("filling")) if p.fillings else None
        if p.fillings and not filling:
            raise ApiError("filling")
        inscription = None
        if p.inscription:
            inscription = str(o.get("inscription") or "").strip()
            if len(inscription) > MAX_INSCRIPTION:
                raise ApiError("inscription")
        days = dict(s.date_status(p))
        try:
            wanted = date.fromisoformat(str(o.get("date")))
        except ValueError:
            raise ApiError("date")
        if wanted not in days:
            raise ApiError("date")
        if days[wanted]:
            raise ApiError("date_full")
        slot = o.get("slot")
        if not isinstance(slot, int) or not 0 <= slot < len(s.catalog.shop.time_slots):
            raise ApiError("slot")
        method = o.get("method")
        if method not in ("delivery", "pickup"):
            raise ApiError("method")
        address, lat, lon = None, None, None
        if method == "delivery":
            address = str(o.get("address") or "").strip() or None
            try:
                lat = float(o["lat"]) if o.get("lat") is not None else None
                lon = float(o["lon"]) if o.get("lon") is not None else None
            except (TypeError, ValueError):
                raise ApiError("location")
            if (lat is None) != (lon is None) or (lat is not None and not (-90 <= lat <= 90 and -180 <= lon <= 180)):
                raise ApiError("location")
            if address and len(address) > MAX_ADDRESS:
                raise ApiError("address")
            if not address and lat is None:
                raise ApiError("address")
        phone = flow.normalize_phone(str(o.get("phone") or ""))
        if not phone:
            raise ApiError("phone")
        gift = None
        if method == "delivery" and isinstance(o.get("gift"), dict):
            g = o["gift"]
            gift_phone = flow.normalize_phone(str(g.get("phone") or ""))
            name = str(g.get("name") or "").strip()[:60]
            if len(name) < 2 or not gift_phone:
                raise ApiError("gift")
            gift = {"name": name, "phone": gift_phone, "note": str(g.get("note") or "").strip()[:150],
                    "surprise": bool(g.get("surprise"))}

        cust_name = " ".join(x for x in (user.get("first_name"), user.get("last_name")) if x)
        return Draft(
            did="app", product_id=p.id, lang=s.lang_of(user), customer_name=cust_name, username=user.get("username"),
            size=size.id, filling=filling.id if filling else None, inscription=inscription,
            photo_kind=("photo" if has_photo else "skipped") if p.reference_photo else None,
            date=wanted.isoformat(), slot=slot, method=method, address=address, lat=lat, lon=lon, phone=phone,
            gift=gift,
        )

    # ---------------------------------------------------------------- owner dashboard

    async def admin_overview(self, request: web.Request) -> web.Response:
        body = await self._owner(request)
        today = self.s.now().date()
        rng = body.get("range", "today")
        first, last = {"today": (today, today), "tomorrow": (today + timedelta(1), today + timedelta(1)),
                       "week": (today, today + timedelta(6))}.get(rng, (today, today))
        orders = self.s.db.orders_between(first.isoformat(), last.isoformat())
        live = [o for o in orders if o["status"] != "rejected"]
        new = self.s.db.orders_with_status("new")
        unpaid = [o for o in self.s.db.orders_with_status(*st.ACTIVE) if o["payment_status"] in ("due", "review")]
        return web.json_response({
            "today": today.isoformat(),
            "stats": {"orders": len(live), "revenue": sum(o["total"] for o in live),
                      "paid": sum(o["paid"] for o in live), "unpaid": len(unpaid)},
            "pending": [await self._order_json(o, admin=True) for o in new],
            "review": [await self._order_json(o, admin=True) for o in unpaid if o["payment_status"] == "review"],
            "orders": [await self._order_json(o, admin=True) for o in orders],
        })

    async def admin_order(self, request: web.Request) -> web.Response:
        body = await self._owner(request)
        o = self.s.db.get_order(int(body.get("num", 0) or 0))
        if not o:
            raise ApiError("not_found", 404)
        return web.json_response({"order": await self._order_json(o, admin=True)})

    async def admin_action(self, request: web.Request) -> web.Response:
        """Stage changes and payment checks. 'rdy' may carry a photo (multipart)."""
        if request.content_type.startswith("multipart/"):
            form = await request.post()
            user = self._user(str(form.get("initData", "")))
            body = {k: form.get(k) for k in ("num", "action", "courier")}
            photo = _image(form.get("photo"))
        else:
            body, user = await self._json_user(request)
            photo = None
        if user["id"] != self.s.cfg.owner_id:
            raise ApiError("forbidden", 403)
        num, action = int(body.get("num") or 0), str(body.get("action") or "")
        if action in ("pok", "pno"):
            o = await ops.confirm_payment(self.s, self.bot, num, ok=action == "pok")
        elif action in st.ACTIONS:
            courier = str(body.get("courier") or "self") if action == "way" else None
            o = await ops.change_status(self.s, self.bot, num, action, photo=photo, courier=courier)
        else:
            raise ApiError("action")
        return web.json_response({"order": await self._order_json(o, admin=True)})

    async def admin_calendar(self, request: web.Request) -> web.Response:
        body = await self._owner(request)
        try:
            year, month = map(int, str(body.get("month")).split("-"))
            first = date(year, month, 1)
        except ValueError:
            first = self.s.now().date().replace(day=1)
        last = first.replace(day=calendar.monthrange(first.year, first.month)[1])
        booked = self.s.db.booked_per_day(first.isoformat(), last.isoformat())
        closed = self.s.db.closed_days()
        days = [{"d": (first + timedelta(i)).isoformat(), "n": booked.get((first + timedelta(i)).isoformat(), 0),
                 "closed": (first + timedelta(i)).isoformat() in closed} for i in range(last.day)]
        return web.json_response({"month": first.strftime("%Y-%m"), "capacity": self.s.capacity(),
                                  "today": self.s.now().date().isoformat(), "days": days})

    async def admin_day(self, request: web.Request) -> web.Response:
        body = await self._owner(request)
        try:
            day = date.fromisoformat(str(body.get("date")))
        except ValueError:
            raise ApiError("date")
        if "closed" in body:
            self.s.db.set_closed(day.isoformat(), bool(body["closed"]))
            log.info("Day %s %s by the owner", day, "closed" if body["closed"] else "opened")
        orders = self.s.db.orders_between(day.isoformat(), day.isoformat())
        return web.json_response({"date": day.isoformat(), "closed": day.isoformat() in self.s.db.closed_days(),
                                  "orders": [await self._order_json(o, admin=True) for o in orders]})

    async def admin_products(self, request: web.Request) -> web.Response:
        await self._owner(request)
        return web.json_response({"products": self._catalog()["products"]})

    async def admin_product(self, request: web.Request) -> web.Response:
        body = await self._owner(request)
        pid = str(body.get("id", ""))
        if not self.s.product(pid):
            raise ApiError("product")
        self.s.db.set_sold_out(pid, bool(body.get("soldOut")))
        log.info("Product %s marked %s", pid, "sold out" if body.get("soldOut") else "available")
        return web.json_response({"ok": True})

    async def admin_settings(self, request: web.Request) -> web.Response:
        body = await self._owner(request)
        for key, lo, hi in (("capacity", 0, 99), ("deposit", 0, 100)):
            if key in body:
                value = body[key]
                if not isinstance(value, int) or not lo <= value <= hi:
                    raise ApiError(key)
                if key == "deposit" and value and not self.s.catalog.shop.card_number:
                    raise ApiError("no_card")
                self.s.db.set_setting("daily_capacity" if key == "capacity" else "deposit_percent", str(value))
        shop = self.s.catalog.shop
        return web.json_response({"capacity": self.s.capacity(), "deposit": self.s.deposit_percent(),
                                  "card": shop.card_number, "cardHolder": shop.card_holder,
                                  "reminder": shop.reminder_time, "summary": shop.summary_time})

    async def admin_gallery(self, request: web.Request) -> web.Response:
        body = await self._owner(request)
        num = int(body.get("num") or 0)
        if not self.s.db.get_order(num):
            raise ApiError("not_found", 404)
        o = self.s.db.update_order(num, in_gallery=1 if body.get("show") else 0)
        return web.json_response({"order": await self._order_json(o, admin=True)})

    async def admin_broadcast(self, request: web.Request) -> web.Response:
        form = await request.post()
        user = self._user(str(form.get("initData", "")))
        if user["id"] != self.s.cfg.owner_id:
            raise ApiError("forbidden", 403)
        text = str(form.get("text") or "").strip()
        if not text or len(text) > promo.MAX_TEXT:
            raise ApiError("text")
        return web.json_response(promo.start(self.s, self.bot, text, _image(form.get("photo"))))

    async def admin_broadcasts(self, request: web.Request) -> web.Response:
        await self._owner(request)
        return web.json_response({"recipients": len(self.s.db.promo_recipients()), "items": self.s.db.broadcasts()})

    # ---------------------------------------------------------------- browser preview

    async def demo_bootstrap(self, request: web.Request) -> web.Response:
        lang = request.query.get("lang", "uz")
        return web.json_response({"lang": lang if lang in ("uz", "ru") else "uz", "phone": None, "firstName": "",
                                  "activeOrders": 0, "demo": True, "isOwner": False, **self._catalog()})

    async def demo_order(self, request: web.Request) -> web.Response:
        """Same checks as a real order, but nothing is stored or sent."""
        form = await request.post()
        try:
            data = json.loads(str(form.get("order", "")))
        except ValueError:
            raise ApiError("bad_json")
        self._draft({"id": 0, "first_name": "Demo"}, data, False)
        return web.json_response({"code": f"{self.s.catalog.shop.order_prefix}-DEMO", "demo": True})


def _image(field) -> bytes | None:
    """An uploaded image, or None. Anything that is not an image is refused."""
    if not isinstance(field, web.FileField):
        return None
    if not (field.content_type or "").startswith("image/"):
        raise ApiError("photo_type")
    return field.file.read()
