"""Promotions: the owner writes one message (optionally with a photo) in the dashboard and the
bot sends it to every customer who hasn't unsubscribed, with an "open catalog" button."""

from __future__ import annotations

import asyncio
import logging

from telegram import Bot, InlineKeyboardButton as IB, InlineKeyboardMarkup, WebAppInfo
from telegram.error import Forbidden, RetryAfter, TelegramError

from .services import Services
from .texts import t

log = logging.getLogger(__name__)
MAX_TEXT = 1000
PAUSE = 0.05  # 20 messages per second, under Telegram's limit of about 30


def _markup(s: Services, lang: str) -> InlineKeyboardMarkup:
    rows = []
    url = s.webapp_url or s.cfg.showcase_url
    if url:
        rows.append([IB(t(lang, "btn_open_catalog"), web_app=WebAppInfo(url))])
    rows.append([IB(t(lang, "btn_promo_off"), callback_data="promo:off")])
    return InlineKeyboardMarkup(rows)


def start(s: Services, bot: Bot, text: str, photo: bytes | None) -> dict:
    """Record the promotion and send it in the background. Returns {id, recipients}."""
    users = s.db.promo_recipients()
    bid = s.db.add_broadcast(text, photo is not None, s.now().strftime("%Y-%m-%d %H:%M"), len(users))
    s.spawn(_send_all(s, bot, bid, users, text, photo))
    log.info("Promotion %s: sending to %d customers", bid, len(users))
    return {"id": bid, "recipients": len(users)}


async def _send_all(s: Services, bot: Bot, bid: int, users: list[int], text: str, photo: bytes | None) -> None:
    sent, media = 0, photo
    for uid in users:
        lang = s.db.get_lang(uid) or "uz"
        for attempt in range(2):
            try:
                if media is not None:
                    msg = await bot.send_photo(uid, media, caption=text, reply_markup=_markup(s, lang))
                    media = msg.photo[-1].file_id  # upload once, then reuse
                else:
                    await bot.send_message(uid, text, reply_markup=_markup(s, lang))
                sent += 1
                break
            except RetryAfter as e:  # Telegram asks to slow down
                await asyncio.sleep(e.retry_after + 1)
            except Forbidden:  # the customer blocked the bot
                s.db.set_promos(uid, False)
                break
            except TelegramError as e:
                log.warning("Promotion %s not sent to %s: %s", bid, uid, e)
                break
        s.db.finish_broadcast(bid, sent)
        await asyncio.sleep(PAUSE)
    log.info("Promotion %s finished: %d of %d sent", bid, sent, len(users))
