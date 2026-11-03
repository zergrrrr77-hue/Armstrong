// 에르덴 시스템 확장 점검: 재료·채집·드롭 · 드로간 제작 · 강화 규칙(안전 구간·소멸·축복)
// 실행: NODE_PATH=$(npm root -g) node forgotten-forge/tests/erden_systems_check.js [스크린샷 폴더]
const { chromium } = require('playwright');
const path = require('path');
const OUT = process.argv[2] || '/tmp';
const URL = 'file://' + path.resolve(__dirname, '../index.html');
function check(cond, msg, fails) { if (!cond) fails.push(msg); console.log((cond ? '  ✓ ' : '  ✗ ') + msg); }
const realError = (t) => !/ERR_TUNNEL_CONNECTION_FAILED|ERR_INTERNET_DISCONNECTED|fonts\.g/.test(t);

(async () => {
  const browser = await chromium.launch();
  const fails = [], errors = [];
  const page = await browser.newPage({ viewport: { width: 1280, height: 760 } });
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error' && realError(m.text())) errors.push(m.text()); });
  const title = () => page.waitForFunction(() => document.querySelectorAll('.cls').length === 3, null, { timeout: 20000 });
  await page.goto(URL); await title();
  await page.evaluate(() => localStorage.clear()); await page.reload(); await title();
  console.log('[시작 화면·이름]');
  await page.waitForTimeout(600);
  const art = await page.evaluate(() => { const bg = document.getElementById('titleBg'), em = document.getElementById('titleEmblem');
    const px = (cv) => { const d = cv.getContext('2d').getImageData(cv.width / 2, cv.height / 2, 1, 1).data; return d[0] + d[1] + d[2]; };
    return { bg: bg.width > 0 && px(bg) > 0, em: px(em) > 200 }; });
  check(art.bg && art.em, '배경(밤하늘·성채)과 빛나는 별의 심장 문장이 그려짐', fails);
  const nk = await page.evaluate(() => { const g = __game; return ['', '가', '가나다라마바사아자', 'ab1', '별@빛', 'ㄱㄴ', '운영자님', 'Admin', '드 로', '아린', 'Luna', '별빛아린'].map(s => [s, g.nickCheck(s).ok]); });
  const want = [false, false, false, false, false, false, false, false, false, true, true, true];
  check(nk.every(([, ok], i) => ok === want[i]), `이름 규칙: ${nk.map(([s, ok]) => `${s || '(빈칸)'}=${ok ? '○' : '×'}`).join(' ')}`, fails);
  await page.locator('.cls').nth(0).click(); await page.fill('#nick', '별@빛'); 
  const blocked = await page.evaluate(() => ({ dis: document.getElementById('start').disabled, msg: document.getElementById('nickMsg').textContent }));
  check(blocked.dis && /특수문자/.test(blocked.msg), `잘못된 이름이면 시작 막힘: ${blocked.msg}`, fails);
  await page.fill('#nick', '아린');
  await page.screenshot({ path: `${OUT}/sys_title.png` });
  await page.setViewportSize({ width: 390, height: 844 }); await page.waitForTimeout(300); await page.screenshot({ path: `${OUT}/sys_title_phone.png` }); await page.setViewportSize({ width: 1280, height: 760 });
  await page.click('#start'); await page.waitForTimeout(800);
  const nm = await page.evaluate(() => { __game.save(); return { p: document.getElementById('pname').textContent, inv: document.getElementById('invName').textContent, sv: JSON.parse(localStorage.getItem('erden_save_v2')).name }; });
  check(nm.p === '아린' && nm.inv === '아린' && nm.sv === '아린', `이름이 상태창·가방·저장에: ${nm.p} / ${nm.inv} / ${nm.sv}`, fails);

  console.log('[재료·몬스터]');
  const m = await page.evaluate(() => { const g = __game; return {
    mats: Object.keys(g.MATERIALS).length, xi: g.XITEMS.mat_dog_hide && g.XITEMS.mat_dog_hide.ico === 3,
    names: [...new Set(g.mobs.map(x => x.d.name))], archerSheet: (g.mobs.find(x => x.type === 'goblin_archer') || {}).sheet,
    future: Object.keys(g.FUTURE_MOBS) }; });
  check(m.mats === 20 && m.xi, `재료 ${m.mats}종 등록 + 재료 아이콘 번호`, fails);
  check(m.names.includes('들개') && m.names.includes('고블린 궁수'), `들판에 들개·고블린 궁수: ${m.names.join(', ')}`, fails);
  check(m.archerSheet === 'goblin', '고블린 궁수는 고블린 그림을 씀', fails);
  check(m.future.join() === 'elasia,kardum', '엘라시아·카르둠 몬스터는 데이터만', fails);
  const drop = await page.evaluate(() => { const g = __game, d = g.mobs.find(x => x.type === 'ooze'); const before = g.drops.length;
    let gel = 0; for (let i = 0; i < 40; i++) { const o = Object.assign({}, d, { dead: false, hp: 0 }); g.drops.length = 0; g.killMob(o); if (g.drops.some(x => x.id === 'mat_slime_gel')) gel++; }
    return gel; });
  check(drop >= 18 && drop <= 39, `슬라임 40마리 → 점액 ${drop}번(기대 약 28)`, fails);

  console.log('[채집]');
  const gat = await page.evaluate(async () => { const g = __game, n = g.map.nodes.find(x => x.kind === 'ore');
    g.P.x = n.x + 0.8; g.P.y = n.y + 0.8; g.P.goal = null; g.P.target = null; const before = g.P.inv.mat_iron_ore || 0;
    const ok = g.startGather(n); await new Promise(r => setTimeout(r, 2300));
    return { nodes: g.map.nodes.length, ok, got: (g.P.inv.mat_iron_ore || 0) - before, ready: n.ready }; });
  check(gat.nodes >= 10 && gat.ok, `채집 지점 ${gat.nodes}곳, 광맥 캐기 시작`, fails);
  check(gat.got >= 1 && !gat.ready, `철광석 +${gat.got}, 다 캔 광맥은 잠시 비활성`, fails);
  await page.screenshot({ path: `${OUT}/sys_gather.png` });

  console.log('[드로간 제작]');
  const cr = await page.evaluate(() => { const g = __game, P = g.P; P.lv = 12; P.gold = 20000; const r = g.RECIPES[0];
    const smith = !!g.map.smith; g.openCraft();
    const lockedRow = [...document.querySelectorAll('#craftList .crow')].length;
    for (const [id, n] of Object.entries(r.mats)) P.inv[id] = n; const bag = P.bag.length;
    g.OPT.dev = true; const ok = g.craftItem(r); g.OPT.dev = false;
    const made = P.bag.length === bag + 1 && P.bag[P.bag.length - 1].key === 'cr_iron_short';
    const matsGone = Object.keys(r.mats).every(id => P.inv[id] === 0);
    // 실패: 재료·에테르 모두 사라짐(확률 0으로 강제)
    for (const [id, n] of Object.entries(r.mats)) P.inv[id] = n; const gold = P.gold; const save = r.ch; r.ch = 0; const fail = g.craftItem(r); r.ch = save;
    const failGone = !fail && Object.keys(r.mats).every(id => P.inv[id] === 0) && P.gold === gold - r.cost;
    const bow = g.RECIPES[1]; for (const [id, n] of Object.entries(bow.mats)) P.inv[id] = n;
    g.renderCraft && 0; document.querySelector('#craftTabs [data-ct="all"]').click();
    const rows = [...document.querySelectorAll('#craftList .crow')].map(x => x.querySelector('.lockr') ? x.querySelector('.lockr').textContent : '');
    return { smith, lockedRow, ok, made, matsGone, failGone, rows, open: !document.getElementById('craft').classList.contains('hidden') }; });
  check(cr.smith && cr.open && cr.lockedRow === 2, `대장간 창 열림, 기사용 제작법 ${cr.lockedRow}개`, fails);
  check(cr.ok && cr.made && cr.matsGone, '철제 숏소드 제작 성공 → 가방에 들어오고 재료 소모', fails);
  check(cr.failGone, '실패하면 재료와 에테르가 사라짐', fails);
  check(cr.rows.length === 6 && /요정 전용/.test(cr.rows[1]) && /열리지 않았/.test(cr.rows[2]), `잠긴 이유 표시: ${cr.rows.slice(1, 3).join(' / ')}`, fails);
  await page.screenshot({ path: `${OUT}/sys_craft.png` });
  const eqp = await page.evaluate(() => { const g = __game; g.closeCraft(); const e = g.P.bag.find(x => x.key === 'cr_iron_short'); const bowE = { uid: 99999, key: 'cr_hunter_bow', enc: 0, r: {} }; g.P.bag.push(bowE);
    const a = g.useItem ? null : null; return { has: !!e }; });
  check(eqp.has, '제작 무기가 가방에 있음', fails);

  console.log('[강화 규칙]');
  const en = await page.evaluate(() => { const g = __game;
    return { c0: g.encChance('weapon', 0, 'common'), c2: g.encChance('weapon', 2, 'common'), c3: g.encChance('weapon', 3, 'common'), u2: g.encChance('weapon', 2, 'uncommon'),
      r1: g.encChance('weapon', 1, 'rare'), r0: g.encChance('weapon', 0, 'rare'),
      f: [g.encFail(1, 'rare'), g.encFail(4, 'common'), g.encFail(7, 'common'), g.encFail(0, 'common')],
      st: [g.encStone('weapon', 'common'), g.encStone('armor', 'uncommon'), g.encStone('weapon', 'rare')], name: g.XITEMS.scroll_weapon.name }; });
  check(en.c0 === 100 && en.c2 === 100 && en.c3 === 60 && en.u2 === 75 && en.r0 === 100 && en.r1 === 82, `안전 구간·확률: 일반+2→${en.c2} · 일반+3→${en.c3} · 고급+2→${en.u2} · 희귀+1→${en.r1}`, fails);
  check(en.f.join() === 'keep,risk,break,none', `실패 결과: ${en.f.join(', ')}`, fails);
  check(en.st.join() === 'scroll_weapon,scroll_armor,star_shard' && en.name.includes('별빛 강화석'), `강화석: ${en.name} / 희귀 이상 정제된 별의 파편`, fails);
  const br = await page.evaluate(() => { const g = __game, P = g.P; const w = P.eq.weapon; w.enc = 7; P.inv.scroll_weapon = 5;
    const R = Math.random; Math.random = () => 0.99; const ok = g.enchantItem(w); Math.random = R;
    const gone = !P.bag.some(x => x.uid === w.uid) && P.eq.weapon && P.eq.weapon.uid !== w.uid && P.eq.weapon.enc === 0;
    // 축복받은 강화석: +7에서 실패해도 유지
    const w2 = P.eq.weapon; w2.enc = 7; P.inv.blessed_stone = 1; Math.random = () => 0.99; g.enchantItem(w2, true); Math.random = R;
    const kept = P.eq.weapon === w2 && w2.enc === 7 && P.inv.blessed_stone === 0;
    // 축복 대성공: +0 → +3
    const w3 = P.eq.weapon; w3.enc = 0; P.inv.blessed_stone = 1; Math.random = () => 0.05; g.enchantItem(w3, true); Math.random = R;
    return { ok, gone, kept, jump: w3.enc, base: P.eq.weapon.key }; });
  check(!br.ok && br.gone, `+7 실패 → 무기 소멸, 기본 무기(${br.base})로 교체`, fails);
  check(br.kept, '축복받은 강화석: 실패해도 단계 유지', fails);
  check(br.jump === 3, `축복받은 강화석 대성공 +0 → +${br.jump}`, fails);

  console.log('[오류]');
  check(errors.length === 0, `페이지 오류 없음${errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''}`, fails);
  await browser.close();
  console.log(fails.length ? `\n실패 ${fails.length}개` : '\n모두 통과');
  process.exit(fails.length ? 1 : 0);
})();
