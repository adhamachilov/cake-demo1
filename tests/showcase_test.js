// Browser test of the static showcase (what Netlify serves): no server, no Telegram.
//   cd tests && npm install            (once)
//   ../.venv/bin/python ../tools/build_showcase.py && node showcase_test.js
// It serves ../showcase itself and plays a visitor: catalog, gallery, gift order, the simulated
// bakery moving the order along, rating, then the owner dashboard and promotions.
const http = require('http');
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const ROOT = path.join(__dirname, '..', 'showcase');
const TYPES = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.json': 'application/json', '.jpg': 'image/jpeg', '.png': 'image/png' };
const server = http.createServer((req, res) => {
  const file = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]).replace(/^\/$/, '/index.html'));
  if (!file.startsWith(ROOT) || !fs.existsSync(file)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
});

const sleep = ms => new Promise(r => setTimeout(r, ms));
let n = 0;
const ok = m => { n++; console.log('  ✓', m); };
const fail = m => { console.error('  ✗', m); process.exit(1); };

server.listen(0, '127.0.0.1', async () => {
  const BASE = `http://127.0.0.1:${server.address().port}/`;
  try {
    let html = await (await fetch(BASE)).text();
    const scripts = [...html.matchAll(/<script src="((?:showcase|app)\.js[^"]*)"><\/script>/g)].map(m => m[1]);
    if (scripts.length !== 2 || !scripts[0].startsWith('showcase.js')) fail('index must load showcase.js before app.js');
    const code = await Promise.all(scripts.map(async s => (await fetch(BASE + s)).text()));
    html = html.replace(/<script src="[^"]*"><\/script>/g, '');
    const dom = new JSDOM(html, { url: BASE, runScripts: 'outside-only', pretendToBeVisual: true });
    const w = dom.window, d = w.document, errors = [];
    w.addEventListener('error', e => errors.push(String(e.error || e.message)));
    w.console.error = (...a) => errors.push(a.join(' '));
    w.matchMedia = q => ({ matches: false, media: q, addEventListener() {}, removeEventListener() {} });
    w.Element.prototype.scrollIntoView = function () {};
    w.URL.createObjectURL = () => 'blob:x'; w.URL.revokeObjectURL = () => {};
    w.confirm = () => true;
    w.fetch = (url, o) => fetch(new URL(url, BASE), o);
    code.forEach(c => w.eval(c));

    const top = () => { const p = d.querySelectorAll('.page:not(.leave)'); return p[p.length - 1]; };
    const tap = sel => { const el = top().querySelector(sel); if (!el) fail('no ' + sel); el.dispatchEvent(new w.MouseEvent('click', { bubbles: true })); };
    const press = () => d.querySelector('.web-main').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    const back = async () => { d.querySelector('.web-back').dispatchEvent(new w.MouseEvent('click', { bubbles: true })); await sleep(650); };
    const type = (sel, v) => { const el = top().querySelector(sel); el.value = v; el.dispatchEvent(new w.Event('input', { bubbles: true })); };
    const until = async (fn, what, ms = 6000) => { const e = Date.now() + ms; while (Date.now() < e) { if (fn()) return; await sleep(50); } fail('timeout: ' + what); };
    const hero = () => { const h = top().querySelector('.status-hero h3'); return h && h.textContent; };

    console.log('\nCatalog');
    await until(() => top().querySelectorAll('.card').length === 11, 'catalog');
    if (!top().querySelector('.owner-cta') || !top().querySelector('.rate-badge')) fail('owner entry/ratings');
    if (d.documentElement.style.getPropertyValue('--accent') !== '#ff2d55') fail('brand color');
    if (top().querySelector('.g-item') || top().querySelector('.hero .logo')) fail('gallery strip and logo should be gone');
    const titleRow = top().querySelector('.hero-top');
    if (!titleRow || !titleRow.querySelector('.eyebrow') || !titleRow.querySelector('.hero-actions')) fail('header layout');
    if (/namoyish|haqiqiy emas|demo/i.test(top().textContent + d.getElementById('toast').textContent)) fail('demo note shown');
    ok('header: date + buttons on one row, name below; brand color; ★ ratings; no gallery, no logo, no "demo" notes');

    console.log('\nGift order');
    tap('[data-product="medovik"]');
    await until(() => d.querySelector('.web-main.show'), 'product');
    press();
    await until(() => top().querySelector('.days'), 'checkout');
    tap('.day:not([disabled])'); tap('[data-slot="1"]');
    type('#addr', 'Chilonzor 9, 12-uy'); type('#phone', '901234567');
    tap('[data-act="gift"]');
    await until(() => top().querySelector('#g-name'), 'gift fields');
    press();
    if (top().querySelector('.total-row')) fail('gift without recipient must be blocked');
    type('#g-name', 'Madina'); type('#g-phone', '907654321'); tap('[data-act="surprise"]');
    press();
    await until(() => top().querySelector('.total-row'), 'review');
    if (!top().textContent.includes("Sovg'a: Madina")) fail('gift in review');
    press();
    await until(() => top().querySelector('.done'), 'done');
    ok('gift needs recipient name + phone, shows in the review; order placed ' + top().querySelector('.code').textContent);

    console.log('\nSimulated bakery');
    tap('[data-act="orders"]');
    await until(() => top().querySelector('.order-card .oc-top'), 'orders');
    tap('.order-card');
    await until(() => hero() === 'Qabul qilindi', 'auto accept', 12000);
    if (!top().querySelector('.card-number')) fail('deposit card');
    ok('~6 s later the bakery accepts it, deposit card shown, toast: ' + JSON.stringify(d.getElementById('toast').textContent));
    const realNow = w.Date.now.bind(w.Date);
    w.Date.now = () => realNow() + 125000;  // two minutes later
    await until(() => hero() === 'Topshirildi' && top().querySelector('.star-row'), 'delivered', 8000);
    tap('[data-star="5"]');
    top().querySelector('#rv-text').value = "Juda zo'r!";
    tap('[data-act="rate"]');
    await until(() => top().textContent.includes('Sizning bahoyingiz'), 'rated');
    ok('two minutes later: delivered with the cake photo; the visitor rates it 5 ★');
    await back(); await back();
    await until(() => top().querySelector('.owner-cta'), 'home');

    console.log('\nOwner dashboard');
    tap('.owner-cta');
    await until(() => top().querySelector('.stat .v') && top().querySelector('.stat .v').textContent !== '–', 'dashboard');
    if (!top().textContent.includes('Tasdiqlash kutilmoqda (1)') || !top().textContent.includes('Cheklarni tekshiring (1)')) fail('sample sections');
    tap('.section .admin-row');
    await until(() => top().querySelector('[data-action="acc"]'), 'pending order');
    tap('[data-action="acc"]');
    await until(() => hero() === 'Qabul qilindi', 'accepted');
    ok('sample orders; the owner accepts one');
    await back();
    tap('[data-nav="promo"]');
    await until(() => top().querySelector('#promo') && top().textContent.includes('128'), 'promo page');
    type('#promo', 'Yangi yil aksiyasi!');
    press();
    await until(() => top().textContent.includes('128/128'), 'promo sent');
    ok('promotions: sent to 128 (simulated) customers, listed under "sent"');
    await back();
    tap('[data-nav="calendar"]');
    await until(() => top().querySelectorAll('.cday.has, .cday.full').length >= 1, 'calendar');
    ok('calendar shows days with orders');

    if (errors.length) fail('JS errors: ' + errors.join(' | '));
    ok('no JavaScript errors');
    console.log(`\nALL ${n} SHOWCASE CHECKS PASSED`);
    process.exit(0);
  } catch (e) { fail(e.stack || e); }
});
