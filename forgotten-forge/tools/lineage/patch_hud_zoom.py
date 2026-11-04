"""2026-11-04 저녁 수정
1) 게임 화면 확대/축소: 휴대폰 두 손가락 벌리기·오므리기, PC 마우스 휠, 키보드 + / -, 설정 > 화면의 단추. 값은 저장됨
2) 고블린 궁수(원거리 몬스터)가 계속 뒤로 도망가던 문제: 물러서기는 0.7초만, 그 뒤 4~6초는 제자리에서 쏨
3) 상태창: 리니지식 가로 HP/MP 막대(왼쪽 HP·MP 표식, 막대 안 가운데 숫자), 레벨·포인트는 이름 줄로 → 초상과 겹치지 않음
   PC 하단 가운데 별 문장이 HP 막대를 가리던 것 제거
4) 글꼴: 게임 전체를 Tahoma(아이폰은 같은 디자이너의 Verdana) + 한글 Noto Sans KR 로 통일
5) 스킬: 처음엔 없음 → Lv 2·5·9·14 에 하나씩 배움(배우기 전에는 휴대폰 화면에 칸도 안 나옴)
실행: python3 forgotten-forge/tools/lineage/patch_hud_zoom.py
"""
import os
import sys

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'game_template.html')
t = open(P, encoding='utf-8').read()
if 'ZOOM_USER' in t:
    sys.exit('이미 적용됨')


def rep(old, new, cnt=1):
    global t
    n = t.count(old)
    if n != cnt:
        sys.exit(f'앵커 {n}개: {old[:80]!r}')
    t = t.replace(old, new)


# ───── 1. 확대/축소 ─────
rep("let vfx = [], hitStop = 0, shake = 0, cam = { x: 0, y: 0 }, W = 0, H = 0, DPR = 1, ZOOM = 2,",
    "let ZOOM_USER = 1;   // 사용자가 정한 확대 배율(0.6~1.8), 설정에 저장\nlet vfx = [], hitStop = 0, shake = 0, cam = { x: 0, y: 0 }, W = 0, H = 0, DPR = 1, ZOOM = 2,")
rep("  ZOOM = W < 720 ? 1.5 : (W < 1400 ? 2 : 2.5);",
    "  ZOOM = (W < 720 ? 1.5 : (W < 1400 ? 2 : 2.5)) * ZOOM_USER;")
rep("cvs.addEventListener('pointerdown', e => handleTap(e.clientX, e.clientY));",
    r"""cvs.addEventListener('pointerdown', e => { if (PINCH.pts.size > 1 || PINCH.active) return; handleTap(e.clientX, e.clientY); });
// ───────── 화면 확대/축소 ─────────
const ZOOM_MIN = 0.6, ZOOM_MAX = 1.8;
let zoomSaveT = 0;
function setZoom(z, quiet) {
  const nz = clamp(Math.round(z * 100) / 100, ZOOM_MIN, ZOOM_MAX);
  if (Math.abs(nz - ZOOM_USER) < 0.001) return ZOOM_USER;
  ZOOM_USER = nz; OPT.zoom = nz; resize();
  clearTimeout(zoomSaveT); zoomSaveT = setTimeout(saveOpt, 300);
  if (!quiet) zoomToast();
  const v = $('vZoom'); if (v) v.textContent = Math.round(nz * 100) + '%';
  return nz;
}
function zoomToast() {
  let el = $('zoomToast');
  if (!el) { el = document.createElement('div'); el.id = 'zoomToast'; el.className = 'hud'; document.body.append(el); }
  el.textContent = `화면 ${Math.round(ZOOM_USER * 100)}%`; el.classList.add('show');
  clearTimeout(el._h); el._h = setTimeout(() => el.classList.remove('show'), 700);
}
// 휴대폰: 두 손가락으로 벌리면 확대, 오므리면 축소(화면·조이스틱 위 어디서든)
const PINCH = { pts: new Map(), active: false, d0: 0, z0: 1 };
const onGameLayer = el => el === cvs || (el && el.closest && el.closest('#joyZone'));
window.addEventListener('pointerdown', e => {
  if (e.pointerType !== 'touch' || !running || !onGameLayer(e.target)) return;
  PINCH.pts.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (PINCH.pts.size === 2) {
    const [a, b] = [...PINCH.pts.values()];
    PINCH.active = true; PINCH.d0 = Math.hypot(a.x - b.x, a.y - b.y) || 1; PINCH.z0 = ZOOM_USER;
    if (JOY.on) { JOY.on = false; JOY.id = null; joyRest(); }   // 조이스틱 이동은 멈춤
  }
}, true);
window.addEventListener('pointermove', e => {
  if (!PINCH.pts.has(e.pointerId)) return;
  PINCH.pts.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (PINCH.active && PINCH.pts.size >= 2) {
    const [a, b] = [...PINCH.pts.values()];
    setZoom(PINCH.z0 * Math.hypot(a.x - b.x, a.y - b.y) / PINCH.d0);
  }
}, true);
const pinchEnd = e => { if (!PINCH.pts.delete(e.pointerId)) return; if (PINCH.pts.size === 0) setTimeout(() => { PINCH.active = false; }, 120); };
window.addEventListener('pointerup', pinchEnd, true);
window.addEventListener('pointercancel', pinchEnd, true);
// PC: 마우스 휠
cvs.addEventListener('wheel', e => { if (!running) return; e.preventDefault(); setZoom(ZOOM_USER * (e.deltaY < 0 ? 1.1 : 1 / 1.1)); }, { passive: false });""")
# 조이스틱: 두 번째 손가락이면 시작하지 않음, 확대 중엔 탭으로 치지 않음
rep("    if (!running || JOY.on) return;\n    e.preventDefault(); audio();",
    "    if (!running || JOY.on || PINCH.active || PINCH.pts.size > 1) return;\n    e.preventDefault(); audio();")
rep("    const tap = !JOY.moved && performance.now() - JOY.t0 < 250;",
    "    const tap = !JOY.moved && performance.now() - JOY.t0 < 250 && !PINCH.active;")
# 키보드 + / -
rep("  if (e.code === 'KeyR' && running && P && !P.dead) {",
    "  if ((e.code === 'Equal' || e.code === 'NumpadAdd') && running) setZoom(ZOOM_USER * 1.1);\n  if ((e.code === 'Minus' || e.code === 'NumpadSubtract') && running) setZoom(ZOOM_USER / 1.1);\n  if (e.code === 'KeyR' && running && P && !P.dead) {")
# 설정 > 화면
rep('''  <div class="osec hidden" data-sec="view">''',
    '''  <div class="osec hidden" data-sec="view">
  <div class="orow"><span>화면 확대 <b id="vZoom">100%</b></span><div class="seg zoomseg"><button type="button" id="zoomOut" aria-label="축소">－</button><button type="button" id="zoomReset">기본</button><button type="button" id="zoomIn" aria-label="확대">＋</button></div></div>
  <div class="note">휴대폰은 두 손가락으로 벌리거나 오므리고, PC는 마우스 휠이나 + / - 키로 바꿀 수 있습니다.</div>''')
rep("function saveOpt() { try { localStorage.setItem(OPT_KEY, JSON.stringify(OPT)); } catch (e) { /* 저장 불가 */ } }",
    """function saveOpt() { try { localStorage.setItem(OPT_KEY, JSON.stringify(OPT)); } catch (e) { /* 저장 불가 */ } }
ZOOM_USER = clamp(+OPT.zoom || 1, 0.6, 1.8);""")

# ───── 2. 원거리 몬스터: 물러서기 제한 ─────
rep("""      else if (ai.keep && d < ai.keep[0]) {
        // 원거리: 너무 가까우면 뒤로 물러남
        const l = d || 1; m.goal = { x: m.x - (P.x - m.x) / l * 2, y: m.y - (P.y - m.y) / l * 2 }; m.retreat = true;
      }""",
    """      else if (ai.keep && d < ai.keep[0] && (m.kiteCd || 0) <= now && Math.hypot(m.x - m.home.x, m.y - m.home.y) < 8) {
        // 원거리: 너무 가까우면 0.7초만 뒤로 물러섬 → 그 뒤 4~6초는 도망가지 않고 그 자리에서 쏨(끝없이 도망가던 문제 수정)
        if (!m.retreat) m.retreatEnd = now + 0.7;
        if (now >= m.retreatEnd) { m.retreat = false; m.kiteCd = now + 4 + Math.random() * 2; m.goal = null; }
        else { const l = d || 1; m.goal = { x: m.x - (P.x - m.x) / l * 1.5, y: m.y - (P.y - m.y) / l * 1.5 }; m.retreat = true; }
      }""")
rep("  goblin_archer: { leash: 13, combo: 1, hurtRes: 0.55, sep: 0.85, keep: [3.0, 4.8] },",
    "  goblin_archer: { leash: 13, combo: 1, hurtRes: 0.55, sep: 0.85, keep: [2.2, 4.4] },")

# ───── 3. 상태창 ─────
rep('''  <div class="orbtxt"><b><span id="pname">기사</span><small id="pcls"></small></b><div class="sbar" id="shp"><i></i></div><div class="sbar" id="smp"><i></i></div><div class="num"><span class="hpt" id="hpt"></span><span class="mpt" id="mpt"></span></div><div id="buffs"></div></div>''',
    '''  <div class="orbtxt"><b><span class="plvt">Lv <span id="plv2">1</span></span><span id="pname">기사</span><small id="pcls"></small><span class="spbadge hidden" id="spBadge" title="능력치 포인트 — 눌러서 올리기">+</span></b>
    <div class="lbar hp" id="shp"><em>HP</em><div class="tr"><i></i><span class="hpt" id="hpt"></span></div></div>
    <div class="lbar mp" id="smp"><em>MP</em><div class="tr"><i></i><span class="mpt" id="mpt"></span></div></div>
    <div id="buffs"></div></div>''')
rep("  $('hpt').textContent = `HP ${Math.ceil(P.hp)}/${P.maxhp}`;\n  $('mpt').textContent = `MP ${Math.floor(P.mp)}/${P.maxmp}`;",
    "  $('hpt').textContent = `${Math.ceil(P.hp)} / ${P.maxhp}`;\n  $('mpt').textContent = `${Math.floor(P.mp)} / ${P.maxmp}`;")
rep("  $('plv').textContent = P.lv;", "  $('plv').textContent = P.lv; $('plv2').textContent = P.lv;")

rep('<span class="spbadge hidden" id="spBadge" title="능력치 포인트">+</span></div>', '</div>')
# ───── 4. 글꼴 ─────
rep('''  --display: "Nanum Myeongjo", "Batang", serif;
  --body: "Noto Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif;''',
    '''  /* 리니지 클라이언트처럼 숫자·영문은 Tahoma(아이폰은 같은 디자이너의 Verdana), 한글은 Noto Sans KR */
  --num: Tahoma, Verdana, "Noto Sans KR", "Apple SD Gothic Neo", sans-serif;
  --display: Tahoma, Verdana, "Noto Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
  --body: Tahoma, Verdana, "Noto Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif;''')
t = t.replace('"Noto Serif KR", "Noto Serif CJK KR", var(--display), serif', 'var(--display)')
t = t.replace('font-family: "Noto Serif KR", serif;', 'font-family: var(--display);')
t = t.replace('"Noto Sans KR", sans-serif', 'Tahoma, Verdana, "Noto Sans KR", sans-serif')   # 캔버스 글자(이름·피해 숫자 등)

# ───── 5. 스킬 습득 레벨 ─────
rep("const SKILL_LV = [1, 2, 4, 6];               // 스킬 1~4 해금 레벨",
    "const SKILL_LV = [2, 5, 9, 14];              // 스킬 1~4 를 배우는 레벨(처음엔 스킬 없음)")
rep("""    const locked = P.lv < skillLvReq(i);
    b.insertAdjacentHTML""", """    const locked = P.lv < skillLvReq(i);
    if (locked && !sk.wb) {   // 아직 못 배운 스킬: PC에는 'Lv N' 빈 칸만, 휴대폰에는 칸 자체가 없음(div 라서 부채꼴 순서에 안 들어감)
      bar.insertAdjacentHTML('beforeend', `<div class="slot extra empty learn" title="${sk.name} — Lv ${skillLvReq(i)}에 배웁니다"><span class="k">${i + 1}</span><div class="lock">Lv ${skillLvReq(i)}</div></div>`);
      return;
    }
    b.insertAdjacentHTML""")
rep("    if (unlocked.length) buildBar();",
    "    if (unlocked.length) { buildBar(); for (const n of unlocked) { banner(`새 스킬: ${n}`, '스킬 칸에 추가되었습니다'); texts.push({ who: P, x: P.x, y: P.y, z: 86, t: 0, s: `새 스킬 ${n}`, c: '#9fe0ff', big: true }); } }")

# ───── CSS ─────
rep("/* 가방: 일괄 판매 · 착용 탭 */", r"""/* 상태창(리니지식 가로 막대): 레벨·이름 줄 + HP/MP 막대 안에 숫자 */
.lvb { display: none !important; }
#status .orbtxt { display: grid; gap: 3px; max-width: none; min-width: 0; }
#status .orbtxt b { display: flex; align-items: center; gap: 6px; font: 800 14px var(--body); white-space: nowrap; min-width: 0; }
#status .orbtxt b #pname { overflow: hidden; text-overflow: ellipsis; }
.plvt { flex: none; font: 800 11px var(--num); color: #ffe08a; padding: 1px 5px; border-radius: 3px; background: linear-gradient(#5e5b55, #2c2b29); border: 1px solid #b4aea2; text-shadow: 0 1px 0 #000; }
#status .spbadge { position: static; flex: none; }
.orb .spbadge { top: -2px; right: -2px; }
.lbar { display: grid; grid-template-columns: 28px 1fr; height: 18px; width: 168px; filter: drop-shadow(0 1px 1px rgba(0,0,0,.7)); }
.lbar em { font: italic 900 10px var(--num); display: grid; place-items: center; color: #fff; border-radius: 9px 0 0 9px; border: 1px solid #0c0b0a; border-right: 0;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.35), inset 0 -2px 3px rgba(0,0,0,.4); text-shadow: 0 1px 0 #000; }
.lbar.hp em { background: linear-gradient(#b84a40, #6a1410); } .lbar.mp em { background: linear-gradient(#4a6ab8, #142a6a); }
.lbar .tr { position: relative; overflow: hidden; background: linear-gradient(#0a0908, #1c1a18); border: 1px solid #0c0b0a; border-radius: 0 4px 4px 0;
  box-shadow: inset 0 0 0 1px #77736b, inset 0 3px 5px rgba(0,0,0,.85); }
#shp .tr i, #smp .tr i { position: absolute; left: 1px; top: 1px; bottom: 1px; height: auto; display: block; border-radius: 0 2px 2px 0; transition: width .15s; }
#shp .tr i { background: linear-gradient(#ff8a7a 0%, #e0403a 35%, #a01812 70%, #6a0a06 100%); }
#smp .tr i { background: linear-gradient(#9ac8ff 0%, #3a7ae8 35%, #1a3aa8 70%, #0c1e66 100%); }
.lbar .tr::after { content: ''; position: absolute; left: 1px; right: 1px; top: 1px; height: 40%; background: linear-gradient(rgba(255,255,255,.28), rgba(255,255,255,0)); pointer-events: none; }
.lbar .tr span { position: absolute; inset: 0; display: grid; place-items: center; z-index: 1; font: 700 11px var(--num); color: #fff; letter-spacing: .03em; font-variant-numeric: tabular-nums;
  text-shadow: 1px 0 0 #000, -1px 0 0 #000, 0 1px 0 #000, 0 -1px 0 #000, 0 0 3px #000; }
@media (max-width: 720px) { .lbar { width: 150px; height: 17px; } #status .orbtxt b { font-size: 13px; } }
@media (hover: hover) and (pointer: fine) and (min-width: 960px) and (min-height: 600px) {
  #dock .em { display: none !important; }                    /* 가운데 별 문장이 HP 막대를 가려서 뺌 */
  #status { bottom: 100px; } #status .orb { width: 58px; height: 58px; }
  .lbar { width: 100%; height: 20px; } .lbar .tr span { font-size: 12px; }
}
.slot.extra.learn .lock { font: 700 10px var(--num); color: #9a968e; }
#zoomToast { left: 50%; top: 38%; transform: translate(-50%, -50%); padding: 6px 14px; border-radius: 16px; background: rgba(20,19,18,.78); border: 1px solid #8e897f;
  color: #fff3d8; font: 800 14px var(--num); opacity: 0; transition: opacity .2s; pointer-events: none !important; z-index: 40; }
#zoomToast.show { opacity: 1; }
.zoomseg button { min-width: 44px; font-size: 15px; font-weight: 800; }
/* 가방: 일괄 판매 · 착용 탭 */""")
# 설정 단추 연결
rep("$('wearBest').addEventListener('click', wearBest);",
    "$('wearBest').addEventListener('click', wearBest);\n$('zoomIn').addEventListener('click', () => setZoom(ZOOM_USER * 1.1));\n$('zoomOut').addEventListener('click', () => setZoom(ZOOM_USER / 1.1));\n$('zoomReset').addEventListener('click', () => { setZoom(1); $('vZoom').textContent = '100%'; });\nsetTimeout(() => { const v = $('vZoom'); if (v) v.textContent = Math.round(ZOOM_USER * 100) + '%'; }, 0);")
rep("window.__game = {\n", "window.__game = {\n  setZoom, get ZOOM() { return ZOOM; }, get ZOOM_USER() { return ZOOM_USER; }, PINCH,\n")
open(P, 'w', encoding='utf-8').write(t)
print('적용 완료')
