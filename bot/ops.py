"""Order operations shared by the owner's chat buttons and the dashboard Mini App:
stage changes, customer notifications, deposit receipts and payment checks."""

from __future__ import annotations

import logging
from datetime import date

from telegram import Bot, CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions, ReplyParameters
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError

from . import status as st
from . import views
from .services import Services
from .texts import esc, fmt_date, money, t

log = logging.getLogger(__name__)
HTML = ParseMode.HTML
NO_PREVIEW = LinkPreviewOptions(is_disabled=True)


class OpError(Exception):
    """Refused operation; `code` is shown by the dashboard and the chat."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


async def change_status(s: Services, bot: Bot, num: int, action: str, *,
                        photo: str | bytes | None = None, courier: str | None = None) -> dict:
    """Move an order to its next stage, tell the customer, refresh the owner's card."""
    o = s.db.get_order(num)
    if not o:
        raise OpError("not_found")
    if not st.allowed(o, action):
        raise OpError("stale")
    new = st.ACTIONS[action][0]
    now = s.now()
    fields = {"status": new, "history": {**o["history"], new: now.strftime("%H:%M")},
              "updated_at": now.strftime("%Y-%m-%d %H:%M:%S")}
    if action == "acc":
        deposit = s.deposit_for(o["total"])
        fields.update(deposit=deposit, payment_status="due" if deposit else "none")
    if action == "way":
        fields["courier"] = (courier or "self").strip()[:120]
        if fields["courier"] != "self":
            s.db.set_setting("last_courier", fields["courier"])
    o = s.db.update_order(num, **fields)
    log.info("Order %s -> %s", s.order_code(num), new)
    s.spawn(_after_status(s, bot, o, photo), key=num)  # the buttons answer at once
    return o


async def _after_status(s: Services, bot: Bot, o: dict, photo) -> None:
    sent = await notify_customer(s, bot, o, photo=photo)
    if photo is not None and sent is not None and sent.photo:
        s.db.update_order(o["num"], ready_photo_id=sent.photo[-1].file_id)
    if sent is None:
        await _owner_note(s, bot, t(s.cfg.owner_lang, "o_notify_failed", phone=esc(o["phone"])))
    latest = s.db.get_order(o["num"])
    await refresh_owner_card(s, bot, latest)
    await _update_widget(s, bot, latest)


async def confirm_payment(s: Services, bot: Bot, num: int, ok: bool) -> dict:
    """Owner checked the receipt (or got the money another way)."""
    o = s.db.get_order(num)
    if not o:
        raise OpError("not_found")
    if o["payment_status"] not in ("due", "review"):
        raise OpError("stale")
    lang = o["lang"]
    if ok:
        amount = o["deposit"] or o["total"]
        o = s.db.update_order(num, payment_status="paid", paid=amount)
        text = t(lang, "n_paid", num=s.order_code(num), amount=money(amount, lang))
        rest = o["total"] - o["paid"]
        if rest > 0:
            text += t(lang, "n_rest", rest=money(rest, lang))
    else:
        o = s.db.update_order(num, payment_status="due", receipt_file_id=None)
        text = t(lang, "n_pay_rejected", num=s.order_code(num), phone=esc(s.catalog.shop.phone))
    log.info("Order %s payment %s", s.order_code(num), "confirmed" if ok else "not found")

    async def tell() -> None:
        await _send(bot, o["user_id"], text)
        await refresh_owner_card(s, bot, s.db.get_order(num))

    s.spawn(tell(), key=num)
    return o


async def submit_receipt(s: Services, bot: Bot, o: dict, *, file_id: str | None = None,
                         kind: str = "photo", upload: bytes | None = None) -> dict:
    """Customer's transfer screenshot: forward it to the owner with confirm buttons."""
    lang = s.cfg.owner_lang
    who = esc(o["customer_name"] or str(o["user_id"]))
    caption = t(lang, "o_receipt", num=s.order_code(o["num"]), amount=money(o["deposit"] or o["total"], lang), who=who)
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton(t(lang, "o_btn_pay_ok"), callback_data=f"own:pok:{o['num']}"),
        InlineKeyboardButton(t(lang, "o_btn_pay_no"), callback_data=f"own:pno:{o['num']}"),
    ]])
    num = o["num"]
    o = s.db.update_order(num, payment_status="review", receipt_file_id=file_id)
    log.info("Order %s: receipt received", s.order_code(num))

    async def forward() -> None:
        media = file_id or upload
        if kind == "document":
            msg = await bot.send_document(s.cfg.owner_id, media, caption=caption, parse_mode=HTML, reply_markup=markup)
            stored = msg.document.file_id
        else:
            msg = await bot.send_photo(s.cfg.owner_id, media, caption=caption, parse_mode=HTML, reply_markup=markup)
            stored = msg.photo[-1].file_id
        s.db.update_order(num, receipt_file_id=stored)
        await refresh_owner_card(s, bot, s.db.get_order(num))

    s.spawn(forward(), key=num)  # uploading the screenshot can take a moment; the customer doesn't wait
    return o


# ---------------------------------------------------------------- customer messages

async def notify_customer(s: Services, bot: Bot, o: dict, photo: str | bytes | None = None):
    """The customer's message for the order's current stage, in their language.
    Returns the sent Message, or None if it could not be delivered."""
    lang, code, shop = o["lang"], s.order_code(o["num"]), s.catalog.shop
    rest = o["total"] - o["paid"]
    status = o["status"]
    markup = None
    if status == "accepted":
        text = t(lang, "n_accepted", num=code)
        if o["payment_status"] == "due":
            text += "\n\n" + t(lang, "n_pay", amount=money(o["deposit"], lang), pct=s.deposit_percent(),
                               card=esc(shop.card_number), holder=esc(shop.card_holder),
                               rest=money(o["total"] - o["deposit"], lang))
            digits = "".join(ch for ch in shop.card_number if ch.isdigit())
            markup = InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "btn_copy_card"),
                                                                 copy_text=CopyTextButton(digits))]])
    elif status == "ready":
        key = "n_ready_p" if o["method"] == "pickup" else "n_ready_d"
        text = t(lang, key, num=code, address=esc(shop.pickup_address[lang]))
    elif status == "on_way":
        text = t(lang, "n_on_way", num=code, courier=esc(views.courier_label(o, lang)))
    else:
        text = t(lang, {"baking": "n_baking", "decorating": "n_decorating", "delivered": "n_delivered",
                        "rejected": "n_rejected"}[status], num=code, phone=esc(shop.phone))
    if status in ("ready", "on_way") and rest > 0:
        text += t(lang, "n_rest", rest=money(rest, lang))

    reply = ReplyParameters(message_id=o["cust_widget_msg_id"], allow_sending_without_reply=True) \
        if o["cust_widget_msg_id"] else None
    try:
        if photo is not None:
            return await bot.send_photo(o["user_id"], photo, caption=text, parse_mode=HTML, reply_markup=markup)
        return await bot.send_message(o["user_id"], text, parse_mode=HTML, reply_markup=markup,
                                      reply_parameters=reply, link_preview_options=NO_PREVIEW)
    except TelegramError as e:
        log.warning("Customer %s not notified about %s: %s", o["user_id"], code, e)
        return None


async def send_reminder(s: Services, bot: Bot, o: dict) -> None:
    lang, shop = o["lang"], s.catalog.shop
    names = o["names"][lang]
    if o["method"] == "delivery":
        where = f"🚚 {t(lang, 'f_delivery')}: {esc(o['address'] or t(lang, 'location_label'))}"
    else:
        where = f"🏠 {t(lang, 'f_pickup')}: {esc(shop.pickup_address[lang])}"
    text = t(lang, "reminder", date=fmt_date(date.fromisoformat(o["delivery_date"]), lang, weekday=False),
             slot=esc(o["time_slot"]), num=s.order_code(o["num"]),
             product=esc(f"{names['product']}, {names['size']}"), where=where)
    rest = o["total"] - o["paid"]
    if rest > 0:
        text += t(lang, "n_rest", rest=money(rest, lang))
    await _send(bot, o["user_id"], text)


# ---------------------------------------------------------------- owner card

async def refresh_owner_card(s: Services, bot: Bot, o: dict) -> None:
    """Update the order card in the owner's chat after any change (from chat or dashboard)."""
    if not o["owner_msg_id"]:
        return
    from .owner import buttons  # owner imports ops

    text, markup = views.owner_card(s, o), buttons(s, o)
    try:
        if o["owner_msg_kind"] in ("photo", "document"):
            await bot.edit_message_caption(chat_id=s.cfg.owner_id, message_id=o["owner_msg_id"], caption=text,
                                           parse_mode=HTML, reply_markup=markup)
        else:
            await bot.edit_message_text(text, chat_id=s.cfg.owner_id, message_id=o["owner_msg_id"], parse_mode=HTML,
                                        reply_markup=markup, link_preview_options=NO_PREVIEW)
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            log.warning("Owner card of %s not refreshed: %s", s.order_code(o["num"]), e)
    except TelegramError as e:
        log.warning("Owner card of %s not refreshed: %s", s.order_code(o["num"]), e)


async def _update_widget(s: Services, bot: Bot, o: dict) -> None:
    if not o["cust_widget_msg_id"]:
        return
    try:
        await s.widgets.edit_chat_data(bot, o["user_id"], o["cust_widget_msg_id"], views.status_data(s, o))
    except TelegramError as e:
        if "not modified" not in str(e).lower():
            log.warning("Status widget of %s not updated: %s", s.order_code(o["num"]), e)


async def _send(bot: Bot, chat_id: int, text: str) -> None:
    try:
        await bot.send_message(chat_id, text, parse_mode=HTML, link_preview_options=NO_PREVIEW)
    except TelegramError as e:
        log.warning("Message to %s not sent: %s", chat_id, e)


async def _owner_note(s: Services, bot: Bot, text: str) -> None:
    await _send(bot, s.cfg.owner_id, text)
