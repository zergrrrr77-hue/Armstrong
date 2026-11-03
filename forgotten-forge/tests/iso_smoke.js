// 잊혀진 대장간(리니지풍) 기본 점검:
// 클래스 3종 시작 → 이동 → 기본 공격 → 스킬 4종 → 물약 → 강화 → 장비 드롭·착용 → 자동사냥 → 던전 입장 → 보스 스킬 → 보스 처치 → 휴대폰 정보창 겹침 → 오류 0건
// 실행: node forgotten-forge/tests/iso_smoke.js [스크린샷 폴더]
const { chromium } = require('playwright');
const path = require('path');
const OUT = process.argv[2] || '/tmp';

function check(cond, msg, fails) { if (!cond) fails.push(msg); console.log((cond ? '  ✓ ' : '  ✗ ') + msg); }

(async () => {
  const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
  const fails = [];
  for (const cls of ['knight', 'elf', 'mage']) {
    console.log(`[${cls}]`);
    const page = await browser.newPage({ viewport: { width: 1280, height: 760 } });
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
    await page.goto('file://' + path.resolve(__dirname, '../index.html'));
    await page.waitForFunction(() => document.querySelectorAll('.cls').length === 3, null, { timeout: 20000 });
    const idx = ['knight', 'elf', 'mage'].indexOf(cls);
    await page.locator('.cls').nth(idx).click();
    if (cls === 'knight') await page.screenshot({ path: `${OUT}/g0_title.png` });
    await page.fill('#nick', '테스터').then(() => page.click('#start'));
    await page.waitForTimeout(600);

    // 이동(키보드)
    const p0 = await page.evaluate(() => ({ x: __game.P.x, y: __game.P.y }));
    await page.keyboard.down('KeyD'); await page.waitForTimeout(700); await page.keyboard.up('KeyD');
    const p1 = await page.evaluate(() => ({ x: __game.P.x, y: __game.P.y }));
    check(Math.hypot(p1.x - p0.x, p1.y - p0.y) > 0.5, '키보드로 이동', fails);
    await page.waitForTimeout(700);
    const tm = await page.evaluate(() => ({ k: __game.musicKind(), t: __game.audio() && __game.audio().track }));
    check(tm.t && tm.t.startsWith(tm.k + '_'), '장면별 배경음악: ' + JSON.stringify(tm), fails);

    // 4단계: Lv 1에서 스킬 잠김·던전 입장 제한 → 레벨업 시 포인트·해금
    const lock = await page.evaluate(() => { const G = __game, P = G.P; P.mp = P.maxmp; G.useSkill(3); return !P.casting; });
    check(lock, 'Lv 1에서 4번 스킬 잠김', fails);
    if (cls === 'knight') {
      await page.evaluate(() => { const P = __game.P; P.x = 51.5; P.y = 46.6; });
      await page.waitForTimeout(500);
      const gate = await page.evaluate(() => __game.map.id === 'field');
      check(gate, '던전 입장 레벨 제한(Lv 5)', fails);
      await page.evaluate(() => { const P = __game.P; P.x = 13.5; P.y = 13.5; });
    }
    const lv = await page.evaluate(() => { const G = __game, P = G.P; const hp0 = P.maxhp; while (P.lv < 8) G.gainXp(G.xpNeed(P.lv)); const sp = P.sp; G.addStat('con'); return { lv: P.lv, sp, hpUp: P.maxhp > hp0, sp2: P.sp }; });
    check(lv.lv === 8 && lv.sp === 14 && lv.sp2 === 13 && lv.hpUp, `레벨업 → 능력치 포인트 ${lv.sp}점, 체력 투자`, fails);
    await page.evaluate(() => { const P = __game.P; P.maxhp = 99999; P.hp = 99999; });
    // 늑대 옆으로 옮겨 기본 공격
    await page.evaluate(() => { const m = __game.mobs.find(m => m.type === 'wolf'); __game.P.x = m.x - 1; __game.P.y = m.y; __game.P.target = m; m.state = 'idle'; });
    await page.waitForTimeout(3500);
    const hit = await page.evaluate(() => __game.mobs.some(m => m.type === 'wolf' && (m.hp < m.maxhp || m.dead)));
    check(hit, '기본 공격으로 피해', fails);
    if (cls === 'knight') await page.screenshot({ path: `${OUT}/g1_field.png` });

    if (cls === 'knight') {
      // 2단계: 넉백·히트스톱·검격 잔상 / 몬스터 몰림 방지 / 원거리 몬스터
      const fx = await page.evaluate(() => { const G = __game, P = G.P; const m = G.mobs.find(x => x.type === 'goblin' && !x.dead); P.x = m.x - 1; P.y = m.y; m.hp = 9999; m.maxhp = 9999; P.target = m; return true; });
      await page.waitForTimeout(2500);
      const c1 = await page.evaluate(() => __game.combat);
      check(c1.kb > 0 && c1.stop > 0 && c1.slash > 0, `넉백 ${c1.kb} · 히트스톱 ${c1.stop} · 검격 잔상 ${c1.slash}`, fails);
      const sep = await page.evaluate(() => { const G = __game, P = G.P; P.target = null; const ws = G.mobs.filter(x => x.type === 'wolf' && !x.dead).slice(0, 4); ws.forEach((w, i) => { w.x = P.x + 2 + i * 0.05; w.y = P.y + 0.02 * i; w.state = 'chase'; }); return ws.length; });
      await page.waitForTimeout(3000);
      const minD = await page.evaluate(() => { const ws = __game.mobs.filter(x => x.type === 'wolf' && !x.dead && Math.hypot(x.x - __game.P.x, x.y - __game.P.y) < 5); let m = 99; for (let i = 0; i < ws.length; i++) for (let j = i + 1; j < ws.length; j++) m = Math.min(m, Math.hypot(ws[i].x - ws[j].x, ws[i].y - ws[j].y)); return m; });
      check(minD > 0.45, `몬스터가 한곳에 겹치지 않음 (최소 간격 ${minD.toFixed(2)})`, fails);
      await page.evaluate(() => { const G = __game, P = G.P; const a = G.mobs.find(x => x.type === 'skeleton_archer' && !x.dead); P.x = a.x - 4.5; P.y = a.y; a.state = 'chase'; a.atkCd = 0; G.combat.mobShots = 0; });
      await page.waitForTimeout(3500);
      const shots = await page.evaluate(() => __game.combat.mobShots);
      check(shots > 0, `해골 궁수 원거리 공격 ${shots}발`, fails);
    }
    // 스킬 4종 (MP·재사용 대기 무시하고 하나씩)
    for (let i = 0; i < 4; i++) {
      await page.evaluate((i) => { const P = __game.P; P.mp = P.maxmp; P.hp = P.maxhp; P.cds = {}; const m = __game.nearestMob(20); if (m) { P.x = m.x - 1.2; P.y = m.y; } __game.useSkill(i); }, i);
      await page.waitForTimeout(250);
      const fx = await page.evaluate(() => __game.fxs.length);
      check(fx > 0, `스킬 ${i + 1} 이펙트 재생`, fails);
      if (cls !== 'knight' && i === 0) await page.screenshot({ path: `${OUT}/g2_${cls}_skill.png` });
      await page.waitForTimeout(900);
    }
    if (cls === 'knight') await page.screenshot({ path: `${OUT}/g2_knight_skill.png` });

    // 물약·강화
    const pot = await page.evaluate(() => { const P = __game.P; if (P.dead) return false; P.hp = 10; const n = P.inv.pot_red; __game.drink('pot_red'); return P.hp > 10 && P.inv.pot_red === n - 1; });
    check(pot, '체력 물약', fails);
    const enc = await page.evaluate(() => { const P = __game.P; P.inv.scroll_weapon = 3; __game.enchant('w'); __game.enchant('w'); return P.wEnc === 2; });
    check(enc, '무기 강화(안전 구간)', fails);
    const gold = await page.evaluate(() => document.getElementById('gold').textContent.includes('에테르'));
    check(gold, '화폐 단위 에테르', fails);

    // 장비 드롭 → 줍기 → 착용
    const eq = await page.evaluate(() => {
      const G = __game, P = G.P;
      const before = G.equipDef(P.weapon.key).atk;
      const key = { knight: 'b_great', elf: 'w_elven', mage: 's_mana' }[P.cls];
      G.drops.push({ id: G.equipDef(key).icon, equip: G.makeEquip(key), n: 1, x: P.x, y: P.y, t: 0 });
      return before;
    });
    await page.waitForTimeout(300);
    const eq2 = await page.evaluate(() => { const G = __game, P = G.P; if (!P.bag.length) return 0; G.equip(P.bag[P.bag.length - 1].uid); return G.equipDef(P.weapon.key).atk; });
    check(eq2 > eq, '장비 줍기·착용으로 공격력 상승', fails);
    await page.keyboard.press('KeyI'); await page.locator('#invTabs button', { hasText: '확률표' }).click(); await page.waitForTimeout(200);
    const tables = await page.evaluate(() => { const d = document.getElementById('dropTable'), e = document.getElementById('encTable'); return d.offsetHeight > 50 && e.offsetHeight > 50 && d.textContent.includes('검은 늑대') && e.textContent.includes('%'); });
    if (cls === 'knight') await (await page.$('#inv')).screenshot({ path: `${OUT}/g8_prob.png` });
    await page.keyboard.press('KeyI');
    check(tables, '드롭률·강화 확률 표 표시', fails);

    if (cls === 'knight') {
      // 3단계: 설정(가방 일시정지), 목표 창 접기, 미니맵 확대, 장비 상세·강화 연출, 자동 물약 기준
      await page.keyboard.press('KeyI'); await page.waitForTimeout(150);
      const pz = await page.evaluate(() => __game.uiPaused);
      await page.keyboard.press('KeyI');
      check(pz === true, '가방을 열면 일시정지(기본 설정)', fails);
      await page.click('#qToggle'); const fold = await page.evaluate(() => document.getElementById('quest').classList.contains('fold')); await page.click('#qToggle');
      check(fold, '목표 창 접기', fails);
      await page.click('#mmIn'); const z = await page.evaluate(() => __game.OPT.mmZoom); await page.click('#mmOut');
      check(z === 2, '미니맵 확대/축소', fails);
      await page.keyboard.press('KeyI');
      await page.locator('#invTabs button', { hasText: '장비' }).click();
      await page.click('#wIcon'); await page.waitForTimeout(100);
      const det = await page.evaluate(() => { const t = document.getElementById('detail').textContent; return ['등급', '공격력', '강화', '착용', '다음 강화', '필요 재료'].every(k => t.includes(k)); });
      check(det, '장비 상세: 등급·능력치·강화·착용·다음 강화·재료', fails);
      await page.evaluate(() => { __game.P.inv.scroll_weapon = 2; __game.P.inv.star_shard = 2; __game.renderInv(); });
      await page.click('#btnEnc'); await page.waitForTimeout(100);
      const toast = await page.evaluate(() => document.getElementById('encToast').textContent);
      check(/강화/.test(toast), '강화 결과 알림: ' + toast, fails);
      await (await page.$('#inv')).screenshot({ path: `${OUT}/g9_detail.png` });
      // 창고형 장비창: 11칸 · 부위 장비 드롭/착용/해제 · 착용 버튼이 화면 안에 보임
      const slots = await page.evaluate(() => document.querySelectorAll('#dslots .dslot').length);
      check(slots === 11, '장비 칸 11개(투구·목걸이·무기·갑옷·방패·망토·장갑·장화·반지 2·팔찌): ' + slots, fails);
      const gear = await page.evaluate(() => {
        const G = __game, P = G.P; P.lv = Math.max(P.lv, 20);
        const hp0 = P.maxhp, keys = ['helm_2', 'gloves_2', 'boots_2', 'cloak_2', 'shield_2', 'amulet_2', 'ringS_2', 'ringI_2', 'bracelet_2'];
        for (const k of keys) P.bag.push(G.makeEquip(k));
        G.renderInv(); return { hp0, def0: G.EQS().def };
      });
      await page.locator('#bagFilter .chip', { hasText: '방어구' }).click();
      await page.locator('#eqgrid .cell[title*="기사의 투구"]').click();
      const vis = await page.evaluate(() => { const b = document.getElementById('btnEquip'); if (!b) return false; const r = b.getBoundingClientRect(); return r.bottom <= innerHeight && r.top >= 0 && r.width > 0; });
      check(vis, '아이템 선택 시 착용 버튼이 화면 안에 보임', fails);
      await page.click('#btnEquip');
      await page.locator('#bagFilter .chip', { hasText: '전체' }).click();
      const g2 = await page.evaluate(() => { const G = __game, P = G.P; for (const e of [...P.bag]) if (/_2$/.test(e.key)) G.equip(e.uid); G.renderInv();
        return { n: Object.values(P.eq).filter(Boolean).length, def: G.EQS().def, hp: P.maxhp, r1: !!P.eq.ring1, r2: !!P.eq.ring2 }; });
      check(g2.n === 11 && g2.r1 && g2.r2, '11부위 모두 착용(반지 2개): ' + g2.n, fails);
      check(g2.def > gear.def0 && g2.hp > gear.hp0, `부위 장비 능력치 반영(방어 ${gear.def0}→${g2.def}, HP ${gear.hp0}→${g2.hp})`, fails);
      await (await page.$('#inv')).screenshot({ path: `${OUT}/g9b_store.png` });
      await page.click('.dslot[data-slot="helm"]'); await page.click('#btnUnequip');
      const un = await page.evaluate(() => !__game.P.eq.helm && __game.P.bag.some(e => e.key === 'helm_2'));
      check(un, '장비 해제 → 가방으로', fails);
      const encH = await page.evaluate(() => { const G = __game, P = G.P; P.inv.scroll_armor = 3; P.inv.star_shard = 3; const e = P.eq.boots; G.enchantItem(e); return P.inv.scroll_armor + P.inv.star_shard === 5; });
      check(encH, '장화를 별빛 강화석(방어구)으로 강화', fails);
      const accNo = await page.evaluate(() => __game.enchantItem(__game.P.eq.amulet) === false);
      check(accNo, '장신구는 강화 불가', fails);
      await page.keyboard.press('KeyI');
      const pot = await page.evaluate(() => { const G = __game, P = G.P; G.OPT.potHp = 60; P.hp = P.maxhp * 0.5; return P.inv.pot_red; });
      await page.waitForTimeout(600);
      const pot2 = await page.evaluate(() => { const P = __game.P; __game.OPT.potHp = 40; return P.inv.pot_red; });
      check(pot2 < pot, '자동 물약 기준 설정(60%) 반영', fails);
    }
    if (cls === 'elf') {
      // 5단계: 골드 획득 연출·기록, 희귀 장비 알림, 등급 빛기둥(드롭 정보에 등급 기록)
      const r5 = await page.evaluate(() => { const G = __game, P = G.P; const g0 = P.gold; G.drops.push({ id: 'gold', n: 33, x: P.x, y: P.y, t: 0 }); G.drops.push({ id: 'bow', equip: G.makeEquip('w_wind'), n: 1, x: P.x, y: P.y, t: 0, grade: 'heroic' }); return g0; });
      await page.waitForTimeout(400);
      const r6 = await page.evaluate(() => ({ gold: __game.P.gold, loot: __game.LOOT.map(l => l.text).join('|'), banner: document.querySelector('#banner b').textContent }));
      check(r6.gold === r5 + 33 && r6.loot.includes('33 에테르') && r6.loot.includes('바람의 활'), '에테르·장비 획득 기록', fails);
      check(r6.banner.includes('바람의 활'), '영웅 장비 획득 알림', fails);
    }
    // 상점: 화로의 신(신전 앞) 옆에서 열고 물약 구매
    const shop = await page.evaluate(() => { const G = __game, P = G.P; const n = G.map.npcs[0]; P.x = n.x + 1.2; P.y = n.y + 1.0; P.gold = 1000; return true; });
    await page.waitForTimeout(300);
    await page.keyboard.press('KeyF'); await page.waitForTimeout(200);
    const bought = await page.evaluate(() => { const G = __game, P = G.P; const n = P.inv.pot_red; const vis = !document.getElementById('shop').classList.contains('hidden'); G.buy(G.SHOP[0], 10); return vis && P.inv.pot_red === n + 10 && P.gold === 750; });
    check(bought, '마을 상점에서 물약 구매', fails);
    const safe = await page.evaluate(() => __game.inTown(__game.P));
    check(safe, '마을은 안전 지대', fails);
    await page.keyboard.press('Escape');
    // 목표: 늑대 처치가 목표 진행에 반영
    const q = await page.evaluate(() => { const S = __game.STATE; return { quest: S.quest || 0, qn: S.qn || 0, text: document.getElementById('qt').textContent }; });
    check(q.text.length > 0, '목표 창 표시: ' + q.text, fails);

    // 자동사냥: 켜 두면 스스로 대상을 찾아 공격
    const k0 = await page.evaluate(() => { const P = __game.P; P.hp = P.maxhp; P.target = null; P.goal = null; __game.setAuto(true); return __game.STATE.kills; });
    await page.waitForTimeout(9000);
    const k1 = await page.evaluate(() => ({ kills: __game.STATE.kills, target: !!__game.P.target, auto: __game.P.auto, hp: __game.P.hp }));
    check(k1.kills > k0 || k1.target, '자동사냥으로 대상 공격', fails);
    await page.evaluate(() => __game.setAuto(false));

    if (cls === 'knight') {
      // 던전 입장
      await page.evaluate(() => { const P = __game.P; P.x = 51.5; P.y = 46.6; });
      await page.waitForTimeout(800);
      const inDungeon = await page.evaluate(() => __game.map.id === 'dungeon');
      check(inDungeon, '지하 계단으로 던전 입장', fails);
      await page.waitForTimeout(600);
      await page.screenshot({ path: `${OUT}/g3_dungeon.png` });
      // 보스 앞으로 이동 → 보스 스킬 관찰
      await page.evaluate(() => { const P = __game.P; P.maxhp = 99999; P.hp = 99999; const b = __game.mobs.find(m => m.type === 'boss'); P.x = b.x - 2.0; P.y = b.y + 0.3; b.state = 'chase'; b.skillCd.skill_hellfire = 0; });
      await page.waitForTimeout(750);
      await page.screenshot({ path: `${OUT}/g4_boss_skill.png` });
      const bossFx = await page.evaluate(() => (__game.STATE.bossSkills || 0) > 0);
      const bm = await page.evaluate(() => ({ k: __game.musicKind(), t: __game.audio() && __game.audio().track }));
      check(bm.k === 'boss' && /^boss_/.test(bm.t || ''), '보스전 배경음악 전환: ' + JSON.stringify(bm), fails);
      check(bossFx, '보스 스킬 사용', fails);
      await page.waitForTimeout(1500);
      // 보스 처치
      await page.evaluate(() => { const b = __game.mobs.find(m => m.type === 'boss'); b.hp = 30; __game.P.target = b; });
      await page.waitForTimeout(7000);
      const dead = await page.evaluate(() => __game.STATE.bossDead);
      check(dead, '보스 처치', fails);
      await page.screenshot({ path: `${OUT}/g5_victory.png` });
    }
    if (cls === 'mage') {
      // 예전 저장 데이터(능력치 없음) 호환
      await page.reload();   // 떠날 때 자동 저장되므로, 시작 화면(저장 꺼짐)에서 고친 뒤 다시 불러옴
      await page.waitForFunction(() => document.querySelectorAll('.cls').length === 3, null, { timeout: 20000 });
      await page.evaluate(() => { const d = JSON.parse(localStorage.getItem('erden_save_v2')); delete d.st; delete d.sp; d.lv = 5; localStorage.setItem('erden_save_v2', JSON.stringify(d)); });
      await page.reload();
      await page.waitForFunction(() => document.querySelectorAll('.cls').length === 3, null, { timeout: 20000 });
      await page.click('#continue'); await page.waitForTimeout(400);
      const compat = await page.evaluate(() => __game.P.lv === 5 && __game.P.sp === 8 && !!__game.P.st);
      check(compat, '예전 저장 불러오기: 레벨만큼 포인트 지급', fails);
    }
    // 저장 → 새로고침 → 이어하기
    const lv0 = await page.evaluate(() => { const P = __game.P; P.lv = 6; P.gold = 4321; __game.save(); return P.lv; });
    await page.reload();
    await page.waitForFunction(() => document.querySelectorAll('.cls').length === 3, null, { timeout: 20000 });
    const contVis = await page.evaluate(() => !document.getElementById('continue').classList.contains('hidden'));
    if (contVis) await page.click('#continue');
    await page.waitForTimeout(500);
    const restored = await page.evaluate(() => __game.P && __game.P.lv === 6 && __game.P.gold === 4321);
    check(contVis && restored, '자동 저장 후 이어하기', fails);
    check(errors.length === 0, '콘솔 오류 0건' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''), fails);
    await page.close();
  }
  // 휴대폰 크기 확인
  const m = await browser.newPage({ viewport: { width: 400, height: 780 } });
  await m.goto('file://' + path.resolve(__dirname, '../index.html'));
  await m.waitForFunction(() => document.querySelectorAll('.cls').length === 3, null, { timeout: 20000 });
  await m.locator('.cls').nth(1).click(); await m.fill('#nick', '테스터').then(() => m.click('#start')); await m.waitForTimeout(800);
  await m.screenshot({ path: `${OUT}/g6_phone.png` });
  const ov = await m.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  check(ov <= 0, '휴대폰 화면 가로 넘침 없음', fails);
  await m.evaluate(() => { const w = __game.mobs.find(x => x.type === 'wolf'); __game.P.target = w; w.hp = w.maxhp - 5; });
  await m.waitForTimeout(400);
  const overlap = await m.evaluate(() => {
    const r = id => document.getElementById(id).getBoundingClientRect();
    const hit = (a, b) => !(a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top);
    const t = r('target');
    return { shown: t.height > 0, a: hit(t, r('status')), b: hit(t, r('mini')), c: hit(t, r('bar')) };
  });
  check(overlap.shown && !overlap.a && !overlap.b && !overlap.c, '휴대폰에서 대상 정보창이 다른 창과 겹치지 않음', fails);
  await m.screenshot({ path: `${OUT}/g7_phone_target.png` });
  await browser.close();
  console.log(fails.length ? `실패 ${fails.length}건` : '모두 통과');
  process.exit(fails.length ? 1 : 0);
})();
