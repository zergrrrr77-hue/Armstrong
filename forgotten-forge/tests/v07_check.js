// v0.7 점검: 리젠·난이도 · 선공/후공 50:50 · 오크 소리 겹침 · 특수 옵션 광채 · 피해 숫자 · 아이콘 메뉴 · 사운드 설정
//           · 강화 연출 · 비교창 · 웨이포인트/이동 스크롤 · 전리품 · 뽑기(확률·천장·마일리지·중복) · 개발자 모드
// 실행: node forgotten-forge/tests/v07_check.js [스크린샷 폴더]
const { chromium } = require('playwright');
const path = require('path');
const OUT = process.argv[2] || '/tmp';
const URL = 'file://' + path.resolve(__dirname, '../index.html');
function check(c, m, f) { if (!c) f.push(m); console.log((c ? '  ✓ ' : '  ✗ ') + m); }

async function boot(browser, opt, cls = 0) {
  const ctx = await browser.newContext(opt); const page = await ctx.newPage(); const errors = [];
  page.on('pageerror', e => errors.push(e.message)); page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(URL);
  await page.waitForFunction(() => document.querySelectorAll('.cls').length === 3, null, { timeout: 20000 });
  await page.evaluate(() => localStorage.clear());
  await page.locator('.cls').nth(cls).click(); await page.click('#start'); await page.waitForTimeout(700);
  return { page, ctx, errors };
}

(async () => {
  const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
  const fails = [];
  console.log('[데스크톱]');
  const { page, errors } = await boot(browser, { viewport: { width: 1280, height: 760 } });

  // 1) 리젠·난이도·경험치
  const tune = await page.evaluate(() => {
    const G = __game, m = G.mobs.find(x => x.type === 'wolf');
    const base = { hp: 90, xp: 18 };
    const sim = () => { m.dead = false; G.killMob(m); let t = 0; while (m.dead && t < 120) { G.simulate(1); t++; for (const o of G.mobs) if (o.state === 'chase') o.state = 'idle'; } return t; };
    G.P.x = 13.5; G.P.y = 13.5; G.P.hp = G.P.maxhp = 99999;
    const back = sim();
    return { respawn: G.RESPAWN_T, back, hp: m.maxhp, xp: m.d.xp, aggr: m.aggr, ratioHp: m.maxhp / base.hp };
  });
  check(tune.respawn === 60 && tune.back >= 59 && tune.back <= 62, `일반 몬스터 리젠 25초 → 60초 (실측 ${tune.back}초)`, fails);
  check(Math.abs(tune.ratioHp - 1.3) < 0.02 && tune.xp >= 25, `난이도·경험치 상향: 체력 ×1.3, 경험치 18 → ${tune.xp}`, fails);

  // 2) 선공/후공 50:50 + 행동 차이
  const ag = await page.evaluate(() => {
    const G = __game, P = G.P, res = {};
    for (const id of ['field', 'dungeon']) { G.enterMap(id); const ms = G.mobs.filter(m => !m.d.boss); res[id] = [ms.filter(m => m.aggr).length, ms.length]; }
    G.enterMap('field'); P.hp = P.maxhp = 99999; P.auto = false;
    const a = G.mobs.find(m => !m.d.boss && m.aggr), p = G.mobs.find(m => !m.d.boss && !m.aggr);
    for (const m of G.mobs) m.state = 'idle';
    P.x = a.x + 2; P.y = a.y; G.simulate(0.3); const aChase = a.state === 'chase';
    for (const m of G.mobs) { m.state = 'idle'; m.calmT = 0; }
    P.x = p.x + 2; P.y = p.y; p.state = 'idle'; G.simulate(0.3); const pIdle = p.state !== 'chase';
    G.combat; P.target = p; P.x = p.x + 1; P.atkCd = 0;
    return { res, aChase, pIdle };
  });
  const half = (a, n) => Math.abs(a - n / 2) <= 1;
  check(half(...ag.res.field) && half(...ag.res.dungeon), `선공:후공 = 50:50 (필드 ${ag.res.field[0]}/${ag.res.field[1]}, 던전 ${ag.res.dungeon[0]}/${ag.res.dungeon[1]})`, fails);
  check(ag.aChase && ag.pIdle, '선공은 다가오면 먼저 공격, 후공은 가만히 있음', fails);
  await page.waitForTimeout(300);
  const lbl = await page.evaluate(() => document.querySelector('#target b').textContent);
  check(/후공|선공/.test(lbl), '대상 이름에 선공/후공 표시: ' + lbl, fails);
  await page.screenshot({ path: `${OUT}/v1_aggr.png` });

  // 3) 오크 소리 겹침: (가) 마을 경계에서 추격↔대기가 매 프레임 바뀌던 상황(수정 전 초당 약 200회) (나) 오크 야영지 정면 전투
  const snd = await page.evaluate(async () => {
    const G = __game, P = G.P, A = G.audio(), out = {};
    for (const scen of ['edge', 'camp']) {
      let v = 0; const orig = A.play.bind(A); A.play = (n, o) => { if (/^orc_/.test(n)) v++; return orig(n, o); };
      G.enterMap('field'); P.hp = P.maxhp = 999999;
      const os = G.mobs.filter(m => m.type === 'orc' || m.type === 'goblin');
      if (scen === 'edge') { for (const m of os.slice(0, 8)) { m.aggr = true; m.x = 20.6 + Math.random(); m.y = 14 + Math.random() * 4; } P.x = 19.4; P.y = 15.5; }
      else { const c = os.find(m => m.type === 'orc'); P.x = c.x; P.y = c.y + 0.5; for (const m of os.filter(m => m.type === 'orc')) { m.aggr = true; m.state = 'chase'; } }
      const t0 = performance.now(); await new Promise(r => setTimeout(r, 3000)); A.play = orig;
      out[scen] = v / ((performance.now() - t0) / 1000);
    }
    P.hp = P.maxhp; G.enterMap('field');
    return out;
  });
  check(snd.edge <= 3.2 && snd.camp > 0 && snd.camp <= 3.2, `오크·고블린 목소리: 마을 경계 ${snd.edge.toFixed(1)}회/초(수정 전 약 200) · 야영지 전투 ${snd.camp.toFixed(1)}회/초`, fails);

  // 4) 특수 옵션 아이템 광채
  const glow = await page.evaluate(() => {
    const G = __game, P = G.P; P.bag.length = 0; P.bag.push(G.makeEquip('b_great', 0, { px: { id: 'echo', v: 15 } })); P.bag.push(G.makeEquip('b_great'));
    document.getElementById('inv').classList.remove('hidden'); G.renderInv();
    const c = document.querySelector('#eqgrid .cell.px'); return c ? getComputedStyle(c).animationName : 'none';
  });
  check(glow === 'pxglow', '특수 옵션 장비 테두리 광채 애니메이션', fails);
  // 5) 비교창: 가방에서 장비를 누르면 착용 중 장비와 나란히
  await page.click('#eqgrid .cell.px'); await page.waitForTimeout(200);
  const cmp = await page.evaluate(() => ({ vis: !document.getElementById('cmp').classList.contains('hidden'), cards: document.querySelectorAll('#cmpGrid .ccard').length, tot: document.getElementById('cmpTot').textContent }));
  check(cmp.vis && cmp.cards === 2 && cmp.tot.includes('전투력'), '비교창: 선택 장비 ↔ 착용 장비 + 전투력 변화', fails);
  await page.screenshot({ path: `${OUT}/v2_compare.png` });
  // 6) 강화 연출: 망치 → 성공/실패 다른 연출
  await page.evaluate(() => { const G = __game, P = G.P; P.inv.scroll_weapon = 5; P.weapon.enc = 8; document.getElementById('cmp').classList.add('hidden'); });
  const okRun = await page.evaluate(() => { const G = __game; const r = Math.random; Math.random = () => 0; const ok = G.enchantItem(G.P.weapon); Math.random = r; return { ok, vis: !document.getElementById('encFx').classList.contains('hidden') }; });
  await page.waitForTimeout(500); await page.screenshot({ path: `${OUT}/v3_enchant_hammer.png` });
  await page.waitForTimeout(700);
  const okTxt = await page.evaluate(() => document.getElementById('encFxT').textContent);
  await page.screenshot({ path: `${OUT}/v4_enchant_ok.png` });
  await page.waitForTimeout(1200);
  const failRun = await page.evaluate(() => { const G = __game; const r = Math.random; Math.random = () => 0.999; const ok = G.enchantItem(G.P.weapon); Math.random = r; return ok; });
  await page.waitForTimeout(1300);
  const failTxt = await page.evaluate(() => document.getElementById('encFxT').textContent);
  await page.screenshot({ path: `${OUT}/v5_enchant_fail.png` });
  await page.waitForTimeout(1000);
  const gone = await page.evaluate(() => document.getElementById('encFx').classList.contains('hidden'));
  check(okRun.ok && okRun.vis && okTxt.includes('성공') && !failRun && failTxt.includes('실패') && gone, `강화 망치 연출: 성공 "${okTxt}" / 실패 "${failTxt}"`, fails);
  await page.evaluate(() => document.getElementById('inv').classList.add('hidden'));

  // 7) 맵 창 왼쪽 위 아이콘 메뉴
  const ic = await page.evaluate(() => { const m = document.getElementById('mini').getBoundingClientRect(); return ['btnAuto', 'btnInv', 'btnGacha', 'btnSnd', 'btnOpt'].map(id => { const r = document.getElementById(id).getBoundingClientRect(); return r.right <= m.left + 1 && r.top >= m.top - 1 && r.top < m.top + 260 && !!document.querySelector('#' + id + ' svg'); }); });
  check(ic.every(Boolean), '자동·가방·뽑기·소리·설정 아이콘이 맵 창 왼쪽 위에 세로로', fails);

  // 8) 사운드 상세 설정
  await page.click('#btnOpt'); await page.waitForTimeout(150);
  const vol = await page.evaluate(() => { const G = __game; const rows = document.querySelectorAll('#volRows .vrow').length; const s0 = G.SFX_STAT.played; G.OPT.mute.mon = true; G.sfx('wolf_attack', {}, 'mon'); const muted = G.SFX_STAT.played === s0; G.OPT.mute.mon = false; return { rows, muted }; });
  await page.screenshot({ path: `${OUT}/v6_settings.png` });
  check(vol.rows === 5 && vol.muted, '사운드 설정: 전체·배경음·효과음·몬스터·환경음, 몬스터 끄기 동작', fails);
  await page.click('#optClose');

  // 9) 웨이포인트 · 이동 포탈 스크롤 · 귀환 주문서
  const wp = await page.evaluate(() => {
    const G = __game, P = G.P; G.enterMap('field'); const W = G.WAYPOINTS.field.find(w => w.id === 'wp_forest');
    const reach = G.WAYPOINTS.field.every(w => G.walkable(Math.floor(G.safeSpot(w.x + 1, w.y + 1).x), Math.floor(G.safeSpot(w.x + 1, w.y + 1).y)));
    P.x = W.x + 1; P.y = W.y + 0.8; G.simulate(0.5); const found = !!G.STATE.wp.wp_forest;
    const tp = G.teleportTo('wp_town'); const inTown = G.inTown(P);
    P.inv.scroll_teleport = 1; G.useItem('scroll_teleport'); const menu = !document.getElementById('wpMenu').classList.contains('hidden');
    G.teleportTo('wp_forest'); const used = P.inv.scroll_teleport === 0 && Math.hypot(P.x - W.x, P.y - W.y) < 3;
    P.inv.scroll_return = 1; G.useItem('scroll_return'); const ret = G.inTown(P);
    return { reach, found, tp, inTown, menu, used, ret };
  });
  check(wp.reach && wp.found && wp.tp && wp.inTown, '웨이포인트: 다가가면 활성화 → 마을로 이동', fails);
  check(wp.menu && wp.used && wp.ret, '이동 포탈 스크롤(목적지 선택·1장 소모) · 귀환 주문서', fails);
  await page.evaluate(() => { const G = __game, P = G.P, W = G.WAYPOINTS.field[0]; P.x = W.x + 1; P.y = W.y + 1; G.openWp(W); });
  await page.waitForTimeout(200); await page.screenshot({ path: `${OUT}/v7_waypoint.png` });
  await page.keyboard.press('Escape');

  // 10) 몬스터 고유 전리품
  const loot = await page.evaluate(() => {
    const G = __game, P = G.P; G.OPT.dev = 'on'; G.drops.length = 0;
    const kinds = new Set(); for (const t of ['goblin', 'wolf', 'spider', 'ooze', 'skeleton', 'skeleton_archer', 'orc']) { const m = G.mobs.find(x => x.type === t) || null; if (!m) continue; m.dead = false; G.killMob(m); }
    for (const d of G.drops) if (d.id.startsWith('loot_')) kinds.add(d.id);
    G.OPT.dev = 'off';
    P.inv.loot_wolf = 3; const g0 = P.gold; G.renderShop(); document.getElementById('sellLoot').click();
    return { kinds: kinds.size, sold: P.gold - g0, name: G.XITEMS.loot_wolf.name };
  });
  check(loot.kinds >= 6 && loot.sold > 0, `몬스터마다 고유 전리품(${loot.kinds}종, 예: ${loot.name}) · 상점 일괄 판매 +${loot.sold}G`, fails);

  // 11) 뽑기: 비용·11회 보장·확률·천장·마일리지·중복 별·펫/변신 효과
  const ga = await page.evaluate(() => {
    const G = __game, P = G.P; P.gold = 1000000; G.gCat = 'pet';
    const g0 = P.gold; const r11 = G.pullGacha(11); const cost11 = g0 - P.gold;
    const g1 = P.gold; G.pullGacha(1); const cost1 = g1 - P.gold;
    // 확률(몬테카를로 40만 회)
    const n = 400000, cnt = [0, 0, 0, 0, 0, 0]; for (let i = 0; i < n; i++) cnt[G.gachaRoll('pet').g]++;
    const pct = cnt.map(c => c / n * 100);
    // 천장
    P.gacha.pet.pity = 79; const p = G.pullGacha(1)[0];
    // 마일리지 교환
    P.gacha.pet.mile = 300; const ex = G.exchangeMile();
    // 중복 → 별
    const before = P.coll.pet.ooze || 0; P.coll.pet.ooze = before; for (let i = 0; i < 2; i++) { const r = G.gachaRoll('pet', 0); }
    G.setPet('boss'); G.simulate(0.5); const pet = G.PET && G.PET.sheet === 'boss';
    const atk0 = G.collBonus('atk');
    G.setMorph('orc'); const morph = P.morph === 'orc' && G.collBonus('spd') > 0;
    return { cost11, cost1, n11: r11.length, rare11: r11.some(x => x.g >= 2), pct, pity: p.g >= 3, ex: ex && ex.g === 4, pet, atk0, morph, stars: Math.max(...Object.values(P.coll.pet)) };
  });
  check(ga.cost11 === 100000 && ga.cost1 === 10000 && ga.n11 === 11 && ga.rare11, '뽑기 비용 1회 10,000 · 11회 100,000(희귀 이상 1회 확정)', fails);
  const want = [70, 20, 8, 1.8, 0.19, 0.01];
  check(ga.pct.slice(0, 4).every((v, i) => Math.abs(v - want[i]) < want[i] * 0.05 + 0.1) && ga.pct[4] < 0.35 && ga.pct[5] < 0.05, '등급 확률 일반 70 · 고급 20 · 희귀 8 · 영웅 1.8 · 전설 0.19 · 신화 0.01: ' + ga.pct.map(v => v.toFixed(2)).join(' / '), fails);
  check(ga.pity && ga.ex, '천장(80회 안 영웅 이상 확정) · 마일리지 300 → 전설 교환', fails);
  check(ga.pet && ga.atk0 > 0 && ga.morph, '펫이 따라다니고 능력치 보너스 · 변신 인형 장착', fails);
  await page.evaluate(() => { __game.toggleGacha(); __game.P.gold = 300000; __game.pullGacha(11); });
  await page.waitForTimeout(1800); await page.screenshot({ path: `${OUT}/v8_gacha.png` });
  await page.evaluate(() => __game.toggleGacha());
  await page.waitForTimeout(400); await page.screenshot({ path: `${OUT}/v9_pet_morph.png` });

  // 12) 개발자 모드: 드롭 100% · 강화 100% · 뽑기 확률 상향
  const dev = await page.evaluate(() => {
    const G = __game, P = G.P; G.OPT.dev = 'on'; G.devChanged();
    P.inv.scroll_weapon = 10; P.weapon.enc = 9; const r = Math.random; Math.random = () => 0.99; const enc = G.enchantItem(P.weapon); Math.random = r;
    G.drops.length = 0; const m = G.mobs.find(x => x.type === 'goblin'); m.dead = false; G.killMob(m); const eq = G.drops.filter(d => d.equip).length;
    let hi = 0; for (let i = 0; i < 10000; i++) if (G.gachaRoll('morph').g >= 4) hi++;
    const badge = !document.getElementById('devBadge').classList.contains('hidden');
    G.OPT.dev = 'off'; G.devChanged();
    return { enc, eq, hi: hi / 100, badge };
  });
  check(dev.enc && dev.eq >= 1 && dev.hi > 10 && dev.badge, `개발자 모드: +9→+10 강화 성공, 장비 드롭 ${dev.eq}개, 뽑기 전설 이상 ${dev.hi}%`, fails);
  // 13) 치명타 피해 숫자
  const crit = await page.evaluate(() => { const G = __game, P = G.P; G.enterMap('field'); const m = G.mobs.find(x => x.type === 'wolf'); P.x = m.x + 1; P.y = m.y; m.hp = m.maxhp = 99999; return true; });
  await page.evaluate(() => { const G = __game, m = G.mobs.find(x => x.type === 'wolf'); for (let i = 0; i < 3; i++) { G.P.atkCd = 0; } });
  await page.evaluate(() => { const G = __game, m = G.mobs.find(x => x.type === 'wolf'); G.P.target = m; });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${OUT}/v10_damage.png` });
  check(crit && errors.length === 0, '콘솔 오류 0건' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''), fails);

  // 휴대폰: 아이콘 메뉴가 화면 안, 뽑기 창 넘침 없음
  console.log('[휴대폰]');
  const mob = await boot(browser, { viewport: { width: 844, height: 390 }, hasTouch: true, isMobile: true, deviceScaleFactor: 2 });
  const mo = await mob.page.evaluate(() => { const ok = ['btnAuto', 'btnInv', 'btnGacha', 'btnSnd', 'btnOpt'].every(id => { const r = document.getElementById(id).getBoundingClientRect(); return r.left >= 0 && r.bottom <= innerHeight && r.width >= 30; }); __game.toggleGacha(); const g = document.getElementById('gacha').getBoundingClientRect(); return { ok, g: g.left >= 0 && g.right <= innerWidth + 1 && g.bottom <= innerHeight + 1 }; });
  await mob.page.screenshot({ path: `${OUT}/v11_mobile_gacha.png` });
  check(mo.ok && mo.g, '휴대폰: 아이콘 메뉴·뽑기 창이 화면 안', fails);
  check(mob.errors.length === 0, '휴대폰 콘솔 오류 0건' + (mob.errors.length ? ': ' + mob.errors.slice(0, 3).join(' | ') : ''), fails);
  await browser.close();
  console.log(fails.length ? `실패 ${fails.length}건:\n - ${fails.join('\n - ')}` : '모두 통과');
  process.exit(fails.length ? 1 : 0);
})();
