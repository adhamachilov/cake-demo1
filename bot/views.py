"""How an order is shown: the customer's summary, the owner's card and the
status widget's data all come from the same order fields."""

from __future__ import annotations

import re
from datetime import date

from .services import Services
from .texts import esc, fmt_date, fmt_phone, money, stars, t
from .widgets import fit_data

LINE = "━━━━━━━━━━━━━━"


def map_link(lat: float, lon: float) -> str:
    return f"https://yandex.uz/maps/?pt={lon:.6f},{lat:.6f}&z=17&l=map"


def details(s: Services, o: dict, lang: str, for_owner: bool = False) -> list[str]:
    """Order lines in `lang`. `o` is an order row, or the same fields built from a draft."""
    names = o["names"][lang]
    out = [f"🎂 <b>{esc(names['product'])}</b> · {esc(names['size'])}"]
    if names.get("filling"):
        out.append(f"🍓 {t(lang, 'f_filling')}: {esc(names['filling'])}")
    if o["inscription"] is not None:
        text = f"«{esc(o['inscription'])}»" if o["inscription"] else t(lang, "no_inscription")
        out.append(f"✍️ {t(lang, 'f_inscription')}: {text}")
    if o["photo_file_id"] or o["photo_kind"] in ("photo", "document"):
        out.append(f"📷 {t(lang, 'f_photo')}: {t(lang, 'photo_attached_owner' if for_owner else 'photo_attached')}")
    elif o["photo_kind"] == "skipped":
        out.append(f"📷 {t(lang, 'f_photo')}: {t(lang, 'photo_skipped')}")
    when = fmt_date(date.fromisoformat(o["delivery_date"]), lang)
    out.append(f"📅 {t(lang, 'f_when')}: {when}, {esc(o['time_slot'])}")
    if o["method"] == "delivery":
        where = esc(o["address"]) if o["address"] else ""
        if o["lat"] is not None:
            link = f'<a href="{esc(map_link(o["lat"], o["lon"]))}">{t(lang, "location_label")}</a>'
            where = f"{where}\n{link}" if where else link
        out.append(f"🚚 {t(lang, 'f_delivery')}: {where}")
    else:
        out.append(f"🏠 {t(lang, 'f_pickup')}: {esc(s.catalog.shop.pickup_address[lang])}")
    if o.get("gift"):
        g = o["gift"]
        line = f"🎁 {t(lang, 'f_gift')}: {esc(g['name'])}, {esc(fmt_phone(g['phone']))}"
        if g.get("surprise"):
            line += f" · {t(lang, 'gift_surprise')}"
        out.append(line)
        if g.get("note"):
            out.append(f"💌 {t(lang, 'f_gift_note')}: «{esc(g['note'])}»")
    out.append(f"📞 {t(lang, 'f_phone')}: {esc(fmt_phone(o['phone']))}")
    out.append("")
    if o["method"] == "delivery":
        fee = money(o["delivery_fee"], lang) if o["delivery_fee"] else t(lang, "free")
        out.append(f"{t(lang, 'f_items')}: {money(o['item_price'], lang)}")
        out.append(f"{t(lang, 'f_fee')}: {fee}")
    out.append(f"💰 <b>{t(lang, 'f_total')}: {money(o['total'], lang)}</b>")
    return out


def owner_card(s: Services, o: dict) -> str:
    lang = s.cfg.owner_lang
    code = s.order_code(o["num"])
    lines = []
    if o["user_id"] == s.cfg.owner_id:
        lines.append(f"<i>{t(lang, 'o_tag')}</i>")
    lines.append(t(lang, "o_new" if o["status"] == "new" else "o_order", num=code))
    lines.append(f"{t(lang, 'o_status')}: <b>{t(lang, 'st_' + o['status'])}</b>")
    lines.append(f"💳 {t(lang, 'f_payment')}: {payment_line(o, lang)}")
    if o["courier"]:
        lines.append(f"🚚 {t(lang, 'f_courier')}: {esc(courier_label(o, lang))}")
    if o.get("rating"):
        lines.append(f"{stars(o['rating'])}" + (f" «{esc(o['review'])}»" if o.get("review") else ""))
    lines.append(LINE)
    lines += details(s, o, lang, for_owner=True)
    lines.append(LINE)
    who = f'<a href="tg://user?id={o["user_id"]}">{esc(o["customer_name"] or str(o["user_id"]))}</a>'
    if o["username"]:
        who += f" (@{esc(o['username'])})"
    lines.append(f"👤 {t(lang, 'f_customer')}: {who}")
    language = "O'zbekcha" if o["lang"] == "uz" else "Русский"
    lines.append(f"🌐 {t(lang, 'f_lang')}: {language}")
    created = o["created_at"]
    lines.append(f"🕐 {t(lang, 'o_created')}: {fmt_date(date.fromisoformat(created[:10]), lang, weekday=False)}, {created[11:16]}")
    return "\n".join(lines)


def payment_line(o: dict, lang: str) -> str:
    rest = o["total"] - o["paid"]
    if o["payment_status"] == "due":
        return t(lang, "pay_due", amount=money(o["deposit"], lang))
    if o["payment_status"] == "review":
        return t(lang, "pay_review")
    if o["payment_status"] == "paid":
        return t(lang, "pay_full") if rest <= 0 else t(lang, "pay_paid", paid=money(o["paid"], lang), rest=money(rest, lang))
    return t(lang, "pay_none")


def courier_label(o: dict, lang: str) -> str:
    return t(lang, "courier_self") if o["courier"] == "self" else (o["courier"] or "")


def visible_length(html_text: str) -> int:
    """Length Telegram counts for captions (after entity parsing)."""
    plain = re.sub(r"<[^>]+>", "", html_text)
    plain = plain.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#x27;", "'").replace("&amp;", "&")
    return len(plain)


def status_data(s: Services, o: dict) -> str:
    """chat_data for the customer's live status widget (max 1024 bytes)."""
    lang = o["lang"]
    names = o["names"][lang]
    d = date.fromisoformat(o["delivery_date"])
    data = {
        "n": s.order_code(o["num"]),
        # the widget knows the original 4 stages
        "s": {"baking": "accepted", "decorating": "accepted", "on_way": "ready"}.get(o["status"], o["status"]),
        "m": "p" if o["method"] == "pickup" else "d",
        "i": f"{names['product']} · {names['size']}",
        "w": f"{d.day:02d}.{d.month:02d} · {o['time_slot']}",
        "p": money(o["total"], lang),
        "t": o["history"],
    }
    return fit_data(data, "i")


def order_line(s: Services, o: dict, lang: str, due: bool = False) -> str:
    names = o["names"][lang]
    when = o["time_slot"] if due else o["created_at"][11:16]
    how = ("🚚" if o["method"] == "delivery" else "🏠") + " " if due else ""
    return (
        f"• <b>#{s.order_code(o['num'])}</b> {esc(when)} · {how}{esc(names['product'])} ({esc(names['size'])}) · "
        f"{money(o['total'], lang)} · {t(lang, 'st_' + o['status'])}  /o{o['num']}"
    )
