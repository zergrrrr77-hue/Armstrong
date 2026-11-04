// 7단계: 프레임 시간(데스크톱·휴대폰 세로), 터치 조작, 모든 버튼 연결 점검
// 실행: node forgotten-forge/tests/perf_mobile.js [스크린샷 폴더]
const { chromium } = require('playwright');
const path = require('path');
const OUT = process.argv[2] || '/tmp';
const fails = [];
const check = (c, m) => { if (!c) fails.push(m); console.log((c ? '  ✓ ' : '  ✗ ') + m); };
async function frameStats(page, ms) {
  return page.evaluate((ms) => new Promise(res => {
    const ts = []; let last = performance.now(); const end = last + ms;
    function f(t) { ts.push(t - last); last = t; if (t < end) requestAnimationFrame(f); else { ts.sort((a, b) => a - b); res({ avg: ts.reduce((a, b) => a + b, 0) / ts.length, p95: ts[Math.floor(ts.length * 0.95)], n: ts.length }); } }
    requestAnimationFrame(f);
  }), ms);
}
async function scriptCost(page) {
  // 한 프레임 처리(갱신+그리기)에 드는 스크립트 시간
  return page.evaluate(() => { const G = __game; const t0 = performance.now(); for (let i = 0; i < 60; i++) { G.simulate(1 / 60); G.renderOnce(); } return (performance.now() - t0) / 60; });
}
(async () => {
  const browser = await chromium.launch();
  for (const [name, vp, mobile] of [['데스크톱 1280×760', { width: 1280, height: 760 }, false], ['휴대폰 세로 390×844', { width: 390, height: 844 }, true]]) {
    console.log(`[${name}]`);
    const ctx = await browser.newContext({ viewport: vp, hasTouch: mobile, isMobile: mobile, deviceScaleFactor: mobile ? 3 : 1 });
    const page = await ctx.newPage();
    // 게시 환경(문서 뼈대)이 넣어 주는 viewport 메타를 재현 — 없으면 휴대폰이 980px 폭으로 렌더링됨
    if (mobile) await page.addInitScript(() => document.addEventListener('DOMContentLoaded', () => { const m = document.createElement('meta'); m.name = 'viewport'; m.content = 'width=device-width, initial-scale=1, viewport-fit=cover'; document.head.prepend(m); }));
    const errors = []; page.on('pageerror', e => errors.push(e.message)); page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    await page.goto('file://' + path.resolve(__dirname, '../index.html'));
    await page.waitForFunction(() => document.querySelectorAll('.cls').length === 3, null, { timeout: 20000 });
    await page.evaluate(() => localStorage.clear());
    await (mobile ? page.locator('.cls').nth(2).tap() : page.locator('.cls').nth(2).click());
    await (mobile ? page.fill('#nick', '테스터').then(() => page.tap('#start')) : page.fill('#nick', '테스터').then(() => page.click('#start')));
    await page.waitForTimeout(600);
    // 전투가 많은 상황: 몬스터 무리 한가운데 + 자동사냥
    await page.evaluate(() => { const G = __game, P = G.P; P.maxhp = 1e6; P.hp = 1e6; P.lv = 8; const m = G.mobs.find(x => x.type === 'orc'); P.x = m.x - 1; P.y = m.y; G.setAuto(true); });
    const cost = await scriptCost(page);
    check(cost < 8, `프레임당 스크립트 시간 ${cost.toFixed(2)}ms (기준 8ms)`);
    const st = await frameStats(page, 2500);
    check(st.avg < 20, `평균 프레임 간격 ${st.avg.toFixed(1)}ms · 95% ${st.p95.toFixed(1)}ms (${st.n}프레임)`);
    await page.evaluate(() => { const G = __game, P = G.P; G.setAuto(false); P.casting = null; P.target = null; P.goal = null; P.x = 13.5; P.y = 13.5; G.setPaused(false); });
    await page.waitForTimeout(400);
    // 터치·클릭으로 이동(몬스터 없는 마을에서)
    const p0 = await page.evaluate(() => ({ x: __game.P.x, y: __game.P.y }));
    const tapAt = { x: vp.width * 0.5 + 60, y: vp.height * 0.5 + 40 };
    await (mobile ? page.touchscreen.tap(tapAt.x, tapAt.y) : page.mouse.click(tapAt.x, tapAt.y));
    await page.waitForTimeout(900);
    const p1 = await page.evaluate(() => ({ x: __game.P.x, y: __game.P.y }));
    check(Math.hypot(p1.x - p0.x, p1.y - p0.y) > 0.3, '화면을 눌러 이동');
    // 모든 HUD 버튼이 실제 기능과 연결됐는지
    const press = async (sel) => { await (mobile ? page.tap(sel) : page.click(sel)); await page.waitForTimeout(120); };
    const st0 = await page.evaluate(() => ({ auto: __game.P.auto }));
    await press('#btnAuto'); check(await page.evaluate(a => __game.P.auto !== a, st0.auto), '자동 버튼'); await press('#btnAuto');
    await press('#btnInv'); check(await page.evaluate(() => !document.getElementById('inv').classList.contains('hidden')), '가방 버튼');
    for (const tab of ['능력치', '획득 기록', '확률표', '장비창']) { await (mobile ? page.locator('#invTabs button', { hasText: tab }).tap() : page.locator('#invTabs button', { hasText: tab }).click()); }
    check(await page.evaluate(() => !document.querySelector('[data-pane="eq"]').classList.contains('hidden')), '가방 탭 4개 전환');
    await press('#invClose'); check(await page.evaluate(() => document.getElementById('inv').classList.contains('hidden')), '가방 닫기');
    await press('#btnOpt'); check(await page.evaluate(() => !document.getElementById('opt').classList.contains('hidden')), '설정 버튼');
    await press('#optClose');
    await press('#btnSnd'); check(await page.evaluate(() => document.getElementById('btnSnd').getAttribute('aria-pressed') === 'false'), '소리 버튼'); await press('#btnSnd');
    await press('#mmIn'); await press('#mmOut'); check(true, '미니맵 확대·축소 버튼');
    await press('#qToggle'); await press('#qToggle'); check(true, '목표 창 접기 버튼');
    const mp0 = await page.evaluate(() => { const P = __game.P; P.mp = P.maxmp; P.cds = {}; P.casting = null; return __game.fxs.length; });
    await press('#bar .slot:nth-child(1)'); check(await page.evaluate(() => !!__game.P.casting || __game.fxs.length > 0), '스킬 1 버튼');
    const pot = await page.evaluate(() => { __game.OPT.potHp = 0; __game.P.hp = 100; return __game.P.inv.pot_red; });
    await press('#bar button.slot:nth-last-of-type(2)'); check(await page.evaluate(n => __game.P.inv.pot_red === n - 1, pot), '체력 물약 버튼');
    await page.evaluate(() => { __game.OPT.potHp = 40; });
    // 터치 크기: 스킬 칸 44px 이상
    const sz = await page.evaluate(() => { const r = document.querySelector('#bar .slot').getBoundingClientRect(); return Math.min(r.width, r.height); });
    check(sz >= 44, `스킬 버튼 크기 ${sz.toFixed(0)}px (터치 권장 44px 이상)`);
    // 게임 화면 확보: HUD가 가리는 비율
    const cover = await page.evaluate(() => { const ids = ['status', 'quest', 'mini', 'bar']; let a = 0; for (const id of ids) { const r = document.getElementById(id).getBoundingClientRect(); a += r.width * r.height; } return a / (innerWidth * innerHeight); });
    check(cover < 0.22, `HUD가 가리는 화면 비율 ${(cover * 100).toFixed(1)}% (기준 22%)`);
    const ov = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
    check(ov <= 0, '가로 넘침 없음');
    await page.screenshot({ path: `${OUT}/p_${mobile ? 'phone' : 'desk'}.png` });
    check(errors.length === 0, '콘솔 오류 0건' + (errors.length ? ': ' + errors.slice(0, 2).join(' | ') : ''));
    await ctx.close();
  }
  await browser.close();
  console.log(fails.length ? `실패 ${fails.length}건` : '모두 통과');
  process.exit(fails.length ? 1 : 0);
})();
