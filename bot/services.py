"""Everything the handlers share, kept in one object on application.bot_data."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram import User
from telegram.ext import ContextTypes

from .catalog import Catalog, Product
from .config import Config
from .db import DB
from .widgets import Widgets

log = logging.getLogger(__name__)


@dataclass
class Draft:
    """An order being filled in. Lives in memory until confirmed or cancelled."""

    did: str                      # short random id, embedded in buttons so old buttons are ignored
    product_id: str
    lang: str
    customer_name: str
    username: str | None
    step: str = "size"
    size: str | None = None
    filling: str | None = None
    inscription: str | None = None   # "" = customer chose no inscription
    photo_id: str | None = None
    photo_kind: str | None = None    # 'photo', 'document' or 'skipped'
    date: str | None = None          # YYYY-MM-DD
    slot: int | None = None
    method: str | None = None        # 'delivery' or 'pickup'
    address: str | None = None
    lat: float | None = None
    lon: float | None = None
    phone: str | None = None
    prompt_id: int | None = None     # the message asking the current question
    prompt_text: str = ""
    reply_kb: bool = False           # current question uses a reply keyboard (contact/location)


@dataclass
class Services:
    cfg: Config
    catalog: Catalog
    db: DB
    widgets: Widgets
    drafts: dict[int, Draft] = field(default_factory=dict)
    widget_checks: dict[int, asyncio.Task] = field(default_factory=dict)
    photo_ids: dict[Path, str] = field(default_factory=dict)  # local image -> Telegram file_id, saves re-uploads
    webapp_url: str | None = None   # public https address of the Mini App, when it is running
    webapp: object = None           # MiniAppServer
    tunnel: object = None           # Tunnel
    files: object = None            # FileStore: Telegram photos shown in the Mini App
    owner_pending: dict[int, dict] = field(default_factory=dict)  # owner is asked for a cake photo / courier
    background: list[asyncio.Task] = field(default_factory=list)  # scheduler etc.
    tasks: set[asyncio.Task] = field(default_factory=set)         # Telegram sends running in the background
    chains: dict = field(default_factory=dict)                    # order number -> its latest background task

    def spawn(self, coro, key=None) -> asyncio.Task:
        """Run slow Telegram work (messages, photo uploads) in the background so the
        customer's app and the owner's buttons answer at once. Work with the same key
        (an order number) runs in order: a customer never gets 'baking' before 'accepted'."""
        prev = self.chains.get(key) if key is not None else None

        async def run():
            if prev is not None:
                await asyncio.wait([prev])
            try:
                await coro
            except Exception:
                log.exception("Background Telegram task failed")

        task = asyncio.get_running_loop().create_task(run())
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        if key is not None:
            self.chains[key] = task
            task.add_done_callback(lambda t: self.chains.pop(key, None) if self.chains.get(key) is t else None)
        return task

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.catalog.shop.timezone)

    def now(self) -> datetime:
        return datetime.now(self.tz)

    def lang_of(self, user: User | dict) -> str:
        uid = user["id"] if isinstance(user, dict) else user.id
        code = (user.get("language_code") if isinstance(user, dict) else user.language_code) or ""
        return self.db.get_lang(uid) or ("ru" if code.startswith("ru") else "uz")

    def product(self, product_id: str) -> Product | None:
        return self.catalog.products.get(product_id)

    def order_code(self, num: int) -> str:
        return f"{self.catalog.shop.order_prefix}-{num}"

    # ---------- owner settings (dashboard overrides catalog.yaml) ----------
    def capacity(self) -> int:
        value = self.db.get_setting("daily_capacity")
        return int(value) if value is not None else self.catalog.shop.daily_capacity

    def deposit_percent(self) -> int:
        value = self.db.get_setting("deposit_percent")
        return int(value) if value is not None else self.catalog.shop.deposit_percent

    def deposit_for(self, total: int) -> int:
        """Deposit asked after acceptance, rounded up to 1 000 so'm."""
        pct = self.deposit_percent()
        return min(total, -(-total * pct // 100_000) * 1000) if pct else 0

    def is_sold_out(self, product_id: str) -> bool:
        return product_id in self.db.sold_out()

    # ---------- dates ----------
    def date_status(self, p: Product) -> list[tuple[date, str | None]]:
        """Every date in the booking window with why it can't be booked: None, 'closed' or 'full'."""
        first = self.now().date() + timedelta(days=p.lead_days)
        days = [first + timedelta(days=i) for i in range(self.catalog.shop.booking_days)]
        closed, cap = self.db.closed_days(), self.capacity()
        booked = self.db.booked_per_day(days[0].isoformat(), days[-1].isoformat())
        out = []
        for d in days:
            iso = d.isoformat()
            why = "closed" if iso in closed else ("full" if cap and booked.get(iso, 0) >= cap else None)
            out.append((d, why))
        return out

    def available_dates(self, p: Product) -> list[date]:
        return [d for d, why in self.date_status(p) if not why]

    def delivery_fee(self, item_price: int) -> int:
        shop = self.catalog.shop
        if shop.free_delivery_from and item_price >= shop.free_delivery_from:
            return 0
        return shop.delivery_fee


def svc(context: ContextTypes.DEFAULT_TYPE) -> Services:
    return context.application.bot_data["svc"]
