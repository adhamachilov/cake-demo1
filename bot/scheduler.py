"""Timed messages, checked every 30 seconds:
  - the owner's morning summary (shop.morning_summary_time)
  - the evening before delivery (shop.reminder_time): a reminder to each customer,
    and tomorrow's list to the owner
Every message is recorded in the database first, so a restart never sends it twice."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from telegram import Bot

from . import ops, owner
from . import status as st
from .services import Services

log = logging.getLogger(__name__)
WINDOW_MINUTES = 180  # a summary is still sent if the bot starts up to 3 hours late


def _in_window(now: datetime, hhmm: str) -> bool:
    h, m = map(int, hhmm.split(":"))
    start = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return start <= now < start + timedelta(minutes=WINDOW_MINUTES)


async def tick(s: Services, bot: Bot) -> None:
    now = s.now()
    today = now.date()
    shop = s.catalog.shop

    if _in_window(now, shop.summary_time) and s.db.get_setting("summary_day") != today.isoformat():
        s.db.set_setting("summary_day", today.isoformat())
        log.info("Sending the morning summary")
        await owner.send_summary(s, bot, today, "morning")

    if now.strftime("%H:%M") >= shop.reminder_time:
        tomorrow = today + timedelta(days=1)
        cutoff = f"{today.isoformat()} {shop.reminder_time}"
        for o in s.db.orders_between(tomorrow.isoformat(), tomorrow.isoformat()):
            # orders placed after the reminder time were just made: no reminder needed
            if o["status"] in st.ACTIVE and not o["reminded"] and o["created_at"][:16] < cutoff:
                s.db.update_order(o["num"], reminded=1)
                await ops.send_reminder(s, bot, o)
                log.info("Reminder sent for %s", s.order_code(o["num"]))
        if _in_window(now, shop.reminder_time) and s.db.get_setting("evening_day") != today.isoformat():
            s.db.set_setting("evening_day", today.isoformat())
            if any(o["status"] in st.ACTIVE for o in s.db.orders_between(tomorrow.isoformat(), tomorrow.isoformat())):
                await owner.send_summary(s, bot, tomorrow, "evening")


async def run(s: Services, bot: Bot) -> None:
    while True:
        try:
            await tick(s, bot)
        except Exception:
            log.exception("Scheduler error")
        await asyncio.sleep(30)
