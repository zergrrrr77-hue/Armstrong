// 에르덴 2단계 점검: 이름 교체 · 지역/근원 데이터 · 저장 v2 · 잊혀진 대장간 저장(v1) 자동 변환
// 실행: node forgotten-forge/tests/erden_stage2_check.js [스크린샷 폴더]
const { chromium } = require('playwright');
const path = require('path');
const OUT = process.argv[2] || '/tmp';
const URL = 'file://' + path.resolve(__dirname, '../index.html');

function check(cond, msg, fails) { if (!cond) fails.push(msg); console.log((cond ? '  ✓ ' : '  ✗ ') + msg); }
// 외부 글꼴(구글 폰트) 연결 실패는 오프라인 환경 탓이므로 오류에서 뺀다
const realError = (t) => !/ERR_TUNNEL_CONNECTION_FAILED|ERR_INTERNET_DISCONNECTED|fonts\.g/.test(t);

(async () => {
  const browser = await chromium.launch();
  const fails = [];
  const page = await browser.newPage({ viewport: { width: 1280, height: 760 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error' && realError(m.text())) errors.push(m.text()); });
  const title = async () => { await page.waitForFunction(() => document.querySelectorAll('.cls').length === 3, null, { timeout: 20000 }); };

  await page.goto(URL); await title();
  await page.evaluate(() => localStorage.clear()); await page.reload(); await title();

  console.log('[이름]');
  const t = await page.evaluate(() => ({ doc: document.title, h1: document.querySelector('#title h1').getAttribute('aria-label'), logo: document.querySelector('#title .logo').textContent }));
  check(t.doc === '에르덴 : 별의 심장' && t.h1 === '에르덴 : 별의 심장' && t.logo === '에르덴', `게임 제목: ${t.doc} / 로고 ${t.logo}`, fails);
  await page.screenshot({ path: `${OUT}/e2_title.png` });
  await page.locator('.cls').nth(0).click(); await page.fill('#nick', '테스터').then(() => page.click('#start')); await page.waitForTimeout(700);
  const ui = await page.evaluate(() => ({ gold: document.getElementById('gold').textContent, zone: document.getElementById('zone').textContent,
    mobNames: [...new Set(__game.mobs.map(m => m.d.name))], body: document.body.innerText }));
  check(/에테르/.test(ui.gold) && !/골드/.test(ui.gold), `화폐: ${ui.gold}`, fails);
  check(ui.zone.includes('아르델'), `지역 이름: ${ui.zone}`, fails);
  const want = ['검은 늑대', '숲 거미', '녹색 슬라임', '고블린 전사', '고블린', '해골 병사'];
  check(want.every(n => ui.mobNames.includes(n)), `평원 몬스터 이름: ${ui.mobNames.join(', ')}`, fails);
  const old = ['다이어울프', '늪 점액', '거대 거미', '오크', '헤스카르', '골드', '몰락한 왕', '웨이포인트', '유니크', '벨카르'];
  const html = await page.content();
  const left = old.filter(w => html.includes(w));
  check(left.length === 0, `옛 이름이 화면 코드에 남지 않음${left.length ? ': ' + left.join(', ') : ''}`, fails);

  console.log('[세계관 데이터]');
  const w = await page.evaluate(() => {
    const g = __game;
    return { regions: Object.keys(g.REGIONS).length, field: g.regionOf('field'), dungeon: g.regionOf('dungeon'), ardel: g.regionOpen('ardel'), elasia: g.regionOpen('elasia'),
      els: Object.keys(g.ELEMENTS).length, mobEl: g.mobs.every(m => !!m.d.el) };
  });
  check(w.regions === 6 && w.field === 'ardel' && w.dungeon === 'ardel', '여섯 지역 등록, 지금 맵 2개는 아르델', fails);
  check(w.ardel && !w.elasia, '아르델은 열림, 엘라시아 숲은 잠김(ch1_done 전)', fails);
  check(w.els === 7 && w.mobEl, '일곱 근원 + 모든 몬스터에 근원 속성', fails);
  const opened = await page.evaluate(() => { __game.STATE.flags.ch1_done = true; const r = __game.regionOpen('elasia'); delete __game.STATE.flags.ch1_done; return r; });
  check(opened, '제1장 기록(ch1_done)이 생기면 엘라시아 숲 열림', fails);
  // 대상 정보에 근원 표시
  await page.evaluate(() => { const m = __game.mobs.find(x => x.d.name === '검은 늑대'); __game.P.target = m; });
  await page.waitForTimeout(300);
  const tinfo = await page.evaluate(() => { const b = document.querySelector('#tgt b, #target b'); return b ? b.textContent : ''; });
  check(tinfo === '' || tinfo.includes('달'), `대상 정보에 근원 표시: ${tinfo || '(대상 창 숨김)'}`, fails);

  console.log('[저장 v2]');
  const sv = await page.evaluate(() => { __game.P.lv = 7; __game.P.gold = 777; __game.save(); return JSON.parse(localStorage.getItem('erden_save_v2')); });
  check(sv && sv.v === 2 && sv.lv === 7 && sv.gold === 777, '새 저장 칸 erden_save_v2 (v: 2)', fails);
  check(sv && ['equests', 'rel', 'flags', 'choices', 'regions', 'clock'].every(k => k in sv.state) && sv.state.clock === 390, '늘어난 저장 항목 6개 + 시작 시각 06:30', fails);
  check(await page.evaluate(() => localStorage.getItem('ff_lineage_save_v1') === null), '새 게임은 예전 칸에 쓰지 않음', fails);

  console.log('[v1 → v2 변환: 순번별]');
  const table = await page.evaluate(() => {
    const base = { v: 1, cls: 'knight', lv: 3, xp: 0, gold: 50, inv: {}, eq: null, bag: [], state: { bossDead: false, kills: 0, quest: 0, qn: 2, wbKill: {}, wp: { wp_town: true } } };
    const out = [];
    for (let q = 0; q <= 6; q++) {
      const d = JSON.parse(JSON.stringify(base)); d.state.quest = q; if (q === 6) d.state.bossDead = true;
      const m = __game.migrateV1(d);
      out.push({ q, done: Object.keys(m.state.equests).sort().join(','), ch1: !!m.state.flags.ch1_done, keepQ: m.state.quest === q && m.state.qn === 2, v: m.v, origV: d.v });
    }
    return { out, bad: __game.migrateV1({ v: 1, cls: 'nobody' }), notV1: __game.migrateV1({ v: 2, cls: 'knight' }) };
  });
  const expect = ['', 'q01,q02,q05', 'q01,q02,q04,q05', 'q01,q02,q04,q05,q08', 'q01,q02,q03,q04,q05,q06,q08',
    'q01,q02,q03,q04,q05,q06,q07,q08,q09', 'q01,q02,q03,q04,q05,q06,q07,q08,q09,q10'];
  for (const r of table.out) check(r.done === expect[r.q] && r.ch1 === (r.q === 6) && r.keepQ && r.v === 2 && r.origV === 1,
    `예전 순번 ${r.q} → 완료 [${r.done || '없음'}]${r.ch1 ? ' + 제1장 끝' : ''}`, fails);
  check(table.bad === null && table.notV1 === null, '직업이 잘못되었거나 v1이 아니면 변환하지 않음', fails);

  console.log('[v1 → v2 변환: 실제 이어하기]');
  await page.goto(URL); await title();   // 게임을 떠나 시작 화면(자동 저장 꺼짐)에서 저장 칸을 고친다
  await page.evaluate(() => {
    const d = JSON.parse(localStorage.getItem('erden_save_v2'));
    d.v = 1; d.lv = 9; d.gold = 1234; for (const k of ['equests', 'rel', 'flags', 'choices', 'regions', 'clock']) delete d.state[k];
    d.state.quest = 6; d.state.bossDead = true;
    localStorage.removeItem('erden_save_v2'); localStorage.setItem('ff_lineage_save_v1', JSON.stringify(d));
  });
  await page.reload(); await title();
  const cont = await page.evaluate(() => { const c = document.getElementById('continue'); return { show: !c.classList.contains('hidden'), text: c.textContent, note: c.title }; });
  check(cont.show && cont.text.includes('Lv 9'), `예전 저장으로 이어하기 버튼: ${cont.text}`, fails);
  await page.click('#continue'); await page.waitForTimeout(800);
  const after = await page.evaluate(() => ({ lv: __game.P.lv, gold: __game.P.gold, ch1: !!__game.STATE.flags.ch1_done, q10: (__game.STATE.equests.q10 || {}).s,
    log: document.getElementById('log').innerText, oldKept: !!localStorage.getItem('ff_lineage_save_v1') }));
  check(after.lv === 9 && after.gold === 1234, '레벨·에테르 그대로 옮겨짐', fails);
  check(after.ch1 && after.q10 === 'done', '보스를 잡은 예전 저장 → 제1장 끝 + 퀘스트 10 완료', fails);
  check(after.log.includes('에르덴으로 옮겼습니다'), '변환 안내 문구', fails);
  check(after.oldKept, '예전 저장 칸은 지우지 않고 보관', fails);
  await page.evaluate(() => __game.save());
  check(await page.evaluate(() => (JSON.parse(localStorage.getItem('erden_save_v2')) || {}).v === 2), '다음 저장부터 v2 칸에 기록', fails);
  await page.screenshot({ path: `${OUT}/e2_migrated.png` });

  console.log('[깨진 예전 저장]');
  await page.goto(URL); await title();
  await page.evaluate(() => { localStorage.removeItem('erden_save_v2'); localStorage.setItem('ff_lineage_save_v1', JSON.stringify({ v: 1, cls: '???' })); });
  await page.reload(); await title();
  const broken = await page.evaluate(() => ({ cont: !document.getElementById('continue').classList.contains('hidden'), warn: document.getElementById('newWarn').textContent,
    kept: localStorage.getItem('ff_lineage_save_v1') !== null }));
  check(!broken.cont && broken.warn.includes('옮기지 못했습니다') && broken.kept, `변환 실패 시 새 게임 + 안내, 예전 저장 보관: ${broken.warn}`, fails);

  check(errors.length === 0, `콘솔 오류 0건${errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''}`, fails);
  await browser.close();
  console.log(fails.length ? `실패 ${fails.length}건` : '모두 통과');
  process.exit(fails.length ? 1 : 0);
})();
