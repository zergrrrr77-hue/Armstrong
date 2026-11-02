// 클래스별 자동사냥 시뮬레이션: 게임 시간 기준 성장·사망·물약·골드
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const out = {};
  for (const cls of ['knight', 'elf', 'mage']) {
    const p = await b.newPage();
    p.on('pageerror', e => console.log('ERR', e.message));
    await p.goto('file://' + require('path').resolve(__dirname, '../index.html'));
    await p.waitForFunction(() => document.querySelectorAll('.cls').length === 3);
    await p.evaluate(() => localStorage.clear());
    await p.evaluate((c) => {
      window.__deaths = 0; window.__pots = 0;
      __game.start(c);
    }, cls);
    await p.waitForTimeout(300);
    const rows = await p.evaluate(() => {
      const G = __game, P = G.P, res = [];
      G.setAuto(true);
      // 포인트는 주 능력치에 자동 투자
      const main = { knight: 'str', elf: 'dex', mage: 'int' }[P.cls];
      const origDie = P;
      let deaths = 0, lastDead = false, pots0 = P.inv.pot_red + P.inv.pot_blue, bought = 0;
      for (let minute = 1; minute <= 35; minute++) {
        for (let k = 0; k < 6; k++) {
          G.simulate(10);
          if (P.dead && !lastDead) deaths++;
          lastDead = P.dead;
          while (P.sp > 0) G.addStat(main);
          // 물약이 떨어지면 상점 가격으로 보충(골드 소비로 계산)
          for (const [id, price] of [['pot_red', 25], ['pot_blue', 35]]) if ((P.inv[id] || 0) < 3 && P.gold >= price * 10) { P.gold -= price * 10; P.inv[id] += 10; bought += 10; }
          // 착용 가능한 더 좋은 장비 자동 착용
          for (const e of [...P.bag]) { const d = G.equipDef(e.key), sl = G.slotFor(e); if (P.lv >= d.lv && G.slotAllowed(sl) && G.statVal(e) > G.statVal(P.eq[sl]) + 0.01) G.equip(e.uid); }
          // 던전 입장 목표에 도달하면 던전에서 사냥
          if (P.lv >= 8 && G.map.id === 'field') G.enterMap('dungeon');
        }
        if (minute % 5 === 0) res.push({ min: minute, lv: P.lv, xp: P.xp, map: G.map.id, deaths, kills: G.STATE.kills, gold: P.gold, potsUsed: pots0 + bought - (P.inv.pot_red + P.inv.pot_blue), bag: P.bag.length, w: G.equipDef(P.weapon.key).name, a: G.equipDef(P.armor.key).name, boss: G.STATE.bossDead });
      }
      return res;
    });
    out[cls] = rows;
    await p.close();
  }
  for (const [c, rows] of Object.entries(out)) {
    console.log('== ' + c);
    for (const r of rows) console.log(`${String(r.min).padStart(2)}분 Lv${r.lv} ${r.map.padEnd(7)} 처치${String(r.kills).padStart(4)} 사망${r.deaths} 골드${String(r.gold).padStart(6)} 물약${String(r.potsUsed).padStart(4)} ${r.w}/${r.a}${r.boss ? ' 보스처치' : ''}`);
  }
  await b.close();
})();
