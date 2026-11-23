"""The order form. Widget customers and simple-menu customers both land
here after picking a product, so the whole form uses ordinary messages and
keyboards and works on every Telegram version.

One question per message. When a question is answered, its message is
edited to show the answer and lose its buttons, so the chat reads like a
filled-in form."""

from __future__ import annotations

import asyncio
import logging
import re
import secrets
from datetime import date

from telegram import (
    Bot,
    CallbackQuery,
    InlineKeyboardButton as IB,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError

from . import keyboards, views
from .catalog import Product
from .services import Draft, Services
from .texts import LANGS, all_langs, esc, fmt_date, fmt_date_short, fmt_phone, money, t

log = logging.getLogger(__name__)

STEPS = ["size", "filling", "inscription", "photo", "date", "slot", "method", "address", "phone", "summary"]
# callback action -> the step it answers
ACTION_STEP = {"sz": "size", "fl": "filling", "ins": "inscription", "ph": "photo",
               "dt": "date", "sl": "slot", "mt": "method", "ok": "summary"}
MAX_INSCRIPTION = 50
MAX_ADDRESS = 300
HTML = ParseMode.HTML


# ---------------------------------------------------------------- steps

def applies(step: str, p: Product, d: Draft) -> bool:
    if step == "size":
        return len(p.sizes) > 1
    if step == "filling":
        return bool(p.fillings)
    if step == "inscription":
        return p.inscription
    if step == "photo":
        return p.reference_photo
    if step == "address":
        return d.method != "pickup"
    return True


def next_step(p: Product, d: Draft, current: str | None) -> str:
    start = STEPS.index(current) + 1 if current else 0
    return next(s for s in STEPS[start:] if applies(s, p, d))


def prev_step(p: Product, d: Draft, current: str) -> str | None:
    return next((s for s in reversed(STEPS[:STEPS.index(current)]) if applies(s, p, d)), None)


def cb(d: Draft, action: str, value: str = "-") -> str:
    return f"f:{d.did}:{action}:{value}"


def nav_row(p: Product, d: Draft) -> list[IB]:
    row = []
    if prev_step(p, d, d.step):
        row.append(IB(t(d.lang, "btn_back"), callback_data=cb(d, "back")))
    row.append(IB(t(d.lang, "btn_cancel"), callback_data=cb(d, "x")))
    return row


def date_options(s: Services, p: Product) -> list[date]:
    """Bookable dates: inside the booking window, not a day off, not fully booked."""
    return s.available_dates(p)


def normalize_phone(raw: str, from_contact: bool = False) -> str | None:
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 9:
        digits = "998" + digits
    if len(digits) == 12 and digits.startswith("998"):
        return "+" + digits
    if (from_contact or raw.strip().startswith("+")) and 10 <= len(digits) <= 15:
        return "+" + digits  # a foreign number
    return None


# ---------------------------------------------------------------- order fields

def item_price(p: Product, d: Draft) -> int:
    filling = p.filling(d.filling)
    return p.size(d.size).price + (filling.extra if filling else 0)


def order_fields(s: Services, d: Draft, user_id: int) -> dict:
    """The draft as the same dict shape as a stored order."""
    p = s.product(d.product_id)
    size = p.size(d.size)
    filling = p.filling(d.filling)
    price = item_price(p, d)
    fee = s.delivery_fee(price) if d.method == "delivery" else 0
    return {
        "user_id": user_id,
        "lang": d.lang,
        "customer_name": d.customer_name,
        "username": d.username,
        "product_id": p.id,
        "size_id": size.id,
        "filling_id": filling.id if filling else None,
        "names": {
            lang: {
                "product": p.name[lang],
                "size": size.name[lang],
                "filling": filling.name[lang] if filling else None,
            }
            for lang in LANGS
        },
        "inscription": d.inscription if p.inscription else None,
        "photo_file_id": d.photo_id,
        "photo_kind": d.photo_kind,
        "delivery_date": d.date,
        "time_slot": s.catalog.shop.time_slots[d.slot],
        "method": d.method,
        "address": d.address if d.method == "delivery" else None,
        "lat": d.lat if d.method == "delivery" else None,
        "lon": d.lon if d.method == "delivery" else None,
        "phone": d.phone,
        "gift": d.gift if d.method == "delivery" else None,
        "item_price": price,
        "delivery_fee": fee,
        "total": price + fee,
    }


# ---------------------------------------------------------------- start

async def start_order(s: Services, bot: Bot, user_id: int, product: Product, name: str, username: str | None) -> None:
    lang = s.db.get_lang(user_id) or "uz"
    if s.is_sold_out(product.id):
        await bot.send_message(user_id, f"{product.emoji} {esc(product.name[lang])}: {t(lang, 'sold_out')}",
                               parse_mode=HTML)
        return
    old = s.drafts.pop(user_id, None)
    if old:
        await close_prompt(bot, user_id, old, None)

    d = Draft(did=secrets.token_hex(2), product_id=product.id, lang=lang, customer_name=name, username=username)
    if len(product.sizes) == 1:
        d.size = product.sizes[0].id
    s.drafts[user_id] = d

    # The product card with its real photo. It also carries the main menu
    # keyboard, which replaces a contact/location keyboard left from an
    # unfinished order.
    caption = t(lang, "product_caption", name=esc(product.name[lang]),
                desc=esc(product.description[lang]), price=esc(product.price_label(lang)))
    menu = keyboards.main_menu(lang)
    if product.photo:
        cached = s.photo_ids.get(product.photo)
        msg = await bot.send_photo(user_id, photo=cached or product.photo, caption=caption,
                                   parse_mode=HTML, reply_markup=menu)
        s.photo_ids[product.photo] = msg.photo[-1].file_id
    else:
        await bot.send_message(user_id, caption, parse_mode=HTML, reply_markup=menu)

    d.step = next_step(product, d, None)
    await prompt(s, bot, user_id, d)


# ---------------------------------------------------------------- asking

async def prompt(s: Services, bot: Bot, user_id: int, d: Draft) -> None:
    p = s.product(d.product_id)
    lang, step = d.lang, d.step
    markup: InlineKeyboardMarkup | ReplyKeyboardMarkup

    if step == "summary":
        fields = order_fields(s, d, user_id)
        text = "\n".join([t(lang, "summary_title"), "", *views.details(s, fields, lang), "", t(lang, "summary_note")])
        markup = InlineKeyboardMarkup([
            [IB(t(lang, "btn_confirm"), callback_data=cb(d, "ok"))],
            nav_row(p, d),
        ])
    else:
        visible = [x for x in STEPS[:-1] if applies(x, p, d)]
        head = t(lang, "step", i=visible.index(step) + 1, n=len(visible))
        rows: list[list[IB]] = []
        if step == "size":
            text = head + t(lang, "q_size")
            rows = [[IB(f"{sz.name[lang]} — {money(sz.price, lang)}", callback_data=cb(d, "sz", sz.id))] for sz in p.sizes]
        elif step == "filling":
            text = head + t(lang, "q_filling")
            rows = [[IB(f.name[lang] + (f" (+{money(f.extra, lang)})" if f.extra else ""),
                        callback_data=cb(d, "fl", f.id))] for f in p.fillings]
        elif step == "inscription":
            text = head + t(lang, "q_inscription", max=MAX_INSCRIPTION)
            rows = [[IB(t(lang, "btn_no_inscription"), callback_data=cb(d, "ins"))]]
        elif step == "photo":
            text = head + t(lang, "q_photo")
            rows = [[IB(t(lang, "btn_skip"), callback_data=cb(d, "ph"))]]
        elif step == "date":
            options = date_options(s, p)
            if not options:  # every day is booked or closed
                s.drafts.pop(user_id, None)
                await bot.send_message(user_id, t(lang, "no_dates", phone=esc(s.catalog.shop.phone)),
                                       reply_markup=keyboards.main_menu(lang))
                return
            text = head + t(lang, "q_date")
            days = [IB(fmt_date_short(x, lang), callback_data=cb(d, "dt", x.strftime("%Y%m%d"))) for x in options]
            rows = [days[i:i + 2] for i in range(0, len(days), 2)]
        elif step == "slot":
            text = head + t(lang, "q_slot")
            slots = [IB(x, callback_data=cb(d, "sl", str(i))) for i, x in enumerate(s.catalog.shop.time_slots)]
            rows = [slots[i:i + 2] for i in range(0, len(slots), 2)]
        elif step == "method":
            text = head + t(lang, "q_method")
            fee = s.delivery_fee(item_price(p, d))
            fee_label = t(lang, "free") if fee == 0 else "+" + money(fee, lang)
            rows = [[IB(t(lang, "btn_delivery", fee=fee_label), callback_data=cb(d, "mt", "d"))],
                    [IB(t(lang, "btn_pickup"), callback_data=cb(d, "mt", "p"))]]
        elif step in ("address", "phone"):
            special = (KeyboardButton(t(lang, "btn_location"), request_location=True) if step == "address"
                       else KeyboardButton(t(lang, "btn_contact"), request_contact=True))
            text = head + t(lang, "q_" + step)
            markup = ReplyKeyboardMarkup([[special], [t(lang, "btn_back"), t(lang, "btn_cancel")]],
                                         resize_keyboard=True)
        else:  # pragma: no cover - STEPS is closed
            raise ValueError(step)
        if step not in ("address", "phone"):
            markup = InlineKeyboardMarkup(rows + [nav_row(p, d)])

    msg = await bot.send_message(user_id, text, parse_mode=HTML, reply_markup=markup)
    d.prompt_id, d.prompt_text = msg.message_id, text
    d.reply_kb = isinstance(markup, ReplyKeyboardMarkup)


async def close_prompt(bot: Bot, user_id: int, d: Draft, answer: str | None) -> None:
    """Turn the current question into a record: show the answer, drop the buttons."""
    message_id, text = d.prompt_id, d.prompt_text
    if not message_id:
        return
    d.prompt_id = None  # before any await: the next question may be sent meanwhile
    text += f"\n✅ <i>{esc(answer)}</i>" if answer else ""
    try:
        await bot.edit_message_text(text, chat_id=user_id, message_id=message_id, parse_mode=HTML)
    except BadRequest:
        pass  # too old to edit, or unchanged


async def advance(s: Services, bot: Bot, user_id: int, d: Draft, answer: str | None) -> None:
    closing = close_prompt(bot, user_id, d, answer)
    d.step = next_step(s.product(d.product_id), d, d.step)
    # two Telegram calls at once instead of one after the other (~0.4 s saved per step)
    await asyncio.gather(closing, prompt(s, bot, user_id, d))


async def go_back(s: Services, bot: Bot, user_id: int, d: Draft) -> None:
    p = s.product(d.product_id)
    prev = prev_step(p, d, d.step)
    if not prev:
        return
    was_reply_kb = d.reply_kb
    await close_prompt(bot, user_id, d, None)
    d.step = prev
    if was_reply_kb and prev not in ("address", "phone"):
        # leaving a contact/location keyboard for an inline question: put the main menu back
        await bot.send_message(user_id, t(d.lang, "btn_back"), reply_markup=keyboards.main_menu(d.lang))
    await prompt(s, bot, user_id, d)


async def cancel(s: Services, bot: Bot, user_id: int, d: Draft) -> None:
    await close_prompt(bot, user_id, d, None)
    s.drafts.pop(user_id, None)
    await bot.send_message(user_id, t(d.lang, "cancelled"), reply_markup=keyboards.main_menu(d.lang))


# ---------------------------------------------------------------- answers: buttons

async def on_callback(s: Services, bot: Bot, q: CallbackQuery, did: str, action: str, value: str) -> None:
    user_id = q.from_user.id
    d = s.drafts.get(user_id)
    lang = d.lang if d else s.lang_of(q.from_user)
    p = s.product(d.product_id) if d else None
    if not d or d.did != did or not p:
        await q.answer(t(lang, "stale"))
        try:
            await q.edit_message_reply_markup(None)
        except TelegramError:
            pass
        return

    if action == "x":
        await q.answer()
        return await cancel(s, bot, user_id, d)
    if action == "back":
        await q.answer()
        return await go_back(s, bot, user_id, d)
    if ACTION_STEP.get(action) != d.step or q.message is None or q.message.message_id != d.prompt_id:
        await q.answer(t(lang, "stale"))
        return

    answer: str | None = None
    if action == "sz":
        size = p.size(value)
        if not size:
            return await q.answer(t(lang, "stale"))
        d.size, answer = size.id, size.name[lang]
    elif action == "fl":
        filling = p.filling(value)
        if not filling:
            return await q.answer(t(lang, "stale"))
        d.filling, answer = filling.id, filling.name[lang]
    elif action == "ins":
        d.inscription, answer = "", t(lang, "no_inscription")
    elif action == "ph":
        d.photo_id, d.photo_kind, answer = None, "skipped", t(lang, "photo_skipped")
    elif action == "dt":
        options = {x.strftime("%Y%m%d"): x for x in date_options(s, p)}
        if value not in options:
            return await q.answer(t(lang, "stale"))
        d.date, answer = options[value].isoformat(), fmt_date(options[value], lang)
    elif action == "sl":
        slots = s.catalog.shop.time_slots
        if not value.isdigit() or int(value) >= len(slots):
            return await q.answer(t(lang, "stale"))
        d.slot, answer = int(value), slots[int(value)]
    elif action == "mt":
        d.method = "delivery" if value == "d" else "pickup"
        if d.method == "pickup":
            d.address = d.lat = d.lon = None
        answer = t(lang, "f_delivery") if d.method == "delivery" else t(lang, "f_pickup")
    elif action == "ok":
        await q.answer()
        return await confirm(s, bot, user_id, d)

    await q.answer()
    await advance(s, bot, user_id, d, answer)


# ---------------------------------------------------------------- answers: messages

async def on_text(s: Services, bot: Bot, msg: Message, d: Draft) -> None:
    user_id, lang, text = msg.from_user.id, d.lang, (msg.text or "").strip()
    if text in all_langs("btn_cancel"):
        return await cancel(s, bot, user_id, d)
    if text in all_langs("btn_back"):
        return await go_back(s, bot, user_id, d)

    if d.step == "inscription":
        if len(text) > MAX_INSCRIPTION:
            return await msg.reply_text(t(lang, "too_long", max=MAX_INSCRIPTION))
        d.inscription = text
        return await advance(s, bot, user_id, d, f"«{text}»")
    if d.step == "address":
        if len(text) > MAX_ADDRESS:
            return await msg.reply_text(t(lang, "too_long", max=MAX_ADDRESS))
        d.address, d.lat, d.lon = text, None, None
        return await advance(s, bot, user_id, d, text)
    if d.step == "phone":
        phone = normalize_phone(text)
        if not phone:
            return await msg.reply_text(t(lang, "bad_phone"))
        return await got_phone(s, bot, user_id, d, phone)
    if d.step == "photo":
        return await msg.reply_text(t(lang, "send_photo_or_skip"))
    await msg.reply_text(t(lang, "use_buttons"))


async def on_contact(s: Services, bot: Bot, msg: Message, d: Draft) -> None:
    if d.step != "phone":
        return await msg.reply_text(t(d.lang, "use_buttons"))
    phone = normalize_phone(msg.contact.phone_number, from_contact=True)
    if not phone:
        return await msg.reply_text(t(d.lang, "bad_phone"))
    await got_phone(s, bot, msg.from_user.id, d, phone)


async def got_phone(s: Services, bot: Bot, user_id: int, d: Draft, phone: str) -> None:
    d.phone = phone
    await close_prompt(bot, user_id, d, fmt_phone(phone))
    # the contact keyboard goes away, the main menu comes back
    await bot.send_message(user_id, f"📞 {fmt_phone(phone)} ✅", reply_markup=keyboards.main_menu(d.lang))
    d.step = next_step(s.product(d.product_id), d, "phone")
    await prompt(s, bot, user_id, d)


async def on_location(s: Services, bot: Bot, msg: Message, d: Draft) -> None:
    if d.step != "address":
        return await msg.reply_text(t(d.lang, "use_buttons"))
    d.lat, d.lon, d.address = msg.location.latitude, msg.location.longitude, None
    await advance(s, bot, msg.from_user.id, d, t(d.lang, "location_label"))


async def on_photo(s: Services, bot: Bot, msg: Message, d: Draft) -> None:
    if d.step != "photo":
        return await msg.reply_text(t(d.lang, "use_buttons"))
    if msg.photo:
        d.photo_id, d.photo_kind = msg.photo[-1].file_id, "photo"
    else:
        d.photo_id, d.photo_kind = msg.document.file_id, "document"
    await advance(s, bot, msg.from_user.id, d, t(d.lang, "photo_attached"))


# ---------------------------------------------------------------- confirm

async def confirm(s: Services, bot: Bot, user_id: int, d: Draft) -> None:
    p = s.product(d.product_id)
    if date.fromisoformat(d.date) not in date_options(s, p):  # the day filled up meanwhile
        await close_prompt(bot, user_id, d, None)
        await bot.send_message(user_id, t(d.lang, "date_taken"))
        d.step = "date"
        return await prompt(s, bot, user_id, d)
    s.drafts.pop(user_id, None)
    await close_prompt(bot, user_id, d, t(d.lang, "confirmed_mark"))
    await place_order(s, bot, d, user_id)


async def place_order(s: Services, bot: Bot, d: Draft, user_id: int,
                      photo_upload: bytes | None = None, from_app: bool = False) -> dict:
    """Store a finished order, confirm it to the customer and send it to the owner.
    Used by the chat form and by the Mini App."""
    from . import owner  # local import: owner imports flow helpers too

    now = s.now()
    fields = order_fields(s, d, user_id)
    fields.update(status="new", history={"new": now.strftime("%H:%M")},
                  created_at=now.strftime("%Y-%m-%d %H:%M:%S"), updated_at=now.strftime("%Y-%m-%d %H:%M:%S"))
    order = s.db.create_order(fields)
    s.db.set_phone(user_id, d.phone)
    log.info("Order %s placed by %s%s", s.order_code(order["num"]), user_id, " (Mini App)" if from_app else "")

    if from_app:  # the app shows "done" right away; the chat messages follow in a moment
        s.spawn(send_confirmation(s, bot, order, with_details=True), key=order["num"])
    else:
        await send_confirmation(s, bot, order)
    s.spawn(owner.notify_new_order(s, bot, order, photo_upload), key=order["num"])
    return order


async def send_confirmation(s: Services, bot: Bot, order: dict, with_details: bool = False) -> None:
    """Confirmation with the order number. Customers whose app has shown a
    widget get it as a live status widget (the caption carries the text);
    everyone else gets a plain message. Mini App orders also get the details,
    because the chat has no summary of them yet."""
    lang, user_id = order["lang"], order["user_id"]
    text = t(lang, "confirmed", num=s.order_code(order["num"]))
    if with_details:
        text += "\n\n" + "\n".join(views.details(s, order, lang))
    html = s.widgets.status_html.get(lang)
    if s.widgets.enabled and html and s.db.widget_ok(user_id):
        try:
            msg = await s.widgets.send(bot, user_id, html, caption=text, chat_data=views.status_data(s, order))
            s.db.update_order(order["num"], cust_widget_msg_id=msg["message_id"])
            return
        except TelegramError as e:
            log.warning("Status widget not sent (%s), sending plain confirmation", e)
    await bot.send_message(user_id, text, parse_mode=HTML, reply_markup=keyboards.main_menu(lang))
