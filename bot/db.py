"""SQLite storage: customers (language, widget support) and orders."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ORDER_NUM_OFFSET = 1000  # first order is #1001, which looks better than #1

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    lang        TEXT,
    first_name  TEXT,
    username    TEXT,
    widget_ok   INTEGER NOT NULL DEFAULT 0,   -- 1 once a widget has reported it rendered
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    num             INTEGER UNIQUE,            -- public order number, id + 1000
    user_id         INTEGER NOT NULL,
    lang            TEXT NOT NULL,
    customer_name   TEXT,
    username        TEXT,
    product_id      TEXT NOT NULL,
    size_id         TEXT,
    filling_id      TEXT,
    names           TEXT NOT NULL,             -- JSON snapshot of product/size/filling names in uz and ru
    inscription     TEXT,
    photo_file_id   TEXT,
    photo_kind      TEXT,                      -- 'photo' or 'document'
    delivery_date   TEXT NOT NULL,             -- YYYY-MM-DD
    time_slot       TEXT NOT NULL,
    method          TEXT NOT NULL,             -- 'delivery' or 'pickup'
    address         TEXT,
    lat             REAL,
    lon             REAL,
    phone           TEXT NOT NULL,
    item_price      INTEGER NOT NULL,
    delivery_fee    INTEGER NOT NULL,
    total           INTEGER NOT NULL,
    status          TEXT NOT NULL DEFAULT 'new',
    history         TEXT NOT NULL DEFAULT '{}', -- JSON {status: "HH:MM"}
    created_at      TEXT NOT NULL,             -- local shop time, YYYY-MM-DD HH:MM:SS
    updated_at      TEXT NOT NULL,
    owner_msg_id    INTEGER,
    owner_msg_kind  TEXT,                      -- 'text', 'photo' or 'document'
    cust_widget_msg_id INTEGER
);

CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);      -- owner's changes, scheduler marks
CREATE TABLE IF NOT EXISTS closed_days (day TEXT PRIMARY KEY);                -- YYYY-MM-DD, no orders
CREATE TABLE IF NOT EXISTS sold_out (product_id TEXT PRIMARY KEY);            -- hidden from ordering
CREATE TABLE IF NOT EXISTS broadcasts (                                        -- promotions sent by the owner
    id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL, has_photo INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL, recipients INTEGER NOT NULL DEFAULT 0, sent INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS orders_created ON orders(created_at);
CREATE INDEX IF NOT EXISTS orders_due ON orders(delivery_date);
CREATE INDEX IF NOT EXISTS orders_user ON orders(user_id);
"""


class DB:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)
        self._add_columns("users", {"phone": "TEXT", "promos": "INTEGER NOT NULL DEFAULT 1"})
        self._add_columns("orders", {
            "payment_status": "TEXT NOT NULL DEFAULT 'none'",  # none | due | review | paid
            "deposit": "INTEGER NOT NULL DEFAULT 0",          # amount asked in advance
            "paid": "INTEGER NOT NULL DEFAULT 0",             # amount confirmed by the owner
            "receipt_file_id": "TEXT",                        # customer's transfer screenshot
            "ready_photo_id": "TEXT",                         # photo of the finished cake
            "courier": "TEXT",
            "reminded": "INTEGER NOT NULL DEFAULT 0",
            "gift": "TEXT",                                   # JSON: recipient name/phone, card note, surprise
            "rating": "INTEGER",                              # 1-5 stars after delivery
            "review": "TEXT",
            "in_gallery": "INTEGER NOT NULL DEFAULT 1",       # finished-cake photo shown in "Our works"
        })
        self.conn.commit()

    def _add_columns(self, table: str, columns: dict[str, str]) -> None:
        """Upgrade an older database in place."""
        have = {r["name"] for r in self.conn.execute(f"PRAGMA table_info({table})")}
        for name, ddl in columns.items():
            if name not in have:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")

    # ---------- settings, days off, sold out ----------
    def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.conn.execute("INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                          (key, value))
        self.conn.commit()

    def closed_days(self) -> set[str]:
        return {r["day"] for r in self.conn.execute("SELECT day FROM closed_days")}

    def set_closed(self, day: str, closed: bool) -> None:
        if closed:
            self.conn.execute("INSERT OR IGNORE INTO closed_days(day) VALUES (?)", (day,))
        else:
            self.conn.execute("DELETE FROM closed_days WHERE day=?", (day,))
        self.conn.commit()

    def sold_out(self) -> set[str]:
        return {r["product_id"] for r in self.conn.execute("SELECT product_id FROM sold_out")}

    def set_sold_out(self, product_id: str, sold_out: bool) -> None:
        if sold_out:
            self.conn.execute("INSERT OR IGNORE INTO sold_out(product_id) VALUES (?)", (product_id,))
        else:
            self.conn.execute("DELETE FROM sold_out WHERE product_id=?", (product_id,))
        self.conn.commit()

    # ---------- promotions ----------
    def set_promos(self, user_id: int, on: bool) -> None:
        self.conn.execute("UPDATE users SET promos=? WHERE user_id=?", (1 if on else 0, user_id))
        self.conn.commit()

    def promo_recipients(self) -> list[int]:
        return [r["user_id"] for r in self.conn.execute("SELECT user_id FROM users WHERE promos=1 ORDER BY user_id")]

    def add_broadcast(self, text: str, has_photo: bool, created_at: str, recipients: int) -> int:
        cur = self.conn.execute("INSERT INTO broadcasts(text, has_photo, created_at, recipients) VALUES (?, ?, ?, ?)",
                                (text, int(has_photo), created_at, recipients))
        self.conn.commit()
        return cur.lastrowid

    def finish_broadcast(self, bid: int, sent: int) -> None:
        self.conn.execute("UPDATE broadcasts SET sent=? WHERE id=?", (sent, bid))
        self.conn.commit()

    def broadcasts(self, limit: int = 5) -> list[dict]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM broadcasts ORDER BY id DESC LIMIT ?", (limit,))]

    # ---------- reviews and gallery ----------
    def gallery(self, limit: int = 12) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM orders WHERE status='delivered' AND ready_photo_id IS NOT NULL AND in_gallery=1 "
            "AND (rating IS NULL OR rating >= 4) ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [_order(r) for r in rows]

    def product_ratings(self) -> dict[str, tuple[float, int]]:
        rows = self.conn.execute("SELECT product_id, AVG(rating) AS a, COUNT(*) AS n FROM orders "
                                 "WHERE rating IS NOT NULL GROUP BY product_id")
        return {r["product_id"]: (round(r["a"], 1), r["n"]) for r in rows}

    def booked_per_day(self, first: str, last: str) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT delivery_date AS d, COUNT(*) AS n FROM orders WHERE delivery_date BETWEEN ? AND ? "
            "AND status!='rejected' GROUP BY delivery_date", (first, last))
        return {r["d"]: r["n"] for r in rows}

    # ---------- users ----------
    def touch_user(self, user_id: int, first_name: str | None, username: str | None) -> None:
        self.conn.execute(
            "INSERT INTO users(user_id, first_name, username) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET first_name=excluded.first_name, username=excluded.username",
            (user_id, first_name, username),
        )
        self.conn.commit()

    def set_lang(self, user_id: int, lang: str) -> None:
        self.conn.execute(
            "INSERT INTO users(user_id, lang) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang",
            (user_id, lang),
        )
        self.conn.commit()

    def get_lang(self, user_id: int) -> str | None:
        row = self.conn.execute("SELECT lang FROM users WHERE user_id=?", (user_id,)).fetchone()
        return row["lang"] if row else None

    def set_widget_ok(self, user_id: int) -> None:
        self.conn.execute(
            "INSERT INTO users(user_id, widget_ok) VALUES (?, 1) ON CONFLICT(user_id) DO UPDATE SET widget_ok=1",
            (user_id,),
        )
        self.conn.commit()

    def set_phone(self, user_id: int, phone: str) -> None:
        self.conn.execute(
            "INSERT INTO users(user_id, phone) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET phone=excluded.phone",
            (user_id, phone),
        )
        self.conn.commit()

    def get_phone(self, user_id: int) -> str | None:
        row = self.conn.execute("SELECT phone FROM users WHERE user_id=?", (user_id,)).fetchone()
        return row["phone"] if row else None

    def widget_ok(self, user_id: int) -> bool:
        row = self.conn.execute("SELECT widget_ok FROM users WHERE user_id=?", (user_id,)).fetchone()
        return bool(row and row["widget_ok"])

    # ---------- orders ----------
    def create_order(self, fields: dict) -> dict:
        fields = dict(fields)
        fields["names"] = json.dumps(fields["names"], ensure_ascii=False)
        if fields.get("gift") is not None:
            fields["gift"] = json.dumps(fields["gift"], ensure_ascii=False)
        fields["history"] = json.dumps(fields.get("history", {}))
        cols = ", ".join(fields)
        marks = ", ".join("?" for _ in fields)
        cur = self.conn.execute(f"INSERT INTO orders({cols}) VALUES ({marks})", tuple(fields.values()))
        order_id = cur.lastrowid
        self.conn.execute("UPDATE orders SET num=? WHERE id=?", (order_id + ORDER_NUM_OFFSET, order_id))
        self.conn.commit()
        return self.get_order(order_id + ORDER_NUM_OFFSET)

    def get_order(self, num: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM orders WHERE num=?", (num,)).fetchone()
        return _order(row) if row else None

    def update_order(self, num: int, **fields) -> dict:
        if "history" in fields:
            fields["history"] = json.dumps(fields["history"])
        sets = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(f"UPDATE orders SET {sets} WHERE num=?", (*fields.values(), num))
        self.conn.commit()
        return self.get_order(num)

    def orders_created_on(self, day: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM orders WHERE substr(created_at, 1, 10)=? ORDER BY id", (day,)
        ).fetchall()
        return [_order(r) for r in rows]

    def orders_due_on(self, day: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM orders WHERE delivery_date=? AND status!='rejected' ORDER BY time_slot, id", (day,)
        ).fetchall()
        return [_order(r) for r in rows]

    def orders_between(self, first: str, last: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM orders WHERE delivery_date BETWEEN ? AND ? ORDER BY delivery_date, time_slot, id", (first, last)
        ).fetchall()
        return [_order(r) for r in rows]

    def orders_with_status(self, *statuses: str) -> list[dict]:
        marks = ", ".join("?" for _ in statuses)
        rows = self.conn.execute(f"SELECT * FROM orders WHERE status IN ({marks}) ORDER BY id", statuses).fetchall()
        return [_order(r) for r in rows]

    def payment_due(self, user_id: int) -> dict | None:
        """The customer's latest order still waiting for a deposit receipt."""
        row = self.conn.execute(
            "SELECT * FROM orders WHERE user_id=? AND payment_status='due' AND status NOT IN ('rejected','delivered') "
            "ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
        return _order(row) if row else None

    def user_orders(self, user_id: int, limit: int = 5) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit)
        ).fetchall()
        return [_order(r) for r in rows]


def _order(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["names"] = json.loads(d["names"])
    d["history"] = json.loads(d["history"] or "{}")
    d["gift"] = json.loads(d["gift"]) if d.get("gift") else None
    return d
