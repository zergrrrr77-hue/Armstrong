// 잊혀진 대장간(리니지풍) 기본 점검:
// 클래스 4종 시작 → 이동 → 기본 공격 → 스킬 4종 → 물약 → 강화 → 던전 입장 → 보스 스킬 → 보스 처치 → 오류 0건
// 실행: node forgotten-forge/tests/iso_smoke.js [스크린샷 폴더]
const { chromium } = require('playwright');
const path = require('path');
const OUT = process.argv[2] || '/tmp';

function check(cond, msg, fails) { if (!cond) fails.push(msg); console.log((cond ? '  ✓ ' : '  ✗ ') + msg); }

(async () => {
  const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
  const fails = [];
  for (const cls of ['knight', 'lord', 'elf', 'mage']) {
    console.log(`[${cls}]`);
    const page = await browser.newPage({ viewport: { width: 1280, height: 760 } });
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
    await page.goto('file://' + path.resolve(__dirname, '../index.html'));
    await page.waitForFunction(() => document.querySelectorAll('.cls').length === 4, null, { timeout: 20000 });
    const idx = ['knight', 'lord', 'elf', 'mage'].indexOf(cls);
    await page.locator('.cls').nth(idx).click();
    if (cls === 'knight') await page.screenshot({ path: `${OUT}/g0_title.png` });
    await page.click('#start');
    await page.waitForTimeout(600);

    // 이동(키보드)
    const p0 = await page.evaluate(() => ({ x: __game.P.x, y: __game.P.y }));
    await page.keyboard.down('KeyD'); await page.waitForTimeout(700); await page.keyboard.up('KeyD');
    const p1 = await page.evaluate(() => ({ x: __game.P.x, y: __game.P.y }));
    check(Math.hypot(p1.x - p0.x, p1.y - p0.y) > 0.5, '키보드로 이동', fails);

    // 늑대 옆으로 옮겨 기본 공격
    await page.evaluate(() => { const m = __game.mobs.find(m => m.type === 'wolf'); __game.P.x = m.x - 1; __game.P.y = m.y; __game.P.target = m; m.state = 'idle'; });
    await page.waitForTimeout(3500);
    const hit = await page.evaluate(() => __game.mobs.some(m => m.type === 'wolf' && (m.hp < m.maxhp || m.dead)));
    check(hit, '기본 공격으로 피해', fails);
    if (cls === 'knight') await page.screenshot({ path: `${OUT}/g1_field.png` });

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
    check(enc, '무기 강화(+6 이하 안전)', fails);

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
      check(bossFx, '보스 스킬 사용', fails);
      await page.waitForTimeout(1500);
      // 보스 처치
      await page.evaluate(() => { const b = __game.mobs.find(m => m.type === 'boss'); b.hp = 30; __game.P.target = b; });
      await page.waitForTimeout(4500);
      const dead = await page.evaluate(() => __game.STATE.bossDead);
      check(dead, '보스 처치', fails);
      await page.screenshot({ path: `${OUT}/g5_victory.png` });
    }
    check(errors.length === 0, '콘솔 오류 0건' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''), fails);
    await page.close();
  }
  // 휴대폰 크기 확인
  const m = await browser.newPage({ viewport: { width: 400, height: 780 } });
  await m.goto('file://' + path.resolve(__dirname, '../index.html'));
  await m.waitForFunction(() => document.querySelectorAll('.cls').length === 4, null, { timeout: 20000 });
  await m.locator('.cls').nth(2).click(); await m.click('#start'); await m.waitForTimeout(800);
  await m.screenshot({ path: `${OUT}/g6_phone.png` });
  const ov = await m.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  check(ov <= 0, '휴대폰 화면 가로 넘침 없음', fails);
  await browser.close();
  console.log(fails.length ? `실패 ${fails.length}건` : '모두 통과');
  process.exit(fails.length ? 1 : 0);
})();
