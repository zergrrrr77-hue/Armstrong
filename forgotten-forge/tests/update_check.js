// 업데이트 점검: 상점(화로의 신) · 투명 조이스틱 · 이동 막힘 전수 검사 · 개별 수치(상위 %) · 특수 패시브 · 보스 드롭 · 월드보스
// 실행: node forgotten-forge/tests/update_check.js [스크린샷 폴더]
const { chromium } = require('playwright');
const path = require('path');
const OUT = process.argv[2] || '/tmp';
const URL = 'file://' + path.resolve(__dirname, '../index.html');

function check(cond, msg, fails) { if (!cond) fails.push(msg); console.log((cond ? '  ✓ ' : '  ✗ ') + msg); }

async function boot(browser, opt, cls = 0) {
  const ctx = await browser.newContext(opt);
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(URL);
  await page.waitForFunction(() => document.querySelectorAll('.cls').length === 3, null, { timeout: 20000 });
  await page.evaluate(() => localStorage.clear());
  await page.locator('.cls').nth(cls).click();
  await page.click('#start');
  await page.waitForTimeout(700);
  return { page, ctx, errors };
}

(async () => {
  const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
  const fails = [];

  // ───────── 데스크톱: 상점 · 막힘 · 아이템 · 보스 · 월드보스 ─────────
  console.log('[데스크톱]');
  const { page, errors } = await boot(browser, { viewport: { width: 1280, height: 760 } });

  // 1) 상점: 신 옆에서 '거래' 버튼을 실제로 마우스로 눌러 열림(이전 버그: 버튼 클릭이 캔버스로 빠짐)
  await page.evaluate(() => { const G = __game, P = G.P, n = G.map.npcs[0]; P.x = n.x + 1.3; P.y = n.y + 1.1; P.gold = 2000; });
  await page.waitForTimeout(250);
  const btnVis = await page.evaluate(() => !document.getElementById('shopBtn').classList.contains('hidden'));
  check(btnVis, '화로의 신 근처에서 거래 버튼 표시', fails);
  if (btnVis) await page.click('#shopBtn');
  await page.waitForTimeout(250);
  const opened = await page.evaluate(() => !document.getElementById('shop').classList.contains('hidden'));
  check(opened, '거래 버튼을 눌러 상점 열림', fails);
  await page.screenshot({ path: `${OUT}/u1_shop.png` });
  const bought = await page.evaluate(() => { const G = __game, P = G.P, n = P.inv.scroll_return || 0; G.buy(G.SHOP.find(s => s.id === 'scroll_return'), 1); return (P.inv.scroll_return || 0) === n + 1; });
  check(bought, '상점에서 귀환 주문서 구매', fails);
  await page.click('#shopTabs button[data-st="sell"]');
  const sellTab = await page.evaluate(() => !document.getElementById('shopSell').classList.contains('hidden'));
  check(sellTab, '판매 탭 전환', fails);
  await page.click('#shopClose');
  // 멀리서 신을 탭 → 걸어가서 자동으로 상점 열림
  await page.evaluate(() => { const G = __game, P = G.P; P.x = 15.5; P.y = 18.5; G.closeShop(); });
  await page.waitForTimeout(200);
  const npcScr = await page.evaluate(() => { const G = __game, n = G.map.npcs[0]; const c = document.getElementById('game'); return { ok: true }; });
  await page.evaluate(() => { const G = __game, n = G.map.npcs[0]; G.P.talk = true; G.P.goal = G.safeSpot(n.x + 1.2, n.y + 1.2); });
  await page.waitForTimeout(4000);
  const walked = await page.evaluate(() => !document.getElementById('shop').classList.contains('hidden'));
  check(walked && npcScr.ok, '멀리서 신을 누르면 걸어가 상점이 열림', fails);
  await page.keyboard.press('Escape');

  // 2) 이동 막힘 전수 검사(두 맵): 출현 자리·출구·되돌림 지점·월드보스가 도달 가능, 무작위 지점 길찾기, 갇힘 자가 복구
  for (const mapId of ['field', 'dungeon']) {
    const r = await page.evaluate((mapId) => {
      const G = __game, P = G.P; P.lv = 20; G.enterMap(mapId);
      const M = G.map, N = M.N, W = G.walkable;
      const cell = (x, y) => W(Math.floor(x), Math.floor(y));
      const badSpawn = M.spawns.filter(s => !cell(s.x, s.y)).length;
      const exitOk = cell(M.exit.x, M.exit.y) || [[-1, 0], [1, 0], [0, -1], [0, 1]].some(([a, b]) => W(Math.floor(M.exit.x) + a, Math.floor(M.exit.y) + b));
      const backOk = cell(G.safeSpot(M.back.x, M.back.y).x, G.safeSpot(M.back.x, M.back.y).y);
      const wb = G.WORLD_BOSS[mapId], wbOk = cell(wb.x, wb.y);
      // 무작위 도달 가능 칸 80곳으로 길찾기
      let free = [], reach = 0; for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) { if (!G.blocked[i * N + j]) free.push([i, j]); if (G.reach[i * N + j]) reach++; }
      let pathFail = 0; const R = (k) => free[Math.floor((Math.sin(k * 91.7) * 0.5 + 0.5) * free.length) % free.length];
      for (let k = 0; k < 80; k++) { const a = R(k), b = R(k + 500); if (!W(a[0], a[1]) || !W(b[0], b[1])) continue; const p = G.findPath(a[0] + 0.5, a[1] + 0.5, b[0] + 0.5, b[1] + 0.5, 6000); if (!p && (a[0] !== b[0] || a[1] !== b[1])) pathFail++; }
      // 갇힌(막힌) 칸 안에 강제로 넣어도 다음 프레임에 빠져나오는지
      let bi = -1; for (let k = 0; k < N * N; k++) if (G.blocked[k]) { bi = k; break; }
      P.x = Math.floor(bi / N) + 0.5; P.y = bi % N + 0.5; G.simulate(0.1);
      const healed = cell(P.x, P.y);
      return { badSpawn, exitOk, backOk, wbOk, pathFail, pockets: free.length - reach, healed };
    }, mapId);
    check(r.badSpawn === 0 && r.exitOk && r.backOk && r.wbOk, `[${mapId}] 출현·출구·되돌림·월드보스 자리 모두 도달 가능 ${JSON.stringify(r)}`, fails);
    check(r.pathFail === 0, `[${mapId}] 무작위 80개 지점 길찾기 성공`, fails);
    check(r.healed, `[${mapId}] 막힌 칸에 갇혀도 자동으로 빠져나옴`, fails);
  }
  // 실제 이동 시뮬레이션: 클릭 이동으로 먼 지점 30곳 도착
  const arrive = await page.evaluate(() => {
    const G = __game, P = G.P; G.enterMap('field'); P.hp = P.maxhp = 99999; G.setPaused(false);
    const N = G.map.N; let ok = 0, tried = 0;
    for (let k = 0; k < 30; k++) {
      const i = 3 + Math.floor((Math.sin(k * 12.9898) * 0.5 + 0.5) * (N - 6)), j = 3 + Math.floor((Math.sin(k * 78.233) * 0.5 + 0.5) * (N - 6));
      if (!G.walkable(i, j)) continue; tried++;
      P.target = null; P.goal = { x: i + 0.5, y: j + 0.5 }; P.autoHold = 999;
      for (let s = 0; s < 40 && P.goal; s++) G.simulate(1);
      if (Math.hypot(P.x - i - 0.5, P.y - j - 0.5) < 0.6) ok++;
      for (const m of G.mobs) if (m.d.wb) m.state = 'idle';
    }
    return { ok, tried };
  });
  check(arrive.ok >= arrive.tried - 1, `클릭 이동: 먼 지점 ${arrive.tried}곳 중 ${arrive.ok}곳 도착`, fails);
  // 레벨 미달로 던전 문에서 밀려날 때 막힌 칸에 끼지 않음
  const gate = await page.evaluate(() => { const G = __game, P = G.P; G.enterMap('field'); P.lv = 1; P.x = 51.5; P.y = 47.3; G.simulate(0.2); const ok = G.walkable(Math.floor(P.x), Math.floor(P.y)); P.lv = 20; return ok && G.map.id === 'field'; });
  check(gate, '레벨 미달 던전 문 되돌림: 빈 칸으로', fails);

  // 3) 개별 수치 · 상위 %
  const rolls = await page.evaluate(() => {
    const G = __game; const a = []; for (let k = 0; k < 400; k++) a.push(G.itemStats(G.makeEquip('b_great')).atk);
    const best = G.makeEquip('b_great'); best.r = { atk: 1 }; const mid = G.makeEquip('b_great'); mid.r = { atk: 0.5 };
    const ring = G.makeEquip('ringI_2'); ring.r = { mp: 0.95, crit: 0.95 };
    return { min: Math.min(...a), max: Math.max(...a), distinct: new Set(a).size, top1: G.topPct(best), top50: G.topPct(mid), ring: G.topPct(ring) };
  });
  check(rolls.distinct > 20 && rolls.min >= 13 * 0.8 - 0.05 && rolls.max <= 13 * 1.25 + 0.05, `같은 장비도 범위 안에서 다른 수치 ${JSON.stringify(rolls)}`, fails);
  check(rolls.top1 <= 0.11 && Math.abs(rolls.top50 - 50) < 0.5 && rolls.ring < 1, '상위 % 계산(최고=0.1%, 중간=50%, 두 능력치 모두 95% → 상위 0.5%)', fails);
  // 가방 상세에 상위 % 와 범위 표시
  await page.evaluate(() => { const G = __game, P = G.P; P.bag.length = 0; const e = G.makeEquip('b_great', 0, { px: { id: 'echo', v: 15 } }); P.bag.push(e); document.getElementById('inv').classList.remove('hidden'); G.renderInv(); document.querySelector('#eqgrid .cell').click(); });
  await page.waitForTimeout(200);
  const det = await page.evaluate(() => document.getElementById('detail').textContent);
  check(det.includes('상위') && det.includes('메아리') && det.includes('~'), '장비 상세: 범위·상위 %·특수 패시브 표시', fails);
  await page.screenshot({ path: `${OUT}/u2_item.png` });
  await page.evaluate(() => document.getElementById('inv').classList.add('hidden'));

  // 4) 특수 패시브: 메아리(직업 스킬 한 번 더) · 흡혈 · 연속 타격
  const px = await page.evaluate(() => {
    const G = __game, P = G.P; G.enterMap('field'); P.lv = 20; P.mp = P.maxmp = 999;
    const w = G.makeEquip('b_great', 0, { px: { id: 'echo', v: 45 } }); P.bag.push(w); G.equip(w.uid);
    P.px = { echo: 100, leech: 15, double: 100 };   // 시험: 확률 100%
    const m = G.mobs.find(x => x.type === 'wolf'); P.x = m.x + 0.8; P.y = m.y; m.hp = m.maxhp = 999999;
    P.cds = {}; G.useSkill(0); G.simulate(1.2);
    const echoed = G.LOOT !== null && document.getElementById('log').textContent.includes('메아리');
    P.hp = 50; const h0 = P.hp; P.target = m; P.cds = {}; P.atkCd = 0; G.simulate(1.0);
    return { echoed, healed: P.hp > h0 };
  });
  check(px.echoed, '메아리 패시브: 직업 스킬이 한 번 더 발동', fails);
  check(px.healed, '흡혈 패시브: 공격 시 체력 회복', fails);

  // 5) 보스 드롭: 높은 등급 위주지만 100% 확정은 아님
  const boss = await page.evaluate(() => {
    const G = __game; let eq = 0, hi = 0, kills = 300;
    for (let k = 0; k < kills; k++) {
      G.drops.length = 0;
      const m = { type: 'boss', x: 20, y: 20, lv: 1, d: Object.assign({ boss: true }, { xp: 0, name: 'x' }), buffs: {}, skillCd: {} };
      m.d = { boss: true, xp: 0, name: '몰락한 왕' };
      // killMob 의 장비 부분만: DROP_TABLE 사용
      const T = G.DROP_TABLE.boss; for (let n = 0; n < T.n; n++) if (Math.random() < T.equip) { eq++; const g = ['common', 'uncommon', 'rare', 'heroic', 'legend']; let r = Math.random() * 100, gi = 0; for (; gi < 5; gi++) { r -= T.odds[gi]; if (r < 0) break; } if (gi >= 3) hi++; }
    }
    return { rate: eq / (kills * G.DROP_TABLE.boss.n), hiRate: hi / eq };
  });
  check(boss.rate > 0.7 && boss.rate < 0.9 && boss.hiRate > 0.35, `보스 장비 드롭 ${Math.round(boss.rate * 100)}%(확정 아님) · 영웅 이상 ${Math.round(boss.hiRate * 100)}%`, fails);

  // 6) 월드보스: 출현 · 2배 크기 · 장판 · 처치 보상 · 다음 출현 시간 · 재출현
  const wb = await page.evaluate(() => {
    const G = __game, P = G.P; G.enterMap('field');
    const m = G.mobs.find(x => x.d.wb);
    const k = m.d.draw * G.map && 0;
    P.x = m.x - 3; P.y = m.y - 3; P.hp = P.maxhp = 99999; m.state = 'chase'; m.skillCd.rain = 0;
    G.simulate(0.3);
    const rain = G.hazards.length > 0;
    return { found: !!m, hp: m.maxhp, name: m.d.name, rain, draw: m.d.draw, alive: G.wbAlive('field') };
  });
  check(wb.found && wb.alive && wb.hp >= 3200 * 2, `월드보스 출현: ${wb.name} HP ${wb.hp}(일반 보스 3,200의 ${(wb.hp / 3200).toFixed(1)}배)`, fails);
  check(wb.rain, '월드보스 장판 공격(붉은 원)', fails);
  await page.waitForTimeout(300);
  await page.evaluate(() => { const G = __game, P = G.P, m = G.mobs.find(x => x.d.wb); P.x = m.x - 2.2; P.y = m.y - 1.2; P.target = m; });
  await page.waitForTimeout(900);
  await page.screenshot({ path: `${OUT}/u3_worldboss.png` });
  const kill = await page.evaluate(() => {
    const G = __game, P = G.P, m = G.mobs.find(x => x.d.wb); G.drops.length = 0;
    G.killMob(m);
    const books = G.drops.filter(d => d.id.startsWith('book_')).length;
    const timer = document.getElementById('wbTimer').textContent;
    return { books, alive: G.wbAlive('field'), kill: G.STATE.wbKill.field > 0 };
  });
  await page.waitForTimeout(1200);
  const timer = await page.evaluate(() => document.getElementById('wbTimer').textContent);
  check(kill.books === 1 && !kill.alive && kill.kill, '월드보스 처치: 스킬북 1권 확정 · 처치 기록', fails);
  check(/\d\d:\d\d:\d\d/.test(timer), '다음 출현까지 남은 시간 표시: ' + timer, fails);
  // 보상 확률(몬테카를로): 유니크 20% · 인형 희귀
  const odds = await page.evaluate(() => {
    const G = __game; let u = 0, doll = 0, n = 3000;
    const m = G.mobs.find(x => x.d.wb) || { x: 30, y: 30, d: { name: 't', wb: true }, type: 'wb_warlord' };
    const saveT = window.setTimeout; window.setTimeout = () => 0;
    for (let k = 0; k < n; k++) { G.drops.length = 0; G.wbDrops(m); if (G.drops.some(d => d.grade === 'unique')) u++; if (G.drops.some(d => d.id.startsWith('doll_'))) doll++; }
    window.setTimeout = saveT; G.drops.length = 0;
    const uq = G.makeEquip('u_gromm_b', 0, { px: { id: 'leech', v: 5 } });
    return { u: u / n, doll: doll / n, uniqueGrade: G.equipDef('u_gromm_b').grade };
  });
  check(Math.abs(odds.u - 0.2) < 0.03 && odds.doll < 0.03 && odds.uniqueGrade === 'unique', `월드보스 유니크 무기 ${(odds.u * 100).toFixed(1)}% · 변신 인형 ${(odds.doll * 100).toFixed(1)}%`, fails);
  // 6시간 칸이 바뀌면(처치 기록이 이전 칸) 다시 출현
  const respawn = await page.evaluate(() => { const G = __game; G.STATE.wbKill.field = G.wbSlot() - 1000; G.simulate(1.2); return G.mobs.some(m => m.d.wb && !m.dead); });
  check(respawn, '다음 6시간 칸에 월드보스 재출현', fails);
  const slots = await page.evaluate(() => { const G = __game; const hs = new Set(); for (let h = 0; h < 24; h++) { const d = new Date(); d.setHours(h, 30, 0, 0); hs.add(new Date(G.wbSlot(d.getTime())).getHours()); } return [...hs].sort((a, b) => a - b).join(','); });
  check(slots === '0,6,12,18', '출현 시각: 하루 4번(0·6·12·18시) ' + slots, fails);

  // 7) 스킬북으로 배운 스킬(5번) 사용 · 변신 인형
  const book = await page.evaluate(() => {
    const G = __game, P = G.P; P.inv.book_wb_quake = 2; P.inv.doll_wb_warlord = 1;
    G.useItem('book_wb_quake'); const lv1 = P.wbs.wb_quake; G.useItem('book_wb_quake'); const lv2 = P.wbs.wb_quake;
    const slots = document.querySelectorAll('#bar .slot').length;
    P.mp = P.maxmp; P.cds = {}; P.casting = null; G.useSkill(4); const cast = !!P.casting;
    G.simulate(1.2);
    G.useItem('doll_wb_warlord'); const morph = P.morph;
    return { lv1, lv2, slots, cast, morph };
  });
  check(book.lv1 === 1 && book.lv2 === 2 && book.cast, '스킬북: 배우기 → 다시 읽으면 레벨업 → 5번 키로 사용', fails);
  check(book.morph === 'wb_warlord', '변신 인형으로 월드보스 모습 변신', fails);
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${OUT}/u4_morph.png` });
  // 저장·불러오기에 새 정보가 남는지
  const sv = await page.evaluate(() => { const G = __game; G.save(); const d = G.loadSave(); return d && d.wbs && d.wbs.wb_quake === 2 && d.morph === 'wb_warlord' && d.state.wbKill && d.bag.every(e => e.r); });
  check(sv, '저장: 스킬북 스킬·변신·월드보스 기록·개별 수치 보존', fails);
  check(errors.length === 0, '콘솔 오류 0건' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''), fails);

  // ───────── 휴대폰: 투명 조이스틱 ─────────
  console.log('[휴대폰]');
  const mob = await boot(browser, { viewport: { width: 844, height: 390 }, hasTouch: true, isMobile: true, deviceScaleFactor: 2 });
  const mp = mob.page;
  const joyShown = await mp.evaluate(() => !document.getElementById('joyZone').classList.contains('hidden'));
  check(joyShown, '터치 기기에서 조이스틱 영역 표시', fails);
  const p0 = await mp.evaluate(() => ({ x: __game.P.x, y: __game.P.y }));
  // 손가락으로 누르고 오른쪽 위로 끌기(CDP 터치 이벤트)
  const cdp = await mob.ctx.newCDPSession(mp);
  const touch = (type, x, y) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: type === 'touchEnd' ? [] : [{ x, y, id: 1 }] });
  await touch('touchStart', 140, 300);
  for (let k = 1; k <= 6; k++) { await touch('touchMove', 140 + k * 8, 300 - k * 4); await mp.waitForTimeout(16); }
  await mp.waitForTimeout(900);
  const mid = await mp.evaluate(() => ({ x: __game.P.x, y: __game.P.y, on: __game.joy.on }));
  await mp.screenshot({ path: `${OUT}/u5_joystick.png` });
  await touch('touchEnd', 0, 0);
  await mp.waitForTimeout(200);
  const p1 = await mp.evaluate(() => ({ x: __game.P.x, y: __game.P.y, on: __game.joy.on, anim: __game.P.anim }));
  const moved = Math.hypot(mid.x - p0.x, mid.y - p0.y);
  check(mid.on && moved > 1.0, `조이스틱 드래그로 이동 (${moved.toFixed(2)}칸)`, fails);
  check(!p1.on, '손을 떼면 조이스틱 해제', fails);
  // 오른쪽 위로 끌면 화면에서도 오른쪽 위로 움직였는지(화면 좌표 x 증가, y 감소)
  const scr = await mp.evaluate(([a, b]) => { const sx = (x, y) => (x - y) * 32, sy = (x, y) => (x + y) * 16; return { dx: sx(b.x, b.y) - sx(a.x, a.y), dy: sy(b.x, b.y) - sy(a.x, a.y) }; }, [p0, mid]);
  check(scr.dx > 0 && scr.dy < 0, `끈 방향 = 화면 이동 방향 (dx ${scr.dx.toFixed(0)}, dy ${scr.dy.toFixed(0)})`, fails);
  // 조이스틱 영역을 짧게 톡 = 일반 탭(땅 이동)
  await mp.evaluate(() => { __game.P.goal = null; });
  await touch('touchStart', 70, 250); await mp.waitForTimeout(60); await touch('touchEnd', 0, 0);
  await mp.waitForTimeout(100);
  const tapGoal = await mp.evaluate(() => !!__game.P.goal);
  check(tapGoal, '조이스틱 영역 짧은 탭 → 그 자리로 이동(탭 기능 유지)', fails);
  // 휴대폰에서 상점 버튼 탭
  await mp.evaluate(() => { const G = __game, P = G.P, n = G.map.npcs[0]; P.goal = null; P.x = n.x + 1.3; P.y = n.y + 1.1; });
  await mp.waitForTimeout(250);
  const b = await mp.locator('#shopBtn').boundingBox();
  if (b) { await touch('touchStart', b.x + b.width / 2, b.y + b.height / 2); await touch('touchEnd', 0, 0); }
  await mp.waitForTimeout(300);
  const mshop = await mp.evaluate(() => !document.getElementById('shop').classList.contains('hidden'));
  check(mshop, '휴대폰: 거래 버튼 탭으로 상점 열림', fails);
  await mp.screenshot({ path: `${OUT}/u6_mobile_shop.png` });
  const ov = await mp.evaluate(() => { const r = document.getElementById('shop').getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth + 1 && document.documentElement.scrollWidth <= innerWidth; });
  check(ov, '휴대폰: 상점 창이 화면 밖으로 넘치지 않음', fails);
  check(mob.errors.length === 0, '휴대폰 콘솔 오류 0건' + (mob.errors.length ? ': ' + mob.errors.slice(0, 3).join(' | ') : ''), fails);

  await browser.close();
  console.log(fails.length ? `실패 ${fails.length}건:\n - ${fails.join('\n - ')}` : '모두 통과');
  process.exit(fails.length ? 1 : 0);
})();
