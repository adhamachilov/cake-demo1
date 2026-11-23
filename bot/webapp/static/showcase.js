/* Showcase backend for the static demo (Netlify): answers the Mini App's API calls inside the
   browser, so the demo works with no server and no bot running.

   - Orders are kept on the visitor's device only (localStorage).
   - The bakery is simulated: a visitor's order moves through every stage by itself in about
     two minutes, unless they drive it themselves from the owner dashboard.
   - The owner dashboard works on the same data, plus a few sample orders from "other customers".

   Included only by tools/build_showcase.py; the live bot never loads this file. */
(() => {
  'use strict';

  const KEY = 'shirin-showcase-v1';
  const STEP_AT = { accepted: 6, baking: 25, decorating: 45, ready: 65, on_way: 85, delivered: 105 };  // seconds
  const COURIER = 'Jasur, +998 90 111 22 33';
  const ACTIONS = {
    acc: ['accepted', ['new']], bak: ['baking', ['accepted']], dec: ['decorating', ['accepted', 'baking']],
    rdy: ['ready', ['accepted', 'baking', 'decorating']], way: ['on_way', ['ready']],
    dlv: ['delivered', ['ready', 'on_way']], rej: ['rejected', ['new', 'accepted', 'baking', 'decorating']],
  };
  const ACTIVE = ['new', 'accepted', 'baking', 'decorating', 'ready', 'on_way'];
  // a pretend bank receipt for orders whose payment is "being checked"
  const RECEIPT = 'data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="360" height="300" viewBox="0 0 360 300"><rect width="360" height="300" fill="#f4f6f8"/>' +
    '<rect x="30" y="24" width="300" height="252" rx="18" fill="#fff" stroke="#e2e6ea"/>' +
    '<circle cx="180" cy="78" r="26" fill="#34c759"/><path d="M168 78l8 8 16-17" stroke="#fff" stroke-width="5" fill="none" stroke-linecap="round"/>' +
    '<text x="180" y="138" text-anchor="middle" font-family="sans-serif" font-size="18" fill="#555">Perevod / Transfer</text>' +
    '<text x="180" y="180" text-anchor="middle" font-family="sans-serif" font-size="30" font-weight="700" fill="#111">205 000 UZS</text>' +
    '<text x="180" y="218" text-anchor="middle" font-family="sans-serif" font-size="15" fill="#888">8600 **** **** 9012</text>' +
    '<text x="180" y="246" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#aaa">DEMO</text></svg>');

  let cat = null;  // catalog.json
  let db = null;   // the visitor's data

  const err = code => Object.assign(new Error(code), { code });
  const pad = n => String(n).padStart(2, '0');
  const hhmm = ms => { const d = new Date(ms); return `${pad(d.getHours())}:${pad(d.getMinutes())}`; };
  const iso = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const day = n => { const d = new Date(); d.setHours(12, 0, 0, 0); d.setDate(d.getDate() + n); return iso(d); };
  const product = id => cat.products.find(p => p.id === id);
  const both = f => ({ uz: f('uz'), ru: f('ru') });

  // ------------------------------------------------------------------ storage

  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(db)); } catch (e) { /* private mode: keep in memory */ }
  }

  function load() {
    try { db = JSON.parse(localStorage.getItem(KEY)); } catch (e) { db = null; }
    if (!db || !Array.isArray(db.orders)) {
      db = { orders: [], next: 1001, closed: [], soldOut: [], capacity: cat.shop.capacity,
             deposit: cat.shop.deposit, lang: null, phone: null };
      seed();
      save();
    }
  }

  // ------------------------------------------------------------------ orders

  function depositFor(total) {
    return db.deposit ? Math.min(total, Math.ceil(total * db.deposit / 100 / 1000) * 1000) : 0;
  }

  function stepsOf(o) {
    return ['new', 'accepted', 'baking', 'decorating', 'ready'].concat(o.method === 'delivery' ? ['on_way'] : [], ['delivered']);
  }

  function makeOrder({ p, sizeId, fillingId, date, rel, slot, method, address, phone, inscription, name, mine }) {
    const size = p.sizes.find(z => z.id === sizeId) || p.sizes[0];
    const filling = p.fillings.find(f => f.id === fillingId) || null;
    const item = size.price + (filling ? filling.extra : 0);
    const fee = method === 'delivery' ? (cat.shop.freeFrom && item >= cat.shop.freeFrom ? 0 : cat.shop.fee) : 0;
    const t0 = Date.now();
    const o = {
      num: db.next++, mine: !!mine, manual: !mine, t0, rel, date, product: p.id,
      names: both(l => ({ product: p.name[l], size: size.name[l], filling: filling ? filling.name[l] : null })),
      slot: cat.shop.slots[slot] || cat.shop.slots[0], method, address: method === 'delivery' ? address : null,
      inscription: p.inscription ? (inscription || '') : null, phone, item, fee, total: item + fee,
      status: 'new', history: { new: hhmm(t0) }, deposit: 0, paid: 0, payment: 'none', courier: null,
      readyPhoto: null, receiptAt: 0, created: `${day(0)} ${hhmm(t0)}`,
      customer: { name, username: null, lang: 'uz' },
    };
    db.orders.push(o);
    return o;
  }

  function enter(o, status, at) {
    o.status = status;
    o.history[status] = hhmm(at || Date.now());
    if (status === 'accepted') { o.deposit = depositFor(o.total); o.payment = o.deposit ? 'due' : 'none'; }
    if (status === 'ready') o.readyPhoto = product(o.product) ? product(o.product).photo : null;
    if (status === 'on_way' && !o.courier) o.courier = COURIER;
  }

  /* The simulated bakery: moves a visitor's own order along by the clock. */
  function tick(o) {
    if (o.rel !== undefined && o.rel !== null) o.date = day(o.rel);  // sample orders stay "current"
    if (!o.mine || o.manual || o.status === 'rejected') return;
    const steps = stepsOf(o), seconds = (Date.now() - o.t0) / 1000;
    for (const s of steps.slice(1)) {
      const at = s === 'delivered' && o.method === 'pickup' ? STEP_AT.on_way : STEP_AT[s];
      if (seconds < at) break;
      if (steps.indexOf(s) > steps.indexOf(o.status)) enter(o, s, o.t0 + at * 1000);
    }
    if (o.payment === 'review' && Date.now() - o.receiptAt > 6000) { o.payment = 'paid'; o.paid = o.deposit; }
    if (o.payment === 'due' && steps.indexOf(o.status) >= steps.indexOf('baking')) { o.payment = 'paid'; o.paid = o.deposit; }
  }

  function nextActions(o) {
    return ({ new: ['acc', 'rej'], accepted: ['bak', 'rdy', 'rej'], baking: ['dec', 'rdy'], decorating: ['rdy'],
              ready: o.method === 'delivery' ? ['way', 'dlv'] : ['dlv'], on_way: ['dlv'] })[o.status] || [];
  }

  function json(o, admin) {
    const p = product(o.product);
    const out = {
      num: o.num, code: `${cat.shop.prefix}-${o.num}`, status: o.status, history: o.history, steps: stepsOf(o),
      names: o.names, date: o.date, slot: o.slot, method: o.method, address: o.address, lat: null, lon: null,
      inscription: o.inscription, total: o.total, item: o.item, fee: o.fee, deposit: o.deposit, paid: o.paid,
      payment: o.payment, courier: o.courier, created: o.created, photo: p ? p.thumb : null, readyPhoto: o.readyPhoto,
    };
    if (admin) {
      Object.assign(out, { customer: o.customer, phone: o.phone, actions: nextActions(o), mapUrl: null, refPhoto: null,
                           receipt: o.payment === 'review' ? RECEIPT : null });
    }
    return out;
  }

  /* A few orders from "other customers", so the owner dashboard isn't empty. Built from
     whatever products the catalog has, so it works for any bakery's catalog. */
  function seed() {
    const ps = cat.products.filter(p => !p.soldOut);
    const pick = i => ps[i % ps.length];
    const rows = [
      { i: 0, rel: 0, slot: 2, method: 'delivery', address: 'Chilonzor 9, 12-uy', name: 'Madina', phone: '+998901112233', to: 'baking', pay: 'paid' },
      { i: 4, rel: 0, slot: 3, method: 'pickup', name: 'Olga', phone: '+998935554411', to: 'ready', pay: 'paid' },
      { i: 1, rel: 1, slot: 1, method: 'delivery', address: 'Yunusobod 4, 17-uy', name: 'Sardor', phone: '+998977001122', to: 'new' },
      { i: 9, rel: 3, slot: 0, method: 'delivery', address: "Mirzo Ulug'bek, Buyuk Ipak Yo'li 15", name: 'Dilnoza', phone: '+998909998877', to: 'accepted', pay: 'review' },
    ];
    for (const r of rows) {
      const p = pick(r.i);
      const o = makeOrder({ p, sizeId: (p.sizes[1] || p.sizes[0]).id, fillingId: p.fillings[0] && p.fillings[0].id,
                            rel: r.rel, date: day(r.rel), slot: r.slot, method: r.method, address: r.address,
                            phone: r.phone, inscription: "Tug'ilgan kuning bilan!", name: r.name, mine: false });
      o.t0 -= 3 * 3600 * 1000;
      o.history = { new: hhmm(o.t0) };
      const steps = stepsOf(o);
      steps.slice(1, steps.indexOf(r.to) + 1).forEach((s, k) => enter(o, s, o.t0 + (k + 1) * 40 * 60 * 1000));
      if (r.pay === 'paid') { o.payment = 'paid'; o.paid = o.deposit; }
      if (r.pay === 'review') o.payment = 'review';
    }
  }

  // ------------------------------------------------------------------ catalog

  function days(p) {
    const out = [];
    for (let i = 0; i < cat.shop.bookingDays; i++) {
      const d = day(p.leadDays + i);
      const n = db.orders.filter(o => o.date === d && o.status !== 'rejected').length;
      out.push({ d, x: db.closed.includes(d) ? 'closed' : (db.capacity && n >= db.capacity ? 'full' : null) });
    }
    return out;
  }

  function catalogPayload() {
    return {
      shop: Object.assign({}, cat.shop, { deposit: db.deposit }),
      categories: cat.categories,
      products: cat.products.map(p => {
        const ds = days(p);
        return Object.assign({}, p, { soldOut: db.soldOut.includes(p.id), days: ds, dates: ds.filter(x => !x.x).map(x => x.d) });
      }),
      limits: cat.limits,
    };
  }

  const find = num => {
    const o = db.orders.find(x => x.num === Number(num));
    if (!o) throw err('not_found');
    return o;
  };
  const mine = () => db.orders.filter(o => o.mine);

  // ------------------------------------------------------------------ the "API"

  const API = {
    bootstrap: () => Object.assign({
      lang: db.lang || ((navigator.language || '').toLowerCase().startsWith('ru') ? 'ru' : 'uz'),
      phone: db.phone, firstName: '', activeOrders: mine().filter(o => ACTIVE.includes(o.status)).length,
      isOwner: true, showcase: true,
    }, catalogPayload()),
    lang: p => { db.lang = p.lang === 'ru' ? 'ru' : 'uz'; return { ok: true }; },
    phone: () => ({ phone: db.phone }),
    orders: () => ({ orders: mine().slice().reverse().map(o => json(o)) }),

    order: p => {
      const data = JSON.parse(p.order);
      const prod = product(data.product);
      if (!prod) throw err('product');
      if (db.soldOut.includes(prod.id)) throw err('sold_out');
      const d = days(prod).find(x => x.d === data.date);
      if (!d) throw err('date');
      if (d.x) throw err('date_full');
      db.phone = data.phone;
      const o = makeOrder({ p: prod, sizeId: data.size, fillingId: data.filling, date: data.date, rel: null, slot: data.slot,
                            method: data.method, address: data.address, phone: data.phone, inscription: data.inscription,
                            name: db.lang === 'ru' ? 'Вы' : 'Siz', mine: true });
      o.customer.lang = db.lang || 'uz';
      return { code: `${cat.shop.prefix}-${o.num}`, num: o.num };
    },

    receipt: p => {
      const o = find(p.num);
      if (o.payment !== 'due') throw err('stale');
      o.payment = 'review';
      o.receiptAt = Date.now();
      return { order: json(o) };
    },

    'admin/overview': p => {
      const t = day(0), ranges = { today: [t, t], tomorrow: [day(1), day(1)], week: [t, day(6)] };
      const [a, b] = ranges[p.range] || ranges.today;
      const inRange = db.orders.filter(o => o.date >= a && o.date <= b).sort((x, y) => (x.date + x.slot).localeCompare(y.date + y.slot));
      const live = inRange.filter(o => o.status !== 'rejected');
      const unpaid = db.orders.filter(o => ACTIVE.includes(o.status) && ['due', 'review'].includes(o.payment));
      return {
        today: t,
        stats: { orders: live.length, revenue: live.reduce((s, o) => s + o.total, 0),
                 paid: live.reduce((s, o) => s + o.paid, 0), unpaid: unpaid.length },
        pending: db.orders.filter(o => o.status === 'new').map(o => json(o, true)),
        review: unpaid.filter(o => o.payment === 'review').map(o => json(o, true)),
        orders: inRange.map(o => json(o, true)),
      };
    },
    'admin/order': p => ({ order: json(find(p.num), true) }),
    'admin/action': p => {
      const o = find(p.num);
      o.manual = true;  // the visitor is driving this order now
      if (p.action === 'pok' || p.action === 'pno') {
        if (!['due', 'review'].includes(o.payment)) throw err('stale');
        if (p.action === 'pok') { o.payment = 'paid'; o.paid = o.deposit || o.total; } else o.payment = 'due';
      } else {
        const rule = ACTIONS[p.action];
        if (!rule || !rule[1].includes(o.status) || (p.action === 'way' && o.method !== 'delivery')) throw err('stale');
        if (p.action === 'way') o.courier = p.courier || 'self';
        enter(o, rule[0]);
      }
      return { order: json(o, true) };
    },
    'admin/calendar': p => {
      const [y, m] = String(p.month || day(0).slice(0, 7)).split('-').map(Number);
      const last = new Date(y, m, 0).getDate();
      const list = [];
      for (let i = 1; i <= last; i++) {
        const d = `${y}-${pad(m)}-${pad(i)}`;
        list.push({ d, n: db.orders.filter(o => o.date === d && o.status !== 'rejected').length, closed: db.closed.includes(d) });
      }
      return { month: `${y}-${pad(m)}`, capacity: db.capacity, today: day(0), days: list };
    },
    'admin/day': p => {
      if ('closed' in p) {
        db.closed = db.closed.filter(d => d !== p.date);
        if (p.closed) db.closed.push(p.date);
      }
      return { date: p.date, closed: db.closed.includes(p.date), orders: db.orders.filter(o => o.date === p.date).map(o => json(o, true)) };
    },
    'admin/products': () => ({ products: catalogPayload().products }),
    'admin/product': p => {
      db.soldOut = db.soldOut.filter(id => id !== p.id);
      if (p.soldOut) db.soldOut.push(p.id);
      return { ok: true };
    },
    'admin/settings': p => {
      if (Number.isInteger(p.capacity)) db.capacity = Math.max(0, Math.min(99, p.capacity));
      if (Number.isInteger(p.deposit)) db.deposit = Math.max(0, Math.min(100, p.deposit));
      return { capacity: db.capacity, deposit: db.deposit, card: cat.shop.card, cardHolder: cat.shop.cardHolder,
               reminder: cat.shop.reminder, summary: cat.shop.summary };
    },
  };

  async function call(path, payload) {
    if (!cat) {
      const r = await fetch('catalog.json', { cache: 'no-cache' });
      if (!r.ok) throw err('server');
      cat = await r.json();
    }
    if (!db) load();
    db.orders.forEach(tick);
    const handler = API[path];
    if (!handler) throw err('server');
    const out = handler(payload || {});
    db.orders.forEach(tick);
    save();
    await new Promise(res => setTimeout(res, 90));  // feels like a real request
    return JSON.parse(JSON.stringify(out));
  }

  window.ShowcaseAPI = { call, reset() { try { localStorage.removeItem(KEY); } catch (e) { /* ignore */ } db = null; } };
})();
