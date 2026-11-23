"""All customer- and owner-facing texts, in Uzbek (Latin) and Russian."""

from __future__ import annotations

import html
from datetime import date

LANGS = ("uz", "ru")
NBSP = " "

T: dict[str, dict[str, str]] = {
    # ---------- start / language ----------
    "choose_lang": {
        "uz": "Assalomu alaykum! 👋 <b>{shop}</b> uy qandolatxonasiga xush kelibsiz.\n"
              "Здравствуйте! Добро пожаловать в домашнюю кондитерскую <b>{shop}</b>.\n\n"
              "Tilni tanlang · Выберите язык:",
    },
    "welcome": {
        "uz": "Ajoyib! 🍰 Biz Toshkentda buyurtma asosida tortlar, bento va desertlar tayyorlaymiz.\n\n"
              "Katalogdan mahsulotni tanlang, qolganini birga hal qilamiz 👇",
        "ru": "Отлично! 🍰 Мы печём торты, бенто и десерты на заказ в Ташкенте.\n\n"
              "Выберите изделие в каталоге, остальное оформим вместе 👇",
    },
    "lang_set": {"uz": "Til: O'zbekcha ✅", "ru": "Язык: Русский ✅"},
    "pick_lang": {"uz": "Tilni tanlang · Выберите язык:", "ru": "Tilni tanlang · Выберите язык:"},

    # ---------- main menu (reply keyboard) ----------
    "btn_catalog": {"uz": "🎂 Katalog", "ru": "🎂 Каталог"},
    "btn_simple": {"uz": "📋 Oddiy menyu", "ru": "📋 Простое меню"},
    "btn_my_orders": {"uz": "📦 Buyurtmalarim", "ru": "📦 Мои заказы"},
    "btn_lang": {"uz": "🌐 Til", "ru": "🌐 Язык"},

    # ---------- catalog widget ----------
    "catalog_caption": {
        "uz": "🍰 <b>{shop}</b> katalogi: mahsulot ustiga bosing.\n"
              "Katalog ko'rinmayaptimi? «📋 Oddiy menyu» tugmasini bosing.",
        "ru": "🍰 Каталог <b>{shop}</b>: нажмите на изделие.\n"
              "Каталог не отображается? Нажмите «📋 Простое меню».",
    },
    "widget_fallback": {
        "uz": "Katalog ko'rinmayaptimi? Telegram ilovangiz uni hali qo'llab-quvvatlamasligi mumkin. "
              "Oddiy menyudan foydalaning 👇",
        "ru": "Каталог не отображается? Возможно, ваша версия Telegram его пока не поддерживает. "
              "Воспользуйтесь простым меню 👇",
    },
    "w_title": {"uz": "{shop}", "ru": "{shop}"},
    "w_sub": {"uz": "Mahsulot ustiga bosing", "ru": "Нажмите на изделие"},
    "w_sending": {"uz": "Yuborilmoqda…", "ru": "Отправляем…"},
    "w_ok": {"uz": "✓ Davom etamiz, chatga qarang 👇", "ru": "✓ Продолжаем, смотрите чат 👇"},
    "w_gone": {"uz": "Bu mahsulot endi mavjud emas", "ru": "Этого изделия больше нет"},
    "w_err": {"uz": "Xatolik, qayta bosing", "ru": "Ошибка, нажмите ещё раз"},
    "w_timeout": {"uz": "Bot javob bermadi, qayta urinib ko'ring", "ru": "Бот не ответил, попробуйте ещё раз"},
    "w_busy": {"uz": "Bir soniya kuting…", "ru": "Секунду…"},
    "w_rate": {"uz": "Juda tez, biroz kuting", "ru": "Слишком быстро, подождите"},
    "w_open_bot": {"uz": "Buyurtma uchun botni oching", "ru": "Откройте бота, чтобы заказать"},

    # ---------- Mini App ----------
    "app_intro": {
        "uz": "🍰 Katalog va buyurtma berish bitta ilovada: rasmlar, narxlar, sana va yetkazib berish. "
              "Pastdagi tugmani bosing 👇",
        "ru": "🍰 Каталог и оформление заказа в одном приложении: фото, цены, дата и доставка. "
              "Нажмите кнопку ниже 👇",
    },
    "btn_open_app": {"uz": "🍰 Katalogni ochish", "ru": "🍰 Открыть каталог"},
    "menu_button": {"uz": "🍰 Katalog", "ru": "🍰 Каталог"},

    # ---------- simple menu (fallback) ----------
    "simple_title": {"uz": "📋 Bo'limni tanlang:", "ru": "📋 Выберите раздел:"},
    "simple_cat": {"uz": "{emoji} <b>{cat}</b>: mahsulotni tanlang:", "ru": "{emoji} <b>{cat}</b>: выберите изделие:"},
    "btn_back_cats": {"uz": "⬅️ Bo'limlar", "ru": "⬅️ Разделы"},

    # ---------- product / order form ----------
    "product_caption": {"uz": "<b>{name}</b>\n{desc}\n\n💰 {price}", "ru": "<b>{name}</b>\n{desc}\n\n💰 {price}"},
    "step": {"uz": "<b>{i}/{n}</b> · ", "ru": "<b>{i}/{n}</b> · "},
    "q_size": {"uz": "⚖️ Hajmini tanlang:", "ru": "⚖️ Выберите размер:"},
    "q_filling": {"uz": "🍓 Nachinkasini tanlang:", "ru": "🍓 Выберите начинку:"},
    "q_inscription": {
        "uz": "✍️ Tort ustiga qanday yozuv yozaylik?\nMatnni yuboring ({max} belgigacha) yoki «Yozuvsiz»ni bosing.",
        "ru": "✍️ Какую надпись сделать на торте?\nОтправьте текст (до {max} символов) или нажмите «Без надписи».",
    },
    "q_photo": {
        "uz": "📷 Namuna rasm bormi? Qanday dizayn xohlayotganingizni rasm qilib yuboring "
              "yoki «O'tkazib yuborish»ni bosing.",
        "ru": "📷 Есть фото-референс? Пришлите картинку с желаемым дизайном или нажмите «Пропустить».",
    },
    "q_date": {"uz": "📅 Qaysi kunga tayyorlaylik?", "ru": "📅 На какую дату приготовить?"},
    "q_slot": {"uz": "🕐 Qulay vaqtni tanlang:", "ru": "🕐 Выберите удобное время:"},
    "q_method": {"uz": "🚚 Qanday olasiz?", "ru": "🚚 Как получите заказ?"},
    "q_address": {
        "uz": "📍 Manzilni yozing (tuman, ko'cha, uy, mo'ljal) yoki pastdagi tugma bilan joylashuvni yuboring:",
        "ru": "📍 Напишите адрес (район, улица, дом, ориентир) или отправьте геолокацию кнопкой ниже:",
    },
    "q_phone": {
        "uz": "📞 Telefon raqamingizni yuboring: pastdagi tugmani bosing yoki +998 90 123 45 67 ko'rinishida yozing.",
        "ru": "📞 Отправьте номер телефона: нажмите кнопку ниже или напишите в виде +998 90 123 45 67.",
    },
    "btn_no_inscription": {"uz": "Yozuvsiz", "ru": "Без надписи"},
    "btn_skip": {"uz": "O'tkazib yuborish ➡️", "ru": "Пропустить ➡️"},
    "btn_back": {"uz": "⬅️ Orqaga", "ru": "⬅️ Назад"},
    "btn_cancel": {"uz": "❌ Bekor qilish", "ru": "❌ Отменить"},
    "btn_confirm": {"uz": "✅ Tasdiqlash", "ru": "✅ Подтвердить"},
    "btn_delivery": {"uz": "🚚 Yetkazib berish ({fee})", "ru": "🚚 Доставка ({fee})"},
    "btn_pickup": {"uz": "🏠 O'zim olib ketaman", "ru": "🏠 Самовывоз"},
    "btn_location": {"uz": "📍 Joylashuvni yuborish", "ru": "📍 Отправить геолокацию"},
    "btn_contact": {"uz": "📱 Raqamni yuborish", "ru": "📱 Отправить номер"},
    "free": {"uz": "bepul", "ru": "бесплатно"},
    "no_inscription": {"uz": "yozuvsiz", "ru": "без надписи"},
    "photo_attached": {"uz": "rasm qabul qilindi", "ru": "фото получено"},
    "photo_attached_owner": {"uz": "ilova qilingan", "ru": "приложено"},
    "photo_skipped": {"uz": "yo'q", "ru": "нет"},
    "location_label": {"uz": "📍 Joylashuv (xaritada)", "ru": "📍 Геолокация (на карте)"},
    "too_long": {"uz": "Juda uzun. {max} belgigacha yozing.", "ru": "Слишком длинно. До {max} символов."},
    "bad_phone": {
        "uz": "Raqam noto'g'ri ko'rinadi. Masalan: +998 90 123 45 67",
        "ru": "Похоже, номер неверный. Пример: +998 90 123 45 67",
    },
    "use_buttons": {"uz": "Iltimos, yuqoridagi tugmalardan birini tanlang 👆", "ru": "Пожалуйста, выберите вариант кнопкой выше 👆"},
    "send_photo_or_skip": {
        "uz": "Rasm yuboring yoki «O'tkazib yuborish»ni bosing 👆",
        "ru": "Пришлите фото или нажмите «Пропустить» 👆",
    },
    "stale": {"uz": "Bu tugma eskirgan", "ru": "Эта кнопка устарела"},
    "cancelled": {"uz": "Buyurtma bekor qilindi. Istalgan vaqtda qaytishingiz mumkin 🙂", "ru": "Заказ отменён. Возвращайтесь в любое время 🙂"},
    "idle": {"uz": "Mahsulotni katalogdan tanlang 👇", "ru": "Выберите изделие в каталоге 👇"},

    # ---------- summary / confirmation ----------
    "summary_title": {"uz": "🧾 <b>Buyurtmangizni tekshiring</b>", "ru": "🧾 <b>Проверьте заказ</b>"},
    "f_filling": {"uz": "Nachinka", "ru": "Начинка"},
    "f_inscription": {"uz": "Yozuv", "ru": "Надпись"},
    "f_photo": {"uz": "Namuna rasm", "ru": "Фото-референс"},
    "f_when": {"uz": "Sana va vaqt", "ru": "Дата и время"},
    "f_delivery": {"uz": "Yetkazib berish", "ru": "Доставка"},
    "f_pickup": {"uz": "Olib ketish", "ru": "Самовывоз"},
    "f_phone": {"uz": "Telefon", "ru": "Телефон"},
    "f_customer": {"uz": "Mijoz", "ru": "Клиент"},
    "f_items": {"uz": "Mahsulot narxi", "ru": "Стоимость изделия"},
    "f_fee": {"uz": "Yetkazib berish", "ru": "Доставка"},
    "f_total": {"uz": "Jami", "ru": "Итого"},
    "f_lang": {"uz": "Mijoz tili", "ru": "Язык клиента"},
    "summary_note": {
        "uz": "Hammasi to'g'rimi? «Tasdiqlash»ni bosing. To'lov buyurtma olinganda amalga oshiriladi.",
        "ru": "Всё верно? Нажмите «Подтвердить». Оплата при получении заказа.",
    },
    "confirmed_mark": {"uz": "Tasdiqlandi", "ru": "Подтверждено"},
    "confirmed": {
        "uz": "🎉 Rahmat! Buyurtmangiz yuborildi.\nBuyurtma raqami: <b>#{num}</b>\n\n"
              "Qandolatchimiz tez orada buyurtmani ko'rib chiqadi. Har bir o'zgarish haqida shu yerda xabar beramiz.",
        "ru": "🎉 Спасибо! Заказ оформлен.\nНомер заказа: <b>#{num}</b>\n\n"
              "Кондитер скоро его рассмотрит. О каждом изменении статуса сообщим здесь.",
    },

    # ---------- statuses ----------
    "st_new": {"uz": "🆕 Yangi", "ru": "🆕 Новый"},
    "st_accepted": {"uz": "✅ Qabul qilindi", "ru": "✅ Принят"},
    "st_ready": {"uz": "🎂 Tayyor", "ru": "🎂 Готов"},
    "st_delivered": {"uz": "📦 Topshirildi", "ru": "📦 Выдан"},
    "st_rejected": {"uz": "❌ Rad etildi", "ru": "❌ Отклонён"},

    # status widget (short labels, no emoji: the widget draws its own marks)
    "sw_new": {"uz": "Yuborildi", "ru": "Отправлен"},
    "sw_accepted": {"uz": "Qabul qilindi", "ru": "Принят"},
    "sw_ready": {"uz": "Tayyor", "ru": "Готов"},
    "sw_delivered_d": {"uz": "Yetkazildi", "ru": "Доставлен"},
    "sw_delivered_p": {"uz": "Olib ketildi", "ru": "Выдан"},
    "sw_rejected": {"uz": "Rad etildi", "ru": "Отклонён"},
    "sw_order": {"uz": "Buyurtma", "ru": "Заказ"},
    "sw_rej_note": {"uz": "Savollar bo'lsa: {phone}", "ru": "Вопросы: {phone}"},

    # notifications to the customer
    "n_accepted": {
        "uz": "✅ Buyurtma <b>#{num}</b> qabul qilindi! Qandolatchimiz tayyorlashni boshlaydi.",
        "ru": "✅ Заказ <b>#{num}</b> принят! Кондитер приступает к работе.",
    },
    "n_rejected": {
        "uz": "😔 Kechirasiz, <b>#{num}</b> buyurtmani bajara olmaymiz. Batafsil: {phone}",
        "ru": "😔 К сожалению, мы не сможем выполнить заказ <b>#{num}</b>. Подробности: {phone}",
    },
    "n_ready_d": {
        "uz": "🎂 Buyurtma <b>#{num}</b> tayyor! Tez orada kuryer yo'lga chiqadi.",
        "ru": "🎂 Заказ <b>#{num}</b> готов! Скоро курьер выедет к вам.",
    },
    "n_ready_p": {
        "uz": "🎂 Buyurtma <b>#{num}</b> tayyor! Olib ketishingiz mumkin:\n{address}",
        "ru": "🎂 Заказ <b>#{num}</b> готов! Можно забирать:\n{address}",
    },
    "n_delivered": {
        "uz": "💝 Buyurtma <b>#{num}</b> topshirildi. Yoqimli ishtaha! Bizni tanlaganingiz uchun rahmat.",
        "ru": "💝 Заказ <b>#{num}</b> выдан. Приятного аппетита! Спасибо, что выбрали нас.",
    },

    # customer's order list
    "my_orders_title": {"uz": "📦 <b>Oxirgi buyurtmalaringiz</b>", "ru": "📦 <b>Ваши последние заказы</b>"},
    "my_orders_empty": {"uz": "Sizda hali buyurtma yo'q.", "ru": "У вас пока нет заказов."},

    # ---------- owner side ----------
    "o_new": {"uz": "🔔 <b>Yangi buyurtma #{num}</b>", "ru": "🔔 <b>Новый заказ #{num}</b>"},
    "o_order": {"uz": "<b>Buyurtma #{num}</b>", "ru": "<b>Заказ #{num}</b>"},
    "o_status": {"uz": "Holat", "ru": "Статус"},
    "o_created": {"uz": "Tushgan vaqti", "ru": "Поступил"},
    "o_btn_accept": {"uz": "✅ Qabul qilish", "ru": "✅ Принять"},
    "o_btn_reject": {"uz": "❌ Rad etish", "ru": "❌ Отклонить"},
    "o_btn_ready": {"uz": "🎂 Tayyor", "ru": "🎂 Готов"},
    "o_btn_delivered": {"uz": "📦 Topshirildi", "ru": "📦 Выдан"},
    "o_btn_reject_yes": {"uz": "Ha, rad etish", "ru": "Да, отклонить"},
    "o_btn_reject_no": {"uz": "⬅️ Yo'q", "ru": "⬅️ Нет"},
    "o_reject_q": {"uz": "Rad etilsinmi? Mijozga xabar boradi.", "ru": "Отклонить? Клиент получит уведомление."},
    "o_changed": {"uz": "Holat: {status}", "ru": "Статус: {status}"},
    "o_already": {"uz": "Holat allaqachon o'zgargan", "ru": "Статус уже изменён"},
    "o_not_owner": {"uz": "Bu tugma faqat do'kon egasi uchun", "ru": "Эта кнопка только для владельца"},
    "o_notify_failed": {
        "uz": "⚠️ Mijozga xabar yetkazilmadi (botni bloklagan bo'lishi mumkin). Telefon: {phone}",
        "ru": "⚠️ Не удалось уведомить клиента (возможно, он заблокировал бота). Телефон: {phone}",
    },
    "o_not_found": {"uz": "Bunday buyurtma topilmadi.", "ru": "Такой заказ не найден."},
    "o_only_owner": {"uz": "Bu buyruq faqat do'kon egasi uchun.", "ru": "Эта команда только для владельца."},
    "o_tag": {"uz": "👑 Do'kon egasi uchun", "ru": "👑 Для владельца"},

    # ---------- v2: stages, payment, courier, reminders ----------
    "st_baking": {"uz": "👩‍🍳 Pishirilmoqda", "ru": "👩‍🍳 Готовится"},
    "st_decorating": {"uz": "🎨 Bezatilmoqda", "ru": "🎨 Украшается"},
    "st_on_way": {"uz": "🚚 Yo'lda", "ru": "🚚 В пути"},
    "n_pay": {
        "uz": "💳 Sanani band qilish uchun oldindan to'lov: <b>{amount}</b> ({pct}%).\n"
              "Karta: <code>{card}</code>\nEgasi: {holder}\n\n"
              "To'lovdan so'ng chek rasmini (skrinshot) shu chatga yuboring. Qolgan {rest} buyurtmani olganingizda to'lanadi.",
        "ru": "💳 Чтобы забронировать дату, внесите предоплату: <b>{amount}</b> ({pct}%).\n"
              "Карта: <code>{card}</code>\nПолучатель: {holder}\n\n"
              "После перевода пришлите сюда скриншот чека. Остаток {rest} оплачивается при получении.",
    },
    "btn_copy_card": {"uz": "📋 Karta raqamini nusxalash", "ru": "📋 Скопировать номер карты"},
    "n_baking": {"uz": "👩‍🍳 Buyurtma <b>#{num}</b>: qandolatchimiz tortingizni pishirishni boshladi!",
                 "ru": "👩‍🍳 Заказ <b>#{num}</b>: кондитер начал печь ваш торт!"},
    "n_decorating": {"uz": "🎨 Buyurtma <b>#{num}</b>: tortingiz bezatilmoqda.",
                     "ru": "🎨 Заказ <b>#{num}</b>: торт украшают."},
    "n_on_way": {"uz": "🚚 Buyurtma <b>#{num}</b> yo'lda!\nKuryer: {courier}",
                 "ru": "🚚 Заказ <b>#{num}</b> в пути!\nКурьер: {courier}"},
    "courier_self": {"uz": "qandolatchimizning o'zi olib boradi", "ru": "привезёт сам кондитер"},
    "n_rest": {"uz": "\n💵 To'lanadigan qoldiq: <b>{rest}</b>", "ru": "\n💵 К оплате при получении: <b>{rest}</b>"},
    "n_paid": {"uz": "✅ Buyurtma <b>#{num}</b>: to'lov qabul qilindi ({amount}). Rahmat!",
               "ru": "✅ Заказ <b>#{num}</b>: оплата получена ({amount}). Спасибо!"},
    "n_pay_rejected": {
        "uz": "😕 Buyurtma <b>#{num}</b>: to'lov topilmadi. Chekni tekshirib, qayta yuboring yoki {phone} raqamiga qo'ng'iroq qiling.",
        "ru": "😕 Заказ <b>#{num}</b>: оплата не найдена. Проверьте чек и пришлите снова или позвоните {phone}.",
    },
    "receipt_got": {"uz": "🧾 Chek qabul qilindi! Qandolatchi tekshirib, tasdiqlaydi.",
                    "ru": "🧾 Чек получен! Кондитер проверит и подтвердит оплату."},
    "reminder": {
        "uz": "⏰ Eslatma: ertaga, {date}, {slot}: buyurtma <b>#{num}</b> ({product}).\n{where}",
        "ru": "⏰ Напоминание: завтра, {date}, {slot}: заказ <b>#{num}</b> ({product}).\n{where}",
    },
    "date_taken": {"uz": "😕 Bu kun hozirgina band bo'lib qoldi. Boshqa sanani tanlang:",
                   "ru": "😕 Этот день только что заняли. Выберите другую дату:"},
    "no_dates": {"uz": "Afsuski, yaqin kunlarda bo'sh joy qolmadi. Iltimos, {phone} raqamiga qo'ng'iroq qiling.",
                 "ru": "К сожалению, на ближайшие дни мест нет. Позвоните, пожалуйста: {phone}."},
    "sold_out": {"uz": "Hozircha tugagan", "ru": "Временно нет в наличии"},
    "sold_out_tag": {"uz": " · tugagan", "ru": " · нет"},
    "f_courier": {"uz": "Kuryer", "ru": "Курьер"},
    "f_payment": {"uz": "To'lov", "ru": "Оплата"},
    "pay_none": {"uz": "olganda to'lanadi", "ru": "при получении"},
    "pay_due": {"uz": "{amount} oldindan to'lov kutilmoqda", "ru": "ожидается предоплата {amount}"},
    "pay_review": {"uz": "🧾 chek yuborildi, tekshiring", "ru": "🧾 прислан чек, проверьте"},
    "pay_paid": {"uz": "✅ {paid} to'langan, qoldiq {rest}", "ru": "✅ оплачено {paid}, остаток {rest}"},
    "pay_full": {"uz": "✅ to'liq to'langan", "ru": "✅ оплачено полностью"},

    # gifts, reviews, promotions
    "f_gift": {"uz": "Sovg'a, oluvchi", "ru": "Подарок, получатель"},
    "f_gift_note": {"uz": "Otkritka", "ru": "Открытка"},
    "gift_surprise": {"uz": "syurpriz: oldindan qo'ng'iroq qilmang", "ru": "сюрприз: не звонить заранее"},
    "rate_ask": {"uz": "\n\nTortimiz qanday bo'ldi? Baholang 👇", "ru": "\n\nКак вам торт? Оцените 👇"},
    "rate_thanks": {"uz": "Rahmat! Bir-ikki so'z bilan fikringizni yozasizmi? Yoki «O'tkazib yuborish»ni bosing.",
                    "ru": "Спасибо! Напишете пару слов о заказе? Или нажмите «Пропустить»."},
    "review_saved": {"uz": "💝 Fikringiz uchun rahmat!", "ru": "💝 Спасибо за отзыв!"},
    "o_review": {"uz": "{stars} <b>#{num}</b> uchun baho\n{text}— {who}", "ru": "{stars} оценка заказа <b>#{num}</b>\n{text}— {who}"},
    "btn_open_catalog": {"uz": "🍰 Katalogni ochish", "ru": "🍰 Открыть каталог"},
    "btn_promo_off": {"uz": "🔕 Aksiyalarni o'chirish", "ru": "🔕 Отписаться от акций"},
    "promo_off_done": {"uz": "Aksiyalar o'chirildi. /start orqali qayta yoqiladi.", "ru": "Вы отписались от акций. /start включит снова."},

    # owner, v2
    "o_btn_baking": {"uz": "👩‍🍳 Pishirilmoqda", "ru": "👩‍🍳 Печём"},
    "o_btn_decorating": {"uz": "🎨 Bezatilmoqda", "ru": "🎨 Украшаем"},
    "o_btn_on_way": {"uz": "🚚 Yo'lga chiqdi", "ru": "🚚 Выехал"},
    "o_btn_paid": {"uz": "💳 To'lov olindi", "ru": "💳 Оплата получена"},
    "o_btn_pay_ok": {"uz": "✅ To'lov tasdiqlandi", "ru": "✅ Оплата подтверждена"},
    "o_btn_pay_no": {"uz": "❌ To'lov topilmadi", "ru": "❌ Оплата не найдена"},
    "o_btn_dashboard": {"uz": "📊 Boshqaruv", "ru": "📊 Панель"},
    "o_btn_details": {"uz": "📊 Batafsil", "ru": "📊 Подробнее"},
    "o_btn_no_photo": {"uz": "Rasmsiz ➡️", "ru": "Без фото ➡️"},
    "o_btn_self": {"uz": "🙋 O'zim olib boraman", "ru": "🙋 Отвезу сам(а)"},
    "o_btn_cancel": {"uz": "Bekor qilish", "ru": "Отмена"},
    "o_ask_photo": {"uz": "📸 <b>#{num}</b>: tayyor tortning rasmini yuboring, mijozga ko'rsatamiz. Yoki «Rasmsiz»ni bosing.",
                    "ru": "📸 <b>#{num}</b>: пришлите фото готового торта, покажем клиенту. Или нажмите «Без фото»."},
    "o_ask_courier": {"uz": "🚚 <b>#{num}</b>: kuryer ismi va telefonini yozing (masalan: Jasur, +998 90 111 22 33) yoki tanlang:",
                      "ru": "🚚 <b>#{num}</b>: напишите имя и телефон курьера (например: Жасур, +998 90 111 22 33) или выберите:"},
    "o_done": {"uz": "✅ Bajarildi", "ru": "✅ Готово"},
    "o_cancelled": {"uz": "Bekor qilindi", "ru": "Отменено"},
    "o_receipt": {"uz": "🧾 <b>#{num}</b>: to'lov cheki\nKutilgan summa: <b>{amount}</b>\nMijoz: {who}",
                  "ru": "🧾 <b>#{num}</b>: чек об оплате\nОжидаемая сумма: <b>{amount}</b>\nКлиент: {who}"},
    "o_dashboard_text": {"uz": "📊 Boshqaruv paneli: buyurtmalar, kalendar, mahsulotlar va sozlamalar.",
                         "ru": "📊 Панель управления: заказы, календарь, товары и настройки."},
    "o_no_app": {"uz": "Mini App hozir o'chiq (tunnel yo'q).", "ru": "Mini App сейчас выключен (нет туннеля)."},
    "o_sum_morning": {"uz": "☀️ <b>Xayrli tong! Bugungi reja</b> · {date}", "ru": "☀️ <b>Доброе утро! План на сегодня</b> · {date}"},
    "o_sum_evening": {"uz": "🌙 <b>Ertangi buyurtmalar</b> · {date}", "ru": "🌙 <b>Заказы на завтра</b> · {date}"},
    "o_sum_day": {"uz": "📋 <b>Buyurtmalar</b> · {date}", "ru": "📋 <b>Заказы</b> · {date}"},
    "o_sum_orders": {"uz": "🎂 Topshiriladi ({n})", "ru": "🎂 Выдать ({n})"},
    "o_sum_new": {"uz": "🆕 Tasdiqlash kutilmoqda ({n})", "ru": "🆕 Ждут подтверждения ({n})"},
    "o_sum_unpaid": {"uz": "💳 Oldindan to'lov kutilmoqda ({n})", "ru": "💳 Ждём предоплату ({n})"},
    "o_sum_empty": {"uz": "Buyurtma yo'q 🙂", "ru": "Заказов нет 🙂"},
    "o_sum_total": {"uz": "Jami: {total} · to'langan: {paid}", "ru": "Сумма: {total} · оплачено: {paid}"},

    # ---------- bot command menu ----------
    "cmd_start": {"uz": "Boshlash / tilni tanlash", "ru": "Начать / выбрать язык"},
    "cmd_catalog": {"uz": "Katalog", "ru": "Каталог"},
    "cmd_menu": {"uz": "Oddiy menyu (tugmalar)", "ru": "Простое меню (кнопки)"},
    "cmd_myorders": {"uz": "Buyurtmalarim", "ru": "Мои заказы"},
    "cmd_orders": {"uz": "Bugungi buyurtmalar (egasi)", "ru": "Заказы на сегодня (владелец)"},
    "cmd_admin": {"uz": "Boshqaruv paneli (egasi)", "ru": "Панель управления (владелец)"},
}


def stars(n: int) -> str:
    return "⭐" * max(0, min(5, int(n)))


def t(lang: str, key: str, **kw) -> str:
    entry = T[key]
    text = entry.get(lang) or entry.get("uz") or next(iter(entry.values()))
    return text.format(**kw) if kw else text


def all_langs(key: str) -> set[str]:
    """Every translation of a button label, used to recognise reply-keyboard presses."""
    return set(T[key].values())


def esc(value) -> str:
    """Escape text for Telegram HTML messages (only &, < and > need it)."""
    return html.escape(str(value), quote=False)


def money(amount: int, lang: str) -> str:
    num = f"{amount:,}".replace(",", NBSP)
    return f"{num}{NBSP}so'm" if lang == "uz" else f"{num}{NBSP}сум"


def plural_people(n: int) -> str:
    """Russian plural after a number: 2-4 -> 'человека', otherwise 'человек'."""
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return "человека"
    return "человек"


UZ_MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust",
             "sentyabr", "oktyabr", "noyabr", "dekabr"]
RU_MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
             "сентября", "октября", "ноября", "декабря"]
UZ_DAYS = ["Du", "Se", "Cho", "Pa", "Ju", "Sha", "Ya"]
RU_DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def fmt_date(d: date, lang: str, weekday: bool = True) -> str:
    if lang == "uz":
        s = f"{d.day}-{UZ_MONTHS[d.month - 1]}"
        return f"{s} ({UZ_DAYS[d.weekday()]})" if weekday else s
    s = f"{d.day} {RU_MONTHS[d.month - 1]}"
    return f"{s} ({RU_DAYS[d.weekday()]})" if weekday else s


def fmt_date_short(d: date, lang: str) -> str:
    """Button label, e.g. 'Du, 24-noy' / 'Пн, 24 ноя'."""
    if lang == "uz":
        return f"{UZ_DAYS[d.weekday()]}, {d.day}-{UZ_MONTHS[d.month - 1][:3]}"
    return f"{RU_DAYS[d.weekday()]}, {d.day} {RU_MONTHS[d.month - 1][:3]}"


def fmt_phone(phone: str) -> str:
    """+998901234567 -> +998 90 123 45 67"""
    d = phone.lstrip("+")
    if len(d) == 12 and d.startswith("998"):
        return f"+998 {d[3:5]} {d[5:8]} {d[8:10]} {d[10:12]}"
    return phone
