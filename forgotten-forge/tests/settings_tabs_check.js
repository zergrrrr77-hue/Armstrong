// 설정창 점검: 스크롤 없이도 탭마다 화면 안에 다 보이는지(휴대폰 가로·세로), 개발자 모드 켜기, 시작 화면 개발자 모드
// 실행: node forgotten-forge/tests/settings_tabs_check.js [스크린샷 폴더]
const { chromium } = require('playwright'); const path = require('path');
const OUT = process.argv[2] || '/tmp';
(async () => {
  const b = await chromium.launch(); let fail = 0;
  const ck = (c, m) => { if (!c) fail++; console.log((c ? '  ✓ ' : '  ✗ ') + m); };
  for (const vp of [{ width: 667, height: 375 }, { width: 844, height: 390 }, { width: 390, height: 844 }, { width: 360, height: 640 }]) {
    const ctx = await b.newContext({ viewport: vp, hasTouch: true, isMobile: true, deviceScaleFactor: 2 });
    const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
    await p.goto('file://' + path.resolve(__dirname, '../index.html'));
    await p.waitForFunction(() => document.querySelectorAll('.cls').length === 3);
    await p.evaluate(() => localStorage.clear());
    await p.locator('.cls').nth(0).click(); await p.click('#start'); await p.waitForTimeout(600);
    await p.locator('#btnOpt').tap(); await p.waitForTimeout(200);
    const fits = {};
    for (const t of ['auto', 'view', 'sound', 'dev']) {
      await p.locator(`#optTabs button[data-ot="${t}"]`).tap(); await p.waitForTimeout(120);
      fits[t] = await p.evaluate(() => { const o = document.getElementById('opt').getBoundingClientRect(); const last = [...document.querySelectorAll('#opt .osec:not(.hidden) *')].pop().getBoundingClientRect(); return last.bottom <= innerHeight && o.top >= 0; });
      if (t === 'dev') await p.screenshot({ path: `${OUT}/opt_${vp.width}x${vp.height}_dev.png` });
    }
    ck(Object.values(fits).every(Boolean), `${vp.width}x${vp.height} 설정 탭 4개 모두 스크롤 없이 화면 안 ${JSON.stringify(fits)}`);
    await p.locator('#opt .seg[data-opt="dev"] button[data-v="on"]').tap(); await p.waitForTimeout(150);
    await p.locator('#devRow button[data-dev="gold"]').tap(); await p.waitForTimeout(150);
    const dev = await p.evaluate(() => ({ on: __game.OPT.dev === 'on', gold: __game.P.gold, badge: !document.getElementById('devBadge').classList.contains('hidden') }));
    ck(dev.on && dev.gold >= 1000000 && dev.badge, `${vp.width}x${vp.height} 개발자 모드 켜기 · 골드 +100만 · DEV 표시`);
    ck(!errs.length, `${vp.width}x${vp.height} 오류 0건`);
    await ctx.close();
  }
  // 시작 화면에서 개발자 모드로 시작
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  const p = await ctx.newPage();
  await p.goto('file://' + path.resolve(__dirname, '../index.html'));
  await p.waitForFunction(() => document.querySelectorAll('.cls').length === 3);
  await p.evaluate(() => localStorage.clear()); await p.reload(); await p.waitForFunction(() => document.querySelectorAll('.cls').length === 3);
  await p.locator('#devTitle').check(); await p.locator('.cls').nth(1).click(); await p.click('#start'); await p.waitForTimeout(500);
  ck(await p.evaluate(() => __game.OPT.dev === 'on' && !document.getElementById('devBadge').classList.contains('hidden')), '시작 화면 "개발자 모드로 시작" 체크');
  await b.close();
  console.log(fail ? `실패 ${fail}건` : '모두 통과'); process.exit(fail ? 1 : 0);
})();
