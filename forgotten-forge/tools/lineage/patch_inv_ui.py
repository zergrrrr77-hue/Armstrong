"""가방 개선 + 회색 돌 UI (2026-11-04 요청)
1) 가방 '일괄 판매': 칸을 눌러 여러 개 고른 뒤 한 번에 판매(일반·고급·전리품 빠른 선택)
2) 자동 판매: 일반 등급 장비는 주울 때 판매(특수 옵션 붙은 장비는 지킴), 판매 금액 기록
3) '착용·해제' 탭: 부위별 착용 장비 + 해제 버튼, 가방의 착용 가능한 장비 + 착용 버튼, 가장 좋은 장비 자동 착용
4) UI 전체를 회색빛 돌 질감으로, PC 하단 바는 단축칸(스킬 8 + 물약 2 + 주문서 2)으로 꽉 채움
실행: python3 forgotten-forge/tools/lineage/patch_inv_ui.py
"""
import os
import sys

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'game_template.html')
t = open(P, encoding='utf-8').read()
if 'id="bulkBtn"' in t:
    sys.exit('이미 적용됨')


def rep(old, new, cnt=1):
    global t
    n = t.count(old)
    if n != cnt:
        sys.exit(f'앵커 {n}개: {old[:80]!r}')
    t = t.replace(old, new)


# ───── 화면 틀 ─────
rep('<button type="button" data-tab="eq" aria-pressed="true">장비창</button>',
    '<button type="button" data-tab="eq" aria-pressed="true">장비창</button><button type="button" data-tab="wear" aria-pressed="false">착용·해제</button>')
rep('''        <span class="bagcount" id="bagCount"></span>
      </div>
      <div class="sgrid" id="eqgrid"></div>''',
    '''        <span class="bagcount" id="bagCount"></span>
        <button type="button" class="bulkbtn" id="bulkBtn">일괄 판매</button>
      </div>
      <div class="bulkbar hidden" id="bulkBar">
        <div class="bq"><button type="button" data-bq="common">일반 장비</button><button type="button" data-bq="uncommon">고급 장비</button><button type="button" data-bq="loot">전리품</button><button type="button" data-bq="none">선택 해제</button></div>
        <div class="bsum"><span id="bulkSum">팔 아이템을 누르세요</span><button type="button" id="bulkSell" disabled>판매</button><button type="button" id="bulkCancel">닫기</button></div>
      </div>
      <div class="sgrid" id="eqgrid"></div>''')
rep('''  <div class="tabpane hidden wpad" data-pane="stat">''',
    '''  <div class="tabpane hidden wpad" data-pane="wear">
    <div class="weartop"><button type="button" id="wearBest">가장 좋은 장비 자동 착용</button><button type="button" id="wearOff">모두 해제</button></div>
    <div class="sect">착용 중</div>
    <div class="wlist" id="wearList"></div>
    <div class="sect">가방에서 착용할 수 있는 장비</div>
    <div class="wlist" id="wearBag"></div>
  </div>
  <div class="tabpane hidden wpad" data-pane="stat">''')

# ───── 자동 판매: 특수 옵션 장비는 지키고, 판매 기록·에테르 표시 갱신 ─────
rep("    if (P.autoSell && dd.grade === 'common') { const pr = Math.round(sellPrice(d.equip)); P.gold += pr; log(`${dd.name} 자동 판매 +${pr} 에테르`); sfx('arrow_hit', { gain: 0.25 }); return; }",
    "    if (P.autoSell && dd.grade === 'common' && !d.equip.px) { const pr = Math.round(sellPrice(d.equip)); P.gold += pr; STATE.autoSold = (STATE.autoSold || 0) + 1; log(`[일반] ${dd.name} 자동 판매 +${pr} 에테르`); lootLog(`[일반] ${dd.name} → 자동 판매 +${pr} 에테르`, 'common'); texts.push({ who: P, x: P.x, y: P.y, z: 58, t: 0, s: `+${pr} 에테르`, c: '#ffd65a' }); sfx('arrow_hit', { gain: 0.25 }); renderInv(); return; }")

# ───── 가방 칸: 일괄 판매 모드에서는 눌러서 고르기 ─────
rep("    if (selUid === e.uid) b.classList.add('sel');\n    b.addEventListener('click', () => { selCons = null; selUid = e.uid; renderInv(); if (OPT.cmpAuto !== 'off') showCompare(e); });",
    "    if (selUid === e.uid && !bulkMode) b.classList.add('sel');\n    if (bulkMode && bulkSel.has(e.uid)) b.classList.add('chk');\n    b.addEventListener('click', () => { if (bulkMode) { bulkToggle(e.uid); return; } selCons = null; selUid = e.uid; renderInv(); if (OPT.cmpAuto !== 'off') showCompare(e); });")
rep("    if (selCons === id) b.classList.add('sel');\n    b.addEventListener('click', () => { selUid = null; selCons = selCons === id ? null : id; renderInv(); });",
    "    if (selCons === id && !bulkMode) b.classList.add('sel');\n    if (bulkMode && bulkSel.has('c:' + id)) b.classList.add('chk');\n    if (bulkMode && !consPrice(id)) b.classList.add('nosell');\n    b.addEventListener('click', () => { if (bulkMode) { if (consPrice(id)) bulkToggle('c:' + id); return; } selUid = null; selCons = selCons === id ? null : id; renderInv(); });")
rep("  for (let i = used; i < Math.max(24, Math.ceil(used / 8) * 8); i++) { const d2 = document.createElement('div'); d2.className = 'cell blank'; g.append(d2); }\n  renderDetail();",
    "  for (let i = used; i < Math.max(24, Math.ceil(used / 8) * 8); i++) { const d2 = document.createElement('div'); d2.className = 'cell blank'; g.append(d2); }\n  renderDetail(); renderBulk(); renderWear();")

# ───── 탭 전환 ─────
rep("  if (tab === 'log') renderLoot();", "  if (tab === 'log') renderLoot();\n  if (tab === 'wear') renderWear();\n  if (tab !== 'eq' && bulkMode) { bulkMode = false; bulkSel.clear(); }")

# ───── 기능 코드 ─────
rep("$('autoSell').addEventListener('change', e => { if (P) { P.autoSell = e.target.checked; save(); } });",
    r"""$('autoSell').addEventListener('change', e => { if (P) { P.autoSell = e.target.checked; save(); } });
// ───────── 일괄 판매: 장비는 uid, 묶음 아이템(전리품·루비·재료)은 'c:아이디' 로 고름 ─────────
let bulkMode = false, bulkConfirm = 0;
const bulkSel = new Set();
function consPrice(id) {   // 묶음 아이템 1개 판매가(0이면 팔 수 없음: 물약·주문서 등)
  if (id.startsWith('loot_') || id.startsWith('mat_')) return (XITEMS[id] && XITEMS[id].price) || 0;
  if (id === 'gem_ruby') return GEM_PRICE;
  return 0;
}
function bulkTotal() {
  let sum = 0, n = 0, rare = 0;
  for (const k of bulkSel) {
    if (typeof k === 'string' && k.startsWith('c:')) { const id = k.slice(2), c = P.inv[id] || 0; sum += consPrice(id) * c; n += c; }
    else { const e = P.bag.find(x => x.uid === k); if (!e) continue; sum += sellPrice(e); n++; if (GRADES.indexOf(equipDef(e.key).grade) >= 2 || e.px || e.enc >= 4) rare++; }
  }
  return { sum: Math.round(sum), n, rare };
}
function bulkToggle(k) { if (bulkSel.has(k)) bulkSel.delete(k); else bulkSel.add(k); bulkConfirm = 0; renderInv(); }
function bulkQuick(kind) {
  bulkConfirm = 0;
  if (kind === 'none') bulkSel.clear();
  else if (kind === 'loot') { for (const [id, n] of Object.entries(P.inv)) if (n > 0 && id.startsWith('loot_')) bulkSel.add('c:' + id); }
  else for (const e of P.bag) if (equipDef(e.key).grade === kind && !e.px && e.enc < 4) bulkSel.add(e.uid);
  renderInv();
}
function renderBulk() {
  if (!P) return;
  $('bulkBar').classList.toggle('hidden', !bulkMode);
  $('bulkBtn').setAttribute('aria-pressed', String(bulkMode));
  $('bulkBtn').textContent = bulkMode ? '일괄 판매 중' : '일괄 판매';
  $('eqgrid').classList.toggle('bulk', bulkMode);
  if (!bulkMode) return;
  const { sum, n, rare } = bulkTotal();
  $('bulkSum').innerHTML = n ? `선택 <b>${n}</b>개 · <b class="g">+${sum.toLocaleString()}</b> 에테르${rare ? ` · <span class="warn">희귀 이상·강화·특수 ${rare}개 포함</span>` : ''}` : '팔 아이템을 누르세요';
  $('bulkSell').disabled = !n;
  $('bulkSell').textContent = bulkConfirm ? '정말 판매?' : '판매';
  $('bulkSell').classList.toggle('confirm', !!bulkConfirm);
}
function sellBulk() {
  if (!bulkSel.size) return false;
  const { sum, n, rare } = bulkTotal();
  if (rare && !bulkConfirm) { bulkConfirm = 1; renderBulk(); return false; }   // 귀한 장비가 섞이면 한 번 더 확인
  for (const k of bulkSel) {
    if (typeof k === 'string' && k.startsWith('c:')) P.inv[k.slice(2)] = 0;
    else { const i = P.bag.findIndex(x => x.uid === k); if (i >= 0) P.bag.splice(i, 1); }
  }
  P.gold += sum; bulkSel.clear(); bulkConfirm = 0; selUid = null; selCons = null;
  log(`아이템 ${n}개를 한 번에 팔아 ${sum.toLocaleString()} 에테르를 받았습니다.`, 'sys'); sfx('enchant_ok', { gain: 0.3 });
  texts.push({ who: P, x: P.x, y: P.y, z: 64, t: 0, s: `+${sum.toLocaleString()} 에테르`, c: '#ffd65a' });
  renderInv(); save();
  return true;
}
$('bulkBtn').addEventListener('click', () => { bulkMode = !bulkMode; bulkSel.clear(); bulkConfirm = 0; selUid = null; selCons = null; renderInv(); });
$('bulkCancel').addEventListener('click', () => { bulkMode = false; bulkSel.clear(); renderInv(); });
$('bulkSell').addEventListener('click', sellBulk);
document.querySelectorAll('#bulkBar [data-bq]').forEach(b => b.addEventListener('click', () => bulkQuick(b.dataset.bq)));
// ───────── 착용·해제 탭 ─────────
const canWear = e => { const d = equipDef(e.key), s = slotFor(e); return slotAllowed(s) && P.lv >= (d.lv || 1) && (!d.base || d.base === P.c.base); };
function wearRow(e, slotLabel, btnText, onClick, extra, disabled) {
  const row = document.createElement('div'); row.className = 'wrow' + (e ? '' : ' empty');
  const cv = document.createElement('canvas'); cv.width = 36; cv.height = 36; row.append(cv);
  const nm = document.createElement('div');
  if (e) { const d = equipDef(e.key); gradeFrame(cv, d.grade, d.icon, e.enc); nm.innerHTML = `<small>${slotLabel}</small><span class="g-${d.grade}">${e.enc ? '+' + e.enc + ' ' : ''}${d.name}</span><em>${statText(e)}${extra || ''}</em>`; }
  else nm.innerHTML = `<small>${slotLabel}</small><span class="none">비어 있음</span>`;
  row.append(nm);
  const b = document.createElement('button'); b.type = 'button'; b.textContent = btnText; b.disabled = !!disabled; b.onclick = onClick; row.append(b);
  return row;
}
function renderWear() {
  if (!P || !$('wearList')) return;
  const L = $('wearList'), B = $('wearBag'); L.innerHTML = ''; B.innerHTML = '';
  for (const sd of SLOTS) {
    if (!slotAllowed(sd.id)) continue;
    const e = P.eq[sd.id];
    L.append(wearRow(e, sd.label, '해제', () => unequip(sd.id), '', !e || sd.id === 'weapon'));
  }
  const order = Object.fromEntries(SLOTS.map((s, i) => [s.id, i]));
  const list = P.bag.filter(e => slotAllowed(slotFor(e))).sort((a, b) => (order[slotFor(a)] - order[slotFor(b)]) || statVal(b) - statVal(a));
  if (!list.length) B.innerHTML = '<div class="note">가방에 착용할 수 있는 장비가 없습니다.</div>';
  for (const e of list) {
    const d = equipDef(e.key), s = slotFor(e), diff = statVal(e) - statVal(P.eq[s]);
    const lvNo = P.lv < (d.lv || 1), clsNo = d.base && d.base !== P.c.base;
    const tag = clsNo ? ` · <b class="no">${BASE_LABEL[d.base]} 전용</b>` : lvNo ? ` · <b class="no">Lv ${d.lv}부터</b>` : diff > 0.01 ? ` · <b class="up">▲ 더 좋음</b>` : diff < -0.01 ? ' · <b class="dn">▼</b>' : '';
    B.append(wearRow(e, SLOTS.find(x => x.id === s).label, '착용', () => equip(e.uid), tag, lvNo || clsNo));
  }
  $('wearOff').disabled = !Object.entries(P.eq).some(([k, v]) => v && k !== 'weapon');
}
function wearBest() {
  let changed = 0;
  for (let guard = 0; guard < 30; guard++) {
    const c = P.bag.filter(canWear).map(e => ({ e, gain: statVal(e) - statVal(P.eq[slotFor(e)]) })).filter(x => x.gain > 0.01).sort((a, b) => b.gain - a.gain)[0];
    if (!c) break;
    equip(c.e.uid); changed++;
  }
  log(changed ? `더 좋은 장비 ${changed}개를 착용했습니다.` : '지금 착용한 장비가 가장 좋습니다.', 'sys');
  renderInv(); return changed;
}
function wearOff() {
  let n = 0;
  for (const sd of SLOTS) if (sd.id !== 'weapon' && P.eq[sd.id]) { if (unequip(sd.id)) n++; else break; }
  if (n) log(`장비 ${n}개를 해제했습니다.`, 'sys');
  renderInv(); return n;
}
$('wearBest').addEventListener('click', wearBest);
$('wearOff').addEventListener('click', wearOff);""")

# ───── PC 하단 바: 스킬 8칸(빈 칸 포함) + 물약 + 주문서 2칸으로 꽉 채움 ─────
rep("""  bar.insertAdjacentHTML('beforeend', '<div class="sep"></div>');
  for (const [id, key] of [['pot_red', 'Q'], ['pot_blue', 'E']]) {""",
    """  // PC 전용 빈 칸: 월드보스 스킬 자리(5~8)를 미리 보여 줌 — div 라서 휴대폰 부채꼴(button 순서)에는 영향 없음
  for (let i = skillIds().length; i < 8; i++) bar.insertAdjacentHTML('beforeend', `<div class="slot extra empty" title="월드보스 스킬 자리 — 월드보스를 쓰러뜨려 얻은 스킬이 들어갑니다"><span class="k">${i + 1}</span></div>`);
  bar.insertAdjacentHTML('beforeend', '<div class="sep"></div>');
  // PC 전용: 귀환·이동 주문서 단축칸(R·T)
  for (const [id, key] of [['scroll_return', 'R'], ['scroll_teleport', 'T']]) {
    const d = document.createElement('div'); d.className = 'slot extra scroll'; d.setAttribute('role', 'button'); d.title = `${itemName(id)} (${key})`; d.dataset.item = id;
    const cv = document.createElement('canvas'); cv.width = 32; cv.height = 32; d.append(cv); iconTo(cv, id);
    d.insertAdjacentHTML('beforeend', `<span class="k">${key}</span><span class="n" data-inv="${id}"></span>`);
    d.addEventListener('click', () => { if (useItem(id)) renderInv(); });
    bar.append(d);
  }
  for (const [id, key] of [['pot_red', 'Q'], ['pot_blue', 'E']]) {""")
rep("  if (e.code === 'Digit6') useSkill(5);",
    "  if (e.code === 'Digit6') useSkill(5);\n  if (e.code === 'KeyR' && running && P && !P.dead) { if (useItem('scroll_return')) renderInv(); }\n  if (e.code === 'KeyT' && running && P && !P.dead) { if (useItem('scroll_teleport')) renderInv(); }")

# 단축칸의 주문서 개수 표시: 물약 개수 갱신하는 곳에 함께
a = t.index("data-pot")
# (개수 갱신은 아래 setInterval 로 따로)
rep("const GEM_PRICE = 150;", """const GEM_PRICE = 150;
setInterval(() => { if (!P) return; document.querySelectorAll('#bar [data-inv]').forEach(s => { const n = P.inv[s.dataset.inv] || 0; s.textContent = n; s.parentElement.classList.toggle('none', !n); }); }, 400);""")

# ───── 회색 돌 테마 ─────
rep(":root { --stone-a: #2c2620; --stone-b: #17140f; --bronze: #8a6a3a; --bronze-hi: #c9a25a; --gold-hi: #f0d48a; --star: #8cc8ff; }",
    """:root { --stone-a: #4a4946; --stone-b: #262523; --bronze: #6e6a62; --bronze-hi: #b4aea2; --gold-hi: #f0d48a; --star: #8cc8ff;
  /* 돌 질감: 잔 알갱이(흰 점) + 큰 얼룩(어두운 반점) — 그림 파일 없이 SVG 노이즈로 */
  --grain: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='180' height='180'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .11 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
  --mottle: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='420' height='420'><filter id='m'><feTurbulence type='fractalNoise' baseFrequency='.018' numOctaves='4' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -1.6 .95'/></filter><rect width='100%' height='100%' filter='url(%23m)' opacity='.55'/></svg>");
  --stone: var(--grain), var(--mottle), linear-gradient(var(--stone-a), var(--stone-b));
  --line: #4c4a46; --line-hi: #8e897f; --panel: rgba(40,39,37,.95); }""")
rep("  background: radial-gradient(circle at 20% 30%, rgba(255,255,255,.03) 0 2px, transparent 3px) 0 0 / 14px 14px, linear-gradient(var(--stone-a), var(--stone-b));\n  border: 2px solid var(--bronze); border-radius: 4px; box-shadow: inset 0 0 0 1px #0c0a07, inset 0 1px 0 2px rgba(201,162,90,.22),",
    "  background: var(--stone);\n  border: 2px solid var(--bronze); border-radius: 4px; box-shadow: inset 0 0 0 1px #0c0b0a, inset 0 1px 0 2px rgba(220,215,200,.14),")
rep("""    background: radial-gradient(circle at 20% 30%, rgba(255,255,255,.03) 0 2px, transparent 3px) 0 0 / 14px 14px,
      radial-gradient(circle at 70% 60%, rgba(0,0,0,.25) 0 2px, transparent 3px) 0 0 / 19px 19px, linear-gradient(#2c2620, #15120e);
    border-top: 2px solid var(--bronze); box-shadow: inset 0 2px 0 rgba(240,212,138,.22), 0 -8px 24px rgba(0,0,0,.6); }""",
    """    background: var(--grain), var(--mottle), linear-gradient(#4c4b48, #2a2927 60%, #1e1d1b);
    border-top: 2px solid var(--bronze-hi); box-shadow: inset 0 2px 0 rgba(255,255,255,.12), inset 0 3px 0 #0c0b0a, 0 -8px 24px rgba(0,0,0,.6); }""")
# PC 하단: 기록 칸 줄이고 가운데(상태·단축칸)를 넓게, 단축칸은 폭에 맞춰 늘어남
rep("  #dock .logbox { position: absolute; left: 12px; bottom: 10px; width: 372px; height: 146px;",
    "  #dock .logbox { position: absolute; left: 12px; bottom: 10px; width: 300px; height: 146px;")
rep("  #log { left: 22px; bottom: 18px; width: 352px; max-height: 128px; overflow: hidden; z-index: 10; }",
    "  #log { left: 22px; bottom: 18px; width: 280px; max-height: 128px; overflow: hidden; z-index: 10; }")
rep("  #status { left: 400px; top: auto; bottom: 104px; width: calc(100vw - 400px - 330px); z-index: 10; }",
    "  #status { left: 326px; top: auto; bottom: 98px; width: calc(100vw - 326px - 330px); z-index: 10; }")
rep("""  #bar { left: 400px; transform: none; bottom: 12px; padding: 0; gap: 4px; background: none; border: 0; box-shadow: none; z-index: 10; }
  #bar .slot { width: 44px; height: 44px; }""",
    """  #bar { left: 326px; width: calc(100vw - 326px - 330px); transform: none; bottom: 12px; padding: 0; gap: 4px; background: none; border: 0; box-shadow: none; z-index: 10;
    display: flex; align-items: flex-end; justify-content: space-between; }
  #bar .slot { flex: 1 1 0; width: auto; height: auto; aspect-ratio: 1 / 1; min-width: 34px; max-width: 70px; }
  #bar .slot canvas { width: 100%; height: 100%; }
  #bar .slot.extra { display: block; }""")

# 나머지 패널·버튼을 회색 돌로(뒤에 두어 앞의 갈색 규칙을 덮음)
rep("/* 드로간 대장간(제작) — 상점 창과 같은 틀 */", r"""/* ═════════ 회색 돌 테마(2026-11-04): 창·탭·칸을 회색 돌 질감으로 ═════════ */
#inv, #shop, #craft, #gacha, #opt, #wpMenu, #cmp, #wmap .wm-frame { background: var(--stone) !important; border: 2px solid var(--bronze-hi) !important;
  box-shadow: 0 0 0 1px #0a0908, inset 0 0 0 1px #0c0b0a, inset 0 1px 0 2px rgba(255,255,255,.08), 0 14px 40px rgba(0,0,0,.7) !important; }
.whead, .shead, #gacha .ghead { background: var(--grain), linear-gradient(#55534f, #343330) !important; border-bottom: 1px solid #0c0b0a !important; box-shadow: inset 0 -1px 0 rgba(255,255,255,.08); }
.tabs button, #craft .tabs button, .chip, .seg button, .vrow button { background: linear-gradient(#3e3d3a, #2a2927) !important; border: 1px solid #141312 !important; box-shadow: inset 0 1px 0 rgba(255,255,255,.08); color: #cfc9bd !important; }
.tabs button[aria-pressed="true"], .chip[aria-pressed="true"], #craft .tabs button[aria-pressed="true"], .seg button[aria-pressed="true"] { background: linear-gradient(#6a6760, #45433f) !important; color: #fff3d0 !important; border-color: #b4aea2 !important; }
.slot, .cell, .dslot, .srow, .crow, .wrow { background: radial-gradient(#3a3936, #1a1918) !important; border-color: #0e0d0c !important; box-shadow: inset 0 0 0 1px #6e6a62, inset 0 0 8px rgba(0,0,0,.65); }
.cell.blank { background: radial-gradient(#2e2d2b, #1a1918) !important; box-shadow: inset 0 0 0 1px #3c3a37; }
.mbtn button { background: var(--grain), linear-gradient(#56544f, #2f2e2b) !important; box-shadow: inset 0 0 0 1px #8e897f, inset 0 1px 0 2px rgba(255,255,255,.08), 0 2px 4px rgba(0,0,0,.6) !important; color: #ece6d8 !important; }
.mbtn button svg { stroke: #f0d48a; }
#quest { background: var(--grain), linear-gradient(rgba(58,57,54,.9), rgba(34,33,31,.82)) !important; border: 1px solid #6e6a62 !important; border-left: 3px solid #b4aea2 !important; }
#dock .logbox, #mini .gold { background: rgba(14,13,12,.55) !important; box-shadow: inset 0 0 0 1px #5c5954, inset 0 2px 6px rgba(0,0,0,.6) !important; }
#dock .logbox::before { background: #3c3b38 !important; border-color: #8e897f !important; }
#dock .em { border-color: #b4aea2 !important; }
.srow button, .crow .cbtn button, .wrow button, .weartop button, #shopSell button, .wclose { background: linear-gradient(#5e5b55, #3a3936) !important; border: 1px solid #b4aea2 !important; color: #fff3d8 !important; box-shadow: inset 0 1px 0 rgba(255,255,255,.18), 0 1px 2px rgba(0,0,0,.6); }
/* 가방: 일괄 판매 · 착용 탭 */
.bulkbtn { min-height: 30px; padding: 0 12px; border-radius: 3px; cursor: pointer; font-weight: 800; font-size: 12px; color: #ffe7a8; background: linear-gradient(#6a5a2a, #3e3416); border: 1px solid #d8bc6a; }
.bulkbtn[aria-pressed="true"] { background: linear-gradient(#a8822a, #6a4e14); color: #fff6d8; box-shadow: 0 0 8px rgba(240,200,110,.5); }
.bulkbar { display: grid; gap: 6px; padding: 7px; border-radius: 4px; background: rgba(20,18,14,.7); border: 1px solid #d8bc6a; }
.bulkbar .bq { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; }
.bulkbar .bq button { min-height: 32px; font-size: 12px; font-weight: 700; border-radius: 3px; cursor: pointer; color: #ece6d8; background: linear-gradient(#4c4a46, #2c2b29); border: 1px solid #8e897f; }
.bulkbar .bsum { display: grid; grid-template-columns: 1fr auto auto; gap: 6px; align-items: center; font-size: 12px; color: #e8e0cc; }
.bulkbar .bsum b.g { color: #ffd65a; } .bulkbar .bsum .warn { color: #ff9a7a; }
.bulkbar .bsum button { min-height: 34px; padding: 0 14px; border-radius: 3px; cursor: pointer; font-weight: 800; color: #fff; background: linear-gradient(#7a6020, #4a3810); border: 1px solid #f0d48a; }
.bulkbar .bsum button:disabled { opacity: .4; cursor: default; }
.bulkbar .bsum button.confirm { background: linear-gradient(#a03a24, #5a1a0c); border-color: #ff9a7a; }
.bulkbar .bsum #bulkCancel { background: linear-gradient(#4c4a46, #2c2b29); border-color: #8e897f; font-weight: 600; }
.sgrid.bulk .cell { cursor: copy; }
.cell.chk { box-shadow: inset 0 0 0 2px #ffd65a, 0 0 8px rgba(255,214,90,.6) !important; }
.cell.chk::after { content: '✓'; position: absolute; right: 2px; top: 0; font: 900 13px var(--body); color: #ffd65a; text-shadow: 0 1px 2px #000; }
.cell.nosell { opacity: .35; }
.weartop { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.weartop button { min-height: 40px; font-weight: 800; border-radius: 3px; cursor: pointer; }
.weartop button:disabled { opacity: .4; }
.wlist { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 6px; }
.wrow { display: grid; grid-template-columns: 38px 1fr auto; gap: 8px; align-items: center; padding: 6px 8px; border: 1px solid #0e0d0c; border-radius: 4px; }
.wrow canvas { width: 38px; height: 38px; image-rendering: pixelated; }
.wrow div { display: grid; gap: 1px; min-width: 0; } .wrow small { font-size: 10px; color: #b4aea2; }
.wrow span { font-weight: 800; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; } .wrow span.none { color: #7e7a72; font-weight: 500; }
.wrow em { font-style: normal; font-size: 11px; color: #cfc9bd; } .wrow b.up { color: #8af07a; } .wrow b.dn { color: #ff9a7a; } .wrow b.no { color: #ffb07a; }
.wrow button { min-width: 58px; min-height: 36px; border-radius: 3px; cursor: pointer; font-weight: 800; }
.wrow button:disabled { opacity: .35; cursor: default; }
.wrow.empty { opacity: .7; }
/* PC 하단 단축칸: 빈 스킬 자리·주문서(휴대폰에서는 숨김) */
.slot.extra { display: none; }
.slot.extra.empty { background: radial-gradient(#2a2927, #141312) !important; box-shadow: inset 0 0 0 1px #4a4844 !important; cursor: default; }
.slot.extra.scroll { cursor: pointer; } .slot.extra.scroll.none canvas { filter: grayscale(1) brightness(.45); }
@media (pointer: coarse) { #bar .slot.extra { display: none !important; } }
/* 드로간 대장간(제작) — 상점 창과 같은 틀 */""")
open(P, 'w', encoding='utf-8').write(t)
print('적용 완료')
