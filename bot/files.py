"""Telegram photos (receipts, finished cakes, reference photos) shown inside the Mini App.

Making a link costs nothing: the link carries the Telegram file id and a signature.
The photo is downloaded from Telegram only when the link is first opened, then kept
in data/files/. Only links the bot handed out work."""

from __future__ import annotations

import hashlib
import hmac
import logging
import urllib.parse
from pathlib import Path

from telegram import Bot
from telegram.error import TelegramError

log = logging.getLogger(__name__)


class FileStore:
    def __init__(self, folder: Path, bot: Bot, secret: str):
        self.dir = folder
        self.dir.mkdir(parents=True, exist_ok=True)
        self.bot = bot
        self.key = hashlib.sha256(("files:" + secret).encode()).digest()

    @staticmethod
    def _name(file_id: str) -> str:
        return hashlib.sha256(file_id.encode()).hexdigest()[:24] + ".jpg"

    def _sign(self, name: str) -> str:
        return hmac.new(self.key, name.encode(), hashlib.sha256).hexdigest()[:24]

    def url(self, file_id: str | None) -> str | None:
        """Relative URL for the Mini App, or None if there is no photo."""
        if not file_id:
            return None
        name = self._name(file_id)
        return f"f/{name}?s={self._sign(name)}&id={urllib.parse.quote(file_id)}"

    async def path(self, name: str, signature: str, file_id: str) -> Path | None:
        """The photo on disk, downloading it from Telegram the first time."""
        if not hmac.compare_digest(self._sign(name), signature or "") or self._name(file_id) != name:
            return None
        path = self.dir / name
        if not path.exists():
            try:
                tg_file = await self.bot.get_file(file_id)
                await tg_file.download_to_drive(path)
            except (TelegramError, OSError) as e:
                log.warning("Could not download a photo for the Mini App: %s", e)
                return None
        return path
