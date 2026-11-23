"""Telegram HTML widgets (Bot API 10.4).

python-telegram-bot does not know these methods yet, so they are called by
name through Bot.do_api_request, which posts straight to
https://api.telegram.org/bot<token>/<method>. Method and parameter names
follow https://core.telegram.org/bots/api#sendwidget and the widget guide
https://core.telegram.org/bots/widgets.

Limits that shape this module (from the guide):
  * HTML: at most 32768 bytes, and at most 4096 bytes after zlib level 9.
  * chat_data / public_data: at most 1024 bytes each.
  * A widget has no network access: images must be inline, so catalog cards
    use drawn tiles and the real photo is sent in the chat after a tap.
"""

from __future__ import annotations

import html as htmlmod
import json
import logging
import zlib
from pathlib import Path

from telegram import Bot, InlineKeyboardMarkup

from .catalog import Catalog
from .texts import LANGS, t

log = logging.getLogger(__name__)

HTML_DIR = Path(__file__).parent / "widget_html"
MAX_HTML_BYTES = 32768
MAX_COMPRESSED = 4096
MAX_DATA_BYTES = 1024


def compressed_size(html: str) -> int:
    """Counted exactly as the server counts (per the widget guide)."""
    return len(zlib.compress(html.encode("utf-8"), 9))


def _minify(src: str) -> str:
    return "\n".join(line.strip() for line in src.splitlines() if line.strip())


def _js(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def build_catalog_html(catalog: Catalog, lang: str) -> str:
    cat_index = {c.id: i for i, c in enumerate(catalog.categories)}
    products = [
        [cat_index[p.category], p.id, p.emoji, p.color, p.name[lang], p.description[lang], p.price_label(lang)]
        for p in catalog.products.values()
    ]
    texts = {
        "sending": t(lang, "w_sending"),
        "ok": t(lang, "w_ok"),
        "gone": t(lang, "w_gone"),
        "err": t(lang, "w_err"),
        "TIMEOUT": t(lang, "w_timeout"),
        "FAILED": t(lang, "w_timeout"),
        "BUSY": t(lang, "w_busy"),
        "RATE_LIMITED": t(lang, "w_rate"),
        "NOT_ALLOWED": t(lang, "w_open_bot"),
    }
    src = (HTML_DIR / "catalog.html").read_text(encoding="utf-8")
    return _minify(
        src.replace("__TITLE__", htmlmod.escape(t(lang, "w_title", shop=catalog.shop.name)))
        .replace("__SUB__", htmlmod.escape(t(lang, "w_sub")))
        .replace("__C__", _js([c.short[lang] for c in catalog.categories]))
        .replace("__P__", _js(products))
        .replace("__T__", _js(texts))
    )


def build_status_html(catalog: Catalog, lang: str) -> str:
    texts = {
        "order": t(lang, "sw_order"),
        "new": t(lang, "sw_new"),
        "accepted": t(lang, "sw_accepted"),
        "ready": t(lang, "sw_ready"),
        "done_d": t(lang, "sw_delivered_d"),
        "done_p": t(lang, "sw_delivered_p"),
        "rejected": t(lang, "sw_rejected"),
        "note": t(lang, "sw_rej_note", phone=catalog.shop.phone),
    }
    src = (HTML_DIR / "status.html").read_text(encoding="utf-8")
    return _minify(src.replace("__T__", _js(texts)))


class Widgets:
    """Builds the widget HTML once per language, checks the size limits on
    start, and wraps the four Bot API widget calls this bot uses."""

    def __init__(self, catalog: Catalog, enabled: bool):
        self.enabled = enabled
        self.catalog_html: dict[str, str | None] = {}
        self.status_html: dict[str, str | None] = {}
        for lang in LANGS:
            self.catalog_html[lang] = self._checked(f"catalog/{lang}", build_catalog_html(catalog, lang))
            self.status_html[lang] = self._checked(f"status/{lang}", build_status_html(catalog, lang))

    @staticmethod
    def _checked(name: str, html: str) -> str | None:
        raw, packed = len(html.encode("utf-8")), compressed_size(html)
        if raw > MAX_HTML_BYTES or packed > MAX_COMPRESSED:
            log.error(
                "Widget %s is too large (%d bytes, %d compressed; limits %d / %d). "
                "Shorten product descriptions in catalog.yaml. Customers get the simple menu meanwhile.",
                name, raw, packed, MAX_HTML_BYTES, MAX_COMPRESSED,
            )
            return None
        log.info("Widget %s: %d bytes, %d compressed (limit %d)", name, raw, packed, MAX_COMPRESSED)
        return html

    # ---------- Bot API calls ----------

    @staticmethod
    async def send(
        bot: Bot,
        chat_id: int,
        html: str,
        *,
        caption: str | None = None,
        chat_data: str | None = None,
        allow_queries: bool = False,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> dict:
        """sendWidget. Returns the sent Message as a dict."""
        params: dict = {"chat_id": chat_id, "html": html}
        if caption:
            params["caption"] = caption
            params["parse_mode"] = "HTML"
        if chat_data is not None:
            params["chat_data"] = chat_data
        if allow_queries:
            params["allow_queries"] = True
        if reply_markup is not None:
            params["reply_markup"] = reply_markup
        return await bot.do_api_request("sendWidget", api_kwargs=params)

    @staticmethod
    async def answer(bot: Bot, widget_query_id: str, data: str | None = None) -> None:
        """answerWidgetQuery. Must be called within 15 seconds of the query."""
        params: dict = {"widget_query_id": widget_query_id}
        if data is not None:
            params["data"] = data
        await bot.do_api_request("answerWidgetQuery", api_kwargs=params)

    @staticmethod
    async def edit_chat_data(bot: Bot, chat_id: int, message_id: int, chat_data: str) -> None:
        """editMessageWidgetData. The running widget gets chatDataChanged and redraws."""
        await bot.do_api_request(
            "editMessageWidgetData",
            api_kwargs={"chat_id": chat_id, "message_id": message_id, "chat_data": chat_data},
        )


def fit_data(data: dict, shrink_key: str) -> str:
    """JSON-encode chat_data, trimming one text field until it fits 1024 bytes."""
    full = str(data.get(shrink_key) or "")
    for cut in range(len(full), -1, -8):
        data[shrink_key] = full[:cut] + ("…" if cut < len(full) else "")
        s = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        if len(s.encode("utf-8")) <= MAX_DATA_BYTES:
            return s
    data[shrink_key] = ""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
