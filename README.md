# Shirin Tortlar: demo Telegram ordering bot

A complete ordering system for a home bakery, inside Telegram. It's a demo for a fictional
Tashkent bakery, built so it can be rebuilt for a real client in under an hour.

**For the customer** (iOS-style Mini App, Uzbek and Russian):
catalog with real photos → cake options (weight, filling, inscription, reference photo) → date
and time → delivery or pickup → review → order. Then they follow the order live:
*accepted → baking → decorating → ready (with a photo of their cake) → on the way (courier) →
delivered*, and pay the deposit by card transfer with a receipt screenshot.

**Also:** the bakery's own logo and color, **gift orders** (recipient, card text, "surprise"),
**ratings and reviews** after delivery with an **"Our works" gallery** of finished cakes, and
**promotions** the owner sends to all customers, with an unsubscribe button.

**For the owner** (chat buttons and a dashboard Mini App): each order arrives as one complete
card with stage buttons. There's a receipt check, a dashboard (today / tomorrow / 7 days with
revenue), a calendar with days off, sold-out switches, a daily order limit, a morning summary,
and automatic customer reminders the day before.

Everything runs on your laptop: long polling for the bot, plus a free tunnel so Telegram can open
the Mini App. No server, no domain, no account. Orders are kept in SQLite (`data/bakery.db`),
and the catalog lives in one file (`catalog.yaml`).

---

## 1. Install (openSUSE Tumbleweed)

Use your **system terminal (Konsole)**. VS Code installed from Flathub runs in a sandbox: its
built-in terminal has no `sudo` and can't install system packages.

```bash
sudo zypper refresh
sudo zypper install python3 python3-pip cloudflared   # cloudflared is optional, see "How it works"

python3 --version          # 3.10 or newer

cd ~/"Documents/paid works/bakery demo bot"
python3 -m venv .venv      # Tumbleweed doesn't allow pip to install into the system Python
source .venv/bin/activate
pip install -r requirements.txt
```

If `python3 -m venv .venv` says *ensurepip is not available*, install the pip wheel package for
your Python version (`zypper search pip-wheel`) and run it again.

## 2. Configure

1. **Bot:** in @BotFather, send `/newbot`, then copy the token.
2. **Owner ID:** send any message to @userinfobot, then copy the number after `Id:`.
3. `cp .env.example .env`, then fill in `BOT_TOKEN` and `OWNER_ID` (the other settings are
   explained in the file). `.env` is in `.gitignore`, and the token is never in the code.
4. **From the owner account, open the bot and press Start once.** Telegram doesn't let a bot
   message someone who never started it.
5. In `catalog.yaml`, set the shop details, including `payment.card_number` (the card for
   deposits) and `deposit_percent`.

## 3. Run

```bash
cd ~/"Documents/paid works/bakery demo bot"
source .venv/bin/activate
python -m bot
```

After a few seconds:

```
Tunnel via localhost.run: https://…  (or trycloudflare.com when cloudflared is installed)
Mini App is online at https://…/
Bot @yourbot is running: https://t.me/yourbot | owner id … | Mini App https://…/ | Ctrl+C to stop
```

Keep the terminal open while you demo, and stop with **Ctrl+C**.

Or run it in the background, independent of any terminal: `./bot.sh start` (also `stop`,
`restart`, `status`, `logs`). The log is kept in `data/bot.log`. Only one copy may run at a time.
A second copy causes a "Another copy of this bot is running" error.

**Browser preview:** `http://127.0.0.1:8080/?demo=1` shows the Mini App in Firefox without
Telegram. Orders there are only checked, never sent. It's handy for showing the design on a laptop.

---

## 4. Test the whole flow yourself

One account works: you're both customer and owner, and owner cards are marked
*👑 Do'kon egasi uchun*. A second account (Telegram Desktop or web.telegram.org) is more realistic.

**Customer**
1. `/start`, pick a language, then tap **🍰 Katalog** (the menu button left of the message
   field) or **🍰 Katalogni ochish**.
2. Pick a cake: weight, filling, inscription, reference photo, then **Davom etish**.
3. Pick a date (full days show *band*, closed days show *yopiq*), a time, delivery with address
   or 📍 location, and the phone (typed or **Telegram raqamimni ulashish**). Then **Tekshirish**,
   then **Buyurtma berish**. You get confetti and order number **#ST-1001**.
4. The 🛍 icon opens **Buyurtmalarim**. Tap the order to see its live timeline.

**Owner**, in the chat
5. The order card arrives (photo plus every detail). Press **✅ Qabul qilish**. The customer gets
   the deposit request: 50%, the card number, and a "copy card number" button.
6. As the customer, send any photo in the chat (the "receipt"), or use **Chekni yuklash** in the
   order page. The owner gets the receipt with **✅ To'lov tasdiqlandi / ❌ To'lov topilmadi**.
7. **👩‍🍳 Pishirilmoqda → 🎂 Tayyor**: the bot asks for a photo of the finished cake. Send one,
   and the customer receives it. Then **🚚 Yo'lga chiqdi**: type the courier (e.g.
   `Jasur, +998 90 111 22 33`) or tap **O'zim olib boraman**. Then **📦 Topshirildi**. The
   customer is notified at every step, and their timeline in the Mini App moves.

**Owner**, in the dashboard (the 📊 icon in the Mini App, `/admin`, or **📊 Batafsil** on a card)
8. **Boshqaruv:** Today / Tomorrow / 7 days, revenue, deposits, orders waiting for acceptance,
   receipts to check. Tap an order for all details and the same stage buttons.
9. **Kalendar:** a month view with orders per day; tap a day and switch **Bu kun yopiq** (day
   off). **Mahsulotlar:** sold-out switches. **Sozlamalar:** daily order limit, deposit %.
10. `/orders` sends today's plan. The same plan arrives automatically at 08:00, plus "tomorrow's
    orders" at 18:00, when customers also get their reminders.

**Fallback**
11. **📋 Oddiy menyu** (or `/menu`) runs the whole order with chat buttons. That's what customers
    get if the Mini App's tunnel is down.

---

## 5. How it works

```
Telegram app ──opens──▶ https://<random>.lhr.life / trycloudflare.com ──tunnel──▶ laptop :8080
                                                                                  │
python -m bot ── long polling (bot) + aiohttp (Mini App + API) + scheduler, one process
```

- **Mini App:** `bot/webapp/static/` (plain HTML, CSS and JS, no build step).
  `bot/webapp/server.py` serves it, plus the photos and a JSON API.
- **Security:** every API call carries Telegram's `initData`, checked with the bot token as the
  [Mini Apps docs](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app)
  describe. Prices, dates, availability and sold-out status are always recalculated on the server.
  `/api/admin/*` answers only `OWNER_ID`. Receipt and cake photos are served via signed links.
- **Tunnel:** `bot/webapp/tunnel.py` uses Cloudflare (`cloudflared`) if installed, else
  [localhost.run](https://localhost.run) over plain `ssh`. The address is random. When it
  changes, the bot updates its menu button, and if the tunnel drops it reconnects. To use your
  own permanent https address, put it in `WEBAPP_URL`.
  **Use Cloudflare for demos.** The free localhost.run tunnel measured about 5 KB/s (a 170 KB
  photo took 42 s); Cloudflare is as fast as your internet. If the bot runs inside a sandbox
  (VS Code from Flathub) and cloudflared is installed on the system, set
  `CLOUDFLARED=flatpak-spawn --host cloudflared` in `.env`.
- **Speed:** the app code and data are gzipped, the catalog uses 520 px photos (~27 KB) and the
  product page 1080 px ones (both made automatically in `data/thumbs/`), and everything is cached
  by the phone. Orders and owner actions answer immediately; Telegram messages are sent right
  after in the background, in order per order.
- **Order stages and actions:** `bot/status.py` (the stages) and `bot/ops.py` (what each action
  does). The chat buttons and the dashboard share them.
- **Payments:** a deposit by card transfer plus a receipt screenshot, which is how most Tashkent
  home bakeries work today. It needs no merchant contract. Telegram's own payments (Click/Payme
  invoices) could be added later for clients with a merchant account.
- **Telegram HTML widgets (Bot API 10.4):** the code is in `bot/widgets.py`, but it's off
  (`WIDGETS=off`) because Telegram currently refuses widgets from ordinary bots
  (`INPUT_MEDIA_WIDGET_NOT_ALLOWED`).

---

## 6. Rebuild it for a real bakery (under an hour)

1. Copy the folder, e.g. `cp -r "bakery demo bot" "bakery-clientname"`, and delete
   `data/bakery.db` in the copy.
2. In @BotFather, create the client's bot (`/setuserpic`, `/setdescription`). Put its token and
   the client's user ID in `.env`.
3. Edit **`catalog.yaml`**: the `shop` block (name, tagline, **brand color and logo**, phone, pickup address, delivery fee,
   **card number and deposit %**, daily limit, reminder and summary times, time slots),
   categories, products, prices. Mark one product `featured: true` for the banner.
4. Replace `images/` with the client's photos (same names, or change `photo:`). JPG or PNG,
   about 4:3. The demo photos are from Pexels (`images/CREDITS.md`), so don't use them for a
   real client.
5. Run `python -m bot`. If something in the catalog is wrong, it names the product and field.

Wording: chat texts are in `bot/texts.py`, and Mini App texts are at the top of
`bot/webapp/static/app.js`, with Uzbek and Russian side by side. The accent color is `--accent`
in `bot/webapp/static/app.css`.

## 7. Files

```
catalog.yaml               shop, payment, products, prices  ← edit per client
images/                    product photos (+ CREDITS.md)
.env                       token, owner ID, Mini App settings (not in git)
bot/__main__.py            entry point: python -m bot
bot/webapp/static/         the Mini App: index.html, app.css, app.js (customer + owner dashboard)
bot/webapp/server.py       Mini App server + API, initData check, dashboard API
bot/webapp/tunnel.py       public https address (cloudflared or localhost.run)
bot/handlers.py            commands, buttons, photos/receipts, startup
bot/flow.py                the chat order form, and order placing shared with the Mini App
bot/status.py, bot/ops.py  order stages; accept/stage/payment actions + customer notifications
bot/owner.py               owner cards and buttons, cake-photo/courier prompts, summaries
bot/scheduler.py           morning summary, reminders the day before
bot/files.py               Telegram photos shown in the Mini App (signed links)
bot/views.py, bot/texts.py how orders are written; all chat texts (uz/ru)
bot/catalog.py, bot/db.py  catalog.yaml checks; SQLite
bot/widgets.py, widget_html/  HTML widgets (off while Telegram blocks them)
tools/make_placeholders.py draws simple placeholder photos for products without one
```

## 8. Showcase on Netlify (works with your laptop off)

A static copy of the Mini App that clients can try anytime: the same catalog, photos and
screens, with a **simulated bakery**. A demo order is accepted after a few seconds, then moves
through baking, decorating, ready (with a cake photo), on the way and delivered in about two
minutes. The **"Siz qandolatchimisiz?"** button opens the owner dashboard with sample orders.
Nothing is real: orders stay on the visitor's own phone (`bot/webapp/static/showcase.js`).

1. Build it (again after any change to `catalog.yaml`, photos or the app):
   `.venv/bin/python tools/build_showcase.py` creates the `showcase/` folder.
2. Publish: log in at https://app.netlify.com (free account, your own), open
   https://app.netlify.com/drop and drag the `showcase` folder onto the page. In
   *Site configuration → Change site name*, pick a name like `shirin-tortlar-demo`. To update,
   open the site → *Deploys* → drag the new folder there.
3. Put the address in `.env` as `SHOWCASE_URL=https://shirin-tortlar-demo.netlify.app` and
   restart the bot once. From then on, whenever the live bot stops, its 🍰 Katalog button opens
   the showcase, inside Telegram too.

With the laptop off, the bot doesn't answer typed messages, only the 🍰 Katalog button works.
The live bot (`python -m bot`) is still the way to show real notifications and owner cards.

## 9. Tests

```bash
.venv/bin/python tests/run_tests.py
```

And the browser test of the Netlify showcase (needs Node.js; `npm install` once in `tests/`):

```bash
.venv/bin/python tools/build_showcase.py && (cd tests && node showcase_test.js)
```

The Python tests run the real bot and Mini App server against a fake Telegram (`tests/fake_telegram.py`)
that answers every call 0.3 s late. They check the order flow, owner actions, payments, photos
and speed. Nothing is sent to the real Telegram, and `.env` isn't used. Run them after changing
the code for a client.

## 10. Troubleshooting

- **`sudo: command not found`:** you're in VS Code's sandboxed terminal. Use Konsole.
- **`No tunnel available`:** install cloudflared (in Konsole), or check that
  `ssh nokey@localhost.run` works. Until then customers get the chat-button menu.
- **The Mini App or photos load slowly:** you're on the localhost.run tunnel (the log says
  `Tunnel via localhost.run`). Install cloudflared (see above). The second opening is fast either
  way, because the phone caches everything.
- **The Mini App doesn't open after a restart:** an old button points at the previous tunnel
  address. Tap 🎂 Katalog (or the menu button) for a fresh one.
- **`Mini App server could not start on port 8080`:** set `WEBAPP_PORT=8090` in `.env`.
- **Orders don't reach the owner:** the owner must press Start in the bot once, and `OWNER_ID`
  must be that account's numeric ID.
- **"Another copy of this bot is running":** close the other terminal running `python -m bot`.
