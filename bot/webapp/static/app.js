/* Shirin Tortlar Mini App.
   Customer: catalog → product → checkout → review → success, "My orders" with live status,
   deposit payment and receipt upload.
   Owner (OWNER_ID): dashboard, order actions, calendar with days off, sold out, settings.
   Talks to the bot's own server (bot/webapp/server.py); every call carries
   Telegram.WebApp.initData, which the server verifies. */
(() => {
  'use strict';

  let tg = window.Telegram && window.Telegram.WebApp;
  // Showcase build (Netlify): showcase.js answers every call in the browser and simulates the bakery
  const LOCAL = window.ShowcaseAPI || null;
  // Browser preview: http://127.0.0.1:8080/?demo=1 (no Telegram; orders are checked but never sent)
  const DEMO = !LOCAL && !(tg && tg.initData) && new URLSearchParams(location.search).has('demo');
  const POLL = LOCAL ? 3000 : 8000;
  const PARAMS = new URLSearchParams(location.search);
  const stackEl = document.getElementById('stack');
  const toastEl = document.getElementById('toast');

  // ------------------------------------------------------------------ texts

  const T = {
    uz: {
      featured: 'Mavsum taklifi', all: 'Hammasi', order: 'Buyurtma', continue: 'Davom etish',
      size: 'Hajmi', filling: 'Nachinka', chooseFilling: 'Nachinkani tanlang',
      inscription: 'Tort ustidagi yozuv', inscriptionPh: "Masalan: Tug'ilgan kuning bilan!",
      inscriptionFoot: 'Ixtiyoriy. {0} belgigacha.',
      refPhoto: 'Namuna rasm', addPhoto: "Rasm qo'shish", changePhoto: 'Boshqa rasm tanlash',
      refFoot: "Qanday dizayn xohlaysiz? Rasm qo'shsangiz, qandolatchi shunga qarab bezaydi.",
      checkoutTitle: 'Qachon va qayerga?', date: 'Sana', time: 'Vaqt',
      delivery: 'Yetkazib berish', pickup: 'Olib ketish',
      address: 'Manzil', addressPh: "Tuman, ko'cha, uy, mo'ljal",
      sendLocation: 'Joylashuvimni yuborish', locationAdded: "Joylashuv qo'shildi", locDenied: 'Joylashuvga ruxsat berilmadi',
      pickupFrom: 'Olib ketish manzili', free: 'bepul', full: 'band', closedDay: 'yopiq',
      feeFoot: "Toshkent bo'ylab yetkazib berish {0}. {1}dan yuqori buyurtmalarga bepul.", feeFootFlat: "Toshkent bo'ylab yetkazib berish {0}.",
      contact: 'Aloqa', phonePh: '+998 90 123 45 67', shareContact: 'Telegram raqamimni ulashish',
      phoneWait: 'Raqam olinmoqda…', phoneOk: "Raqam qo'shildi", typePhone: "Raqamni qo'lda yozing",
      check: 'Tekshirish', reviewTitle: 'Buyurtmangiz', items: 'Mahsulot narxi', fee: 'Yetkazib berish', total: 'Jami',
      payNote: "Qabul qilingach, sanani band qilish uchun {0}% oldindan to'lov so'raladi (karta orqali). Qolgani olganda.",
      payNoteCash: "To'lov buyurtmani olganingizda: naqd yoki karta orqali.", placeOrder: 'Buyurtma berish',
      noInscription: 'yozuvsiz', none: "yo'q", when: 'Sana va vaqt', phone: 'Telefon',
      needDate: 'Sanani tanlang', needSlot: 'Vaqtni tanlang', needAddress: 'Manzilni yozing yoki joylashuvni yuboring',
      needPhone: "Telefon raqamini to'g'ri kiriting",
      doneTitle: 'Buyurtma yuborildi!', doneText: "Qandolatchimiz tez orada tasdiqlaydi. Har bir bosqich haqida chatda xabar beramiz.",
      myOrders: 'Buyurtmalarim', close: 'Yopish', ordersEmptyT: "Hali buyurtma yo'q", ordersEmpty: 'Katalogdan birinchi tortingizni tanlang 🎂',
      soldOut: 'Tugagan', soldOutMsg: 'Bu mahsulot hozircha tugagan',
      st_new: 'Yuborildi', st_accepted: 'Qabul qilindi', st_baking: 'Pishirilmoqda', st_decorating: 'Bezatilmoqda',
      st_ready: 'Tayyor', st_on_way: "Yo'lda", st_delivered: 'Topshirildi', st_rejected: 'Rad etildi',
      tl_new: 'Buyurtma yuborildi', tl_accepted: 'Qabul qilindi', tl_baking: 'Pishirilmoqda', tl_decorating: 'Bezatilmoqda',
      tl_ready: 'Tayyor', tl_on_way: "Yo'lda", tl_delivered_d: 'Yetkazildi', tl_delivered_p: 'Olib ketildi',
      d_new: "Qandolatchi tez orada ko'rib chiqadi", d_accepted: 'Buyurtmangiz qabul qilindi', d_baking: 'Tortingiz pechda 🔥',
      d_decorating: 'Bezak berilmoqda ✨', d_ready_d: "Tayyor! Tez orada yo'lga chiqadi", d_ready_p: 'Tayyor! Olib ketishingiz mumkin',
      d_on_way: "Kuryer yo'lda", d_delivered: 'Yoqimli ishtaha! 💝', d_rejected: 'Afsuski, bu buyurtma bajarilmaydi',
      payment: "To'lov", payDue: "Oldindan to'lov: {0}", payDueText: "Sanani band qilish uchun shu kartaga o'tkazing va chekni yuklang:",
      copy: 'Nusxalash', copied: 'Nusxalandi', uploadReceipt: 'Chekni yuklash', receiptSent: 'Chek yuborildi, tekshirilmoqda',
      paidT: "To'langan: {0}", restT: "Olganda to'lanadi: {0}", payOnDelivery: "To'lov buyurtmani olganda", paidFull: "To'liq to'langan",
      courier: 'Kuryer', selfCourier: "Qandolatchining o'zi olib boradi", cakePhoto: 'Tayyor tortingiz', details: 'Tafsilotlar',
      rejectedNote: "Savollar bo'lsa: {0}",
      // owner
      dash: 'Boshqaruv', today: 'Bugun', tomorrow: 'Ertaga', week: '7 kun',
      s_orders: 'Buyurtmalar', s_revenue: 'Tushum', s_paid: 'Oldindan olingan', s_unpaid: "To'lov kutilmoqda",
      pendingT: 'Tasdiqlash kutilmoqda', receiptsT: 'Cheklarni tekshiring', ordersT: 'Buyurtmalar', noOrders: "Buyurtma yo'q",
      calendar: 'Kalendar', products: 'Mahsulotlar', settings: 'Sozlamalar', customer: 'Mijoz', writeChat: 'Telegramda yozish',
      openMap: 'Xaritada ochish', receipt: "To'lov cheki",
      a_acc: 'Qabul qilish', a_rej: 'Rad etish', a_bak: 'Pishirishni boshladim', a_dec: "Bezashga o'tdim", a_rdy: 'Tayyor',
      a_way: "Yo'lga chiqdi", a_dlv: 'Topshirildi', a_pok: "To'lov tasdiqlandi", a_pno: "To'lov topilmadi", a_paid: "To'lov olindi",
      rejectQ: 'Buyurtma rad etilsinmi? Mijozga xabar boradi.', readyT: 'Tort tayyor', readyFoot: "Tayyor tort rasmi mijozga yuboriladi. Ixtiyoriy, lekin mijozlar juda yaxshi ko'radi.",
      markReady: 'Tayyor deb belgilash', courierT: 'Kim yetkazadi?', courierPh: 'Ism va telefon', send: 'Yuborish',
      selfBtn: "O'zim olib boraman", dayClosed: 'Bu kun yopiq', dayClosedFoot: 'Yopiq kunga yangi buyurtma qabul qilinmaydi.',
      sold: 'Sotuvda', capacity: 'Kuniga buyurtmalar', capacityFoot: "Shuncha buyurtma bo'lsa, kun «band» bo'ladi. 0 = cheklovsiz.",
      deposit: "Oldindan to'lov", depositFoot: "Qabul qilingandan keyin so'raladi. 0% = hammasi olganda.", card: 'Karta',
      cardFoot: "Karta raqami catalog.yaml faylida o'zgartiriladi.", autoMsgs: 'Avtomatik xabarlar',
      reminderAt: 'Mijozga eslatma (bir kun oldin)', summaryAt: 'Ertalabki hisobot', done: 'Bajarildi', saved: 'Saqlandi',
      err_stale: "Holat allaqachon o'zgargan", err_date_full: "Bu kun band bo'lib qoldi, boshqa kunni tanlang",
      err_sold_out: 'Bu mahsulot hozircha tugagan',
      err_auth: 'Ilovani botdagi tugma orqali qayta oching', err_date: 'Bu sana endi mavjud emas, boshqasini tanlang',
      err_phone: "Telefon raqamini to'g'ri kiriting", err_address: 'Manzilni tekshiring', err_server: "Xatolik yuz berdi. Qayta urinib ko'ring",
      err_network: 'Internet aloqasini tekshiring', err_photo_type: 'Faqat rasm yuklash mumkin',
      outsideT: 'Telegram ichida oching', outside: "Bu ilova Telegram bot ichida ishlaydi. Botga o'ting va «Katalogni ochish» tugmasini bosing.",
      loadErr: 'Katalog yuklanmadi', retry: 'Qayta urinish', demoNote: "Brauzerda ko'rish: buyurtmalar yuborilmaydi",
      showcaseNote: "Namoyish: buyurtmalar haqiqiy emas, qandolatxona avtomatik javob beradi",
      showcaseDone: "Bu namoyish: buyurtmangiz holati bir necha daqiqada o'zi o'zgaradi. «Buyurtmalarim»da kuzating!",
      ownerCta: "👩‍🍳 Siz qandolatchimisiz? Egasi panelini ko'ring", ownerCtaSub: "Buyurtmalar, to'lovlar, kalendar",
      works: 'Bizning ishlarimiz', ratings: '{0} ta baho', gift: "Sovg'a", giftSend: "Sovg'a sifatida yuborish",
      giftSub: "Boshqa odamga, otkritka bilan", giftName: 'Oluvchining ismi', giftPhone: 'Oluvchining telefoni',
      giftNote: 'Otkritkaga yozuv (ixtiyoriy)', surprise: 'Syurpriz', surpriseSub: "Oluvchiga oldindan qo'ng'iroq qilmaymiz",
      needGift: "Oluvchining ismi va telefonini yozing", giftTo: "Sovg'a: {0}", err_gift: "Oluvchining ismi va telefonini tekshiring",
      rateT: 'Buyurtmani baholang', rateText: 'Fikringiz (ixtiyoriy)', rateSend: 'Baho berish', rateThanks: 'Rahmat! 💝',
      yourRating: 'Sizning bahoyingiz', inGallery: "«Bizning ishlarimiz»da ko'rsatish", inGalleryFoot: "Tayyor tort rasmi va baho ilova ichidagi galereyada ko'rinadi.",
      promo: 'Aksiyalar', promoT: 'Aksiya yuborish', promoTo: '{0} ta mijozga yuboriladi',
      promoPh: "Masalan: 🎄 Yangi yil setlariga buyurtmalar ochildi! 25-dekabrgacha 10% chegirma.",
      promoFoot: "Har bir xabar ostida «Katalogni ochish» tugmasi va obunani o'chirish imkoniyati bo'ladi.",
      promoQ: '{0} ta mijozga yuborilsinmi?', promoSent: '{0} ta mijozga yuborilmoqda', promoPast: 'Yuborilganlar',
      promoNone: "Hali aksiya yuborilmagan", needText: 'Xabar matnini yozing',
      wd: ['Yakshanba', 'Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma', 'Shanba'],
      wdS: ['Ya', 'Du', 'Se', 'Cho', 'Pa', 'Ju', 'Sha'],
      mon: ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentyabr', 'oktyabr', 'noyabr', 'dekabr'],
      monS: ['yan', 'fev', 'mar', 'apr', 'may', 'iyn', 'iyl', 'avg', 'sen', 'okt', 'noy', 'dek'],
      monN: ['Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun', 'Iyul', 'Avgust', 'Sentyabr', 'Oktyabr', 'Noyabr', 'Dekabr'],
    },
    ru: {
      featured: 'Сезонное предложение', all: 'Все', order: 'Заказать', continue: 'Продолжить',
      size: 'Размер', filling: 'Начинка', chooseFilling: 'Выберите начинку',
      inscription: 'Надпись на торте', inscriptionPh: 'Например: С днём рождения!',
      inscriptionFoot: 'Необязательно. До {0} символов.',
      refPhoto: 'Фото-референс', addPhoto: 'Добавить фото', changePhoto: 'Выбрать другое фото',
      refFoot: 'Какой дизайн хотите? Добавьте картинку, и кондитер украсит по ней.',
      checkoutTitle: 'Когда и куда?', date: 'Дата', time: 'Время',
      delivery: 'Доставка', pickup: 'Самовывоз',
      address: 'Адрес', addressPh: 'Район, улица, дом, ориентир',
      sendLocation: 'Отправить мою геолокацию', locationAdded: 'Геолокация добавлена', locDenied: 'Доступ к геолокации не разрешён',
      pickupFrom: 'Адрес самовывоза', free: 'бесплатно', full: 'занято', closedDay: 'выходной',
      feeFoot: 'Доставка по Ташкенту {0}. Бесплатно для заказов от {1}.', feeFootFlat: 'Доставка по Ташкенту {0}.',
      contact: 'Контакт', phonePh: '+998 90 123 45 67', shareContact: 'Поделиться номером из Telegram',
      phoneWait: 'Получаем номер…', phoneOk: 'Номер добавлен', typePhone: 'Введите номер вручную',
      check: 'Проверить', reviewTitle: 'Ваш заказ', items: 'Стоимость изделия', fee: 'Доставка', total: 'Итого',
      payNote: 'После подтверждения попросим предоплату {0}% картой, чтобы забронировать дату. Остаток при получении.',
      payNoteCash: 'Оплата при получении: наличными или картой.', placeOrder: 'Оформить заказ',
      noInscription: 'без надписи', none: 'нет', when: 'Дата и время', phone: 'Телефон',
      needDate: 'Выберите дату', needSlot: 'Выберите время', needAddress: 'Напишите адрес или отправьте геолокацию',
      needPhone: 'Введите корректный номер телефона',
      doneTitle: 'Заказ отправлен!', doneText: 'Кондитер скоро подтвердит заказ. О каждом этапе напишем в чате.',
      myOrders: 'Мои заказы', close: 'Закрыть', ordersEmptyT: 'Заказов пока нет', ordersEmpty: 'Выберите свой первый торт в каталоге 🎂',
      soldOut: 'Нет в наличии', soldOutMsg: 'Этого изделия сейчас нет',
      st_new: 'Отправлен', st_accepted: 'Принят', st_baking: 'Готовится', st_decorating: 'Украшается',
      st_ready: 'Готов', st_on_way: 'В пути', st_delivered: 'Выдан', st_rejected: 'Отклонён',
      tl_new: 'Заказ отправлен', tl_accepted: 'Принят', tl_baking: 'Готовится', tl_decorating: 'Украшается',
      tl_ready: 'Готов', tl_on_way: 'В пути', tl_delivered_d: 'Доставлен', tl_delivered_p: 'Выдан',
      d_new: 'Кондитер скоро рассмотрит заказ', d_accepted: 'Ваш заказ принят', d_baking: 'Торт в духовке 🔥',
      d_decorating: 'Украшаем ✨', d_ready_d: 'Готов! Скоро выедет к вам', d_ready_p: 'Готов! Можно забирать',
      d_on_way: 'Курьер в пути', d_delivered: 'Приятного аппетита! 💝', d_rejected: 'К сожалению, заказ не будет выполнен',
      payment: 'Оплата', payDue: 'Предоплата: {0}', payDueText: 'Чтобы забронировать дату, переведите на эту карту и загрузите чек:',
      copy: 'Копировать', copied: 'Скопировано', uploadReceipt: 'Загрузить чек', receiptSent: 'Чек отправлен, проверяется',
      paidT: 'Оплачено: {0}', restT: 'При получении: {0}', payOnDelivery: 'Оплата при получении', paidFull: 'Оплачено полностью',
      courier: 'Курьер', selfCourier: 'Привезёт сам кондитер', cakePhoto: 'Ваш готовый торт', details: 'Детали',
      rejectedNote: 'Вопросы: {0}',
      dash: 'Панель', today: 'Сегодня', tomorrow: 'Завтра', week: '7 дней',
      s_orders: 'Заказы', s_revenue: 'Выручка', s_paid: 'Предоплаты', s_unpaid: 'Ждут оплаты',
      pendingT: 'Ждут подтверждения', receiptsT: 'Проверьте чеки', ordersT: 'Заказы', noOrders: 'Заказов нет',
      calendar: 'Календарь', products: 'Товары', settings: 'Настройки', customer: 'Клиент', writeChat: 'Написать в Telegram',
      openMap: 'Открыть на карте', receipt: 'Чек об оплате',
      a_acc: 'Принять', a_rej: 'Отклонить', a_bak: 'Начала печь', a_dec: 'Украшаем', a_rdy: 'Готов',
      a_way: 'Выехал', a_dlv: 'Выдан', a_pok: 'Оплата подтверждена', a_pno: 'Оплата не найдена', a_paid: 'Оплата получена',
      rejectQ: 'Отклонить заказ? Клиент получит уведомление.', readyT: 'Торт готов', readyFoot: 'Фото готового торта отправим клиенту. Необязательно, но клиентам очень нравится.',
      markReady: 'Отметить готовым', courierT: 'Кто везёт?', courierPh: 'Имя и телефон', send: 'Отправить',
      selfBtn: 'Отвезу сам(а)', dayClosed: 'Выходной день', dayClosedFoot: 'На выходной день новые заказы не принимаются.',
      sold: 'В продаже', capacity: 'Заказов в день', capacityFoot: 'Когда заказов столько, день становится «занят». 0 = без ограничений.',
      deposit: 'Предоплата', depositFoot: 'Запрашивается после подтверждения. 0% = всё при получении.', card: 'Карта',
      cardFoot: 'Номер карты меняется в файле catalog.yaml.', autoMsgs: 'Автоматические сообщения',
      reminderAt: 'Напоминание клиенту (за день)', summaryAt: 'Утренняя сводка', done: 'Готово', saved: 'Сохранено',
      err_stale: 'Статус уже изменён', err_date_full: 'Этот день уже занят, выберите другой',
      err_sold_out: 'Этого изделия сейчас нет',
      err_auth: 'Откройте приложение заново кнопкой в боте', err_date: 'Эта дата уже недоступна, выберите другую',
      err_phone: 'Введите корректный номер телефона', err_address: 'Проверьте адрес', err_server: 'Что-то пошло не так. Попробуйте ещё раз',
      err_network: 'Проверьте подключение к интернету', err_photo_type: 'Можно загрузить только фото',
      outsideT: 'Откройте в Telegram', outside: 'Это приложение работает внутри Telegram-бота. Откройте бота и нажмите «Открыть каталог».',
      loadErr: 'Каталог не загрузился', retry: 'Повторить', demoNote: 'Просмотр в браузере: заказы не отправляются',
      showcaseNote: 'Демо: заказы не настоящие, кондитерская отвечает автоматически',
      showcaseDone: 'Это демо: статус заказа сам изменится за пару минут. Следите в «Мои заказы»!',
      ownerCta: '👩‍🍳 Вы кондитер? Посмотрите панель владельца', ownerCtaSub: 'Заказы, оплаты, календарь',
      works: 'Наши работы', ratings: '{0} оценок', gift: 'Подарок', giftSend: 'Отправить как подарок',
      giftSub: 'Другому человеку, с открыткой', giftName: 'Имя получателя', giftPhone: 'Телефон получателя',
      giftNote: 'Текст открытки (необязательно)', surprise: 'Сюрприз', surpriseSub: 'Не звоним получателю заранее',
      needGift: 'Укажите имя и телефон получателя', giftTo: 'Подарок: {0}', err_gift: 'Проверьте имя и телефон получателя',
      rateT: 'Оцените заказ', rateText: 'Ваш отзыв (необязательно)', rateSend: 'Оценить', rateThanks: 'Спасибо! 💝',
      yourRating: 'Ваша оценка', inGallery: 'Показывать в «Наших работах»', inGalleryFoot: 'Фото готового торта и оценка видны в галерее приложения.',
      promo: 'Акции', promoT: 'Отправить акцию', promoTo: 'Получат {0} клиентов',
      promoPh: 'Например: 🎄 Открыт приём заказов на новогодние сеты! До 25 декабря скидка 10%.',
      promoFoot: 'Под каждым сообщением будет кнопка «Открыть каталог» и возможность отписаться.',
      promoQ: 'Отправить {0} клиентам?', promoSent: 'Отправляем {0} клиентам', promoPast: 'Отправленные',
      promoNone: 'Акций ещё не было', needText: 'Напишите текст сообщения',
      wd: ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'],
      wdS: ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'],
      mon: ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'],
      monS: ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'],
      monN: ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'],
    },
  };

  const svg = (w, path, extra = '') => `<svg width="${w}" height="${w}" viewBox="0 0 24 24" ${extra}>${path}</svg>`;
  const stroke = 'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"';
  const ICON = {
    bag: svg(20, '<path d="M5.5 7.5h13l-1 12.5h-11z"/><path d="M9 9V6.5a3 3 0 0 1 6 0V9"/>', stroke),
    chart: svg(19, '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>', stroke),
    plus: svg(14, '<path d="M12 5v14M5 12h14"/>', 'fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"'),
    check: '<svg class="check" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7"/></svg>',
    tick: svg(13, '<path d="M5 12.5l4.5 4.5L19 7"/>', 'fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"'),
    chev: '<svg class="chev" width="8" height="14" viewBox="0 0 8 14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 1l6 6-6 6"/></svg>',
    left: '<svg width="9" height="15" viewBox="0 0 9 15" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M7.5 1.5 1.5 7.5l6 6"/></svg>',
    right: '<svg width="9" height="15" viewBox="0 0 9 15" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 1.5l6 6-6 6"/></svg>',
    camera: svg(17, '<path d="M3.5 8.5h3.5l2-3h6l2 3h3.5v11h-17z"/><circle cx="12" cy="13.5" r="3.5"/>', 'fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"'),
    pin: svg(17, '<path d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7zm0 9.6a2.6 2.6 0 1 1 0-5.2 2.6 2.6 0 0 1 0 5.2z"/>', 'fill="currentColor"'),
    phone: svg(16, '<path d="M6.6 10.8a15 15 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25c1.1.37 2.3.57 3.6.57a1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.57 3.6a1 1 0 0 1-.25 1z"/>', 'fill="currentColor"'),
    house: svg(17, '<path d="M12 3 2.5 11h2.7v9.5h5.3v-6h3v6h5.3V11h2.7z"/>', 'fill="currentColor"'),
    cal: svg(17, '<rect x="3.5" y="5" width="17" height="15.5" rx="3"/><path d="M3.5 10h17M8 3v4M16 3v4"/>', 'fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"'),
    cake: svg(17, '<path d="M4 20h16M5 20v-6.5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2V20M12 11.5V8M12 5.5v.01"/><path d="M5 15.5c1.5 1 3 1 4.5 0s3-1 4.5 0 3 1 5 0"/>', 'fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"'),
    gear: svg(17, '<circle cx="12" cy="12" r="3.2"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>', 'fill="none" stroke="currentColor" stroke-width="1.8"'),
    card: svg(17, '<rect x="2.5" y="5" width="19" height="14" rx="3"/><path d="M2.5 10h19M6.5 15h4"/>', 'fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"'),
    truck: svg(17, '<path d="M2.5 6.5h11v9h-11zM13.5 10h4l3 3v2.5h-7z"/><circle cx="6.5" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/>', 'fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"'),
    receiptSm: svg(17, '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2z"/><path d="M9 8h6M9 12h6"/>', 'fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"'),
    x: svg(11, '<path d="M6 6l12 12M18 6 6 18"/>', 'fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round"'),
    receipt: svg(30, '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2z"/><path d="M9 8h6M9 12h6"/>', 'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"'),
    megaphone: svg(17, '<path d="M3.5 10v4h3l7 4.5v-13l-7 4.5z"/><path d="M17 8.5a5 5 0 0 1 0 7"/>', 'fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"'),
    tg: svg(30, '<path d="M21.4 4.6 2.9 11.7c-1.3.5-1.3 1.2-.2 1.5l4.7 1.5 1.8 5.6c.2.6.1.9.8.9.5 0 .7-.2 1-.5l2.3-2.2 4.7 3.5c.9.5 1.5.2 1.7-.8l3.1-14.6c.3-1.3-.5-1.8-1.4-1.5z"/>', 'fill="currentColor"'),
  };
  const STATUS_EMOJI = { new: '📝', accepted: '✅', baking: '👩‍🍳', decorating: '🎨', ready: '🎂', on_way: '🚚', delivered: '💝', rejected: '😔' };

  // ------------------------------------------------------------------ state & helpers

  const state = {
    lang: 'uz', data: null, active: 0, cat: 'all', pages: [], sending: false, demoOrders: [],
    order: null,  // { p, size, filling, inscription, photo, photoUrl }
    co: { date: null, slot: null, method: 'delivery', address: '', lat: null, lon: null, phone: '', gift: null },
    range: 'today', calMonth: null,
  };

  const L = () => T[state.lang] || T.uz;
  const t = (k, ...a) => {
    let s = L()[k];
    if (s === undefined) s = T.uz[k] !== undefined ? T.uz[k] : k;
    a.forEach((v, i) => { s = s.replace('{' + i + '}', v); });
    return s;
  };
  const loc = o => (o ? (o[state.lang] || o.uz || '') : '');
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const money = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + ' ' + (state.lang === 'ru' ? 'сум' : "so'm");
  const ver = v => !!(tg && tg.isVersionAtLeast && tg.isVersionAtLeast(v));
  const isOwner = () => !!(state.data && state.data.isOwner);
  const namesOf = o => o.names[state.lang] || o.names.uz || Object.values(o.names)[0];

  function hap(kind) {
    try {
      const h = tg && tg.HapticFeedback;
      if (!h) return;
      if (kind === 'select') h.selectionChanged();
      else if (kind === 'success' || kind === 'error' || kind === 'warning') h.notificationOccurred(kind);
      else h.impactOccurred(kind || 'light');
    } catch (e) { /* older clients */ }
  }

  let toastTimer = 0;
  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove('show'), 2400);
  }

  function shake(el) {
    if (!el) return;
    el.classList.remove('shake');
    void el.offsetWidth;
    el.classList.add('shake');
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  async function copyText(text) {
    try { await navigator.clipboard.writeText(text); } catch (e) {
      const ta = document.createElement('textarea');
      ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); } catch (e2) { /* nothing else to try */ }
      ta.remove();
    }
    hap('success'); toast(t('copied'));
  }

  const parseISO = s => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); };
  const isoOf = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  function fmtDate(iso, withDay = true) {
    const d = parseISO(iso);
    const base = state.lang === 'uz' ? `${d.getDate()}-${L().mon[d.getMonth()]}` : `${d.getDate()} ${L().mon[d.getMonth()]}`;
    return withDay ? `${base}, ${L().wdS[d.getDay()]}` : base;
  }
  function fmtToday() {
    const d = new Date();
    const date = state.lang === 'uz' ? `${d.getDate()}-${L().mon[d.getMonth()]}` : `${d.getDate()} ${L().mon[d.getMonth()]}`;
    return `${L().wd[d.getDay()]}, ${date}`;
  }

  function normPhone(s) {
    const raw = String(s || '').trim();
    let d = raw.replace(/\D/g, '');
    if (d.length === 9) d = '998' + d;
    if (d.length === 12 && d.startsWith('998')) return '+' + d;
    if (raw.startsWith('+') && d.length >= 10 && d.length <= 15) return '+' + d;
    return null;
  }
  function fmtPhone(p) {
    const d = String(p || '').replace(/\D/g, '');
    return d.length === 12 && d.startsWith('998') ? `+998 ${d.slice(3, 5)} ${d.slice(5, 8)} ${d.slice(8, 10)} ${d.slice(10)}` : (p || '');
  }
  const fmtCard = c => String(c || '').replace(/\D/g, '').replace(/(\d{4})(?=\d)/g, '$1 ');

  function itemPrice() {
    const o = state.order;
    const size = o.p.sizes.find(z => z.id === o.size);
    const fill = o.p.fillings.find(f => f.id === o.filling);
    return (size ? size.price : 0) + (fill ? fill.extra : 0);
  }
  function deliveryFee(item) {
    if (state.co.method !== 'delivery') return 0;
    const s = state.data.shop;
    return s.freeFrom && item >= s.freeFrom ? 0 : s.fee;
  }

  const apiError = code => Object.assign(new Error(code), { code });
  async function call(path, init) {
    let r;
    try { r = await fetch('api/' + path, init); } catch (e) { throw apiError('network'); }
    let j = {};
    try { j = await r.json(); } catch (e) { /* not json */ }
    if (!r.ok) throw apiError(j.error || 'server');
    return j;
  }
  async function api(path, payload) {
    if (LOCAL) return LOCAL.call(path, payload);
    if (DEMO) {
      if (path === 'bootstrap') return call('demo?lang=' + (navigator.language || '').slice(0, 2), { method: 'GET' });
      if (path === 'orders') return { orders: state.demoOrders };
      return path === 'phone' ? { phone: null } : { ok: true };
    }
    return call(path, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(Object.assign({ initData: tg ? tg.initData : '' }, payload || {})),
    });
  }
  async function apiForm(path, fields) {
    if (LOCAL) return LOCAL.call(path, fields);
    const body = new FormData();
    body.append('initData', tg ? tg.initData : '');
    Object.entries(fields).forEach(([k, v]) => {
      if (v == null) return;
      if (v instanceof Blob) body.append(k, v, 'photo.jpg'); else body.append(k, String(v));
    });
    return call(path, { method: 'POST', body });
  }
  const errText = code => (L()['err_' + code] ? t('err_' + code) : t('err_server'));

  /* Phone photos are large; send at most 1280 px as JPEG (about 150 KB). */
  async function shrinkImage(file) {
    try {
      const bmp = await createImageBitmap(file);
      const k = Math.min(1, 1280 / Math.max(bmp.width, bmp.height));
      const c = document.createElement('canvas');
      c.width = Math.round(bmp.width * k); c.height = Math.round(bmp.height * k);
      c.getContext('2d').drawImage(bmp, 0, 0, c.width, c.height);
      const blob = await new Promise(res => c.toBlob(res, 'image/jpeg', 0.8));
      return blob || file;
    } catch (e) { return file; }
  }
  /* Opens the photo picker; resolves with a resized image or null. */
  function pickPhoto() {
    return new Promise(resolve => {
      const input = document.createElement('input');
      input.type = 'file'; input.accept = 'image/*'; input.hidden = true;
      input.addEventListener('change', async () => {
        const f = input.files && input.files[0];
        input.remove();
        resolve(f ? await shrinkImage(f) : null);
      });
      document.body.appendChild(input);
      input.click();
    });
  }

  // ------------------------------------------------------------------ Telegram chrome

  /* The bakery's own color (catalog.yaml: shop.brand.color). */
  function applyBrand(color) {
    if (!/^#[0-9a-f]{6}$/i.test(color || '')) return;
    document.documentElement.style.setProperty('--accent', color);
    document.documentElement.style.setProperty('--accent-soft', color + '1f');
  }
  const starsHtml = n => `<span class="stars">${'★'.repeat(n)}<i>${'★'.repeat(5 - n)}</i></span>`;

  function applyTheme() {
    const dark = tg && tg.colorScheme ? tg.colorScheme === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    const bg = dark ? '#000000' : '#f2f2f7';
    try {
      if (ver('6.1')) { tg.setHeaderColor(bg); tg.setBackgroundColor(bg); }
      if (ver('7.10')) tg.setBottomBarColor(bg);
    } catch (e) { /* older clients */ }
  }

  let mainHandler = null;
  function mainButton(text, onClick, opts) {
    if (!tg) return;
    const mb = tg.MainButton;
    if (mainHandler) { mb.offClick(mainHandler); mainHandler = null; }
    if (!text) { mb.hide(); return; }
    const accent = (opts && opts.color) || getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#ff2d55';
    const params = { text, color: accent, text_color: '#ffffff', is_visible: true, is_active: true };
    if (ver('7.10')) params.has_shine_effect = !!(opts && opts.shine);
    mb.setParams(params);
    mainHandler = () => { hap('medium'); onClick(); };
    mb.onClick(mainHandler);
  }

  function confirmBox(text) {
    return new Promise(resolve => {
      if (tg && ver('6.2') && tg.showConfirm) tg.showConfirm(text, ok => resolve(!!ok));
      else resolve(window.confirm(text));
    });
  }

  // ------------------------------------------------------------------ navigation stack (iOS push/pop)

  function syncChrome() {
    const top = state.pages[state.pages.length - 1];
    if (tg) {
      if (state.pages.length > 1) tg.BackButton.show(); else tg.BackButton.hide();
      if (ver('6.2')) { if (top && top.confirmClose) tg.enableClosingConfirmation(); else tg.disableClosingConfirmation(); }
    }
    if (top && top.onShow) top.onShow(); else mainButton(null);
  }

  function push(render, animate = true) {
    const page = document.createElement('section');
    page.className = 'page' + (animate && state.pages.length ? ' enter' : '');
    stackEl.appendChild(page);
    const prev = state.pages[state.pages.length - 1];
    state.pages.push(page);
    render(page);
    if (prev) {
      requestAnimationFrame(() => requestAnimationFrame(() => {
        page.classList.remove('enter');
        prev.classList.add('behind');
      }));
    }
    syncChrome();
    return page;
  }

  function pop() {
    if (state.pages.length < 2) return;
    const page = state.pages.pop();
    const prev = state.pages[state.pages.length - 1];
    if (page.onLeave) page.onLeave();
    page.classList.add('leave');
    prev.classList.remove('behind');
    setTimeout(() => page.remove(), 560);
    if (prev.refresh) prev.refresh();
    syncChrome();
  }

  function reset(render) {
    state.pages.forEach(p => { if (p.onLeave) p.onLeave(); p.remove(); });
    state.pages = [];
    return push(render, false);
  }

  const isTop = page => state.pages[state.pages.length - 1] === page;
  /* Big photos: show the small one (already loaded for the grid) at once, swap in the sharp one when it arrives. */
  function sharpen(root) {
    root.querySelectorAll('img[data-full]').forEach(img => {
      const full = new Image();
      full.onload = () => { img.src = full.src; };
      full.src = img.dataset.full;
      img.removeAttribute('data-full');
    });
  }
  /* Calls fn every `ms` while the page is on top and the app is visible. */
  function poll(page, fn, ms) {
    const id = setInterval(() => { if (isTop(page) && !document.hidden) fn(); }, ms);
    const prev = page.onLeave;
    page.onLeave = () => { clearInterval(id); if (prev) prev(); };
  }

  // ------------------------------------------------------------------ small shared pieces

  const pill = status => `<span class="status-pill st-${esc(status)}">${esc(t('st_' + status))}</span>`;
  const switchHtml = (on, attrs) => `<button class="switch${on ? ' on' : ''}" ${attrs} role="switch" aria-checked="${!!on}"></button>`;

  function progressBar(o) {
    if (o.status === 'rejected') return '';
    const k = o.steps.indexOf(o.status);
    return `<div class="bar">${o.steps.map((s, i) => `<i class="${i < k || (i === k && s === 'delivered') ? 'on' : i === k ? 'cur' : ''}"></i>`).join('')}</div>`;
  }

  function timeline(o) {
    const k = o.steps.indexOf(o.status);
    return `<div class="tl">${o.steps.map((s, i) => {
      const cls = i < k || (i === k && s === 'delivered') ? 'done' : i === k ? 'cur' : 'todo';
      const label = s === 'delivered' ? t(o.method === 'pickup' ? 'tl_delivered_p' : 'tl_delivered_d') : t('tl_' + s);
      return `<div class="tl-row ${cls}"><div class="tl-dot">${cls === 'todo' ? '' : ICON.tick}</div>
        <div class="tl-text">${esc(label)}</div><div class="tl-time">${esc((o.history || {})[s] || '')}</div></div>`;
    }).join('')}</div>`;
  }

  function statusLine(o) {
    if (o.status === 'ready') return t(o.method === 'pickup' ? 'd_ready_p' : 'd_ready_d');
    return t('d_' + o.status);
  }

  // ------------------------------------------------------------------ home

  function renderHome(page) {
    const d = state.data;
    const featured = d.products.find(p => p.featured && !p.soldOut);
    const chips = [{ id: 'all', label: t('all') }].concat(d.categories.map(c => ({ id: c.id, label: `${c.emoji} ${loc(c.name)}` })));
    page.innerHTML = `
      <div class="hero">
        <div>
          ${d.shop.logo ? `<img class="logo" src="${esc(d.shop.logo)}" alt="">` : ''}
          <div class="eyebrow">${esc(fmtToday())}</div>
          <h1 class="large-title">${esc(d.shop.name)}</h1>
          ${loc(d.shop.tagline) ? `<p class="tagline">${esc(loc(d.shop.tagline))}</p>` : ''}
        </div>
        <div class="hero-actions">
          <button class="circle-btn lang-btn" data-act="lang">${state.lang === 'uz' ? 'UZ' : 'RU'}</button>
          ${isOwner() ? `<button class="circle-btn" data-act="dash" aria-label="${esc(t('dash'))}">${ICON.chart}</button>` : ''}
          <button class="circle-btn" data-act="orders" aria-label="${esc(t('myOrders'))}">${ICON.bag}${state.active ? `<span class="badge">${state.active}</span>` : ''}</button>
        </div>
      </div>
      ${featured ? `
        <button class="featured${featured.photo ? '' : ' img-done'}" data-product="${esc(featured.id)}">
          ${featured.photo ? `<img src="${esc(featured.thumb)}" data-full="${esc(featured.photo)}" alt="">` : ''}
          <div class="featured-text">
            <div class="featured-kicker">${esc(t('featured'))}</div>
            <div class="featured-title">${esc(loc(featured.name))}</div>
            <div class="featured-row"><span class="featured-price">${esc(loc(featured.price))}</span><span class="pill-light">${esc(t('order'))}</span></div>
          </div>
        </button>` : ''}
      ${(d.gallery || []).length ? `
        <h2 class="section-title">${esc(t('works'))}</h2>
        <div class="gallery">${d.gallery.map((g, i) => `
          <button class="g-item" data-g="${i}"><div class="g-ph"><img loading="lazy" src="${esc(g.photo)}" alt=""></div>
            <div class="g-cap">${g.stars ? starsHtml(g.stars) : ''}<span>${esc(g.name)}</span></div></button>`).join('')}
        </div>` : ''}
      ${LOCAL ? `<button class="owner-cta" data-act="dash"><span><b>${esc(t('ownerCta'))}</b><small>${esc(t('ownerCtaSub'))}</small></span>${ICON.chev}</button>` : ''}
      <div class="chips-bar"><div class="chips">
        ${chips.map(c => `<button class="chip${c.id === state.cat ? ' on' : ''}" data-cat="${esc(c.id)}">${esc(c.label)}</button>`).join('')}
      </div></div>
      <div class="grid"></div>`;
    renderGrid(page);
    sharpen(page);

    page.addEventListener('click', e => {
      const el = e.target.closest('[data-product],[data-cat],[data-act],[data-g]');
      if (!el) return;
      if (el.dataset.g) { hap('light'); const g = state.data.gallery[Number(el.dataset.g)]; push(pg => renderWork(pg, g)); return; }
      if (el.dataset.product) { hap('light'); openProduct(el.dataset.product); }
      else if (el.dataset.cat) {
        if (state.cat === el.dataset.cat) return;
        hap('select');
        state.cat = el.dataset.cat;
        page.querySelectorAll('.chip').forEach(c => c.classList.toggle('on', c.dataset.cat === state.cat));
        el.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
        renderGrid(page);
      } else if (el.dataset.act === 'orders') { hap('light'); push(renderOrders); }
      else if (el.dataset.act === 'dash') { hap('light'); push(renderDash); }
      else if (el.dataset.act === 'lang') { switchLang(); }
    });
    const bar = page.querySelector('.chips-bar');
    page.addEventListener('scroll', () => bar.classList.toggle('scrolled', bar.getBoundingClientRect().top <= 0.5), { passive: true });
    page.refresh = () => {
      const btn = page.querySelector('[data-act="orders"]');
      const b = btn.querySelector('.badge');
      if (!state.active) { if (b) b.remove(); return; }
      if (b) b.textContent = state.active; else btn.insertAdjacentHTML('beforeend', `<span class="badge">${state.active}</span>`);
    };
    page.onShow = () => mainButton(null);
  }

  function renderGrid(page) {
    const list = state.data.products.filter(p => state.cat === 'all' || p.category === state.cat);
    page.querySelector('.grid').innerHTML = list.map((p, i) => `
      <button class="card${p.soldOut ? ' sold-out' : ''}" data-product="${esc(p.id)}" style="animation-delay:${Math.min(i, 8) * 45}ms">
        <div class="ph${p.thumb ? '' : ' img-done'}" style="background-color:${esc(p.color)}33">
          ${p.thumb ? `<img loading="lazy" decoding="async" src="${esc(p.thumb)}" alt="">` : `<span class="emoji">${esc(p.emoji)}</span>`}
          ${p.soldOut ? `<span class="sold-badge">${esc(t('soldOut'))}</span>` : ''}
          ${p.rating ? `<span class="rate-badge">★ ${p.rating.avg}</span>` : ''}
        </div>
        <div class="cb">
          <div class="cn">${esc(loc(p.name))}</div>
          <div class="cd">${esc(loc(p.desc))}</div>
          <div class="cf"><span class="cp">${esc(loc(p.price))}</span><span class="plus">${ICON.plus}</span></div>
        </div>
      </button>`).join('');
  }

  function renderWork(page, g) {
    const names = g.names[state.lang] || g.names.uz;
    page.innerHTML = `
      <div class="ready-photo work-photo"><img src="${esc(g.photo)}" alt=""></div>
      <div class="section"><div class="group"><div class="row"><span class="rl"><b>${esc(names.product)}</b><small>${esc(names.size)}${names.filling ? ' · ' + esc(names.filling) : ''}</small></span></div>
        ${g.stars ? `<div class="row"><span class="rl">${starsHtml(g.stars)}${g.text ? `<div class="work-text">«${esc(g.text)}»</div>` : ''}<small>— ${esc(g.name)}, ${esc(fmtDate(g.date, false))}</small></span></div>` : ''}
      </div></div>`;
    page.onShow = () => mainButton(null);
  }

  async function switchLang() {
    hap('select');
    state.lang = state.lang === 'uz' ? 'ru' : 'uz';
    document.documentElement.lang = state.lang;
    reset(renderHome);
    try { await api('lang', { lang: state.lang }); } catch (e) { /* the bot keeps the old language */ }
  }

  async function refreshData() {
    try {
      const d = await api('bootstrap');
      state.data = d;
      state.active = d.activeOrders || state.active;
    } catch (e) { /* keep what we have */ }
  }

  // ------------------------------------------------------------------ product

  function openProduct(id) {
    const p = state.data.products.find(x => x.id === id);
    if (!p) return;
    if (p.soldOut) { hap('warning'); toast(t('soldOutMsg')); return; }
    if (state.order && state.order.photoUrl) URL.revokeObjectURL(state.order.photoUrl);
    state.order = { p, size: p.sizes[0].id, filling: null, inscription: '', photo: null, photoUrl: null };
    push(renderProduct);
  }

  function renderProduct(page) {
    const o = state.order, p = o.p;
    const max = state.data.limits.inscription;
    page.confirmClose = true;
    page.innerHTML = `
      <div class="pp-hero${p.photo ? '' : ' img-done'}" style="background-color:${esc(p.color)}33">${p.photo ? `<img src="${esc(p.thumb)}" data-full="${esc(p.photo)}" alt="">` : ''}</div>
      <div class="pp-head">
        <h2 class="pp-name">${esc(loc(p.name))}</h2>
        ${p.rating ? `<div class="pp-rating">${starsHtml(Math.round(p.rating.avg))} <b>${p.rating.avg}</b> · ${esc(t('ratings', p.rating.n))}</div>` : ''}
        <p class="pp-desc">${esc(loc(p.desc))}</p>
        <div class="pp-price" id="price"></div>
      </div>
      <div class="section" id="sec-size">
        <div class="sh">${esc(t('size'))}</div>
        <div class="group">${p.sizes.map(z => `
          <button class="row${z.id === o.size ? ' sel' : ''}" data-size="${esc(z.id)}">
            <span class="rl">${esc(loc(z.name))}</span><span class="rv">${money(z.price)}</span>${ICON.check}
          </button>`).join('')}
        </div>
      </div>
      ${p.fillings.length ? `
      <div class="section" id="sec-filling">
        <div class="sh">${esc(t('filling'))}</div>
        <div class="group">${p.fillings.map(f => `
          <button class="row" data-filling="${esc(f.id)}">
            <span class="rl">${esc(loc(f.name))}</span>${f.extra ? `<span class="rv">+${money(f.extra)}</span>` : ''}${ICON.check}
          </button>`).join('')}
        </div>
      </div>` : ''}
      ${p.inscription ? `
      <div class="section">
        <div class="sh">${esc(t('inscription'))}</div>
        <div class="group"><label class="row field">
          <input id="ins" maxlength="${max}" placeholder="${esc(t('inscriptionPh'))}" value="${esc(o.inscription)}" enterkeyhint="done">
          <span class="count" id="ins-count">${o.inscription.length}/${max}</span>
        </label></div>
        <div class="sf">${esc(t('inscriptionFoot', max))}</div>
      </div>` : ''}
      ${p.photoRef ? `
      <div class="section">
        <div class="sh">${esc(t('refPhoto'))}</div>
        <div class="group" id="photo-group"></div>
        <div class="sf">${esc(t('refFoot'))}</div>
        <input type="file" id="file" accept="image/*" hidden>
      </div>` : ''}`;

    const update = () => {
      const price = itemPrice();
      page.querySelector('#price').innerHTML = money(price);
      page.onShow = () => mainButton(`${t('continue')} · ${money(price)}`, goCheckout);
      if (isTop(page)) page.onShow();
    };
    const renderPhoto = () => {
      const g = page.querySelector('#photo-group');
      if (!g) return;
      g.innerHTML = o.photoUrl ? `
        <div class="row">
          <img class="thumb" src="${o.photoUrl}" alt="">
          <button class="rl row-link" data-act="pick">${esc(t('changePhoto'))}</button>
          <button class="x-btn" data-act="unpick" aria-label="x">${ICON.x}</button>
        </div>` : `
        <button class="row icon-row" data-act="pick">
          <span class="row-icon" style="background:var(--orange)">${ICON.camera}</span>
          <span class="rl row-link">${esc(t('addPhoto'))}</span>
        </button>`;
    };
    renderPhoto();
    update();
    sharpen(page);

    page.addEventListener('click', e => {
      const el = e.target.closest('[data-size],[data-filling],[data-act]');
      if (!el) return;
      if (el.dataset.size) {
        o.size = el.dataset.size; hap('select');
        page.querySelectorAll('[data-size]').forEach(r => r.classList.toggle('sel', r === el));
        update();
      } else if (el.dataset.filling) {
        o.filling = el.dataset.filling; hap('select');
        page.querySelectorAll('[data-filling]').forEach(r => r.classList.toggle('sel', r === el));
        update();
      } else if (el.dataset.act === 'pick') {
        page.querySelector('#file').click();
      } else if (el.dataset.act === 'unpick') {
        hap('light');
        if (o.photoUrl) URL.revokeObjectURL(o.photoUrl);
        o.photo = null; o.photoUrl = null; renderPhoto();
      }
    });
    const ins = page.querySelector('#ins');
    if (ins) {
      ins.addEventListener('input', () => { o.inscription = ins.value; page.querySelector('#ins-count').textContent = `${ins.value.length}/${max}`; });
      ins.addEventListener('keydown', e => { if (e.key === 'Enter') ins.blur(); });
    }
    const file = page.querySelector('#file');
    if (file) {
      file.addEventListener('change', async () => {
        const f = file.files && file.files[0];
        file.value = '';
        if (!f) return;
        o.photo = await shrinkImage(f);
        if (o.photoUrl) URL.revokeObjectURL(o.photoUrl);
        o.photoUrl = URL.createObjectURL(o.photo);
        hap('success'); renderPhoto();
      });
    }

    function goCheckout() {
      if (p.fillings.length && !o.filling) {
        hap('error'); toast(t('chooseFilling')); shake(page.querySelector('#sec-filling'));
        return;
      }
      push(renderCheckout);
    }
  }

  // ------------------------------------------------------------------ checkout

  function renderCheckout(page) {
    const p = state.order.p, co = state.co, shop = state.data.shop;
    if (!p.dates.includes(co.date)) co.date = null;
    if (!co.phone && state.data.phone) co.phone = fmtPhone(state.data.phone);
    page.confirmClose = true;
    page.innerHTML = `
      <h2 class="page-title">${esc(t('checkoutTitle'))}</h2>
      <div class="section" id="sec-date">
        <div class="sh">${esc(t('date'))}</div>
        <div class="days">${p.days.map(({ d: iso, x }) => { const d = parseISO(iso); return `
          <button class="day${iso === co.date ? ' sel' : ''}${x ? ' off' : ''}" ${x ? 'disabled' : `data-date="${iso}"`}>
            <div class="dw">${esc(L().wdS[d.getDay()])}</div><div class="dn">${d.getDate()}</div>
            <div class="dm">${esc(x ? t(x === 'full' ? 'full' : 'closedDay') : L().monS[d.getMonth()])}</div>
          </button>`; }).join('')}
        </div>
      </div>
      <div class="section" id="sec-slot">
        <div class="sh">${esc(t('time'))}</div>
        <div class="slots">${shop.slots.map((s, i) => `<button class="slot${i === co.slot ? ' sel' : ''}" data-slot="${i}">${esc(s)}</button>`).join('')}</div>
      </div>
      <div class="section">
        <div class="segmented" data-v="${co.method === 'pickup' ? 1 : 0}" style="--n:2;--i:${co.method === 'pickup' ? 1 : 0}">
          <span class="seg-thumb"></span>
          <button class="seg${co.method === 'delivery' ? ' on' : ''}" data-method="delivery">${esc(t('delivery'))}</button>
          <button class="seg${co.method === 'pickup' ? ' on' : ''}" data-method="pickup">${esc(t('pickup'))}</button>
        </div>
      </div>
      <div id="where"></div>
      <div class="section" id="sec-phone">
        <div class="sh">${esc(t('contact'))}</div>
        <div class="group">
          <label class="row field icon-row">
            <span class="row-icon" style="background:var(--green)">${ICON.phone}</span>
            <input id="phone" type="tel" inputmode="tel" autocomplete="tel" placeholder="${esc(t('phonePh'))}" value="${esc(co.phone)}">
          </label>
          ${ver('6.9') && !LOCAL ? `<button class="row" data-act="contact"><span class="rl row-link">${esc(t('shareContact'))}</span></button>` : ''}
        </div>
      </div>`;

    let locationOk = false;
    const renderWhere = () => {
      const w = page.querySelector('#where');
      if (co.method === 'pickup') {
        w.innerHTML = `
          <div class="section">
            <div class="sh">${esc(t('pickupFrom'))}</div>
            <div class="group"><div class="row icon-row">
              <span class="row-icon" style="background:var(--accent)">${ICON.house}</span>
              <span class="rl">${esc(loc(shop.pickup))}</span><span class="rv">${esc(t('free'))}</span>
            </div></div>
          </div>`;
        return;
      }
      const foot = shop.freeFrom ? t('feeFoot', money(shop.fee), money(shop.freeFrom)) : t('feeFootFlat', money(shop.fee));
      w.innerHTML = `
        <div class="section" id="sec-address">
          <div class="sh">${esc(t('address'))}</div>
          <div class="group">
            <label class="row field"><textarea id="addr" rows="2" maxlength="${state.data.limits.address}" placeholder="${esc(t('addressPh'))}">${esc(co.address)}</textarea></label>
            ${locationOk ? (co.lat != null ? `
              <div class="row icon-row">
                <span class="row-icon" style="background:var(--blue)">${ICON.pin}</span>
                <span class="rl">${esc(t('locationAdded'))}<small>${co.lat.toFixed(5)}, ${co.lon.toFixed(5)}</small></span>
                <button class="x-btn" data-act="unlocate" aria-label="x">${ICON.x}</button>
              </div>` : `
              <button class="row icon-row" data-act="locate">
                <span class="row-icon" style="background:var(--blue)">${ICON.pin}</span>
                <span class="rl row-link">${esc(t('sendLocation'))}</span>
              </button>`) : ''}
          </div>
          <div class="sf">${esc(foot)}</div>
        </div>
        <div class="section" id="sec-gift">
          <div class="sh">🎁 ${esc(t('gift'))}</div>
          <div class="group">
            <div class="row"><span class="rl">${esc(t('giftSend'))}<small>${esc(t('giftSub'))}</small></span>${switchHtml(!!co.gift, 'data-act="gift"')}</div>
            ${co.gift ? `
            <label class="row field"><input id="g-name" maxlength="60" placeholder="${esc(t('giftName'))}" value="${esc(co.gift.name)}"></label>
            <label class="row field"><input id="g-phone" type="tel" inputmode="tel" placeholder="${esc(t('giftPhone'))}" value="${esc(co.gift.phone)}"></label>
            <label class="row field"><textarea id="g-note" rows="2" maxlength="150" placeholder="${esc(t('giftNote'))}">${esc(co.gift.note)}</textarea></label>
            <div class="row"><span class="rl">${esc(t('surprise'))}<small>${esc(t('surpriseSub'))}</small></span>${switchHtml(co.gift.surprise, 'data-act="surprise"')}</div>` : ''}
          </div>
        </div>`;
      ['name', 'phone', 'note'].forEach(k => {
        const el = w.querySelector('#g-' + k);
        if (el) el.addEventListener('input', () => { co.gift[k] = el.value; });
      });
      const addr = w.querySelector('#addr');
      addr.addEventListener('input', () => { co.address = addr.value; });
    };
    renderWhere();

    const lm = ver('8.0') && tg.LocationManager;
    if (lm) {
      const ready = () => { locationOk = !!lm.isLocationAvailable; if (co.method === 'delivery') renderWhere(); };
      try { if (lm.isInited) ready(); else lm.init(ready); } catch (e) { /* no location support */ }
    }

    const phone = page.querySelector('#phone');
    phone.addEventListener('input', () => { co.phone = phone.value; });

    page.addEventListener('click', e => {
      const el = e.target.closest('[data-date],[data-slot],[data-method],[data-act]');
      if (!el) return;
      if (el.dataset.date) {
        co.date = el.dataset.date; hap('select');
        page.querySelectorAll('.day').forEach(b => b.classList.toggle('sel', b === el));
      } else if (el.dataset.slot !== undefined) {
        co.slot = Number(el.dataset.slot); hap('select');
        page.querySelectorAll('.slot').forEach(b => b.classList.toggle('sel', b === el));
      } else if (el.dataset.method) {
        if (co.method === el.dataset.method) return;
        co.method = el.dataset.method; hap('select');
        const seg = page.querySelector('.segmented');
        const i = co.method === 'pickup' ? 1 : 0;
        seg.dataset.v = i; seg.style.setProperty('--i', i);
        seg.querySelectorAll('.seg').forEach(b => b.classList.toggle('on', b === el));
        renderWhere();
      } else if (el.dataset.act === 'locate') {
        lm.getLocation(data => {
          if (!data) { hap('error'); toast(t('locDenied')); return; }
          co.lat = data.latitude; co.lon = data.longitude; hap('success'); renderWhere();
        });
      } else if (el.dataset.act === 'unlocate') {
        co.lat = co.lon = null; hap('light'); renderWhere();
      } else if (el.dataset.act === 'gift') {
        co.gift = co.gift ? null : { name: '', phone: '', note: '', surprise: false }; hap('select'); renderWhere();
      } else if (el.dataset.act === 'surprise') {
        co.gift.surprise = !co.gift.surprise; hap('select'); el.classList.toggle('on', co.gift.surprise);
      } else if (el.dataset.act === 'contact') {
        shareContact(phone);
      }
    });

    page.onShow = () => mainButton(t('check'), () => {
      if (!co.date) { hap('error'); toast(t('needDate')); return shake(page.querySelector('#sec-date')); }
      if (co.slot == null) { hap('error'); toast(t('needSlot')); return shake(page.querySelector('#sec-slot')); }
      if (co.method === 'delivery' && co.address.trim().length < 5 && co.lat == null) {
        hap('error'); toast(t('needAddress')); return shake(page.querySelector('#sec-address'));
      }
      if (co.method === 'delivery' && co.gift && (co.gift.name.trim().length < 2 || !normPhone(co.gift.phone))) {
        hap('error'); toast(t('needGift')); return shake(page.querySelector('#sec-gift'));
      }
      if (!normPhone(co.phone)) { hap('error'); toast(t('needPhone')); return shake(page.querySelector('#sec-phone')); }
      if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
      push(renderReview);
    });
  }

  /* requestContact only says whether the user agreed; the number itself reaches
     the bot as a chat message, and the app fetches it from the bot. */
  function shareContact(input) {
    tg.requestContact(ok => {
      if (!ok) return;
      toast(t('phoneWait'));
      let tries = 0;
      const tryOnce = async () => {
        try {
          const r = await api('phone');
          if (r.phone) {
            state.co.phone = fmtPhone(r.phone); state.data.phone = r.phone;
            input.value = state.co.phone; hap('success'); toast(t('phoneOk'));
            return;
          }
        } catch (e) { /* retry */ }
        if (++tries < 10) setTimeout(tryOnce, 700); else toast(t('typePhone'));
      };
      setTimeout(tryOnce, 500);
    });
  }

  // ------------------------------------------------------------------ review

  function renderReview(page) {
    const o = state.order, p = o.p, co = state.co, shop = state.data.shop;
    const size = p.sizes.find(z => z.id === o.size);
    const fill = p.fillings.find(f => f.id === o.filling);
    const item = itemPrice(), fee = deliveryFee(item);
    const where = co.method === 'pickup'
      ? loc(shop.pickup)
      : [co.address.trim(), co.lat != null ? `📍 ${t('locationAdded')}` : ''].filter(Boolean).join('\n');
    page.confirmClose = true;
    page.innerHTML = `
      <h2 class="page-title">${esc(t('reviewTitle'))}</h2>
      <div class="section">
        <div class="group">
          <div class="row">
            ${p.thumb ? `<img class="thumb thumb-lg" src="${esc(p.thumb)}" alt="">` : ''}
            <span class="rl"><b>${esc(loc(p.name))}</b><small>${esc(loc(size.name))}${fill ? ' · ' + esc(loc(fill.name)) : ''}</small></span>
          </div>
          ${p.inscription ? `<div class="row"><span class="rl">${esc(t('inscription'))}</span><span class="rv">${o.inscription.trim() ? '«' + esc(o.inscription.trim()) + '»' : esc(t('noInscription'))}</span></div>` : ''}
          ${p.photoRef ? `<div class="row"><span class="rl">${esc(t('refPhoto'))}</span>${o.photoUrl ? `<img class="thumb" src="${o.photoUrl}" alt="">` : `<span class="rv">${esc(t('none'))}</span>`}</div>` : ''}
          <div class="row"><span class="rl">${esc(t('when'))}</span><span class="rv">${esc(fmtDate(co.date))} · ${esc(shop.slots[co.slot])}</span></div>
          <div class="row"><span class="rl">${esc(co.method === 'pickup' ? t('pickup') : t('delivery'))}<small style="white-space:pre-line">${esc(where)}</small></span></div>
          ${co.method === 'delivery' && co.gift ? `<div class="row"><span class="rl">🎁 ${esc(t('giftTo', co.gift.name.trim()))}<small>${esc(fmtPhone(normPhone(co.gift.phone)))}${co.gift.surprise ? ' · ' + esc(t('surprise')) : ''}${co.gift.note.trim() ? ' · «' + esc(co.gift.note.trim()) + '»' : ''}</small></span></div>` : ''}
          <div class="row"><span class="rl">${esc(t('phone'))}</span><span class="rv">${esc(fmtPhone(normPhone(co.phone)))}</span></div>
        </div>
      </div>
      <div class="section">
        <div class="group">
          ${co.method === 'delivery' ? `
          <div class="row"><span class="rl">${esc(t('items'))}</span><span class="rv">${money(item)}</span></div>
          <div class="row"><span class="rl">${esc(t('fee'))}</span><span class="rv">${fee ? money(fee) : esc(t('free'))}</span></div>` : ''}
          <div class="row total-row"><span class="rl">${esc(t('total'))}</span><span class="rv">${money(item + fee)}</span></div>
        </div>
        <div class="sf">${esc(shop.deposit ? t('payNote', shop.deposit) : t('payNoteCash'))}</div>
      </div>`;
    page.onShow = () => mainButton(`${t('placeOrder')} · ${money(item + fee)}`, submit, { shine: true });
  }

  async function submit() {
    if (state.sending) return;
    state.sending = true;
    const o = state.order, co = state.co;
    if (tg) tg.MainButton.showProgress(false);
    const order = {
      product: o.p.id, size: o.size, filling: o.filling, inscription: o.inscription.trim(),
      date: co.date, slot: co.slot, method: co.method,
      address: co.method === 'delivery' ? co.address.trim() : '', lat: co.method === 'delivery' ? co.lat : null,
      lon: co.method === 'delivery' ? co.lon : null, phone: normPhone(co.phone),
      gift: co.method === 'delivery' && co.gift ? { name: co.gift.name.trim(), phone: normPhone(co.gift.phone), note: co.gift.note.trim(), surprise: co.gift.surprise } : null,
    };
    try {
      const j = await apiForm(DEMO ? 'demo/order' : 'order', { order: JSON.stringify(order), photo: o.photo });
      hap('success');
      state.active += 1;
      state.co.gift = null;
      state.data.phone = order.phone;
      if (DEMO) {
        const now = new Date();
        const steps = ['new', 'accepted', 'baking', 'decorating', 'ready'].concat(co.method === 'delivery' ? ['on_way'] : [], ['delivered']);
        state.demoOrders.unshift({
          num: 0, code: j.code, status: 'new', history: { new: now.toTimeString().slice(0, 5) }, steps,
          names: { [state.lang]: { product: loc(o.p.name), size: loc(o.p.sizes.find(z => z.id === o.size).name) } },
          date: co.date, slot: state.data.shop.slots[co.slot], method: co.method, address: order.address,
          total: itemPrice() + deliveryFee(itemPrice()), item: itemPrice(), fee: deliveryFee(itemPrice()),
          deposit: 0, paid: 0, payment: 'none', photo: o.p.thumb,
        });
        setTimeout(() => toast(t('demoNote')), 1200);
      }
      reset(page => renderDone(page, j.code));
      confetti();
    } catch (e) {
      hap('error');
      toast(errText(e.code));
      if (e.code === 'date_full' || e.code === 'sold_out') {
        await refreshData();
        state.co.date = null;
        state.order.p = state.data.products.find(x => x.id === o.p.id) || o.p;
        pop(); pop();
        if (e.code === 'date_full') push(renderCheckout);
      }
    } finally {
      state.sending = false;
      if (tg) tg.MainButton.hideProgress();
    }
  }

  // ------------------------------------------------------------------ success

  function renderDone(page, code) {
    page.innerHTML = `
      <div class="done">
        <svg class="done-badge" viewBox="0 0 100 100" fill="none" stroke="var(--green)" stroke-width="6" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="50" cy="50" r="45"/><path d="M30 52l13 13 27-29"/>
        </svg>
        <h2>${esc(t('doneTitle'))}</h2>
        <span class="code">#${esc(code)}</span>
        <p>${esc(t(LOCAL ? 'showcaseDone' : 'doneText'))}</p>
        <button class="tinted-btn" data-act="orders">${esc(t('myOrders'))}</button>
      </div>`;
    page.addEventListener('click', e => {
      if (!e.target.closest('[data-act="orders"]')) return;
      hap('light');
      reset(renderHome);
      push(renderOrders);
    });
    page.onShow = () => mainButton(t('close'), () => tg.close());
  }

  function confetti() {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const box = document.createElement('div');
    box.className = 'confetti';
    const colors = ['#ff2d55', '#ff9500', '#ffcc00', '#34c759', '#5ac8fa', '#af52de'];
    for (let i = 0; i < 36; i++) {
      const c = document.createElement('i');
      c.style.left = Math.random() * 100 + '%';
      c.style.background = colors[i % colors.length];
      c.style.animationDelay = Math.random() * 0.35 + 's';
      c.style.setProperty('--dx', (Math.random() * 160 - 80) + 'px');
      c.style.setProperty('--rot', (Math.random() * 720 - 360) + 'deg');
      box.appendChild(c);
    }
    document.body.appendChild(box);
    setTimeout(() => box.remove(), 3200);
  }

  // ------------------------------------------------------------------ my orders (live)

  function renderOrders(page) {
    let orders = null;
    const paint = () => {
      page.innerHTML = `<h2 class="page-title">${esc(t('myOrders'))}</h2><div id="list" style="margin-top:18px">${
        orders === null ? [0, 1].map(() => '<div class="order-card"><div class="skeleton" style="height:64px"></div></div>').join('')
          : orders.length ? orders.map(orderCard).join('')
            : `<div class="empty"><div class="empty-icon">${ICON.receipt}</div><h3>${esc(t('ordersEmptyT'))}</h3>${esc(t('ordersEmpty'))}</div>`}</div>`;
    };
    const load = async () => {
      try {
        const before = orders;
        orders = (await api('orders')).orders;
        state.active = orders.filter(x => !['delivered', 'rejected'].includes(x.status)).length;
        if (before) notifyChanges(before, orders);
        paint();
      } catch (e) { if (orders === null) page.innerHTML = `<div class="empty"><h3>${esc(errText(e.code))}</h3></div>`; }
    };
    paint();
    load();
    poll(page, load, POLL);
    page.addEventListener('click', e => {
      const el = e.target.closest('[data-code]');
      if (!el || !orders) return;
      hap('light');
      const o = orders.find(x => x.code === el.dataset.code);
      if (o) push(pg => renderMyOrder(pg, o));
    });
    page.refresh = load;
    page.onShow = () => mainButton(null);
  }

  /* A toast + vibration when an order the customer is watching moves to the next stage. */
  function notifyChanges(before, after) {
    const old = Object.fromEntries(before.map(x => [x.code, x.status]));
    const moved = after.find(x => old[x.code] && old[x.code] !== x.status);
    if (moved) { hap('success'); toast(`${STATUS_EMOJI[moved.status] || '🔔'} #${moved.code}: ${t('st_' + moved.status)}`); }
  }

  function orderCard(o) {
    const names = namesOf(o);
    const payBadge = o.payment === 'due' ? `<span class="pay-badge">💳 ${esc(t('payDue', money(o.deposit)))}</span>` : '';
    return `
      <button class="order-card" data-code="${esc(o.code)}">
        <div class="oc-top">
          ${o.photo ? `<img class="thumb" src="${esc(o.photo)}" alt="">` : ''}
          <div class="oc-main"><div class="oc-code">#${esc(o.code)} · ${esc(fmtDate(o.date))}</div><div class="oc-name">${esc(names.product)} · ${esc(names.size)}</div></div>
          ${pill(o.status)}
        </div>
        ${progressBar(o)}
        <div class="oc-foot"><span>${esc(statusLine(o))}</span><b>${money(o.total)}</b></div>
        ${payBadge}
      </button>`;
  }

  function renderMyOrder(page, order) {
    let o = order, picked = 0;
    const shop = state.data.shop;
    const paint = () => {
      const names = namesOf(o);
      const rest = o.total - o.paid;
      let pay = '';
      if (o.status !== 'rejected' && o.payment === 'due') {
        pay = `
        <div class="section"><div class="sh">${esc(t('payment'))}</div>
          <div class="pay-card">
            <div class="pay-amount">${esc(t('payDue', money(o.deposit)))}</div>
            <div class="pay-text">${esc(t('payDueText'))}</div>
            <button class="card-number" data-act="copy">${esc(fmtCard(shop.card))}<span>${esc(t('copy'))}</span></button>
            <div class="pay-holder">${esc(shop.cardHolder)}</div>
            <button class="action-btn" data-act="receipt">${esc(t('uploadReceipt'))}</button>
          </div>
          <div class="sf">${esc(t('restT', money(o.total - o.deposit)))}</div></div>`;
      } else if (o.status !== 'rejected' && o.payment === 'review') {
        pay = `
        <div class="section"><div class="sh">${esc(t('payment'))}</div><div class="group">
          <div class="row icon-row"><span class="row-icon" style="background:var(--orange)">${ICON.receiptSm}</span>
          <span class="rl">${esc(t('receiptSent'))}</span></div></div></div>`;
      } else if (o.payment === 'paid') {
        pay = `
        <div class="section"><div class="sh">${esc(t('payment'))}</div><div class="group">
          <div class="row icon-row"><span class="row-icon" style="background:var(--green)">${ICON.card}</span>
          <span class="rl">${esc(t('paidT', money(o.paid)))}<small>${rest > 0 ? esc(t('restT', money(rest))) : esc(t('paidFull'))}</small></span></div></div></div>`;
      }
      page.innerHTML = `
        <div class="status-hero">
          <div class="big">${STATUS_EMOJI[o.status] || '🎂'}</div>
          <div><div class="oc-code">#${esc(o.code)}</div><h3>${esc(t('st_' + o.status))}</h3><p>${esc(statusLine(o))}</p></div>
        </div>
        ${o.readyPhoto ? `<div class="section"><div class="sh">${esc(t('cakePhoto'))}</div><div class="ready-photo"><img src="${esc(o.readyPhoto)}" alt=""></div></div>` : ''}
        ${o.courier && o.status === 'on_way' ? `<div class="section"><div class="group"><div class="row icon-row">
          <span class="row-icon" style="background:var(--blue)">${ICON.truck}</span>
          <span class="rl">${esc(t('courier'))}<small>${esc(o.courier === 'self' ? t('selfCourier') : o.courier)}</small></span></div></div></div>` : ''}
        ${pay}
        ${o.status === 'rejected' ? `<div class="section"><div class="sf">${esc(t('rejectedNote', shop.phone))}</div></div>` : `
        <div class="section"><div class="group tl-group">${timeline(o)}</div></div>`}
        ${o.status === 'delivered' && !o.rating ? `
        <div class="section" id="sec-rate"><div class="sh">${esc(t('rateT'))}</div><div class="rate-card">
          <div class="star-row">${[1, 2, 3, 4, 5].map(k => `<button class="star${k <= picked ? ' on' : ''}" data-star="${k}">★</button>`).join('')}</div>
          <textarea id="rv-text" rows="2" maxlength="500" placeholder="${esc(t('rateText'))}"></textarea>
          <button class="action-btn" data-act="rate"${picked ? '' : ' disabled'}>${esc(t('rateSend'))}</button>
        </div></div>` : ''}
        ${o.rating ? `<div class="section"><div class="group"><div class="row"><span class="rl">${esc(t('yourRating'))}${o.review ? `<small>«${esc(o.review)}»</small>` : ''}</span>${starsHtml(o.rating)}</div></div></div>` : ''}
        <div class="section"><div class="sh">${esc(t('details'))}</div><div class="group">
          <div class="row">${o.photo ? `<img class="thumb" src="${esc(o.photo)}" alt="">` : ''}<span class="rl"><b>${esc(names.product)}</b><small>${esc(names.size)}${names.filling ? ' · ' + esc(names.filling) : ''}</small></span></div>
          <div class="row"><span class="rl">${esc(t('when'))}</span><span class="rv">${esc(fmtDate(o.date))} · ${esc(o.slot)}</span></div>
          <div class="row"><span class="rl">${esc(o.method === 'pickup' ? t('pickup') : t('delivery'))}<small>${esc(o.method === 'pickup' ? loc(shop.pickup) : (o.address || t('locationAdded')))}</small></span></div>
          ${o.gift ? `<div class="row"><span class="rl">🎁 ${esc(t('giftTo', o.gift.name))}<small>${esc(fmtPhone(o.gift.phone))}${o.gift.surprise ? ' · ' + esc(t('surprise')) : ''}${o.gift.note ? ' · «' + esc(o.gift.note) + '»' : ''}</small></span></div>` : ''}
          <div class="row total-row"><span class="rl">${esc(t('total'))}</span><span class="rv">${money(o.total)}</span></div>
        </div></div>`;
    };
    paint();
    page.addEventListener('click', async e => {
      const el = e.target.closest('[data-act],[data-star]');
      if (!el) return;
      if (el.dataset.star) {
        picked = Number(el.dataset.star); hap('select');
        page.querySelectorAll('.star').forEach(b => b.classList.toggle('on', Number(b.dataset.star) <= picked));
        page.querySelector('[data-act="rate"]').disabled = false;
        return;
      }
      if (el.dataset.act === 'rate') {
        el.disabled = true;
        try {
          const r = await api('review', { num: o.num, stars: picked, text: page.querySelector('#rv-text').value });
          o = r.order; hap('success'); toast(t('rateThanks')); paint();
        } catch (err) { hap('error'); toast(errText(err.code)); el.disabled = false; }
        return;
      }
      if (el.dataset.act === 'copy') copyText(String(shop.card).replace(/\D/g, ''));
      else if (el.dataset.act === 'receipt') {
        const photo = await pickPhoto();
        if (!photo) return;
        el.disabled = true;
        try {
          const r = await apiForm('receipt', { num: o.num, photo });
          o = r.order; hap('success'); toast(t('receiptSent')); paint();
        } catch (err) { hap('error'); toast(errText(err.code)); el.disabled = false; }
      }
    });
    if (!DEMO) {
      poll(page, async () => {
        try {
          const fresh = (await api('orders')).orders.find(x => x.code === o.code);
          if (fresh && JSON.stringify(fresh) !== JSON.stringify(o)) { notifyChanges([o], [fresh]); o = fresh; paint(); }
        } catch (e) { /* next time */ }
      }, POLL);
    }
    page.onShow = () => mainButton(null);
  }

  // ------------------------------------------------------------------ owner dashboard

  function renderDash(page) {
    let data = null;
    const ranges = ['today', 'tomorrow', 'week'];
    const paint = () => {
      const i = ranges.indexOf(state.range);
      const s = data && data.stats;
      const list = (title, orders) => orders.length ? `
        <div class="section"><div class="sh">${esc(title)} (${orders.length})</div><div class="group">${orders.map(adminRow).join('')}</div></div>` : '';
      page.innerHTML = `
        <div class="hero"><div><div class="eyebrow">${esc(fmtToday())}</div><h1 class="large-title">${esc(t('dash'))}</h1></div></div>
        <div class="section" style="margin-top:12px">
          <div class="segmented" style="--n:3;--i:${i}">
            <span class="seg-thumb"></span>
            ${ranges.map(r => `<button class="seg${r === state.range ? ' on' : ''}" data-range="${r}">${esc(t(r))}</button>`).join('')}
          </div>
        </div>
        <div class="stats">
          ${[['s_orders', s ? s.orders : '–'], ['s_revenue', s ? money(s.revenue) : '–'], ['s_paid', s ? money(s.paid) : '–'], ['s_unpaid', s ? s.unpaid : '–']]
            .map(([k, v]) => `<div class="stat"><div class="k">${esc(t(k))}</div><div class="v">${esc(v)}</div></div>`).join('')}
        </div>
        ${data ? list(t('pendingT'), data.pending) + list(t('receiptsT'), data.review) : ''}
        <div class="section"><div class="sh">${esc(t('ordersT'))} · ${esc(t(state.range))}</div>
          <div class="group">${data === null ? '<div class="row"><div class="skeleton" style="height:40px;flex:1"></div></div>'
            : data.orders.length ? data.orders.map(adminRow).join('') : `<div class="row"><span class="rl" style="color:var(--label-2)">${esc(t('noOrders'))}</span></div>`}</div>
        </div>
        <div class="section"><div class="group">
          ${[['promo', ICON.megaphone, 'var(--orange)'], ['calendar', ICON.cal, 'var(--red)'], ['products', ICON.cake, 'var(--accent)'], ['settings', ICON.gear, '#8e8e93']].map(([k, icon, color]) => `
            <button class="row icon-row" data-nav="${k}"><span class="row-icon" style="background:${color}">${icon}</span><span class="rl">${esc(t(k))}</span>${ICON.chev}</button>`).join('')}
        </div></div>`;
    };
    const load = async () => {
      try { data = await api('admin/overview', { range: state.range }); paint(); } catch (e) { toast(errText(e.code)); }
    };
    paint();
    load();
    poll(page, load, 20000);
    page.addEventListener('click', e => {
      const el = e.target.closest('[data-range],[data-num],[data-nav]');
      if (!el) return;
      if (el.dataset.range) {
        if (state.range === el.dataset.range) return;
        hap('select'); state.range = el.dataset.range; paint(); load();
      } else if (el.dataset.num) { hap('light'); openAdminOrder(Number(el.dataset.num)); }
      else if (el.dataset.nav === 'calendar') { hap('light'); push(renderCalendar); }
      else if (el.dataset.nav === 'products') { hap('light'); push(renderProducts); }
      else if (el.dataset.nav === 'settings') { hap('light'); push(renderSettings); }
      else if (el.dataset.nav === 'promo') { hap('light'); push(renderPromo); }
    });
    page.refresh = load;
    page.onShow = () => mainButton(null);
  }

  function adminRow(o) {
    const names = namesOf(o);
    const pay = o.payment === 'review' ? ' · 🧾' : o.payment === 'due' ? ' · 💳' : '';
    return `<button class="row admin-row" data-num="${o.num}">
      <span class="slot-tag">${esc(fmtDate(o.date, false))}<br>${esc(String(o.slot).split('–')[0])}</span>
      <span class="rl"><b>${esc(names.product)}</b> · ${esc(names.size)}<small>#${esc(o.code)} · ${esc((o.customer && o.customer.name) || '')}${pay}</small></span>
      ${pill(o.status)}
    </button>`;
  }

  async function openAdminOrder(num) {
    try {
      const { order } = await api('admin/order', { num });
      push(page => renderAdminOrder(page, order));
    } catch (e) { toast(errText(e.code)); }
  }

  function renderAdminOrder(page, order) {
    let o = order;
    const shop = state.data.shop;
    const paint = () => {
      const names = namesOf(o);
      const c = o.customer;
      const actions = o.actions.filter(a => a !== 'rej');
      const payRow = o.payment === 'none' ? t('payOnDelivery') : o.payment === 'paid'
        ? `${t('paidT', money(o.paid))}${o.total - o.paid > 0 ? ' · ' + t('restT', money(o.total - o.paid)) : ''}`
        : `${t('payDue', money(o.deposit))}${o.payment === 'review' ? ' · 🧾' : ''}`;
      page.innerHTML = `
        <div class="status-hero">
          <div class="big">${STATUS_EMOJI[o.status] || '🎂'}</div>
          <div><div class="oc-code">#${esc(o.code)} · ${esc(fmtDate(o.date))} · ${esc(o.slot)}</div><h3>${esc(t('st_' + o.status))}</h3><p>${esc(names.product)} · ${esc(names.size)}</p></div>
        </div>
        ${actions.length || o.payment === 'due' || o.payment === 'review' ? `<div class="section actions">
          ${o.payment === 'review' && o.status !== 'rejected' ? `
            ${o.receipt ? `<div class="sh">${esc(t('receipt'))}</div><div class="ready-photo"><img src="${esc(o.receipt)}" alt=""></div>` : ''}
            <button class="action-btn green" data-pay="pok">${esc(t('a_pok'))}</button>
            <button class="action-btn danger" data-pay="pno">${esc(t('a_pno'))}</button>` : ''}
          ${actions.map((a, i) => `<button class="action-btn${i ? ' secondary' : ''}" data-action="${a}">${esc(t('a_' + a))}</button>`).join('')}
          ${o.payment === 'due' && o.status !== 'rejected' ? `<button class="action-btn secondary" data-pay="pok">💳 ${esc(t('a_paid'))}</button>` : ''}
        </div>` : ''}
        ${o.status === 'rejected' ? '' : `<div class="section"><div class="group tl-group">${timeline(o)}</div></div>`}
        ${o.readyPhoto ? `<div class="section"><div class="sh">${esc(t('cakePhoto'))}</div><div class="ready-photo"><img src="${esc(o.readyPhoto)}" alt=""></div></div>` : ''}
        <div class="section"><div class="sh">${esc(t('customer'))}</div><div class="group">
          <div class="row"><span class="rl"><b>${esc(c.name || '—')}</b>${c.username ? `<small>@${esc(c.username)}</small>` : ''}</span><span class="rv">${c.lang === 'ru' ? 'RU' : 'UZ'}</span></div>
          <button class="row icon-row" data-copy="${esc(o.phone)}"><span class="row-icon" style="background:var(--green)">${ICON.phone}</span><span class="rl">${esc(fmtPhone(o.phone))}</span><span class="rv row-link">${esc(t('copy'))}</span></button>
          ${c.username ? `<button class="row" data-tg="${esc(c.username)}"><span class="rl row-link">${esc(t('writeChat'))}</span>${ICON.chev}</button>` : ''}
        </div></div>
        <div class="section"><div class="sh">${esc(t('details'))}</div><div class="group">
          <div class="row">${o.photo ? `<img class="thumb" src="${esc(o.photo)}" alt="">` : ''}<span class="rl"><b>${esc(names.product)}</b><small>${esc(names.size)}${names.filling ? ' · ' + esc(names.filling) : ''}</small></span></div>
          ${o.inscription != null ? `<div class="row"><span class="rl">${esc(t('inscription'))}</span><span class="rv">${o.inscription ? '«' + esc(o.inscription) + '»' : esc(t('noInscription'))}</span></div>` : ''}
          ${o.refPhoto ? `<div class="row"><span class="rl">${esc(t('refPhoto'))}</span></div><div class="ready-photo inset"><img src="${esc(o.refPhoto)}" alt=""></div>` : ''}
          <div class="row"><span class="rl">${esc(o.method === 'pickup' ? t('pickup') : t('delivery'))}<small>${esc(o.method === 'pickup' ? loc(shop.pickup) : (o.address || t('locationAdded')))}</small></span></div>
          ${o.gift ? `<div class="row"><span class="rl">🎁 ${esc(t('giftTo', o.gift.name))}<small>${esc(fmtPhone(o.gift.phone))}${o.gift.surprise ? ' · ' + esc(t('surprise')) : ''}${o.gift.note ? ' · «' + esc(o.gift.note) + '»' : ''}</small></span></div>` : ''}
          ${o.mapUrl ? `<button class="row icon-row" data-map="${esc(o.mapUrl)}"><span class="row-icon" style="background:var(--blue)">${ICON.pin}</span><span class="rl row-link">${esc(t('openMap'))}</span>${ICON.chev}</button>` : ''}
          ${o.courier ? `<div class="row"><span class="rl">${esc(t('courier'))}</span><span class="rv">${esc(o.courier === 'self' ? t('selfCourier') : o.courier)}</span></div>` : ''}
          ${o.method === 'delivery' ? `<div class="row"><span class="rl">${esc(t('items'))}</span><span class="rv">${money(o.item)}</span></div>
          <div class="row"><span class="rl">${esc(t('fee'))}</span><span class="rv">${o.fee ? money(o.fee) : esc(t('free'))}</span></div>` : ''}
          <div class="row total-row"><span class="rl">${esc(t('total'))}</span><span class="rv">${money(o.total)}</span></div>
          <div class="row"><span class="rl">${esc(t('payment'))}</span><span class="rv">${esc(payRow)}</span></div>
          ${o.rating ? `<div class="row"><span class="rl">${starsHtml(o.rating)}${o.review ? `<small>«${esc(o.review)}»</small>` : ''}</span></div>` : ''}
        </div></div>
        ${o.status === 'delivered' && o.readyPhoto ? `<div class="section"><div class="group"><div class="row"><span class="rl">${esc(t('inGallery'))}</span>${switchHtml(o.inGallery, 'data-gal="1"')}</div></div>
          <div class="sf">${esc(t('inGalleryFoot'))}</div></div>` : ''}
        ${o.actions.includes('rej') ? `<div class="section"><button class="action-btn danger" data-action="rej">${esc(t('a_rej'))}</button></div>` : ''}`;
    };
    paint();
    const act = async (action, extra) => {
      try {
        const r = extra && 'photo' in extra
          ? await apiForm('admin/action', { num: o.num, action, photo: extra.photo })
          : await api('admin/action', Object.assign({ num: o.num, action }, extra || {}));
        o = r.order; hap('success'); toast(t('done')); paint();
      } catch (e) {
        hap('error'); toast(errText(e.code));
        try { o = (await api('admin/order', { num: o.num })).order; paint(); } catch (e2) { /* keep */ }
      }
    };
    page.addEventListener('click', async e => {
      const el = e.target.closest('[data-action],[data-pay],[data-copy],[data-tg],[data-map],[data-gal]');
      if (!el) return;
      if (el.dataset.gal) {
        hap('select'); el.classList.toggle('on');
        try { o = (await api('admin/gallery', { num: o.num, show: !o.inGallery })).order; paint(); } catch (err) { toast(errText(err.code)); }
        return;
      }
      if (el.dataset.copy) return copyText(el.dataset.copy);
      if (el.dataset.tg) return tg.openTelegramLink('https://t.me/' + el.dataset.tg);
      if (el.dataset.map) return tg.openLink(el.dataset.map);
      if (el.dataset.pay) return act(el.dataset.pay);
      const a = el.dataset.action;
      if (a === 'rej') { if (await confirmBox(t('rejectQ'))) act('rej'); return; }
      if (a === 'rdy') return push(pg => renderReadyPage(pg, o, photo => { pop(); act('rdy', { photo }); }));
      if (a === 'way') return push(pg => renderCourierPage(pg, courier => { pop(); act('way', { courier }); }));
      act(a);
    });
    poll(page, async () => {
      try {
        const fresh = (await api('admin/order', { num: o.num })).order;
        if (JSON.stringify(fresh) !== JSON.stringify(o)) { o = fresh; paint(); }
      } catch (e) { /* next time */ }
    }, 15000);
    page.onShow = () => mainButton(null);
  }

  function renderPromo(page) {
    let info = null, photo = null, url = null, text = '';
    const paint = () => {
      page.innerHTML = `
        <h2 class="page-title">${esc(t('promoT'))}</h2>
        <p class="page-sub">${info ? esc(t('promoTo', info.recipients)) : '…'}</p>
        <div class="section"><div class="group">
          <label class="row field"><textarea id="promo" rows="5" maxlength="1000" placeholder="${esc(t('promoPh'))}">${esc(text)}</textarea></label>
          ${url ? `<div class="row"><img class="thumb" src="${url}" alt=""><button class="rl row-link" data-act="pick">${esc(t('changePhoto'))}</button><button class="x-btn" data-act="unpick">${ICON.x}</button></div>`
                : `<button class="row icon-row" data-act="pick"><span class="row-icon" style="background:var(--orange)">${ICON.camera}</span><span class="rl row-link">${esc(t('addPhoto'))}</span></button>`}
        </div><div class="sf">${esc(t('promoFoot'))}</div></div>
        <div class="section"><div class="sh">${esc(t('promoPast'))}</div><div class="group">${info && info.items.length
          ? info.items.map(b => `<div class="row"><span class="rl">${esc(b.text.slice(0, 60))}${b.text.length > 60 ? '…' : ''}<small>${esc(b.created_at)}${b.has_photo ? ' · 📷' : ''}</small></span><span class="rv">${b.sent}/${b.recipients}</span></div>`).join('')
          : `<div class="row"><span class="rl" style="color:var(--label-2)">${esc(t('promoNone'))}</span></div>`}</div></div>`;
      page.querySelector('#promo').addEventListener('input', e => { text = e.target.value; });
    };
    const load = async () => { try { info = await api('admin/broadcasts'); paint(); } catch (e) { toast(errText(e.code)); } };
    paint(); load();
    page.addEventListener('click', async e => {
      const el = e.target.closest('[data-act]');
      if (!el) return;
      if (el.dataset.act === 'pick') {
        const ph = await pickPhoto();
        if (ph) { photo = ph; if (url) URL.revokeObjectURL(url); url = URL.createObjectURL(ph); paint(); }
      } else if (el.dataset.act === 'unpick') { photo = null; url = null; paint(); }
    });
    page.onShow = () => mainButton(t('send'), async () => {
      if (!text.trim()) { hap('error'); toast(t('needText')); return shake(page.querySelector('.group')); }
      if (!(await confirmBox(t('promoQ', info ? info.recipients : 0)))) return;
      try {
        const r = await apiForm('admin/broadcast', { text: text.trim(), photo });
        hap('success'); toast(t('promoSent', r.recipients));
        text = ''; photo = null; url = null; load();
      } catch (err) { hap('error'); toast(errText(err.code)); }
    });
  }

  function renderReadyPage(page, o, done) {
    let photo = null, url = null;
    const paint = () => {
      page.innerHTML = `
        <h2 class="page-title">${esc(t('readyT'))}</h2><p class="page-sub">#${esc(o.code)}</p>
        <div class="section">${url ? `<div class="ready-photo"><img src="${url}" alt=""></div>` : ''}
          <div class="group" style="${url ? 'margin-top:12px' : ''}">
            <button class="row icon-row" data-act="pick"><span class="row-icon" style="background:var(--orange)">${ICON.camera}</span><span class="rl row-link">${esc(url ? t('changePhoto') : t('addPhoto'))}</span></button>
          </div>
          <div class="sf">${esc(t('readyFoot'))}</div></div>`;
    };
    paint();
    page.addEventListener('click', async e => {
      if (!e.target.closest('[data-act="pick"]')) return;
      const p = await pickPhoto();
      if (!p) return;
      photo = p; if (url) URL.revokeObjectURL(url); url = URL.createObjectURL(p); hap('success'); paint();
    });
    page.onShow = () => mainButton(t('markReady'), () => done(photo), { color: '#34c759' });
  }

  function renderCourierPage(page, done) {
    page.innerHTML = `
      <h2 class="page-title">${esc(t('courierT'))}</h2>
      <div class="section"><div class="group">
        <label class="row field icon-row"><span class="row-icon" style="background:var(--blue)">${ICON.truck}</span>
          <input id="courier" placeholder="${esc(t('courierPh'))}" maxlength="120"></label>
        <button class="row" data-act="self"><span class="rl row-link">🙋 ${esc(t('selfBtn'))}</span></button>
      </div></div>`;
    const input = page.querySelector('#courier');
    page.addEventListener('click', e => { if (e.target.closest('[data-act="self"]')) { hap('light'); done('self'); } });
    page.onShow = () => mainButton(t('send'), () => {
      if (!input.value.trim()) { hap('error'); return shake(input.closest('.group')); }
      done(input.value.trim());
    });
  }

  function renderCalendar(page) {
    let month = state.calMonth || isoOf(new Date()).slice(0, 7), data = null;
    const paint = () => {
      const [y, m] = month.split('-').map(Number);
      const lead = (new Date(y, m - 1, 1).getDay() + 6) % 7;  // Monday first
      const wd = [1, 2, 3, 4, 5, 6, 0].map(i => L().wdS[i]);
      const cells = data ? data.days.map(dd => {
        const cls = ['cday'];
        if (dd.closed) cls.push('closed');
        else if (data.capacity && dd.n >= data.capacity) cls.push('full');
        else if (dd.n) cls.push('has');
        if (dd.d === data.today) cls.push('today');
        if (dd.d < data.today) cls.push('past');
        return `<button class="${cls.join(' ')}" data-day="${dd.d}"><span>${Number(dd.d.slice(8))}</span>
          <span class="cnt">${dd.closed ? '✕' : data.capacity ? `${dd.n}/${data.capacity}` : dd.n}</span></button>`;
      }).join('') : '';
      page.innerHTML = `
        <div class="cal-head"><h2 class="cal-title">${esc(L().monN[m - 1])} ${y}</h2>
          <div class="cal-nav"><button class="circle-btn" data-m="-1">${ICON.left}</button><button class="circle-btn" data-m="1">${ICON.right}</button></div></div>
        <div class="cal">${wd.map(w => `<div class="wd">${esc(w)}</div>`).join('')}${'<div></div>'.repeat(lead)}${cells}</div>
        <div class="sf" style="margin:14px 32px">${esc(t('capacityFoot'))}</div>`;
    };
    const load = async () => {
      try { data = await api('admin/calendar', { month }); paint(); } catch (e) { toast(errText(e.code)); }
    };
    paint(); load();
    page.addEventListener('click', e => {
      const el = e.target.closest('[data-m],[data-day]');
      if (!el) return;
      if (el.dataset.m) {
        hap('select');
        const [y, m] = month.split('-').map(Number);
        month = isoOf(new Date(y, m - 1 + Number(el.dataset.m), 1)).slice(0, 7);
        state.calMonth = month; data = null; paint(); load();
      } else { hap('light'); push(pg => renderDay(pg, el.dataset.day)); }
    });
    page.refresh = load;
    page.onShow = () => mainButton(null);
  }

  function renderDay(page, iso) {
    let data = null;
    const paint = () => {
      page.innerHTML = `
        <h2 class="page-title">${esc(fmtDate(iso))}</h2>
        <div class="section"><div class="group">
          <div class="row"><span class="rl">${esc(t('dayClosed'))}</span>${data ? switchHtml(data.closed, 'data-act="toggle"') : ''}</div>
        </div><div class="sf">${esc(t('dayClosedFoot'))}</div></div>
        <div class="section"><div class="sh">${esc(t('ordersT'))}</div><div class="group">${data === null ? '<div class="row"><div class="skeleton" style="height:40px;flex:1"></div></div>'
          : data.orders.length ? data.orders.map(adminRow).join('') : `<div class="row"><span class="rl" style="color:var(--label-2)">${esc(t('noOrders'))}</span></div>`}</div></div>`;
    };
    const load = async body => {
      try { data = await api('admin/day', Object.assign({ date: iso }, body || {})); paint(); } catch (e) { toast(errText(e.code)); }
    };
    paint(); load();
    page.addEventListener('click', e => {
      const el = e.target.closest('[data-act],[data-num]');
      if (!el) return;
      if (el.dataset.num) { hap('light'); openAdminOrder(Number(el.dataset.num)); return; }
      if (!data) return;
      hap('select'); el.classList.toggle('on'); load({ closed: !data.closed });
    });
    page.refresh = () => load();
    page.onShow = () => mainButton(null);
  }

  function renderProducts(page) {
    let products = null;
    const paint = () => {
      page.innerHTML = `<h2 class="page-title">${esc(t('products'))}</h2>
        <div class="section"><div class="sh">${esc(t('sold'))}</div><div class="group">${products === null ? '<div class="row"><div class="skeleton" style="height:44px;flex:1"></div></div>'
          : products.map(p => `<div class="row">${p.thumb ? `<img class="thumb" loading="lazy" src="${esc(p.thumb)}" alt="">` : ''}
            <span class="rl">${esc(loc(p.name))}<small>${esc(loc(p.price))}</small></span>${switchHtml(!p.soldOut, `data-id="${esc(p.id)}"`)}</div>`).join('')}</div></div>`;
    };
    const load = async () => { try { products = (await api('admin/products')).products; paint(); } catch (e) { toast(errText(e.code)); } };
    paint(); load();
    page.addEventListener('click', async e => {
      const el = e.target.closest('[data-id]');
      if (!el || !products) return;
      const p = products.find(x => x.id === el.dataset.id);
      p.soldOut = !p.soldOut; hap('select'); el.classList.toggle('on', !p.soldOut);
      try {
        await api('admin/product', { id: p.id, soldOut: p.soldOut });
        const mine = state.data.products.find(x => x.id === p.id);
        if (mine) mine.soldOut = p.soldOut;
      } catch (err) { toast(errText(err.code)); load(); }
    });
    page.onShow = () => mainButton(null);
  }

  function renderSettings(page) {
    let s = null;
    const stepper = (key, value, step) => `<div class="stepper"><button data-key="${key}" data-d="-${step}">−</button><b>${esc(value)}</b><button data-key="${key}" data-d="${step}">+</button></div>`;
    const paint = () => {
      page.innerHTML = `<h2 class="page-title">${esc(t('settings'))}</h2>${s === null ? '' : `
        <div class="section"><div class="group"><div class="row"><span class="rl">${esc(t('capacity'))}</span>${stepper('capacity', s.capacity, 1)}</div></div>
          <div class="sf">${esc(t('capacityFoot'))}</div></div>
        <div class="section"><div class="group"><div class="row"><span class="rl">${esc(t('deposit'))}</span>${stepper('deposit', s.deposit + '%', 10)}</div>
          <div class="row icon-row"><span class="row-icon" style="background:var(--blue)">${ICON.card}</span><span class="rl">${esc(fmtCard(s.card))}<small>${esc(s.cardHolder)}</small></span></div></div>
          <div class="sf">${esc(t('depositFoot'))} ${esc(t('cardFoot'))}</div></div>
        <div class="section"><div class="sh">${esc(t('autoMsgs'))}</div><div class="group">
          <div class="row"><span class="rl">${esc(t('summaryAt'))}</span><span class="rv">${esc(s.summary)}</span></div>
          <div class="row"><span class="rl">${esc(t('reminderAt'))}</span><span class="rv">${esc(s.reminder)}</span></div></div></div>`}`;
    };
    const save = async body => { try { s = await api('admin/settings', body || {}); paint(); if (body) toast(t('saved')); } catch (e) { toast(errText(e.code)); } };
    paint(); save();
    page.addEventListener('click', e => {
      const el = e.target.closest('[data-key]');
      if (!el || !s) return;
      const key = el.dataset.key, max = key === 'capacity' ? 99 : 100;
      const value = Math.max(0, Math.min(max, s[key] + Number(el.dataset.d)));
      if (value === s[key]) return;
      hap('select'); save({ [key]: value });
    });
    page.onShow = () => mainButton(null);
  }

  // ------------------------------------------------------------------ boot

  function renderSkeleton(page) {
    const card = `<div class="sk-card"><div class="skeleton" style="aspect-ratio:4/3;border-radius:0"></div>
      <div style="padding:10px 12px 12px"><div class="skeleton" style="width:70%;height:15px"></div>
      <div class="skeleton" style="width:95%;height:11px;margin-top:8px"></div><div class="skeleton" style="width:60%;height:11px;margin-top:5px"></div>
      <div class="skeleton" style="width:45%;height:13px;margin-top:12px"></div></div></div>`;
    page.innerHTML = `
      <div class="hero"><div style="width:100%"><div class="skeleton" style="width:42%;height:12px"></div>
        <div class="skeleton" style="width:68%;height:32px;margin-top:9px"></div>
        <div class="skeleton" style="width:55%;height:14px;margin-top:9px"></div></div></div>
      <div class="skeleton" style="height:210px;margin:14px 20px 6px;border-radius:22px"></div>
      <div class="chips" style="padding:10px 20px">${[0, 1, 2, 3, 4].map(() => '<div class="skeleton sk-chip"></div>').join('')}</div>
      <div class="grid">${card.repeat(4)}</div>`;
  }

  function renderMessage(page, title, text, retry) {
    page.innerHTML = `<div class="empty" style="padding-top:120px"><div class="empty-icon">${ICON.tg}</div>
      <h3>${esc(title)}</h3>${esc(text)}${retry ? `<div style="margin-top:22px"><button class="tinted-btn" data-act="retry">${esc(t('retry'))}</button></div>` : ''}</div>`;
    page.addEventListener('click', e => { if (e.target.closest('[data-act="retry"]')) boot(); });
  }

  /* Browser preview: on-page stand-ins for Telegram's bottom button and back button. */
  function browserTg() {
    document.body.classList.add('web');
    const btn = document.createElement('button');
    btn.className = 'web-main';
    const back = document.createElement('button');
    back.className = 'web-back';
    back.setAttribute('aria-label', 'Back');
    back.innerHTML = '<svg width="10" height="17" viewBox="0 0 10 17" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M8.5 1.5 1.5 8.5l7 7"/></svg>';
    document.body.append(btn, back);
    const MB = {
      handlers: [],
      setParams(p) {
        if ('text' in p) btn.textContent = p.text;
        if ('color' in p) btn.style.background = p.color;
        if ('is_visible' in p) btn.classList.toggle('show', !!p.is_visible);
        if ('is_active' in p) btn.disabled = !p.is_active;
        return MB;
      },
      onClick(f) { MB.handlers.push(f); return MB; },
      offClick(f) { MB.handlers = MB.handlers.filter(x => x !== f); return MB; },
      show() { btn.classList.add('show'); return MB; },
      hide() { btn.classList.remove('show'); return MB; },
      showProgress() { btn.classList.add('busy'); return MB; },
      hideProgress() { btn.classList.remove('busy'); return MB; },
    };
    btn.addEventListener('click', () => MB.handlers.slice().forEach(f => f()));
    const BB = { handlers: [], show() { back.classList.add('show'); }, hide() { back.classList.remove('show'); }, onClick(f) { BB.handlers.push(f); } };
    back.addEventListener('click', () => BB.handlers.forEach(f => f()));
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    return {
      initData: '', isVersionAtLeast: () => false,
      get colorScheme() { return mq.matches ? 'dark' : 'light'; },
      ready() {}, expand() {}, close() { toast(t('demoNote')); },
      onEvent(name, f) { if (name === 'themeChanged' && mq.addEventListener) mq.addEventListener('change', f); },
      MainButton: MB, BackButton: BB, HapticFeedback: null,
    };
  }

  async function boot() {
    reset(renderSkeleton);
    if (!DEMO && !LOCAL && !(tg && tg.initData)) { reset(page => renderMessage(page, t('outsideT'), t('outside'))); return; }
    try {
      const d = await api('bootstrap');
      state.data = d;
      applyBrand(d.shop.color);
      state.lang = d.lang === 'ru' ? 'ru' : 'uz';
      state.active = d.activeOrders || 0;
      document.documentElement.lang = state.lang;
      reset(renderHome);
      if (DEMO) toast(t('demoNote'));
      if (LOCAL) setTimeout(() => toast(t('showcaseNote')), 600);
      if (d.isOwner && PARAMS.has('admin')) {  // opened from the owner's "📊" buttons
        push(renderDash, false);
        if (PARAMS.get('order')) openAdminOrder(Number(PARAMS.get('order')));
      }
    } catch (e) {
      reset(page => renderMessage(page, t('loadErr'), errText(e.code), true));
    }
  }

  const markLoaded = e => {
    const img = e.target;
    if (img.tagName !== 'IMG') return;
    img.classList.add('loaded');
    if (img.parentElement) img.parentElement.classList.add('img-done');  // stop the shimmer
  };
  stackEl.addEventListener('load', markLoaded, true);
  stackEl.addEventListener('error', markLoaded, true);

  if (DEMO || (LOCAL && !(tg && tg.initData))) tg = browserTg();
  applyTheme();
  if (tg) {
    tg.ready();
    tg.expand();
    if (ver('7.7')) tg.disableVerticalSwipes();
    tg.onEvent('themeChanged', () => { applyTheme(); syncChrome(); });
    tg.BackButton.onClick(() => { hap('light'); pop(); });
  }
  boot();
})();
