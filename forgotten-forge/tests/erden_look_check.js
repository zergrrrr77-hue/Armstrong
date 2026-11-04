// 장비 점수제 외형 4단계 점검: 점수 계산 · 단계 경계 · 장비를 바꾸면 모습(시트)이 바뀜 · 알림 · 이어하기
// 실행: NODE_PATH=$(npm root -g) node forgotten-forge/tests/erden_look_check.js [스크린샷 폴더]
const { chromium } = require('playwright');
const path = require('path');
const OUT = process.argv[2] || '/tmp';
const URL = 'file://' + path.resolve(__dirname, '../index.html');
function check(cond, msg, fails) { if (!cond) fails.push(msg); console.log((cond ? '  ✓ ' : '  ✗ ') + msg); }
const realError = (t) => !/ERR_TUNNEL_CONNECTION_FAILED|ERR_INTERNET_DISCONNECTED|fonts\.g/.test(t);
(async () => {
  const browser = await chromium.launch(); const fails = [];
  const page = await browser.newPage({ viewport: { width: 1280, height: 760 } }); const errors = [];
  page.on('pageerror', e => errors.push(e.message)); page.on('console', m => { if (m.type() === 'error' && realError(m.text())) errors.push(m.text()); });
  await page.goto(URL); await page.waitForFunction(() => document.querySelectorAll('.cls').length === 3);
  for (const [ci, cls] of [[0, 'knight'], [1, 'elf'], [2, 'mage']]) {
    console.log(`[${cls}]`);
    await page.evaluate(() => localStorage.clear()); await page.reload(); await page.waitForFunction(() => document.querySelectorAll('.cls').length === 3);
    await page.locator('.cls').nth(ci).click(); await page.fill('#nick', '테스터'); await page.click('#start'); await page.waitForTimeout(500);
    const r = await page.evaluate((cls) => {
      const G = __game, P = G.P; P.lv = 40;
      const start = [P.lookTier, P.sheet];
      const put = grade => {
        const slots = ['helm', 'cloak', 'gloves', 'boots'].concat(cls === 'knight' ? ['shield'] : []);
        for (const s of slots) { const d = Object.values(G.GEAR).find(x => x.slot === s && x.grade === grade); if (d) P.eq[s] = G.makeEquip(d.key); }
        const a = G.EQUIP[P.c.base].armor.find(x => x.grade === grade); if (a) P.eq.armor = G.makeEquip(a.key);
        G.applyStats(); return [P.lookTier, P.sheet, +G.lookScore().toFixed(2), document.getElementById('banner').textContent];
      };
      return { start, rare: put('rare'), heroic: put('heroic'), legend: put('legend'), back: put('common'),
        sheets: Object.keys(META_KEYS = {}).length };
    }, cls);
    check(r.start[0] === 1 && r.start[1] === cls, `시작: 1단계 기본 모습(${r.start[1]})`, fails);
    check(r.rare[0] === 2 && r.rare[2] === 3 && r.rare[1] === cls + '_t2', `희귀 장비 한 벌 → 점수 ${r.rare[2]} → 2단계 (${r.rare[1]})`, fails);
    check(r.heroic[0] === 3 && r.legend[0] === 4 && r.legend[1] === cls + '_t4', `영웅 한 벌 → 3단계(${r.heroic[1]}) · 전설 한 벌 → 4단계(${r.legend[1]})`, fails);
    check(/외형/.test(r.legend[3]), `단계가 바뀌면 알림: "${r.legend[3].slice(0, 30)}"`, fails);
    check(r.back[0] === 1 && r.back[1] === cls, '일반 장비로 바꾸면 다시 1단계', fails);
    // 경계값: 갑옷만 희귀(3×3=9) + 나머지 일반 → (9 + 일반 개수) / 칸수
    const edge = await page.evaluate(() => { const G = __game, P = G.P; const a = G.EQUIP[P.c.base].armor.find(x => x.grade === 'legend'); P.eq.armor = G.makeEquip(a.key); for (const s of ['helm', 'cloak', 'gloves', 'boots', 'shield']) P.eq[s] = null; G.applyStats(); return [+G.lookScore().toFixed(2), P.lookTier]; });
    check(edge[1] === G_EXPECT(edge[0]), `전설 갑옷만: 점수 ${edge[0]} → ${edge[1]}단계(갑옷 3배 계산)`, fails);
    // 저장 후 이어하기에서도 같은 모습
    const sv = await page.evaluate(() => { const G = __game, P = G.P; const g = Object.values(G.GEAR); for (const s of ['helm', 'cloak', 'gloves', 'boots', 'shield']) { const d = g.find(x => x.slot === s && x.grade === 'heroic'); if (d) P.eq[s] = G.makeEquip(d.key); } const a = G.EQUIP[P.c.base].armor.find(x => x.grade === 'heroic'); P.eq.armor = G.makeEquip(a.key); G.applyStats(); G.save(); return P.lookTier; });
    await page.reload(); await page.waitForFunction(() => document.querySelectorAll('.cls').length === 3); await page.click('#continue'); await page.waitForTimeout(600);
    const after = await page.evaluate(() => [__game.P.lookTier, __game.P.sheet]);
    check(after[0] === sv && after[0] === 3, `이어하기 후에도 ${after[0]}단계 모습(${after[1]})`, fails);
    await page.keyboard.press('KeyI'); await page.waitForTimeout(300);
    const txt = await page.evaluate(() => document.getElementById('lookSum').textContent);
    check(/외형 3단계/.test(txt) && /장비 점수/.test(txt), `가방에 표시: ${txt}`, fails);
    await page.screenshot({ path: `${OUT}/look_${cls}.png` });
    await page.keyboard.press('KeyI');
  }
  check(errors.length === 0, `오류 없음${errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''}`, fails);
  await browser.close();
  console.log(fails.length ? `\n실패 ${fails.length}개` : '\n모두 통과');
  process.exit(fails.length ? 1 : 0);
})();
function G_EXPECT(sc) { return 1 + [2.5, 3.5, 4.5].filter(c => sc >= c).length; }
