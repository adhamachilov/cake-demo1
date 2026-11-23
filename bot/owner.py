"""The owner's side in the chat: one complete card per order with stage buttons,
the cake-photo and courier prompts, receipt checks, and the daily summaries.
The actual changes happen in ops.py, shared with the dashboard Mini App."""

from __future__ import annotations

import logging
import time
from datetime import date

from telegram import Bot, CallbackQuery, InlineKeyboardButton as IB, InlineKeyboardMarkup, LinkPreviewOptions, Message, WebAppInfo
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError

from . import ops, views
from . import status as st
from .services import Services
from .texts import esc, fmt_date, money, t

log = logging.getLogger(__name__)
HTML = ParseMode.HTML
NO_PREVIEW = LinkPreviewOptions(is_disabled=True)
CAPTION_LIMIT = 1024
PENDING_TTL = 15 * 60  # an unanswered photo/courier question expires after 15 minutes

BUTTON_TEXT = {"acc": "o_btn_accept", "rej": "o_btn_reject", "bak": "o_btn_baking", "dec": "o_btn_decorating",
               "rdy": "o_btn_ready", "way": "o_btn_on_way", "dlv": "o_btn_delivered"}


def dashboard_url(s: Services, num: int | None = None) -> str | None:
    if not s.webapp_url:
        return None
    return s.webapp_url + "?admin=1" + (f"&order={num}" if num else "")


def buttons(s: Services, o: dict) -> InlineKeyboardMarkup | None:
    lang, n = s.cfg.owner_lang, o["num"]
    stage = [IB(t(lang, BUTTON_TEXT[a]), callback_data=f"own:{a}:{n}") for a in st.next_actions(o)]
    rows = [stage[i:i + 2] for i in range(0, len(stage), 2)]
    if o["payment_status"] in ("due", "review") and o["status"] in st.ACTIVE:
        rows.append([IB(t(lang, "o_btn_paid"), callback_data=f"own:pok:{n}")])
    if url := dashboard_url(s, n):
        rows.append([IB(t(lang, "o_btn_details"), web_app=WebAppInfo(url))])
    return InlineKeyboardMarkup(rows) if rows else None


def reject_confirm(s: Services, o: dict) -> InlineKeyboardMarkup:
    lang, n = s.cfg.owner_lang, o["num"]
    return InlineKeyboardMarkup([[IB(t(lang, "o_btn_reject_yes"), callback_data=f"own:rjy:{n}"),
                                  IB(t(lang, "o_btn_reject_no"), callback_data=f"own:rjn:{n}")]])


# ---------------------------------------------------------------- order card

async def send_card(s: Services, bot: Bot, o: dict, photo_upload: bytes | None = None) -> None:
    """Send the order card to the owner: one message, with the reference photo when there is one.
    `photo_upload` is a photo uploaded in the Mini App (not yet on Telegram's servers)."""
    chat_id, text, markup = s.cfg.owner_id, views.owner_card(s, o), buttons(s, o)
    photo = o["photo_file_id"] or photo_upload
    if photo:
        send = bot.send_photo if o["photo_kind"] == "photo" else bot.send_document
        try:
            if views.visible_length(text) <= CAPTION_LIMIT:
                msg = await send(chat_id, photo, caption=text, parse_mode=HTML, reply_markup=markup)
                _remember(s, o, msg, o["photo_kind"])
                return
            first = await send(chat_id, photo)  # very long order: photo first, then the card
            _remember(s, o, first, None)
        except BadRequest as e:
            log.warning("Reference photo of %s not sent (%s); sending the card without it", s.order_code(o["num"]), e)
    msg = await bot.send_message(chat_id, text, parse_mode=HTML, reply_markup=markup, link_preview_options=NO_PREVIEW)
    s.db.update_order(o["num"], owner_msg_id=msg.message_id, owner_msg_kind="text")


def _remember(s: Services, o: dict, msg, kind: str | None) -> None:
    """Save the card's message id, and the photo's Telegram file_id so /o<num> can resend it."""
    fields = {}
    if kind:
        fields.update(owner_msg_id=msg.message_id, owner_msg_kind=kind)
    if not o["photo_file_id"]:
        fields["photo_file_id"] = msg.photo[-1].file_id if msg.photo else msg.document.file_id
    if fields:
        s.db.update_order(o["num"], **fields)


async def notify_new_order(s: Services, bot: Bot, o: dict, photo_upload: bytes | None = None) -> None:
    try:
        await send_card(s, bot, o, photo_upload)
    except TelegramError as e:
        log.error(
            "Could not deliver order %s to OWNER_ID=%s: %s. The owner account must open the bot and press "
            "/start once, and OWNER_ID must be that account's numeric ID.",
            s.order_code(o["num"]), s.cfg.owner_id, e,
        )


async def open_order(s: Services, bot: Bot, num: int) -> None:
    o = s.db.get_order(num)
    if not o:
        await bot.send_message(s.cfg.owner_id, t(s.cfg.owner_lang, "o_not_found"))
        return
    await send_card(s, bot, o)


# ---------------------------------------------------------------- buttons

async def on_callback(s: Services, bot: Bot, q: CallbackQuery, action: str, num: int) -> None:
    lang = s.cfg.owner_lang
    if q.from_user.id != s.cfg.owner_id:
        await q.answer(t(s.lang_of(q.from_user), "o_not_owner"), show_alert=True)
        return
    o = s.db.get_order(num)
    if not o:
        await q.answer(t(lang, "o_not_found"), show_alert=True)
        return

    if action == "rej":  # ask before rejecting
        if not st.allowed(o, "rej"):
            return await _stale(s, bot, q, o)
        await q.answer(t(lang, "o_reject_q"))
        return await q.edit_message_reply_markup(reject_confirm(s, o))
    if action == "rjn":
        await q.answer()
        return await q.edit_message_reply_markup(buttons(s, o))
    if action == "rdy":  # ask for a photo of the finished cake first
        if not st.allowed(o, "rdy"):
            return await _stale(s, bot, q, o)
        await q.answer()
        return await _ask(s, bot, num, "ready", t(lang, "o_ask_photo", num=s.order_code(num)),
                          [[IB(t(lang, "o_btn_no_photo"), callback_data=f"own:rnp:{num}")]])
    if action == "way":  # ask who delivers
        if not st.allowed(o, "way"):
            return await _stale(s, bot, q, o)
        await q.answer()
        rows = [[IB(t(lang, "o_btn_self"), callback_data=f"own:wsf:{num}")]]
        if last := s.db.get_setting("last_courier"):
            rows.append([IB(f"🚚 {last}"[:60], callback_data=f"own:wls:{num}")])
        return await _ask(s, bot, num, "courier", t(lang, "o_ask_courier", num=s.order_code(num)), rows)
    if action == "cxl":
        await q.answer(t(lang, "o_cancelled"))
        return await _close_pending(s, bot, t(lang, "o_cancelled"))

    try:
        if action in ("pok", "pno"):
            await ops.confirm_payment(s, bot, num, ok=action == "pok")
            if q.message and q.message.message_id != o["owner_msg_id"]:
                await _mark_done(q, t(lang, "o_done"))  # the receipt message
        elif action == "rnp":
            await _close_pending(s, bot, t(lang, "o_done"))
            await ops.change_status(s, bot, num, "rdy")
        elif action in ("wsf", "wls"):
            courier = "self" if action == "wsf" else (s.db.get_setting("last_courier") or "self")
            await _close_pending(s, bot, t(lang, "o_done"))
            await ops.change_status(s, bot, num, "way", courier=courier)
        else:
            action = "rej" if action == "rjy" else action
            await ops.change_status(s, bot, num, action)
    except ops.OpError:
        return await _stale(s, bot, q, s.db.get_order(num))
    o = s.db.get_order(num)
    await q.answer(t(lang, "o_changed", status=t(lang, "st_" + o["status"])))
    if q.message and q.message.message_id != o["owner_msg_id"] and action not in ("pok", "pno"):
        await _refresh_this(s, q, o)  # a card reopened with /o<num>


async def _stale(s: Services, bot: Bot, q: CallbackQuery, o: dict) -> None:
    await q.answer(t(s.cfg.owner_lang, "o_already"))
    if q.message and q.message.message_id == o["owner_msg_id"]:
        await ops.refresh_owner_card(s, bot, o)
    else:
        await _refresh_this(s, q, o)


async def _refresh_this(s: Services, q: CallbackQuery, o: dict) -> None:
    text, markup = views.owner_card(s, o), buttons(s, o)
    try:
        if q.message.photo or q.message.document:
            await q.edit_message_caption(caption=text, parse_mode=HTML, reply_markup=markup)
        else:
            await q.edit_message_text(text, parse_mode=HTML, reply_markup=markup, link_preview_options=NO_PREVIEW)
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            log.warning("Card not refreshed: %s", e)


async def _mark_done(q: CallbackQuery, note: str) -> None:
    try:
        caption = (q.message.caption_html or "") + f"\n\n<b>{note}</b>"
        await q.edit_message_caption(caption=caption, parse_mode=HTML, reply_markup=None)
    except BadRequest:
        pass


# ---------------------------------------------------------------- questions to the owner (photo, courier)

async def _ask(s: Services, bot: Bot, num: int, kind: str, text: str, rows: list) -> None:
    await _close_pending(s, bot, None)
    rows = rows + [[IB(t(s.cfg.owner_lang, "o_btn_cancel"), callback_data=f"own:cxl:{num}")]]
    msg = await bot.send_message(s.cfg.owner_id, text, parse_mode=HTML, reply_markup=InlineKeyboardMarkup(rows))
    s.owner_pending[s.cfg.owner_id] = {"kind": kind, "num": num, "msg": msg.message_id, "text": text, "at": time.time()}


async def _close_pending(s: Services, bot: Bot, note: str | None) -> None:
    p = s.owner_pending.pop(s.cfg.owner_id, None)
    if not p:
        return
    try:
        await bot.edit_message_text(p["text"] + (f"\n<b>{note}</b>" if note else ""), chat_id=s.cfg.owner_id,
                                    message_id=p["msg"], parse_mode=HTML)
    except BadRequest:
        pass


def pending(s: Services) -> dict | None:
    p = s.owner_pending.get(s.cfg.owner_id)
    if p and time.time() - p["at"] > PENDING_TTL:
        s.owner_pending.pop(s.cfg.owner_id, None)
        return None
    return p


async def owner_input(s: Services, bot: Bot, msg: Message) -> bool:
    """The owner answered a photo or courier question. Returns True if the message was used."""
    p = pending(s)
    if not p or msg.from_user.id != s.cfg.owner_id:
        return False
    lang = s.cfg.owner_lang
    try:
        if p["kind"] == "ready" and (msg.photo or (msg.document and (msg.document.mime_type or "").startswith("image/"))):
            photo = msg.photo[-1].file_id if msg.photo else msg.document.file_id
            await _close_pending(s, bot, t(lang, "o_done"))
            await ops.change_status(s, bot, p["num"], "rdy", photo=photo)
            return True
        if p["kind"] == "courier" and msg.text and not msg.text.startswith("/"):
            await _close_pending(s, bot, t(lang, "o_done"))
            await ops.change_status(s, bot, p["num"], "way", courier=msg.text)
            return True
    except ops.OpError:
        await msg.reply_text(t(lang, "o_already"))
        return True
    return False


# ---------------------------------------------------------------- summaries

def summary_text(s: Services, day: date, kind: str = "day") -> str:
    """kind: 'morning' (today's plan), 'evening' (tomorrow), 'day' (/orders)."""
    lang = s.cfg.owner_lang
    title = {"morning": "o_sum_morning", "evening": "o_sum_evening"}.get(kind, "o_sum_day")
    lines = [t(lang, title, date=fmt_date(day, lang)), ""]

    due = [o for o in s.db.orders_between(day.isoformat(), day.isoformat()) if o["status"] in st.ACTIVE]
    lines.append(f"<b>{t(lang, 'o_sum_orders', n=len(due))}</b>")
    for o in due:
        names = o["names"][lang]
        where = "🚚 " + esc((o["address"] or t(lang, "location_label"))[:40]) if o["method"] == "delivery" else "🏠"
        lines.append(f"• {esc(o['time_slot'])} · <b>#{s.order_code(o['num'])}</b> {esc(names['product'])} "
                     f"({esc(names['size'])}) · {where} · {t(lang, 'st_' + o['status'])} /o{o['num']}")
    if not due:
        lines.append(t(lang, "o_sum_empty"))
    else:
        total = sum(o["total"] for o in due)
        paid = sum(o["paid"] for o in due)
        lines.append(f"<i>{t(lang, 'o_sum_total', total=money(total, lang), paid=money(paid, lang))}</i>")

    if kind != "evening":
        new = s.db.orders_with_status("new")
        if new:
            lines += ["", f"<b>{t(lang, 'o_sum_new', n=len(new))}</b>"]
            lines += [views.order_line(s, o, lang) for o in new]
        unpaid = [o for o in s.db.orders_with_status(*st.ACTIVE) if o["payment_status"] in ("due", "review")]
        if unpaid:
            lines += ["", f"<b>{t(lang, 'o_sum_unpaid', n=len(unpaid))}</b>"]
            lines += [f"• <b>#{s.order_code(o['num'])}</b> · {money(o['deposit'], lang)} · "
                      f"{views.payment_line(o, lang)} /o{o['num']}" for o in unpaid]
    return "\n".join(lines)


async def send_summary(s: Services, bot: Bot, day: date, kind: str = "day", chat_id: int | None = None) -> None:
    text = summary_text(s, day, kind)
    markup = None
    if url := dashboard_url(s):
        markup = InlineKeyboardMarkup([[IB(t(s.cfg.owner_lang, "o_btn_dashboard"), web_app=WebAppInfo(url))]])
    chunks, chunk = [], ""
    for line in text.split("\n"):  # Telegram's 4096-character limit
        if len(chunk) + len(line) + 1 > 3900:
            chunks.append(chunk)
            chunk = ""
        chunk += line + "\n"
    chunks.append(chunk)
    for i, part in enumerate(chunks):
        await bot.send_message(chat_id or s.cfg.owner_id, part, parse_mode=HTML, link_preview_options=NO_PREVIEW,
                               reply_markup=markup if i == len(chunks) - 1 else None)
