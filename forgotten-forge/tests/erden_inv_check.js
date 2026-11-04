// 가방 개선 점검: 일반 장비 자동 판매 · 일괄 판매 · 착용/해제 탭 · PC 하단 단축칸 · 휴대폰 화면
// 실행: NODE_PATH=$(npm root -g) node forgotten-forge/tests/erden_inv_check.js [스크린샷 폴더]
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
  const { page, errors } = await boot(browser, { viewport: { width: 1280, height: 760 } }, 0);

  console.log('[자동 판매]');
  const as = await page.evaluate(() => { const G = __game, P = G.P; P.autoSell = true; const bag = P.bag.length, gold = P.gold;
    const key = G.Object ? null : null;
    const common = Object.values(G.GEAR).find(d => d.grade === 'common').key;
    G.drops.push({ id: 'x', equip: G.makeEquip(common), n: 1, x: P.x, y: P.y, t: 0 });
    G.drops.push({ id: 'x', equip: G.makeEquip(common, 0, { px: { id: 'echo', v: 10 } }), n: 1, x: P.x, y: P.y, t: 0 });
    return { bag, gold }; });
  await page.waitForTimeout(500);
  const as2 = await page.evaluate(() => ({ bag: __game.P.bag.length, gold: __game.P.gold, px: __game.P.bag.some(e => e.px) }));
  check(as2.gold > as.gold && as2.bag === as.bag + 1 && as2.px, `일반 장비는 주울 때 자동 판매(+${as2.gold - as.gold} 에테르), 특수 옵션 장비는 가방에 보관`, fails);
  const as3 = await page.evaluate(async () => { const G = __game, P = G.P; P.autoSell = false; const common = Object.values(G.GEAR).find(d => d.grade === 'common').key; const bag = P.bag.length;
    G.drops.push({ id: 'x', equip: G.makeEquip(common), n: 1, x: P.x, y: P.y, t: 0 }); await new Promise(r => setTimeout(r, 500)); return P.bag.length - bag; });
  check(as3 === 1, '자동 판매를 끄면 가방에 들어옴', fails);

  console.log('[일괄 판매]');
  await page.evaluate(() => { const G = __game, P = G.P; P.bag.length = 0;
    const ks = Object.values(G.GEAR); for (const g of ['common', 'common', 'common', 'uncommon', 'uncommon', 'rare']) P.bag.push(G.makeEquip(ks.find(d => d.grade === g).key));
    P.inv.loot_wolf = 3; P.inv.loot_goblin = 2; G.renderInv(); });
  await page.keyboard.press('KeyI'); await page.waitForTimeout(200);
  await page.click('#bulkBtn'); await page.click('#bulkBar [data-bq="common"]'); await page.click('#bulkBar [data-bq="loot"]');
  const sel = await page.evaluate(() => ({ n: document.querySelectorAll('#eqgrid .cell.chk').length, sum: document.getElementById('bulkSum').textContent }));
  await page.screenshot({ path: `${OUT}/inv_bulk.png` });
  const g0 = await page.evaluate(() => __game.P.gold);
  await page.click('#bulkSell');
  const after = await page.evaluate(() => ({ bag: __game.P.bag.length, loot: (__game.P.inv.loot_wolf || 0) + (__game.P.inv.loot_goblin || 0), gold: __game.P.gold }));
  check(sel.n === 5 && after.bag === 3 && after.loot === 0 && after.gold > g0, `일반 3 + 전리품 2묶음 선택(${sel.sum}) → 한 번에 판매, 남은 장비 ${after.bag}`, fails);
  // 희귀 장비가 섞이면 한 번 더 확인
  await page.click('#bulkBtn'); await page.click('#bulkBtn');
  await page.evaluate(() => { const r = __game.P.bag.find(e => __game.equipDef(e.key).grade === 'rare'); document.querySelectorAll('#eqgrid .cell')[0].click(); });
  await page.click('#bulkSell');
  const conf = await page.evaluate(() => ({ txt: document.getElementById('bulkSell').textContent, bag: __game.P.bag.length }));
  await page.click('#bulkSell');
  const conf2 = await page.evaluate(() => __game.P.bag.length);
  check(conf.txt === '정말 판매?' && conf.bag === 3 && conf2 === 2, '희귀 이상 장비는 "정말 판매?" 한 번 더 누르면 판매', fails);
  await page.click('#bulkCancel');

  console.log('[착용·해제 탭]');
  await page.locator('#invTabs button', { hasText: '착용·해제' }).click(); await page.waitForTimeout(150);
  const w = await page.evaluate(() => ({ rows: document.querySelectorAll('#wearList .wrow').length, bag: document.querySelectorAll('#wearBag .wrow').length }));
  check(w.rows >= 10 && w.bag >= 1, `착용 중 ${w.rows}칸 · 가방 착용 후보 ${w.bag}개 표시`, fails);
  await page.screenshot({ path: `${OUT}/inv_wear.png` });
  const best = await page.evaluate(() => { const G = __game, P = G.P; P.lv = 20; const before = Object.values(P.eq).filter(Boolean).length; G.renderInv(); document.getElementById('wearBest').click(); return { before, after: Object.values(P.eq).filter(Boolean).length }; });
  check(best.after > best.before, `가장 좋은 장비 자동 착용: 착용 ${best.before} → ${best.after}칸`, fails);
  const off = await page.evaluate(() => { document.getElementById('wearOff').click(); const P = __game.P; return Object.entries(P.eq).filter(([k, v]) => v && k !== 'weapon').length; });
  check(off === 0, '모두 해제(무기는 그대로)', fails);
  const one = await page.evaluate(() => { const b = [...document.querySelectorAll('#wearBag .wrow button')].find(x => !x.disabled); if (!b) return false; b.click(); return Object.entries(__game.P.eq).filter(([k, v]) => v && k !== 'weapon').length === 1; });
  check(one, '목록의 "착용" 버튼으로 하나 착용', fails);
  await page.keyboard.press('KeyI');

  console.log('[PC 하단 바]');
  const bar = await page.evaluate(() => { const b = document.getElementById('bar').getBoundingClientRect(), s = document.getElementById('status').getBoundingClientRect();
    const slots = [...document.querySelectorAll('#bar .slot')].filter(x => x.offsetWidth > 0); const last = slots[slots.length - 1].getBoundingClientRect(), first = slots[0].getBoundingClientRect();
    return { n: slots.length, w: Math.round(first.width), fill: Math.round((last.right - first.left) / s.width * 100) }; });
  check(bar.n === 12 && bar.w >= 38 && bar.fill >= 90, `단축칸 ${bar.n}개(스킬 8·주문서 2·물약 2), 한 칸 ${bar.w}px, 가운데 폭의 ${bar.fill}% 채움`, fails);
  const rkey = await page.evaluate(() => { __game.P.inv.scroll_return = 2; return true; });
  await page.keyboard.press('KeyR'); await page.waitForTimeout(200);
  check(await page.evaluate(() => __game.P.inv.scroll_return === 1), 'R 키로 귀환 주문서 사용', fails);
  await page.screenshot({ path: `${OUT}/hud_pc.png` });
  check(errors.length === 0, `PC 오류 없음${errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''}`, fails);

  console.log('[휴대폰]');
  const m = await boot(browser, { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true }, 1);
  const mb = await m.page.evaluate(() => { const vis = [...document.querySelectorAll('#bar .slot')].filter(x => x.offsetWidth > 0); return { n: vis.length, inside: vis.every(x => { const r = x.getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth && r.bottom <= innerHeight; }) }; });
  check(mb.n === 2 && mb.inside, `휴대폰 Lv 1 단축칸 ${mb.n}개(스킬은 Lv 2부터 · 물약 2) 모두 화면 안`, fails);
  await m.page.screenshot({ path: `${OUT}/hud_phone.png` });
  await m.page.evaluate(() => { const G = __game, P = G.P; const ks = Object.values(G.GEAR); for (const g of ['common', 'uncommon']) P.bag.push(G.makeEquip(ks.find(d => d.grade === g).key)); });
  await m.page.tap('#btnInv'); await m.page.waitForTimeout(200); await m.page.tap('#bulkBtn'); await m.page.waitForTimeout(150);
  await m.page.screenshot({ path: `${OUT}/inv_phone.png` });
  await m.page.locator('#invTabs button', { hasText: '착용·해제' }).tap(); await m.page.waitForTimeout(150);
  await m.page.screenshot({ path: `${OUT}/wear_phone.png` });
  check(m.errors.length === 0, `휴대폰 오류 없음${m.errors.length ? ': ' + m.errors.slice(0, 3).join(' | ') : ''}`, fails);
  await browser.close();
  console.log(fails.length ? `\n실패 ${fails.length}개` : '\n모두 통과');
  process.exit(fails.length ? 1 : 0);
})();
