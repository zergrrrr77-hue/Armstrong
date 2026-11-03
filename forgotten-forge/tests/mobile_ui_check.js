// 휴대폰 UI 점검: 설정·뽑기·상점·가방을 손가락으로 끝까지 밀 수 있는지, 공격 버튼, 가로 넘침
// 실행: node forgotten-forge/tests/mobile_ui_check.js
const { chromium } = require('playwright'); const path = require('path');
let fail = 0;
(async () => {
  const b = await chromium.launch();
  for (const vp of [{ width: 844, height: 390 }, { width: 390, height: 844 }]) {
    const ctx = await b.newContext({ viewport: vp, hasTouch: true, isMobile: true, deviceScaleFactor: 2 });
    const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
    await p.goto('file://' + path.resolve(__dirname + '/../index.html'));
    await p.waitForFunction(() => document.querySelectorAll('.cls').length === 3);
    await p.evaluate(() => localStorage.clear()); await p.locator('.cls').nth(0).click(); await p.click('#start'); await p.waitForTimeout(700);
    const cdp = await ctx.newCDPSession(p);
    const swipe = async (sel) => {
      const r = await p.locator(sel).boundingBox(); const x = r.x + r.width / 2, y0 = r.y + r.height * 0.75, y1 = r.y + r.height * 0.2;
      const T = (type, y) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: type === 'touchEnd' ? [] : [{ x, y, id: 1 }] });
      await T('touchStart', y0); for (let y = y0 - 12; y >= y1; y -= 12) { await T('touchMove', y); await p.waitForTimeout(16); } await T('touchEnd');
      await p.waitForTimeout(300);
      return p.evaluate(s => { const e = document.querySelector(s); return { top: e.scrollTop, max: e.scrollHeight - e.clientHeight }; }, sel);
    };
    const res = {};
    await p.evaluate(() => document.getElementById('btnOpt').click()); await p.waitForTimeout(200);
    res.opt = await swipe('#opt'); res.optHint = await p.evaluate(() => document.getElementById('opt').classList.contains('more'));
    await p.evaluate(() => { document.getElementById('opt').classList.add('hidden'); __game.P.gold = 500000; __game.toggleGacha(); __game.pullGacha(11); }); await p.waitForTimeout(400);
    res.gacha = await swipe('#gacha .gbody');
    await p.evaluate(() => { __game.toggleGacha(); const G = __game, n = G.map.npcs[0]; G.P.x = n.x + 1.2; G.P.y = n.y + 1; G.openShop(true); }); await p.waitForTimeout(300);
    res.shop = await swipe('#shop');
    await p.evaluate(() => { __game.closeShop(); document.getElementById('btnInv').click(); }); await p.waitForTimeout(300);
    res.inv = await swipe(vp.width > vp.height ? '#inv .doll' : '#inv .wbody');
    // 공격 버튼
    await p.evaluate(() => { document.getElementById('inv').classList.add('hidden'); const G = __game, m = G.mobs.find(x => x.type === 'goblin'); G.P.x = m.x + 3; G.P.y = m.y; });
    const atkVis = await p.evaluate(() => !document.getElementById('atkBtn').classList.contains('hidden'));
    const bb = await p.locator('#atkBtn').boundingBox();
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: bb.x + 30, y: bb.y + 30, id: 1 }] }); await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    await p.waitForTimeout(200);
    res.atk = atkVis && await p.evaluate(() => !!__game.P.target);
    res.overflow = await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth && document.documentElement.scrollHeight <= innerHeight + 1);
    const ok = (vp.width < vp.height || ((res.opt.top > 0 || res.opt.max === 0) && (res.shop.top > 0 || res.shop.max === 0))) && res.gacha.top > 0 && res.inv.top > 0 && res.atk && res.overflow && !errs.length; if (!ok) fail++; console.log((ok ? '  ✓ ' : '  ✗ ') + vp.width + 'x' + vp.height + ' 창 스크롤·공격 버튼·넘침 ' + JSON.stringify(res));
    await ctx.close();
  }
  await b.close();
  console.log(fail ? `실패 ${fail}건` : '모두 통과'); process.exit(fail ? 1 : 0);
})();
