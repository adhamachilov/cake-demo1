"""Keyboards that are not part of the order form."""

from __future__ import annotations

from telegram import InlineKeyboardButton as IB
from telegram import InlineKeyboardMarkup, ReplyKeyboardMarkup, WebAppInfo

from .catalog import Catalog
from .texts import t


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [t(lang, "btn_catalog"), t(lang, "btn_simple")],
            [t(lang, "btn_my_orders"), t(lang, "btn_lang")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def lang_choice() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[IB("🇺🇿 O'zbekcha", callback_data="lang:uz"), IB("🇷🇺 Русский", callback_data="lang:ru")]])


def open_app(lang: str, url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [IB(t(lang, "btn_open_app"), web_app=WebAppInfo(url))],
        [IB(t(lang, "btn_simple"), callback_data="menu")],
    ])


def open_simple_menu(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[IB(t(lang, "btn_simple"), callback_data="menu")]])


def categories(catalog: Catalog, lang: str) -> InlineKeyboardMarkup:
    buttons = [IB(f"{c.emoji} {c.name[lang]}".strip(), callback_data=f"cat:{c.id}") for c in catalog.categories]
    return InlineKeyboardMarkup([buttons[i:i + 2] for i in range(0, len(buttons), 2)])


def products(catalog: Catalog, cat_id: str, lang: str, sold_out: set[str] = frozenset()) -> InlineKeyboardMarkup:
    rows = [
        [IB(f"{p.emoji} {p.name[lang]} · {p.price_label(lang)}" + (t(lang, "sold_out_tag") if p.id in sold_out else ""),
            callback_data=f"prod:{p.id}")]
        for p in catalog.in_category(cat_id)
    ]
    rows.append([IB(t(lang, "btn_back_cats"), callback_data="cats")])
    return InlineKeyboardMarkup(rows)
