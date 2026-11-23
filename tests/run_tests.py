"""End-to-end tests: the real bot + Mini App server against a fake Telegram that answers
every call 0.3 s late (like a real connection from Tashkent).

    .venv/bin/python tests/run_tests.py

Nothing is sent to the real Telegram; your .env is not used."""

from __future__ import annotations

import asyncio
import gzip
import hashlib
import hmac
import io
import json
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))

import httpx  # noqa: E402
from PIL import Image  # noqa: E402
from telegram.ext import Application  # noqa: E402

from bot import handlers  # noqa: E402
from bot.catalog import load_catalog  # noqa: E402
from bot.config import Config  # noqa: E402
from bot.db import DB  # noqa: E402
from bot.services import Services  # noqa: E402
from bot.widgets import Widgets  # noqa: E402
from fake_telegram import FakeTelegram  # noqa: E402

TOKEN, OWNER, CUST = "123:TEST", 999, 555
TG_PORT, APP_PORT = 18901, 18902
LATENCY = 0.3
BASE = f"http://127.0.0.1:{APP_PORT}/"
fake = FakeTelegram(TG_PORT, latency=LATENCY)
passed: list[str] = []


def ok(label: str) -> None:
    passed.append(label)
    print("  ✓", label)


def init_data(user: dict) -> str:
    fields = {"auth_date": str(int(time.time())), "query_id": "AAH", "user": json.dumps(user, separators=(",", ":"))}
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(fields)


CUSTOMER = init_data({"id": CUST, "first_name": "Dilnoza", "username": "dilnoza", "language_code": "uz"})
OWNER_INIT = init_data({"id": OWNER, "first_name": "Owner"})


def jpeg(size=(800, 600)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (240, 120, 160)).save(buf, "JPEG")
    return buf.getvalue()


def chat_msg(uid: int, **content) -> dict:
    m = {"message_id": int(time.time() * 1000) % 10**9, "date": int(time.time()),
         "chat": {"id": uid, "type": "private"}, "from": {"id": uid, "is_bot": False, "first_name": "U"}, **content}
    if content.get("text", "").startswith("/"):
        m["entities"] = [{"type": "bot_command", "offset": 0, "length": len(content["text"].split()[0])}]
    return {"message": m}


def callback(uid: int, data: str, message_id: int = 1) -> dict:
    msg = fake.messages.get(message_id) or {"message_id": message_id, "date": int(time.time()),
                                           "chat": {"id": uid, "type": "private"}, "text": "x"}
    return {"callback_query": {"id": f"cq{time.time()}", "chat_instance": "c", "data": data, "message": msg,
                               "from": {"id": uid, "is_bot": False, "first_name": "U"}}}


async def wait(method, since, pred=lambda p: True, timeout=8.0):
    return await asyncio.to_thread(fake.wait, method, since, pred, timeout)


async def main() -> None:
    tmp = Path(tempfile.mkdtemp())
    cfg = Config(token=TOKEN, owner_id=OWNER, owner_lang="uz", widgets_enabled=False,
                 catalog_path=ROOT / "catalog.yaml", db_path=tmp / "test.db",
                 api_base_url=f"http://127.0.0.1:{TG_PORT}/bot", webapp_port=APP_PORT, webapp_url=None, tunnel=False)
    catalog = load_catalog(cfg.catalog_path)
    s = Services(cfg=cfg, catalog=catalog, db=DB(cfg.db_path), widgets=Widgets(catalog, False))
    app = (Application.builder().token(TOKEN).base_url(cfg.api_base_url)
           .base_file_url(f"http://127.0.0.1:{TG_PORT}/file/bot").build())
    app.bot_data["svc"] = s
    handlers.register(app)
    await app.initialize()
    await handlers.post_init(app)
    await app.start()
    await app.updater.start_polling(allowed_updates=handlers.ALLOWED_UPDATES, poll_interval=0.0, timeout=1)
    web = httpx.AsyncClient(base_url=BASE, timeout=15)
    try:
        await test_assets(web)
        num = await test_app_order(s, web)
        await test_owner_actions(s, web, num)
        await test_reviews_gallery(s, web, num)
        await test_promotions(s, web)
        await test_chat_flow(s)
    finally:
        await web.aclose()
        await app.updater.stop()
        await app.stop()
        await handlers.post_stop(app)
        await app.shutdown()
        fake.stop()
    print(f"\nALL {len(passed)} CHECKS PASSED")


async def test_assets(web: httpx.AsyncClient) -> None:
    print("\nLoading speed (bytes through the tunnel)")
    page = await web.get("/")
    assert page.headers["cache-control"] == "no-store" and "app.js?v=" in page.text
    raw = (ROOT / "bot/webapp/static/app.js").stat().st_size
    js = await web.get("/app.js", headers={"Accept-Encoding": "gzip"})
    sent = int(js.headers.get("content-length") or len(gzip.compress(js.content)))
    assert js.headers.get("content-encoding") == "gzip" and "immutable" in js.headers["cache-control"]
    assert sent < raw * 0.35, (sent, raw)
    ok(f"app.js sent gzipped: {sent // 1024} KB instead of {raw // 1024} KB, cached by the phone for good")
    original = (ROOT / "images/medovik.jpg").stat().st_size
    small = await web.get("/img/medovik.jpg?w=520")
    big = await web.get("/img/medovik.jpg?w=1080")
    assert Image.open(io.BytesIO(small.content)).width == 520 and Image.open(io.BytesIO(big.content)).width == 1080
    assert len(small.content) < original / 3 and "immutable" in small.headers["cache-control"]
    ok(f"catalog card photo {len(small.content) // 1024} KB (original {original // 1024} KB); "
       f"product page photo {len(big.content) // 1024} KB")
    boot = await web.post("/api/bootstrap", json={"initData": CUSTOMER}, headers={"Accept-Encoding": "gzip"})
    assert boot.headers.get("content-encoding") == "gzip"
    p = boot.json()["products"][0]
    assert "w=520" in p["thumb"] and "w=1080" in p["photo"]
    ok("catalog data gzipped; cards use the small photo, product pages the big one")


async def test_app_order(s: Services, web: httpx.AsyncClient) -> int:
    print("\nMini App order with a slow Telegram")
    boot = (await web.post("/api/bootstrap", json={"initData": CUSTOMER})).json()
    rv = next(p for p in boot["products"] if p["id"] == "red_velvet")
    order = {"product": "red_velvet", "size": "w2", "filling": "mango", "inscription": "Tabriklaymiz!",
             "date": rv["dates"][0], "slot": 1, "method": "delivery", "address": "Chilonzor 9, 12-uy",
             "lat": None, "lon": None, "phone": "+998901234567",
             "gift": {"name": "Madina", "phone": "90 765 43 21", "note": "Tug'ilgan kuning bilan!", "surprise": True}}
    since = len(fake.calls)
    t0 = time.perf_counter()
    r = await web.post("/api/order", data={"initData": CUSTOMER, "order": json.dumps(order)},
                       files={"photo": ("ref.jpg", jpeg(), "image/jpeg")})
    took = time.perf_counter() - t0
    assert r.status_code == 200, r.text
    assert took < LATENCY, took
    ok(f"the app shows 'order placed' after {took * 1000:.0f} ms (each Telegram call takes {LATENCY * 1000:.0f} ms)")
    conf = await wait("sendMessage", since, lambda p: p["chat_id"] == str(CUST))
    card = await wait("sendPhoto", since, lambda p: p["chat_id"] == str(OWNER))
    assert r.json()["code"] in conf["text"] and "Qizil baxmal" in card["caption"] and card["photo"].startswith("<upload")
    ok("then the customer's confirmation and the owner's card with the photo arrive in the background")
    assert "🎁" in card["caption"] and "Madina" in card["caption"] and "syurpriz" in card["caption"] and "Tug'ilgan" in card["caption"]
    ok("gift order: the owner's card shows recipient, phone, card text and 'surprise'")
    return r.json()["num"]


async def test_owner_actions(s: Services, web: httpx.AsyncClient, num: int) -> None:
    print("\nOwner taps quickly; customer messages stay in order")
    await asyncio.sleep(1.5)  # owner card stored
    since = len(fake.calls)
    times = []
    for action in ("acc", "bak"):
        t0 = time.perf_counter()
        r = await web.post("/api/admin/action", json={"initData": OWNER_INIT, "num": num, "action": action})
        times.append(time.perf_counter() - t0)
        assert r.status_code == 200, r.text
    t0 = time.perf_counter()
    r = await web.post("/api/admin/action", data={"initData": OWNER_INIT, "num": str(num), "action": "rdy"},
                       files={"photo": ("cake.jpg", jpeg(), "image/jpeg")})
    times.append(time.perf_counter() - t0)
    assert r.json()["order"]["status"] == "ready" and max(times) < LATENCY, times
    ok(f"accept → baking → ready (with photo) answered in {', '.join(f'{x * 1000:.0f}' for x in times)} ms")
    acc = await wait("sendMessage", since, lambda p: p["chat_id"] == str(CUST) and "qabul qilindi" in p["text"])
    bak = await wait("sendMessage", since, lambda p: p["chat_id"] == str(CUST) and "pishirishni" in p["text"])
    rdy = await wait("sendPhoto", since, lambda p: p["chat_id"] == str(CUST) and "tayyor" in p["caption"])
    seq = [p for _, p in fake.calls[since:]]
    assert seq.index(acc) < seq.index(bak) < seq.index(rdy)
    ok("the customer got 'accepted (pay 50%)', 'baking', then the cake photo, in that order")

    since = len(fake.calls)
    t0 = time.perf_counter()
    r = await web.post("/api/receipt", data={"initData": CUSTOMER, "num": str(num)},
                       files={"photo": ("r.jpg", jpeg(), "image/jpeg")})
    took = time.perf_counter() - t0
    assert r.status_code == 200 and r.json()["order"]["payment"] == "review" and took < LATENCY, (r.text, took)
    await wait("sendPhoto", since, lambda p: p["chat_id"] == str(OWNER) and "cheki" in p["caption"])
    ok(f"receipt upload answered in {took * 1000:.0f} ms; the owner receives it right after")
    await asyncio.sleep(0.8)
    detail = (await web.post("/api/admin/order", json={"initData": OWNER_INIT, "num": num})).json()["order"]
    t0 = time.perf_counter()
    for key in ("receipt", "readyPhoto", "refPhoto"):
        img = await web.get("/" + detail[key])
        assert img.status_code == 200 and img.content.startswith(b"\xff\xd8"), key
    forged = detail["receipt"].replace("s=", "s=0")
    assert (await web.get("/" + forged)).status_code == 404
    ok(f"receipt, cake and reference photos load on demand ({(time.perf_counter() - t0) * 1000:.0f} ms); forged links refused")


async def test_reviews_gallery(s: Services, web: httpx.AsyncClient, num: int) -> None:
    print("\nDelivery, rating, gallery")
    since = len(fake.calls)
    for action in ("way", "dlv"):
        r = await web.post("/api/admin/action", json={"initData": OWNER_INIT, "num": num, "action": action, "courier": "Jasur"})
        assert r.status_code == 200, r.text
    done = await wait("sendMessage", since, lambda p: p["chat_id"] == str(CUST) and "topshirildi" in p["text"])
    assert f"rate:{num}:5" in done["reply_markup"]
    ok("'delivered' message asks for 1-5 stars")
    since = len(fake.calls)
    fake.push(callback(CUST, f"rate:{num}:5", fake.next_msg))
    await wait("sendMessage", since, lambda p: p["chat_id"] == str(CUST) and "⭐⭐⭐⭐⭐" in p["text"])
    since = len(fake.calls)
    fake.push(chat_msg(CUST, text="Juda mazali edi, rahmat!"))
    note = await wait("sendMessage", since, lambda p: p["chat_id"] == str(OWNER) and "⭐⭐⭐⭐⭐" in p["text"])
    assert "Juda mazali" in note["text"]
    ok("customer taps 5 ⭐ and writes a comment; the owner gets the review")
    boot = (await web.post("/api/bootstrap", json={"initData": CUSTOMER})).json()
    g = boot["gallery"]
    rv = next(p for p in boot["products"] if p["id"] == "red_velvet")
    assert len(g) == 1 and g[0]["stars"] == 5 and g[0]["text"].startswith("Juda") and g[0]["photo"].startswith("f/")
    assert rv["rating"] == {"avg": 5.0, "n": 1}
    assert boot["shop"]["color"] == "#ff2d55"
    ok("the review is stored (gallery data ready); the cake shows ★ 5.0; brand color served")
    await web.post("/api/admin/gallery", json={"initData": OWNER_INIT, "num": num, "show": False})
    assert (await web.post("/api/bootstrap", json={"initData": CUSTOMER})).json()["gallery"] == []
    ok("the owner can hide it from the gallery")


async def test_promotions(s: Services, web: httpx.AsyncClient) -> None:
    print("\nPromotions")
    info = (await web.post("/api/admin/broadcasts", json={"initData": OWNER_INIT})).json()
    since = len(fake.calls)
    r = await web.post("/api/admin/broadcast", data={"initData": OWNER_INIT, "text": "🎄 Yangi yil setlari: 10% chegirma!"},
                       files={"photo": ("promo.jpg", jpeg(), "image/jpeg")})
    assert r.status_code == 200 and r.json()["recipients"] == info["recipients"] >= 2, r.text
    sent = [await wait("sendPhoto", since, lambda p, u=u: p["chat_id"] == str(u) and "chegirma" in p.get("caption", ""))
            for u in s.db.promo_recipients()]
    assert all("promo:off" in p["reply_markup"] for p in sent)
    assert sent[0]["photo"].startswith("<upload") and not sent[-1]["photo"].startswith("<upload")
    ok(f"promotion with photo sent to all {len(sent)} customers (photo uploaded once, then reused)")
    fake.push(callback(CUST, "promo:off"))
    for _ in range(40):
        if CUST not in s.db.promo_recipients():
            break
        await asyncio.sleep(0.1)
    assert CUST not in s.db.promo_recipients()
    ok("'unsubscribe' removes the customer from future promotions")


async def test_chat_flow(s: Services) -> None:
    print("\nChat order form")
    uid = 777
    s.db.set_lang(uid, "uz")
    since = len(fake.calls)
    fake.push(callback(uid, "prod:bento_classic"))
    prompt = await wait("sendMessage", since, lambda p: p["chat_id"] == str(uid) and "Hajmini" in p["text"])
    did = json.loads(prompt["reply_markup"])["inline_keyboard"][0][0]["callback_data"].split(":")[1]
    since = len(fake.calls)
    t0 = time.perf_counter()
    fake.push(callback(uid, f"f:{did}:sz:s10", fake.next_msg))
    await wait("sendMessage", since, lambda p: p["chat_id"] == str(uid) and "Nachinka" in p["text"])
    took = time.perf_counter() - t0
    edit = await wait("editMessageText", since, lambda p: "10 sm" in p["text"])
    assert "✅" in edit["text"] and took < LATENCY * 2.7, took
    ok(f"a form step takes {took:.2f} s with 3 Telegram calls of {LATENCY} s (answering and asking run together)")


if __name__ == "__main__":
    asyncio.run(main())
