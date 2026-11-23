"""A free public HTTPS address for the Mini App on this laptop, no server or domain needed.

Two providers, tried in this order:
  1. Cloudflare quick tunnel: `cloudflared tunnel --url http://127.0.0.1:<port>`
     (install: sudo zypper install cloudflared). Address: https://<random>.trycloudflare.com
  2. localhost.run over plain ssh: `ssh -R 80:127.0.0.1:<port> nokey@localhost.run`
     Needs nothing but ssh. Address: https://<random>.lhr.life

The address is random and can change (on restart, or when the provider rotates it).
Whenever it changes, `on_url` is called so the bot can update its menu button.
If the tunnel process dies, it is restarted."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shlex
import shutil
from typing import Awaitable, Callable

log = logging.getLogger(__name__)

# Each provider prints other links too (docs, admin pages), so match only the tunnel line.
PROVIDERS = {
    "cloudflared": re.compile(r"(?P<url>https://(?!api\.)[a-z0-9-]+\.trycloudflare\.com)"),
    "localhost.run": re.compile(r"tunneled with tls termination, (?P<url>https://[a-z0-9.-]+)"),
}


def _command(provider: str, port: int) -> list[str] | None:
    if provider == "cloudflared":
        # CLOUDFLARED may be a full command, e.g. "flatpak-spawn --host cloudflared" from a sandbox
        exe = shlex.split(os.getenv("CLOUDFLARED", "")) or ([shutil.which("cloudflared")] if shutil.which("cloudflared") else [])
        return [*exe, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"] if exe else None
    exe = shutil.which("ssh")
    if not exe:
        return None
    return [exe, "-T", "-o", "StrictHostKeyChecking=accept-new", "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3", "-o", "ExitOnForwardFailure=yes", "-o", "BatchMode=yes",
            "-R", f"80:127.0.0.1:{port}", "nokey@localhost.run"]


class Tunnel:
    def __init__(self, port: int, on_url: Callable[[str], Awaitable[None]] | None = None):
        self.port, self.on_url = port, on_url
        self.provider: str | None = None
        self.url: str | None = None
        self.proc: asyncio.subprocess.Process | None = None
        self._watch: asyncio.Task | None = None
        self._stopping = False

    async def start(self, timeout: float = 45) -> str | None:
        for provider in PROVIDERS:
            cmd = _command(provider, self.port)
            if not cmd:
                log.info("Tunnel provider %s not available", provider)
                continue
            url = await self._launch(provider, cmd, timeout)
            if url:
                self.provider, self.url = provider, url
                self._watch = asyncio.get_running_loop().create_task(self._supervise(cmd))
                log.info("Tunnel via %s: %s", provider, url)
                return url
        log.warning("No tunnel available (install cloudflared, or check that ssh can reach localhost.run). "
                    "The Mini App is off this run; customers get the simple menu.")
        return None

    async def _launch(self, provider: str, cmd: list[str], timeout: float) -> str | None:
        self.proc = await asyncio.create_subprocess_exec(
            *cmd, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        pattern = PROVIDERS[provider]
        try:
            async with asyncio.timeout(timeout):
                while raw := await self.proc.stdout.readline():
                    if m := pattern.search(raw.decode(errors="replace")):
                        return m.group("url")
        except TimeoutError:
            pass
        log.warning("%s did not report a public address", provider)
        await self._kill()
        return None

    async def _supervise(self, cmd: list[str]) -> None:
        """Keep reading the tunnel's output (a full pipe would stall it), follow address
        changes, and restart the tunnel if it exits."""
        pattern = PROVIDERS[self.provider]
        while not self._stopping:
            while self.proc and (raw := await self.proc.stdout.readline()):
                m = pattern.search(raw.decode(errors="replace"))
                if m and m.group("url") != self.url:
                    self.url = m.group("url")
                    log.info("Tunnel address changed: %s", self.url)
                    if self.on_url:
                        await self.on_url(self.url)
            if self._stopping:
                return
            log.warning("Tunnel (%s) closed; reconnecting in 5 s", self.provider)
            await asyncio.sleep(5)
            url = await self._launch(self.provider, cmd, 45)
            if url and url != self.url:
                self.url = url
                log.info("Tunnel reconnected: %s", url)
                if self.on_url:
                    await self.on_url(url)
            elif not url:
                await asyncio.sleep(25)

    async def _kill(self) -> None:
        if self.proc and self.proc.returncode is None:
            self.proc.terminate()
            try:
                await asyncio.wait_for(self.proc.wait(), 5)
            except TimeoutError:
                self.proc.kill()

    async def stop(self) -> None:
        self._stopping = True
        if self._watch:
            self._watch.cancel()
        await self._kill()
        self.proc = None
