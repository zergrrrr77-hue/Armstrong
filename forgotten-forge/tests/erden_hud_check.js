// 화면 확대/축소 · 원거리 몬스터 물러서기 · 새 상태창 · 글꼴 · 스킬 레벨 습득 점검
// 실행: NODE_PATH=$(npm root -g) node forgotten-forge/tests/erden_hud_check.js [스크린샷 폴더]
const { chromium } = require('playwright');
const path = require('path');
const OUT = process.argv[2] || '/tmp';
const URL = 'file://' + path.resolve(__dirname, '../index.html');
function check(cond, msg, fails) { if (!cond) fails.push(msg); console.log((cond ? '  ✓ ' : '  ✗ ') + msg); }
const realError = (t) => !/ERR_TUNNEL_CONNECTION_FAILED|ERR_INTERNET_DISCONNECTED|fonts\.g/.test(t);
async function boot(browser, opt, cls) {
  const ctx = await browser.newContext(opt); const page = await ctx.newPage(); const errors = [];
  page.on('pageerror', e => errors.push(e.message)); page.on('console', m => { if (m.type() === 'error' && realError(m.text())) errors.push(m.text()); });
  if (opt.isMobile) await page.addInitScript(() => document.addEventListener('DOMContentLoaded', () => { const m = document.createElement('meta'); m.name = 'viewport'; m.content = 'width=device-width, initial-scale=1, viewport-fit=cover'; document.head.prepend(m); }));
  await page.goto(URL); await page.waitForFunction(() => document.querySelectorAll('.cls').length === 3);
  await page.evaluate(() => localStorage.clear()); await page.reload(); await page.waitForFunction(() => document.querySelectorAll('.cls').length === 3);
  await page.locator('.cls').nth(cls).click(); await page.fill('#nick', '테스터'); await page.click('#start'); await page.waitForTimeout(700);
  return { page, errors, ctx };
}
(async () => {
  const browser = await chromium.launch(); const fails = [];
  const { page, errors } = await boot(browser, { viewport: { width: 1280, height: 760 } }, 1);

  console.log('[스킬 습득]');
  const s1 = await page.evaluate(() => ({ btn: document.querySelectorAll('#bar button.slot').length, learn: document.querySelectorAll('#bar .slot.learn').length, lv: __game.SKILL_LV.join(',') }));
  check(s1.btn === 2 && s1.learn === 4, `Lv 1: 스킬 없음(물약 2칸만, 배울 스킬 자리 ${s1.learn}칸 · 습득 레벨 ${s1.lv})`, fails);
  const s2 = await page.evaluate(() => { const G = __game; G.gainXp(G.xpNeed(1)); return { lv: G.P.lv, btn: document.querySelectorAll('#bar button.slot').length, banner: document.getElementById('banner').textContent }; });
  check(s2.lv === 2 && s2.btn === 3 && /새 스킬/.test(s2.banner), `Lv 2 달성 → 스킬 1개 습득 (${s2.banner.slice(0, 30)})`, fails);
  const s3 = await page.evaluate(() => { const G = __game; while (G.P.lv < 14) G.gainXp(G.xpNeed(G.P.lv)); return document.querySelectorAll('#bar button.slot').length; });
  check(s3 === 6, `Lv 14: 스킬 4개 모두 습득 (단축칸 버튼 ${s3})`, fails);

  console.log('[확대/축소]');
  const z0 = await page.evaluate(() => __game.ZOOM);
  await page.mouse.move(640, 300); await page.mouse.wheel(0, -300); await page.waitForTimeout(100);
  const z1 = await page.evaluate(() => __game.ZOOM);
  await page.keyboard.press('Minus'); await page.keyboard.press('Minus'); await page.keyboard.press('Minus');
  const z2 = await page.evaluate(() => __game.ZOOM);
  check(z1 > z0 && z2 < z1, `휠로 확대 ${z0}→${z1.toFixed(2)}, - 키로 축소 → ${z2.toFixed(2)}`, fails);
  const lim = await page.evaluate(() => { const G = __game; G.setZoom(9, true); const a = G.ZOOM_USER; G.setZoom(0.01, true); const b = G.ZOOM_USER; G.setZoom(1, true); return [a, b]; });
  check(lim[0] === 1.8 && lim[1] === 0.6, `확대 범위 ${lim[1] * 100}% ~ ${lim[0] * 100}%`, fails);
  const keep = await page.evaluate(() => { __game.setZoom(1.3, true); return JSON.parse(localStorage.getItem('ff_lineage_opt_v1') || '{}').zoom; });
  await page.waitForTimeout(400);
  check(await page.evaluate(() => JSON.parse(localStorage.getItem('ff_lineage_opt_v1')).zoom) === 1.3, '확대 배율이 설정에 저장됨', fails);
  await page.evaluate(() => __game.setZoom(1, true));

  console.log('[고블린 궁수]');
  const ar = await page.evaluate(async () => { const G = __game, P = G.P; G.enterMap('field'); P.hp = P.maxhp = 999999; P.autoOn = false;
    const m = G.mobs.find(x => x.type === 'goblin_archer' && !x.dead); P.x = m.x + 1.2; P.y = m.y; P.target = null; P.goal = null;
    m.aggr = true; m.state = 'chase'; const sx = m.x, sy = m.y, shots0 = G.combat.mobShots;
    let far = 0; const t0 = performance.now();
    while (performance.now() - t0 < 6000) { await new Promise(r => setTimeout(r, 100)); P.x = m.x + 1.2; P.y = m.y; far = Math.max(far, Math.hypot(m.x - sx, m.y - sy)); }
    return { far, shots: G.combat.mobShots - shots0 }; });
  check(ar.far < 3 && ar.shots >= 2, `플레이어가 계속 붙어도 멀리 도망가지 않음(최대 ${ar.far.toFixed(1)}칸 이동) · 화살 ${ar.shots}발`, fails);

  console.log('[상태창·글꼴]');
  await page.evaluate(() => { const G = __game; G.enterMap('field'); G.P.hp = G.P.maxhp = 871; G.P.hp = 798; G.P.sp = 2; });
  await page.waitForTimeout(400);
  const st = await page.evaluate(() => { const r = id => document.getElementById(id).getBoundingClientRect(); const hit = (a, b) => !(a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top);
    const orb = document.querySelector('#status .orb').getBoundingClientRect();
    return { hpt: document.getElementById('hpt').textContent, inBar: hit(r('hpt'), r('shp')), sp: !hit(r('spBadge'), orb), dock: getComputedStyle(document.querySelector('#dock .em')).display,
      font: getComputedStyle(document.body).fontFamily, lvl: document.getElementById('plv2').textContent }; });
  check(/^\d+ \/ 871$/.test(st.hpt) && st.inBar, `HP 숫자가 막대 안에: "${st.hpt}"`, fails);
  check(st.sp && st.dock === 'none', '포인트(+)·레벨 표시가 초상과 안 겹치고, 가운데 별 문장 제거', fails);
  check(/^Tahoma, Verdana/.test(st.font), `게임 글꼴: ${st.font.split(',').slice(0, 3).join(',')}`, fails);
  await page.screenshot({ path: `${OUT}/hud2_pc.png` });
  await page.screenshot({ path: `${OUT}/hud2_pc_status.png`, clip: { x: 300, y: 580, width: 680, height: 180 } });
  check(errors.length === 0, `PC 오류 없음${errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''}`, fails);

  console.log('[휴대폰]');
  const m = await boot(browser, { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true }, 0);
  const z = await m.page.evaluate(async () => { const c = document.getElementById('game'), G = __game, z0 = G.ZOOM;
    const ev = (type, id, x, y) => c.dispatchEvent(new PointerEvent(type, { pointerId: id, pointerType: 'touch', clientX: x, clientY: y, bubbles: true, isPrimary: id === 1 }));
    ev('pointerdown', 1, 150, 300); ev('pointerdown', 2, 240, 300);
    for (let k = 1; k <= 5; k++) { ev('pointermove', 1, 150 - k * 12, 300); ev('pointermove', 2, 240 + k * 12, 300); await new Promise(r => setTimeout(r, 16)); }
    ev('pointerup', 1, 90, 300); ev('pointerup', 2, 300, 300); const z1 = G.ZOOM;
    ev('pointerdown', 3, 100, 300); ev('pointerdown', 4, 300, 300);
    for (let k = 1; k <= 5; k++) { ev('pointermove', 3, 100 + k * 16, 300); ev('pointermove', 4, 300 - k * 16, 300); await new Promise(r => setTimeout(r, 16)); }
    ev('pointerup', 3, 180, 300); ev('pointerup', 4, 220, 300);
    return { z0, z1, z2: G.ZOOM, moved: !!G.P.goal }; });
  check(z.z1 > z.z0 && z.z2 < z.z1, `두 손가락 벌리기 확대 ${z.z0}→${z.z1.toFixed(2)}, 오므리기 축소 → ${z.z2.toFixed(2)}`, fails);
  await m.page.evaluate(() => { const G = __game; G.setZoom(1, true); G.P.lv = 1; G.P.sp = 2; G.gainXp(G.xpNeed(1)); });
  await m.page.waitForTimeout(500);
  const mb = await m.page.evaluate(() => { const vis = [...document.querySelectorAll('#bar .slot')].filter(x => x.offsetWidth > 0); const s = document.getElementById('status').getBoundingClientRect(), mi = document.getElementById('mini').getBoundingClientRect();
    return { n: vis.length, overlap: !(s.right <= mi.left || s.bottom <= mi.top) }; });
  check(mb.n === 3 && !mb.overlap, `휴대폰 Lv 2: 스킬 1 + 물약 2칸, 상태창이 미니맵과 안 겹침`, fails);
  await m.page.screenshot({ path: `${OUT}/hud2_phone.png` });
  check(m.errors.length === 0, `휴대폰 오류 없음${m.errors.length ? ': ' + m.errors.slice(0, 3).join(' | ') : ''}`, fails);
  await browser.close();
  console.log(fails.length ? `\n실패 ${fails.length}개` : '\n모두 통과');
  process.exit(fails.length ? 1 : 0);
})();
