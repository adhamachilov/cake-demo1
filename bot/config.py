"""Settings from the .env file. Nothing secret is ever hard-coded."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:
    token: str
    owner_id: int
    owner_lang: str
    widgets_enabled: bool
    catalog_path: Path
    db_path: Path
    api_base_url: str | None
    webapp_port: int
    webapp_url: str | None   # fixed public https URL; if empty, a Cloudflare quick tunnel is started
    tunnel: bool
    showcase_url: str | None = None  # static showcase (Netlify): the menu button when the live app is off


def _fail(msg: str) -> None:
    print(f"\n[config error] {msg}\nSee README.md, section 'Configure'.\n", file=sys.stderr)
    sys.exit(1)


def load_config() -> Config:
    load_dotenv(ROOT / ".env")

    token = os.getenv("BOT_TOKEN", "").strip()
    if not token or ":" not in token:
        _fail("BOT_TOKEN is missing in .env (get it from @BotFather).")

    owner_raw = os.getenv("OWNER_ID", "").strip()
    if not owner_raw.lstrip("-").isdigit():
        _fail("OWNER_ID in .env must be your numeric Telegram user ID (get it from @userinfobot).")

    owner_lang = os.getenv("OWNER_LANG", "uz").strip().lower()
    if owner_lang not in ("uz", "ru"):
        _fail("OWNER_LANG must be 'uz' or 'ru'.")

    def flag(var: str, default: str) -> bool:
        return os.getenv(var, default).strip().lower() not in ("off", "0", "false", "no")

    widgets = flag("WIDGETS", "off")

    port_raw = os.getenv("WEBAPP_PORT", "8080").strip()
    if not port_raw.isdigit():
        _fail("WEBAPP_PORT must be a number, e.g. 8080.")
    webapp_url = os.getenv("WEBAPP_URL", "").strip().rstrip("/") or None
    if webapp_url and not webapp_url.startswith("https://"):
        _fail("WEBAPP_URL must start with https:// (Telegram opens Mini Apps only over HTTPS).")

    def path(var: str, default: str) -> Path:
        p = Path(os.getenv(var, default).strip() or default)
        return p if p.is_absolute() else ROOT / p

    return Config(
        token=token,
        owner_id=int(owner_raw),
        owner_lang=owner_lang,
        widgets_enabled=widgets,
        catalog_path=path("CATALOG_PATH", "catalog.yaml"),
        db_path=path("DB_PATH", "data/bakery.db"),
        api_base_url=os.getenv("BOT_API_URL", "").strip() or None,
        webapp_port=int(port_raw),
        webapp_url=webapp_url,
        tunnel=flag("TUNNEL", "on"),
        showcase_url=_https("SHOWCASE_URL"),
    )


def _https(var: str) -> str | None:
    value = os.getenv(var, "").strip()
    if value and not value.startswith("https://"):
        _fail(f"{var} must start with https://")
    return value.rstrip("/") + "/" if value else None
