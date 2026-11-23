"""Ratings after delivery: 1-5 stars from a button under the "delivered" message (or in the
Mini App), then an optional comment. Good reviews with a finished-cake photo appear in the
Mini App's "Our works" gallery."""

from __future__ import annotations

import logging

from telegram import Bot, CallbackQuery, InlineKeyboardButton as IB, InlineKeyboardMarkup, Message
from telegram.constants import ParseMode
from telegram.error import TelegramError

from .services import Services
from .texts import esc, stars, t

log = logging.getLogger(__name__)
MAX_REVIEW = 500


def rating_buttons(num: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[IB(f"{k} ⭐", callback_data=f"rate:{num}:{k}") for k in range(1, 6)]])


async def on_rate(s: Services, bot: Bot, q: CallbackQuery, num: int, value: int) -> None:
    o = s.db.get_order(num)
    lang = s.lang_of(q.from_user)
    if not o or o["user_id"] != q.from_user.id or o["status"] != "delivered" or not 1 <= value <= 5:
        return await q.answer(t(lang, "stale"))
    first = o["rating"] is None
    s.db.update_order(num, rating=value)
    await q.answer(stars(value))
    try:
        await q.edit_message_reply_markup(None)
    except TelegramError:
        pass
    if first:
        s.review_pending[q.from_user.id] = num
        await bot.send_message(q.from_user.id, f"{stars(value)}\n{t(lang, 'rate_thanks')}",
                               reply_markup=InlineKeyboardMarkup([[IB(t(lang, "btn_skip"), callback_data=f"rv:skip:{num}")]]))


async def on_skip(s: Services, bot: Bot, q: CallbackQuery, num: int) -> None:
    s.review_pending.pop(q.from_user.id, None)
    await q.answer()
    try:
        await q.edit_message_reply_markup(None)
    except TelegramError:
        pass
    o = s.db.get_order(num)
    if o and o["user_id"] == q.from_user.id:
        await notify_owner(s, bot, o)


async def on_text(s: Services, bot: Bot, msg: Message) -> bool:
    """The customer's comment after rating. Returns True if the message was used."""
    num = s.review_pending.pop(msg.from_user.id, None)
    if num is None or not msg.text or msg.text.startswith("/"):
        return False
    o = await save(s, bot, num, msg.from_user.id, None, msg.text)
    if o:
        await msg.reply_text(t(o["lang"], "review_saved"))
    return True


async def save(s: Services, bot: Bot, num: int, user_id: int, value: int | None, text: str | None) -> dict | None:
    """Store a rating and/or comment (chat or Mini App) and tell the owner."""
    o = s.db.get_order(num)
    if not o or o["user_id"] != user_id or o["status"] != "delivered":
        return None
    fields = {}
    if value is not None and 1 <= value <= 5:
        fields["rating"] = value
    if text and text.strip():
        fields["review"] = text.strip()[:MAX_REVIEW]
    if fields:
        o = s.db.update_order(num, **fields)
        log.info("Review for %s: %s stars", s.order_code(num), o["rating"])
        await notify_owner(s, bot, o)
    return o


async def notify_owner(s: Services, bot: Bot, o: dict) -> None:
    if not o["rating"]:
        return
    lang = s.cfg.owner_lang
    text = t(lang, "o_review", stars=stars(o["rating"]), num=s.order_code(o["num"]),
             text=f"«{esc(o['review'])}»\n" if o["review"] else "", who=esc(o["customer_name"] or ""))
    try:
        await bot.send_message(s.cfg.owner_id, text, parse_mode=ParseMode.HTML)
    except TelegramError as e:
        log.warning("Review not sent to the owner: %s", e)
