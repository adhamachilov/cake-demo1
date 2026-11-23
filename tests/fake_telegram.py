"""A small fake Telegram Bot API server for tests: records every call the bot makes,
serves updates we push, and can add a delay per call to imitate a real network."""

from __future__ import annotations

import email.parser
import email.policy
import json
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BOT = {"id": 4242, "is_bot": True, "first_name": "Shirin Tortlar", "username": "shirin_test_bot"}
SILENT = ("getUpdates", "getMe", "deleteWebhook", "setMyCommands", "setChatMenuButton")


class FakeTelegram:
    def __init__(self, port: int, latency: float = 0.0):
        self.calls: list[tuple[str, dict]] = []
        self.updates: list[dict] = []
        self.messages: dict[int, dict] = {}
        self.latency = latency  # seconds added to every API call except getUpdates
        self.next_update = 1
        self.next_msg = 100
        self.cv = threading.Condition()
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def handle(self):
                try:
                    super().handle()
                except (BrokenPipeError, ConnectionResetError):
                    pass  # the bot closed a long poll early (shutdown)

            def do_POST(self):
                if "/file/bot" in self.path:  # download after getFile
                    self._send(200, b"\xff\xd8\xff\xe0FAKEJPEG\xff\xd9", "image/jpeg")
                    return
                method = self.path.rsplit("/", 1)[-1]
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                params = fake._parse(self.headers.get("Content-Type", ""), body)
                ok, result = fake._handle(method, params)
                out = {"ok": True, "result": result} if ok else {"ok": False, "error_code": 400, "description": result}
                self._send(200 if ok else 400, json.dumps(out).encode(), "application/json")

            do_GET = do_POST

            def _send(self, code, data, ctype):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    # ---------------------------------------------------------------- server side
    @staticmethod
    def _parse(ctype: str, body: bytes) -> dict:
        if ctype.startswith("application/json"):
            return json.loads(body or b"{}")
        if ctype.startswith("multipart/form-data"):
            msg = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(
                b"Content-Type: " + ctype.encode() + b"\r\n\r\n" + body)
            out = {}
            for part in msg.iter_parts():
                name = part.get_param("name", header="content-disposition")
                payload = part.get_payload(decode=True)
                out[name] = f"<upload {len(payload)} bytes>" if part.get_filename() else payload.decode()
            return out
        return {k: v[0] for k, v in urllib.parse.parse_qs(body.decode()).items()}

    def _message(self, chat_id, **extra) -> dict:
        self.next_msg += 1
        m = {"message_id": self.next_msg, "date": int(time.time()),
             "chat": {"id": int(chat_id), "type": "private"}, "from": BOT, **extra}
        self.messages[m["message_id"]] = m
        return m

    def _handle(self, method: str, p: dict):
        if method == "getUpdates":
            offset = int(p.get("offset", 0) or 0)
            end = time.time() + min(float(p.get("timeout", 0) or 0), 1.0)
            with self.cv:
                while True:
                    ready = [u for u in self.updates if u["update_id"] >= offset]
                    if ready or time.time() >= end:
                        return True, ready
                    self.cv.wait(0.05)
        if self.latency and method not in SILENT:
            time.sleep(self.latency)
        with self.cv:
            self.calls.append((method, p))
            self.cv.notify_all()
        if method == "getMe":
            return True, BOT
        if method in ("deleteWebhook", "setMyCommands", "setChatMenuButton", "answerCallbackQuery",
                      "answerWidgetQuery", "editMessageWidgetData"):
            return True, True
        if method == "getFile":
            return True, {"file_id": p["file_id"], "file_unique_id": "u", "file_size": 12, "file_path": "photos/x.jpg"}
        if method == "sendMessage":
            return True, self._message(p["chat_id"], text=p["text"])
        if method == "sendPhoto":
            return True, self._message(p["chat_id"], caption=p.get("caption", ""), photo=[
                {"file_id": f"PHOTO_{self.next_msg}", "file_unique_id": "u", "width": 1280, "height": 960}])
        if method == "sendDocument":
            return True, self._message(p["chat_id"], caption=p.get("caption", ""),
                                       document={"file_id": f"DOC_{self.next_msg}", "file_unique_id": "u"})
        if method in ("editMessageText", "editMessageCaption", "editMessageReplyMarkup"):
            m = dict(self.messages.get(int(p.get("message_id", 0)), {}))
            m.update({k: p[k] for k in ("text", "caption") if k in p})
            return True, m or self._message(p["chat_id"])
        return False, f"Not Found: {method} is not faked"

    # ---------------------------------------------------------------- test side
    def push(self, update: dict) -> None:
        with self.cv:
            update["update_id"] = self.next_update
            self.next_update += 1
            self.updates.append(update)
            self.cv.notify_all()

    def wait(self, method: str, since: int, pred=lambda p: True, timeout: float = 8.0) -> dict:
        """The first `method` call after index `since` matching `pred`."""
        end = time.time() + timeout
        with self.cv:
            while True:
                for m, p in self.calls[since:]:
                    if m == method and pred(p):
                        return p
                if time.time() > end:
                    raise AssertionError(f"no {method} call; calls since: {[m for m, _ in self.calls[since:]]}")
                self.cv.wait(0.05)

    def stop(self) -> None:
        self.server.shutdown()
