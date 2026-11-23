"""Loads and checks catalog.yaml, so a typo produces a clear error on start
instead of a broken button in front of a customer."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .config import ROOT
from .texts import LANGS, money, plural_people

log = logging.getLogger(__name__)

ID_RE = re.compile(r"^[a-z0-9_-]{1,24}$")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class CatalogError(Exception):
    pass


@dataclass(frozen=True)
class Size:
    id: str
    name: dict[str, str]
    price: int


@dataclass(frozen=True)
class Filling:
    id: str
    name: dict[str, str]
    extra: int = 0


@dataclass(frozen=True)
class Category:
    id: str
    emoji: str
    name: dict[str, str]
    short: dict[str, str]


@dataclass(frozen=True)
class Product:
    id: str
    category: str
    name: dict[str, str]
    description: dict[str, str]
    photo: Path | None
    emoji: str
    color: str
    sizes: list[Size]
    fillings: list[Filling]
    inscription: bool
    reference_photo: bool
    lead_days: int
    price_per_kg: int | None = None
    featured: bool = False

    def size(self, size_id: str | None) -> Size | None:
        return next((s for s in self.sizes if s.id == size_id), None)

    def filling(self, filling_id: str | None) -> Filling | None:
        return next((f for f in self.fillings if f.id == filling_id), None)

    def price_label(self, lang: str) -> str:
        """Short price for cards and buttons: '190 000 so'm/kg' or 'from 145 000 so'm'."""
        if self.price_per_kg:
            return money(self.price_per_kg, lang) + ("/kg" if lang == "uz" else "/кг")
        low = min(s.price for s in self.sizes)
        if len(self.sizes) == 1:
            return money(low, lang)
        return (money(low, lang) + "dan") if lang == "uz" else ("от " + money(low, lang))


@dataclass(frozen=True)
class Shop:
    name: str
    tagline: dict[str, str]
    order_prefix: str
    phone: str
    pickup_address: dict[str, str]
    delivery_fee: int
    free_delivery_from: int
    min_lead_days: int
    booking_days: int
    time_slots: list[str]
    timezone: str
    card_number: str = ""          # where customers transfer the deposit
    card_holder: str = ""
    deposit_percent: int = 0       # 0 = everything is paid on delivery
    daily_capacity: int = 0        # max orders per delivery day, 0 = unlimited
    reminder_time: str = "18:00"   # customer reminder, the day before delivery
    summary_time: str = "08:00"    # owner's morning summary


@dataclass
class Catalog:
    shop: Shop
    categories: list[Category]
    products: dict[str, Product] = field(default_factory=dict)

    def category(self, cat_id: str) -> Category | None:
        return next((c for c in self.categories if c.id == cat_id), None)

    def in_category(self, cat_id: str) -> list[Product]:
        return [p for p in self.products.values() if p.category == cat_id]


def _texts(obj, where: str) -> dict[str, str]:
    if not isinstance(obj, dict):
        raise CatalogError(f"{where}: expected {{ uz: ..., ru: ... }}")
    out = {}
    for lang in LANGS:
        val = obj.get(lang)
        if not isinstance(val, str) or not val.strip():
            raise CatalogError(f"{where}: missing the '{lang}' text")
        out[lang] = val.strip()
    return out


def _check_id(value, where: str) -> str:
    if not isinstance(value, str) or not ID_RE.match(value):
        raise CatalogError(
            f"{where}: id {value!r} must be 1-24 chars of lowercase latin letters, digits, _ or -"
        )
    return value


def _int(value, where: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise CatalogError(f"{where}: expected a whole number >= {minimum}, got {value!r}")
    return value


def _hhmm(value, where: str) -> str:
    text = str(value)
    if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", text):
        raise CatalogError(f"{where}: use HH:MM, e.g. 08:00 (in quotes)")
    return text


def _weight_sizes(p: dict, where: str) -> list[Size]:
    per_kg = _int(p["price_per_kg"], f"{where}.price_per_kg", 1)
    weights = p.get("weights_kg")
    if not isinstance(weights, list) or not weights:
        raise CatalogError(f"{where}: price_per_kg needs a weights_kg list, e.g. [1.5, 2, 3]")
    sizes = []
    for w in weights:
        if not isinstance(w, (int, float)) or w <= 0:
            raise CatalogError(f"{where}.weights_kg: {w!r} is not a positive number")
        kg_uz = f"{w:g}".replace(".", ",")
        people = max(1, round(w * 5))
        sizes.append(
            Size(
                id=f"w{w:g}",
                name={
                    "uz": f"{kg_uz} kg · ~{people} kishi",
                    "ru": f"{kg_uz} кг · ~{people} {plural_people(people)}",
                },
                price=int(round(per_kg * w / 1000.0)) * 1000,
            )
        )
    return sizes


def load_catalog(path: Path) -> Catalog:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise CatalogError(f"catalog file not found: {path}")
    except yaml.YAMLError as e:
        raise CatalogError(f"{path.name} is not valid YAML: {e}")
    if not isinstance(raw, dict):
        raise CatalogError(f"{path.name} is empty or malformed")

    s = raw.get("shop") or {}
    try:
        slots = [str(x) for x in s["time_slots"]]
        shop = Shop(
            name=str(s["name"]),
            tagline=_texts(s["tagline"], "shop.tagline") if s.get("tagline") else {"uz": "", "ru": ""},
            order_prefix=str(s.get("order_prefix", "ORD")),
            phone=str(s["phone"]),
            pickup_address=_texts(s["pickup_address"], "shop.pickup_address"),
            delivery_fee=_int(s.get("delivery_fee", 0), "shop.delivery_fee"),
            free_delivery_from=_int(s.get("free_delivery_from", 0), "shop.free_delivery_from"),
            min_lead_days=_int(s.get("min_lead_days", 1), "shop.min_lead_days"),
            booking_days=_int(s.get("booking_days", 7), "shop.booking_days", 1),
            time_slots=slots,
            timezone=str(s.get("timezone", "Asia/Tashkent")),
            card_number=str((s.get("payment") or {}).get("card_number", "")),
            card_holder=str((s.get("payment") or {}).get("card_holder", "")),
            deposit_percent=_int((s.get("payment") or {}).get("deposit_percent", 0), "shop.payment.deposit_percent"),
            daily_capacity=_int(s.get("daily_capacity", 0), "shop.daily_capacity"),
            reminder_time=_hhmm(s.get("reminder_time", "18:00"), "shop.reminder_time"),
            summary_time=_hhmm(s.get("morning_summary_time", "08:00"), "shop.morning_summary_time"),
        )
    except KeyError as e:
        raise CatalogError(f"shop: missing field {e}")
    if not shop.time_slots:
        raise CatalogError("shop.time_slots: add at least one time slot")
    if shop.deposit_percent > 100:
        raise CatalogError("shop.payment.deposit_percent: 0-100")
    if shop.deposit_percent and not shop.card_number:
        raise CatalogError("shop.payment: a deposit needs card_number")

    categories = []
    for i, c in enumerate(raw.get("categories") or []):
        where = f"categories[{i}]"
        name = _texts(c.get("name"), f"{where}.name")
        categories.append(
            Category(
                id=_check_id(c.get("id"), where),
                emoji=str(c.get("emoji", "")),
                name=name,
                short=_texts(c["short"], f"{where}.short") if c.get("short") else name,
            )
        )
    if not categories:
        raise CatalogError("categories: add at least one category")
    cat_ids = {c.id for c in categories}

    filling_lists: dict[str, list[Filling]] = {}
    for list_name, items in (raw.get("fillings") or {}).items():
        filling_lists[list_name] = [
            Filling(
                id=_check_id(f.get("id"), f"fillings.{list_name}[{j}]"),
                name=_texts(f.get("name"), f"fillings.{list_name}[{j}].name"),
                extra=_int(f.get("extra", 0), f"fillings.{list_name}[{j}].extra"),
            )
            for j, f in enumerate(items or [])
        ]

    catalog = Catalog(shop=shop, categories=categories)
    for i, p in enumerate(raw.get("products") or []):
        pid = _check_id(p.get("id"), f"products[{i}]")
        where = f"product '{pid}'"
        if pid in catalog.products:
            raise CatalogError(f"{where}: duplicate id")
        if p.get("category") not in cat_ids:
            raise CatalogError(f"{where}: category {p.get('category')!r} is not in categories")

        if "price_per_kg" in p:
            sizes = _weight_sizes(p, where)
        elif p.get("sizes"):
            sizes = [
                Size(
                    id=_check_id(sz.get("id"), f"{where}.sizes[{j}]"),
                    name=_texts(sz.get("name"), f"{where}.sizes[{j}].name"),
                    price=_int(sz.get("price"), f"{where}.sizes[{j}].price", 1),
                )
                for j, sz in enumerate(p["sizes"])
            ]
        else:
            raise CatalogError(f"{where}: needs either price_per_kg + weights_kg, or sizes")

        fillings: list[Filling] = []
        if p.get("fillings"):
            if p["fillings"] not in filling_lists:
                raise CatalogError(f"{where}: fillings list {p['fillings']!r} is not defined")
            fillings = filling_lists[p["fillings"]]

        photo = None
        if p.get("photo"):
            photo = Path(p["photo"])
            photo = photo if photo.is_absolute() else ROOT / photo
            if not photo.is_file():
                log.warning("%s: photo %s not found, the product will be shown without it", where, photo)
                photo = None

        color = str(p.get("color", "#f4a7c3"))
        if not HEX_RE.match(color):
            raise CatalogError(f"{where}: color must look like #f4a7c3")

        cat = next(c for c in categories if c.id == p["category"])
        catalog.products[pid] = Product(
            id=pid,
            category=p["category"],
            name=_texts(p.get("name"), f"{where}.name"),
            description=_texts(p.get("description"), f"{where}.description"),
            photo=photo,
            emoji=str(p.get("emoji") or cat.emoji or "🍰"),
            color=color,
            sizes=sizes,
            fillings=fillings,
            inscription=bool(p.get("inscription", False)),
            reference_photo=bool(p.get("reference_photo", False)),
            lead_days=_int(p.get("lead_days", shop.min_lead_days), f"{where}.lead_days"),
            price_per_kg=p.get("price_per_kg"),
            featured=bool(p.get("featured", False)),
        )

    if not catalog.products:
        raise CatalogError("products: add at least one product")
    return catalog
