"""Connects Telegram updates to the bot's features."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import date

import httpx
from telegram import (
    Bot,
    BotCommand,
    BotCommandScopeChat,
    BotCommandScopeDefault,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonCommands,
    MenuButtonWebApp,
    Update,
    WebAppInfo,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, Conflict, NetworkError, TelegramError, TimedOut
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    TypeHandler,
    filters,
)

from . import flow, keyboards, ops, owner, scheduler
from .files import FileStore
from .services import Services, svc
from .texts import all_langs, esc, fmt_date, t
from .webapp.server import MiniAppServer
from .webapp.tunnel import Tunnel

log = logging.getLogger(__name__)
HTML = ParseMode.HTML

# The Bot API keeps the previous allowed_updates if none are passed, so the
# widget update types are listed explicitly (the widget guide asks for both).
ALLOWED_UPDATES = ["message", "callback_query", "widget_query", "shared_widget_query"]

# Widget-capable apps run the catalog's script as soon as it is on screen, and
# its first line pings the bot. No ping within this time = the app could not
# show the widget, so the customer gets the simple menu.
WIDGET_CHECK_SECONDS = 12


# ---------------------------------------------------------------- catalog / menus

async def send_catalog(s: Services, bot: Bot, user_id: int, lang: str) -> None:
    """The catalog entry point: the Mini App when it is running, else an HTML
    widget (if WIDGETS=on), else the simple button menu."""
    if s.webapp_url:
        await bot.send_message(user_id, t(lang, "app_intro"), reply_markup=keyboards.open_app(lang, s.webapp_url))
        return
    html = s.widgets.catalog_html.get(lang)
    if not (s.widgets.enabled and html):
        return await send_simple_menu(s, bot, user_id, lang)
    try:
        await s.widgets.send(
            bot, user_id, html,
            caption=t(lang, "catalog_caption", shop=esc(s.catalog.shop.name)),
            allow_queries=True,
            reply_markup=keyboards.open_simple_menu(lang),
        )
    except TelegramError as e:
        log.warning("sendWidget failed for %s (%s); falling back to the simple menu", user_id, e)
        return await send_simple_menu(s, bot, user_id, lang)
    if not s.db.widget_ok(user_id):
        schedule_widget_check(s, bot, user_id, lang)


def schedule_widget_check(s: Services, bot: Bot, user_id: int, lang: str) -> None:
    old = s.widget_checks.pop(user_id, None)
    if old:
        old.cancel()

    async def check() -> None:
        try:
            await asyncio.sleep(WIDGET_CHECK_SECONDS)
            if not s.db.widget_ok(user_id):
                log.info("No widget ping from %s: this app likely cannot show widgets, sending the simple menu", user_id)
                await send_simple_menu(s, bot, user_id, lang, intro="widget_fallback")
        except TelegramError as e:
            log.warning("Fallback menu not sent to %s: %s", user_id, e)
        finally:
            if s.widget_checks.get(user_id) is asyncio.current_task():
                s.widget_checks.pop(user_id, None)

    s.widget_checks[user_id] = asyncio.get_running_loop().create_task(check())


def widget_seen(s: Services, user_id: int) -> None:
    """The customer's app ran one of our widgets."""
    if not s.db.widget_ok(user_id):
        s.db.set_widget_ok(user_id)
        log.info("Widgets work for %s", user_id)
    task = s.widget_checks.pop(user_id, None)
    if task:
        task.cancel()


async def send_simple_menu(s: Services, bot: Bot, user_id: int, lang: str, intro: str = "simple_title") -> None:
    await bot.send_message(user_id, t(lang, intro), reply_markup=keyboards.categories(s.catalog, lang))


async def safe_edit(q, text: str, markup) -> None:
    try:
        await q.edit_message_text(text, parse_mode=HTML, reply_markup=markup)
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            raise


async def my_orders(s: Services, bot: Bot, user_id: int, lang: str) -> None:
    orders = s.db.user_orders(user_id)
    if not orders:
        return await bot.send_message(user_id, t(lang, "my_orders_empty"), reply_markup=keyboards.main_menu(lang))
    lines = [t(lang, "my_orders_title"), ""]
    for o in orders:
        names = o["names"][lang]
        when = fmt_date(date.fromisoformat(o["delivery_date"]), lang, weekday=False)
        lines.append(f"• <b>#{s.order_code(o['num'])}</b> · {esc(names['product'])} ({esc(names['size'])}) · "
                     f"{when} · {t(lang, 'st_' + o['status'])}")
    await bot.send_message(user_id, "\n".join(lines), parse_mode=HTML, reply_markup=keyboards.main_menu(lang))


# ---------------------------------------------------------------- commands

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s, u = svc(context), update.effective_user
    s.db.touch_user(u.id, u.first_name, u.username)
    await update.message.reply_text(t("uz", "choose_lang", shop=esc(s.catalog.shop.name)),
                                    parse_mode=HTML, reply_markup=keyboards.lang_choice())


async def cmd_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s, u = svc(context), update.effective_user
    await send_catalog(s, context.bot, u.id, s.lang_of(u))


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s, u = svc(context), update.effective_user
    await send_simple_menu(s, context.bot, u.id, s.lang_of(u))


async def cmd_myorders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s, u = svc(context), update.effective_user
    await my_orders(s, context.bot, u.id, s.lang_of(u))


async def cmd_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s, u = svc(context), update.effective_user
    if u.id != s.cfg.owner_id:
        return await update.message.reply_text(t(s.lang_of(u), "o_only_owner"))
    await owner.send_summary(s, context.bot, s.now().date(), "day", chat_id=u.id)


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s, u = svc(context), update.effective_user
    if u.id != s.cfg.owner_id:
        return await update.message.reply_text(t(s.lang_of(u), "o_only_owner"))
    lang, url = s.cfg.owner_lang, owner.dashboard_url(s)
    if not url:
        return await update.message.reply_text(t(lang, "o_no_app"))
    await update.message.reply_text(t(lang, "o_dashboard_text"), reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton(t(lang, "o_btn_dashboard"), web_app=WebAppInfo(url))]]))


async def cmd_open_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s, u = svc(context), update.effective_user
    if u.id != s.cfg.owner_id:
        return await update.message.reply_text(t(s.lang_of(u), "o_only_owner"))
    num = int(re.match(r"^/o(\d+)", update.message.text).group(1))
    await owner.open_order(s, context.bot, num)


# ---------------------------------------------------------------- buttons

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s, q, bot = svc(context), update.callback_query, context.bot
    user, data = q.from_user, q.data or ""
    lang = s.lang_of(user)

    if data.startswith("lang:") and data[5:] in ("uz", "ru"):
        lang = data[5:]
        s.db.touch_user(user.id, user.first_name, user.username)
        s.db.set_lang(user.id, lang)
        if user.id in s.drafts:
            s.drafts[user.id].lang = lang
        await q.answer(t(lang, "lang_set"))
        try:
            await q.edit_message_reply_markup(None)
        except BadRequest:
            pass
        await bot.send_message(user.id, t(lang, "welcome"), reply_markup=keyboards.main_menu(lang))
        return await send_catalog(s, bot, user.id, lang)

    if data == "menu":
        await q.answer()
        return await send_simple_menu(s, bot, user.id, lang)
    if data == "cats":
        await q.answer()
        return await safe_edit(q, t(lang, "simple_title"), keyboards.categories(s.catalog, lang))
    if data.startswith("cat:"):
        cat = s.catalog.category(data[4:])
        if not cat:
            return await q.answer(t(lang, "stale"))
        await q.answer()
        return await safe_edit(q, t(lang, "simple_cat", emoji=cat.emoji, cat=esc(cat.name[lang])),
                               keyboards.products(s.catalog, cat.id, lang, s.db.sold_out()))
    if data.startswith("prod:"):
        product = s.product(data[5:])
        if not product:
            return await q.answer(t(lang, "stale"))
        await q.answer()
        return await flow.start_order(s, bot, user.id, product, user.full_name, user.username)
    if data.startswith("f:"):
        parts = data.split(":", 3)
        if len(parts) == 4:
            return await flow.on_callback(s, bot, q, parts[1], parts[2], parts[3])
    if data.startswith("own:"):
        parts = data.split(":")
        if len(parts) == 3 and parts[2].isdigit():
            return await owner.on_callback(s, bot, q, parts[1], int(parts[2]))
    await q.answer()


# ---------------------------------------------------------------- messages

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s, msg, u = svc(context), update.message, update.effective_user
    lang, text, bot = s.lang_of(u), (update.message.text or "").strip(), context.bot
    if u.id == s.cfg.owner_id and await owner.owner_input(s, bot, msg):  # courier name for an order
        return
    if text in all_langs("btn_catalog"):
        return await send_catalog(s, bot, u.id, lang)
    if text in all_langs("btn_simple"):
        return await send_simple_menu(s, bot, u.id, lang)
    if text in all_langs("btn_my_orders"):
        return await my_orders(s, bot, u.id, lang)
    if text in all_langs("btn_lang"):
        return await msg.reply_text(t(lang, "pick_lang"), reply_markup=keyboards.lang_choice())
    draft = s.drafts.get(u.id)
    if draft:
        return await flow.on_text(s, bot, msg, draft)
    await msg.reply_text(t(lang, "idle"), reply_markup=keyboards.main_menu(lang))


async def _with_draft(update: Update, context: ContextTypes.DEFAULT_TYPE, handler) -> None:
    s, u = svc(context), update.effective_user
    draft = s.drafts.get(u.id)
    if draft:
        return await handler(s, context.bot, update.message, draft)
    lang = s.lang_of(u)
    await update.message.reply_text(t(lang, "idle"), reply_markup=keyboards.main_menu(lang))


async def on_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s, u, contact = svc(context), update.effective_user, update.message.contact
    draft = s.drafts.get(u.id)
    if draft and draft.step == "phone":
        return await flow.on_contact(s, context.bot, update.message, draft)
    # Shared from the Mini App (requestContact): keep it quietly, the app picks it up via /api/phone.
    if contact.user_id in (None, u.id):
        phone = flow.normalize_phone(contact.phone_number, from_contact=True)
        if phone:
            s.db.set_phone(u.id, phone)
            return
    await _with_draft(update, context, flow.on_contact)


async def on_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _with_draft(update, context, flow.on_location)


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """A photo is, in this order: the owner's finished-cake photo, a reference photo in the
    order form, or a customer's deposit receipt."""
    s, msg, u, bot = svc(context), update.message, update.effective_user, context.bot
    if u.id == s.cfg.owner_id and await owner.owner_input(s, bot, msg):
        return
    draft = s.drafts.get(u.id)
    if draft and draft.step == "photo":
        return await flow.on_photo(s, bot, msg, draft)
    due = s.db.payment_due(u.id)
    if due:
        kind = "photo" if msg.photo else "document"
        file_id = msg.photo[-1].file_id if msg.photo else msg.document.file_id
        try:
            await ops.submit_receipt(s, bot, due, file_id=file_id, kind=kind)
        except TelegramError as e:
            log.error("Receipt for %s not forwarded to the owner: %s", s.order_code(due["num"]), e)
        return await msg.reply_text(t(s.lang_of(u), "receipt_got"))
    await _with_draft(update, context, flow.on_photo)


# ---------------------------------------------------------------- widget queries

def _update_field(update: Update, name: str) -> dict | None:
    """python-telegram-bot 22.8 predates widgets and keeps unknown update
    fields in api_kwargs. A future version may parse them into objects."""
    value = (update.api_kwargs or {}).get(name) or getattr(update, name, None)
    if value is not None and not isinstance(value, dict):
        value = value.to_dict()
    return value


async def on_widget_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    wq = _update_field(update, "widget_query")
    shared = _update_field(update, "shared_widget_query")
    if not wq and not shared:
        return  # an ordinary update: the normal handlers take it
    s, bot = svc(context), context.bot

    if shared:  # this bot sends no shared widgets; answer anyway so a widget never waits
        await _answer(s, bot, shared["id"], None)
        raise ApplicationHandlerStop

    user, data = wq["from"], wq.get("data") or ""
    widget_seen(s, user["id"])

    if data == "hi":  # the catalog's ping on load
        await _answer(s, bot, wq["id"], "ok")
    elif data.startswith("p:"):
        product = s.product(data[2:])
        if not product:
            await _answer(s, bot, wq["id"], "gone")
        else:
            # answer first (15 s limit), then do the slower work
            await _answer(s, bot, wq["id"], "ok")
            s.db.touch_user(user["id"], user.get("first_name"), user.get("username"))
            name = " ".join(x for x in (user.get("first_name"), user.get("last_name")) if x)
            await flow.start_order(s, bot, user["id"], product, name, user.get("username"))
    else:
        await _answer(s, bot, wq["id"], "bad")
    raise ApplicationHandlerStop


async def _answer(s: Services, bot: Bot, query_id: str, data: str | None) -> None:
    try:
        await s.widgets.answer(bot, query_id, data)
    except TelegramError as e:
        log.warning("answerWidgetQuery failed: %s", e)


# ---------------------------------------------------------------- lifecycle

async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    err = context.error
    if isinstance(err, Conflict):
        log.error("Another copy of this bot is running (Telegram allows only one). Stop the other copy.")
    elif isinstance(err, (NetworkError, TimedOut)):
        log.warning("Network problem talking to Telegram (%s); retrying", err)
    else:
        log.error("Error while handling an update", exc_info=err)


async def post_init(app: Application) -> None:
    s: Services = app.bot_data["svc"]
    me = await app.bot.get_me()
    commands = {
        lang: [BotCommand(c, t(lang, "cmd_" + c)) for c in ("start", "catalog", "menu", "myorders")]
        for lang in ("uz", "ru")
    }
    try:
        await app.bot.set_my_commands(commands["uz"], scope=BotCommandScopeDefault())
        await app.bot.set_my_commands(commands["ru"], scope=BotCommandScopeDefault(), language_code="ru")
    except TelegramError as e:
        log.warning("Could not set the command menu: %s", e)
    try:
        lang = s.cfg.owner_lang
        await app.bot.set_my_commands(commands[lang] + [BotCommand("orders", t(lang, "cmd_orders")),
                                                        BotCommand("admin", t(lang, "cmd_admin"))],
                                      scope=BotCommandScopeChat(s.cfg.owner_id))
    except TelegramError as e:
        log.warning("Owner command menu not set (%s). Open the bot from the owner account and press /start.", e)

    s.files = FileStore(s.cfg.db_path.parent / "files", app.bot, s.cfg.token)
    await start_mini_app(s, app.bot)
    s.background.append(asyncio.get_running_loop().create_task(scheduler.run(s, app.bot)))

    mini_app = s.webapp_url or "off (simple menu only, see the warning above)"
    log.info("Bot @%s is running: https://t.me/%s  | owner id %s | Mini App %s | Ctrl+C to stop",
             me.username, me.username, s.cfg.owner_id, mini_app)


async def start_mini_app(s: Services, bot: Bot) -> None:
    """Serve the Mini App locally, give it a public https address, and put it on the bot's menu button."""
    s.webapp = MiniAppServer(s, bot)
    try:
        await s.webapp.start(s.cfg.webapp_port)
    except OSError as e:
        log.error("Mini App server could not start on port %s (%s). Set WEBAPP_PORT in .env to a free port.",
                  s.cfg.webapp_port, e)
        s.webapp = None
        return await _reset_menu_button(bot, s)

    log.info("Browser preview (no Telegram needed): http://127.0.0.1:%s/?demo=1", s.cfg.webapp_port)
    s.spawn(s.webapp.warm_up())

    async def use_url(url: str) -> None:
        s.webapp_url = url.rstrip("/") + "/"
        if await _reachable(s.webapp_url, s.webapp.health_token):
            log.info("Mini App is online at %s", s.webapp_url)
        else:
            log.warning("Mini App address %s does not answer yet; it usually does within a minute", s.webapp_url)
        try:
            await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(t("uz", "menu_button"), WebAppInfo(s.webapp_url)))
        except TelegramError as e:
            log.warning("Menu button not set: %s", e)

    url = s.cfg.webapp_url
    if not url and s.cfg.tunnel:
        s.tunnel = Tunnel(s.cfg.webapp_port, on_url=use_url)
        url = await s.tunnel.start()
    if not url:
        return await _reset_menu_button(bot, s)
    await use_url(url)


async def _reset_menu_button(bot: Bot, s: Services | None = None) -> None:
    """No live Mini App: point the menu button at the static showcase if there is one
    (it works even with this laptop off), else remove it."""
    url = s.cfg.showcase_url if s else None
    button = MenuButtonWebApp(t("uz", "menu_button"), WebAppInfo(url)) if url else MenuButtonCommands()
    try:
        await bot.set_chat_menu_button(menu_button=button)
        if url:
            log.info("Menu button now opens the showcase: %s", url)
    except TelegramError as e:
        log.warning("Menu button not changed: %s", e)


async def _reachable(url: str, token: str, tries: int = 10) -> bool:
    """True only if the address really leads to this bot's Mini App server."""
    async with httpx.AsyncClient(timeout=5) as client:
        for _ in range(tries):
            try:
                r = await client.get(url + "health")
                if r.status_code == 200 and r.text == token:
                    return True
            except httpx.HTTPError:
                pass
            await asyncio.sleep(2)
    return False


async def post_stop(app: Application) -> None:
    s: Services = app.bot_data["svc"]
    for task in s.widget_checks.values():
        task.cancel()
    s.widget_checks.clear()
    for task in s.background:
        task.cancel()
    if s.tasks:  # let messages that are on their way finish (Ctrl+C right after an order)
        await asyncio.wait(list(s.tasks), timeout=15)
    if s.tunnel:
        await s.tunnel.stop()
    if s.webapp:
        await s.webapp.stop()
    if s.cfg.showcase_url:  # the live app is going away: clients keep the showcase
        await _reset_menu_button(app.bot, s)


def register(app: Application) -> None:
    app.add_handler(TypeHandler(Update, on_widget_update), group=-1)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("catalog", cmd_catalog))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("myorders", cmd_myorders))
    app.add_handler(CommandHandler("orders", cmd_orders))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(MessageHandler(filters.Regex(r"^/o\d+(@\w+)?$"), cmd_open_order))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.CONTACT, on_contact))
    app.add_handler(MessageHandler(filters.LOCATION, on_location))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)
