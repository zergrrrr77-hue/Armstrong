// 쿼터뷰 판 기본 점검: 실행 → 새 캐릭터 → 이동 → 전투 → 자동 사냥 → 보스 방 → 오류 0건
// 실행: node forgotten-forge/tests/iso_smoke.js [스크린샷 폴더]
const { chromium } = require('playwright');
const path = require('path');
const OUT = process.argv[2] || '/tmp';
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 960, height: 600 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto('file://' + path.resolve(__dirname, '../index.html'));
  await page.waitForTimeout(800);
  await page.evaluate(() => localStorage.clear());
  await page.click('#btnNew');
  await page.waitForTimeout(400);
  await page.screenshot({ path: OUT + '/s0_create.png' });
  await page.click('#createGo');
  await page.waitForTimeout(1200);
  await page.screenshot({ path: OUT + '/s1_village.png' });
  // 오른쪽(풀숲 길)으로 걷기
  await page.keyboard.down('KeyD'); await page.waitForTimeout(2500); await page.keyboard.up('KeyD');
  await page.keyboard.down('KeyW'); await page.waitForTimeout(600); await page.keyboard.up('KeyW');
  await page.screenshot({ path: OUT + '/s2_walk.png' });
  const p1 = await page.evaluate(() => ({ x: __forge.P.x, y: __forge.P.y }));
  // 자동 사냥으로 슬라임 잡기
  await page.keyboard.press('KeyQ');
  await page.evaluate(() => { const e = __forge.enemies.find((e) => e.type === 'slime'); __forge.P.x = e.x - 1.5; __forge.P.y = e.y; });
  await page.waitForTimeout(5000);
  await page.screenshot({ path: OUT + '/s3_auto.png' });
  const kills = await page.evaluate(() => __forge.S.q.slimes);
  // 숲으로 이동해 고블린
  await page.evaluate(() => { const e = __forge.enemies.find((e) => e.type === 'goblin'); __forge.P.x = e.x - 1.6; __forge.P.y = e.y + 0.4; });
  await page.waitForTimeout(6000);
  await page.screenshot({ path: OUT + '/s4_forest.png' });
  const gob = await page.evaluate(() => __forge.S.q.goblin);
  // 무기 계열 바꿔 가며 공격
  for (const id of ['knightspear', 'earth', 'starbow']) {
    await page.evaluate((id) => { const i = __forge.rollInst(id, 2); i.uid = __forge.S.nextUid++; __forge.S.inv.push(i); __forge.equip(i.uid); const e = __forge.enemies.find((e) => !e.dead && e.type !== 'boss'); __forge.P.x = e.x - 1.2; __forge.P.y = e.y - 0.2; }, id);
    await page.waitForTimeout(1600);
    await page.screenshot({ path: OUT + `/s5_${id}.png` });
  }
  // 동굴 + 보스
  await page.evaluate(() => { __forge.S.level = 12; __forge.P.hp = 999; __forge.P.x = 52; __forge.P.y = 12; });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: OUT + '/s6_cave.png' });
  await page.evaluate(() => { __forge.P.x = 54.5; __forge.P.y = 8.2; });
  await page.waitForTimeout(2600);
  await page.screenshot({ path: OUT + '/s7_boss.png' });
  await page.waitForTimeout(25000);
  let boss = await page.evaluate(() => { const b = __forge.enemies.find((e) => e.type === 'boss'); return { hp: b.hp, dead: b.dead, key: __forge.S.hasKey, P: __forge.P.hp }; });
  await page.screenshot({ path: OUT + '/s8_after.png' });
  // 열쇠 줍기
  await page.evaluate(() => { const k = __forge.drops.find((d) => d.kind === 'key'); if (k) { __forge.P.x = k.x; __forge.P.y = k.y; } });
  await page.waitForTimeout(2500);
  boss.key = await page.evaluate(() => __forge.S.hasKey);
  // 가방 열기
  await page.keyboard.press('KeyI'); await page.waitForTimeout(400);
  await page.screenshot({ path: OUT + '/s9_inv.png' });
  console.log(JSON.stringify({ p1, kills, gob, boss, errors }, null, 1));
  await browser.close();
})();
