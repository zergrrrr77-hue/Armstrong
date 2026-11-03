"""에르덴 시작 화면 개편 + 캐릭터 이름(닉네임) 입력 패치(한 번만 적용).
- 배경: 밤하늘·별·먼 산맥과 성채 실루엣·안개를 캔버스로 그림
- 가운데: 빛나는 '별의 심장' 문장(맥박처럼 밝아졌다 어두워짐)
- 돌·철·양피지 틀: 바깥 철 테두리 + 리벳(못), 안쪽 양피지 띠
- 닉네임: 한글·영문 2~8자, 특수문자·금지어 거르기 → 저장, 상태창·가방에 표시
실행: python3 forgotten-forge/tools/lineage/patch_title.py
"""
import os
import sys

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'game_template.html')
t = open(P, encoding='utf-8').read()
if 'id="nick"' in t:
    sys.exit('이미 적용됨')


def rep(old, new):
    global t
    n = t.count(old)
    if n != 1:
        sys.exit(f'앵커 {n}개: {old[:70]!r}')
    t = t.replace(old, new)


# ── 화면 틀(HTML) ──
rep("""<div id="title">
  <div class="inner">
    <div class="eyebrow">어두운 중세 쿼터뷰 RPG</div>
    <h1>에르덴 : 별의 심장</h1>""",
    """<div id="title">
  <canvas id="titleBg" aria-hidden="true"></canvas>
  <div class="inner">
    <div class="crest"><canvas id="titleEmblem" width="200" height="200" aria-hidden="true"></canvas>
      <div class="eyebrow">ERDEN · HEART OF THE STARS</div>
      <h1>에르덴 : 별의 심장</h1></div>""")
rep("""    <div class="classes" id="classes"></div>
    <div class="cont">""",
    """    <div class="classes" id="classes"></div>
    <div class="nickbox">
      <label for="nick">캐릭터 이름</label>
      <div class="nickrow"><input id="nick" type="text" maxlength="8" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="한글·영문 2~8자" enterkeyhint="done">
        <span class="nickmsg" id="nickMsg" aria-live="polite">이름을 지어 주세요</span></div>
    </div>
    <div class="cont">""")
rep("    <b>가방 · 장비</b>", "    <b><span id=\"invName\"></span> · 가방</b>")

# ── 모양(CSS) ──
rep("#title .inner { max-width: 1040px; margin: 0 auto; display: grid; gap: 22px; }",
    r"""#title .inner { position: relative; max-width: 1040px; margin: 0 auto; display: grid; gap: 22px; padding: 26px clamp(16px, 3vw, 34px) 30px;
  /* 돌 판 + 철 테두리 + 안쪽 양피지 띠 */
  background: linear-gradient(rgba(30,25,20,.86), rgba(14,12,10,.9)), repeating-linear-gradient(115deg, rgba(255,255,255,.015) 0 2px, transparent 2px 7px);
  border: 3px solid #4a4038; border-radius: 4px;
  box-shadow: 0 0 0 1px #0a0806, 0 0 0 5px #23201c, 0 0 0 6px #0a0806, inset 0 0 0 1px #6a5a44, inset 0 0 0 5px rgba(196,168,120,.14), inset 0 0 40px rgba(0,0,0,.6), 0 20px 60px rgba(0,0,0,.7); }
#title .inner::before, #title .inner::after { content: ''; position: absolute; top: 8px; width: 9px; height: 9px; border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, #c8bcaa, #5a5048 60%, #1a1612); box-shadow: 0 1px 1px #000; }
#title .inner::before { left: 8px; } #title .inner::after { right: 8px; }
#titleBg { position: fixed; inset: 0; width: 100%; height: 100%; z-index: -1; display: block; }
#title .crest { display: grid; justify-items: center; text-align: center; gap: 4px; margin-top: -6px; }
#title .crest canvas { width: 132px; height: 132px; }
#title .crest h1 { background: linear-gradient(#fff4d8, #e8c88a 55%, #a8803e); -webkit-background-clip: text; background-clip: text; color: transparent;
  filter: drop-shadow(0 2px 0 #000) drop-shadow(0 0 14px rgba(255,200,120,.25)); letter-spacing: .02em; }
#title .crest .eyebrow { letter-spacing: .32em; font-size: 11px; }
#title > .inner > p { justify-self: center; text-align: center; padding: 10px 16px; border-radius: 3px;
  background: linear-gradient(#d8c8a0, #bca878); color: #2a2014; box-shadow: inset 0 0 18px rgba(90,60,20,.45), 0 0 0 1px #4a3a22; }
#title > .inner > p i { color: #5a3a14; }
.nickbox { display: grid; gap: 6px; justify-self: start; width: min(420px, 100%); }
.nickbox label { font-size: 12px; letter-spacing: .14em; color: var(--gold); }
.nickrow { display: grid; grid-template-columns: 1fr; gap: 4px; }
#nick { font: 700 18px var(--body); color: #fbe7b8; background: #0f0c09; border: 1px solid #5a4a34; border-radius: 3px; padding: 10px 12px;
  box-shadow: inset 0 2px 6px rgba(0,0,0,.6); outline: none; }
#nick:focus { border-color: var(--gold); }
#nick.bad { border-color: #c8584a; } #nick.good { border-color: #7ab85a; }
.nickmsg { font-size: 12px; color: var(--muted); min-height: 16px; } .nickmsg.bad { color: #ff9a8a; } .nickmsg.good { color: #b8f0a0; }
.orbtxt small { font-size: 10px; color: var(--gold); letter-spacing: .06em; opacity: .85; }""")

# ── 상태창: 이름 밑에 직업 ──
rep('<b id="pname">기사</b>', '<b id="pname">기사</b><small id="pcls"></small>')

# ── 동작(JS) ──
rep("// ───────────────────────── 시작 화면 ─────────────────────────\nlet chosen = null;",
    r"""// ───────────────────────── 시작 화면 ─────────────────────────
let chosen = null;
// 캐릭터 이름 규칙: 한글(완성형)·영문만, 2~8자, 금지어 불가
const NICK_BAN = ['운영자', '관리자', '운영진', 'gm', 'admin', 'system', '시스템', '드로간', '세리아', '시발', '씨발', 'ㅅㅂ', '병신', '개새', '좆', '존나', '미친', 'fuck', 'shit', 'sex', '섹스', '느금'];
function nickCheck(raw) {
  const s = String(raw == null ? '' : raw).normalize('NFC').trim();
  if (!s) return { ok: false, msg: '이름을 지어 주세요', s };
  if (/\s/.test(s)) return { ok: false, msg: '띄어쓰기는 쓸 수 없습니다', s };
  if (/[ㄱ-ㅎㅏ-ㅣ]/.test(s)) return { ok: false, msg: '완성된 글자만 쓸 수 있습니다 (ㄱ, ㅏ 같은 낱자 불가)', s };
  if (!/^[가-힣A-Za-z]+$/.test(s)) return { ok: false, msg: '한글과 영문만 쓸 수 있습니다 (숫자·특수문자 불가)', s };
  if (s.length < 2) return { ok: false, msg: '2글자 이상이어야 합니다', s };
  if (s.length > 8) return { ok: false, msg: '8글자까지 쓸 수 있습니다', s };
  const low = s.toLowerCase();
  if (NICK_BAN.some(w => low.includes(w))) return { ok: false, msg: '쓸 수 없는 단어가 들어 있습니다', s };
  return { ok: true, msg: `「${s}」 — 좋은 이름입니다`, s };
}
let nickOk = null;
function startReady() {
  const r = nickCheck($('nick').value); nickOk = r.ok ? r.s : null;
  const typed = $('nick').value.length > 0;
  $('nick').classList.toggle('bad', typed && !r.ok); $('nick').classList.toggle('good', r.ok);
  $('nickMsg').textContent = r.msg; $('nickMsg').className = 'nickmsg' + (typed ? (r.ok ? ' good' : ' bad') : '');
  const c = chosen && CLASSES[chosen];
  $('start').disabled = !(c && nickOk);
  $('start').textContent = !c ? '클래스를 고르세요' : !nickOk ? '이름을 정하세요' : `${nickOk} · ${c.label}(으)로 시작`;
}
// 시작 화면 배경: 밤하늘·별·먼 산맥·성채 실루엣·안개(창 크기가 바뀌면 다시 그림)
const TB = { stars: [], fog: 0 };
function drawTitleBg() {
  const cv = $('titleBg'); if (!cv || $('title').classList.contains('hidden')) return;
  const w = cv.clientWidth, h = cv.clientHeight, dpr = Math.min(2, window.devicePixelRatio || 1);
  if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) {
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
    TB.stars = Array.from({ length: Math.round(w * h / 2600) }, () => ({ x: Math.random(), y: Math.random() * 0.72, r: Math.random() < 0.08 ? 1.6 : 0.8, p: Math.random() * 6.28 }));
  }
  const c = cv.getContext('2d'); c.setTransform(dpr, 0, 0, dpr, 0, 0);
  const tt = performance.now() / 1000;
  const sky = c.createLinearGradient(0, 0, 0, h); sky.addColorStop(0, '#05060c'); sky.addColorStop(0.55, '#141226'); sky.addColorStop(0.8, '#2a1c1a'); sky.addColorStop(1, '#0a0807');
  c.fillStyle = sky; c.fillRect(0, 0, w, h);
  for (const s of TB.stars) { c.globalAlpha = 0.35 + 0.45 * (0.5 + 0.5 * Math.sin(tt * 1.3 + s.p)); c.fillStyle = s.r > 1 ? '#ffe9b8' : '#cfd8ff'; c.fillRect(s.x * w, s.y * h, s.r, s.r); }
  c.globalAlpha = 1;
  // 은하수처럼 번지는 별빛
  const mw = c.createRadialGradient(w * 0.5, h * 0.18, 10, w * 0.5, h * 0.18, Math.max(w, h) * 0.55);
  mw.addColorStop(0, 'rgba(255,214,150,.16)'); mw.addColorStop(0.5, 'rgba(120,110,200,.06)'); mw.addColorStop(1, 'rgba(0,0,0,0)'); c.fillStyle = mw; c.fillRect(0, 0, w, h);
  const ridge = (base, amp, seed, col) => {
    c.fillStyle = col; c.beginPath(); c.moveTo(0, h);
    for (let x = 0; x <= w + 8; x += 8) { const k = x / w * 6.28; c.lineTo(x, h * base - amp * (Math.sin(k * 1.7 + seed) * 0.6 + Math.sin(k * 4.3 + seed * 2) * 0.3 + Math.sin(k * 9.1 + seed) * 0.1)); }
    c.lineTo(w, h); c.closePath(); c.fill();
  };
  ridge(0.74, h * 0.09, 1.2, '#1a1722');
  // 먼 성채: 언덕 위 탑 세 개와 성벽
  const cx = w * 0.72, cy = h * 0.66; c.fillStyle = '#100e14';
  c.fillRect(cx - 70, cy - 26, 140, 30);
  for (const [dx, tw, th] of [[-62, 16, 64], [-8, 22, 92], [46, 16, 58]]) { c.fillRect(cx + dx, cy - th, tw, th); c.beginPath(); c.moveTo(cx + dx - 3, cy - th); c.lineTo(cx + dx + tw / 2, cy - th - 20); c.lineTo(cx + dx + tw + 3, cy - th); c.fill(); }
  for (let i = -66; i < 70; i += 10) c.fillRect(cx + i, cy - 32, 6, 6);
  c.fillStyle = `rgba(255,190,110,${0.55 + 0.3 * Math.sin(tt * 2.2)})`; c.fillRect(cx - 2, cy - 70, 3, 5); c.fillRect(cx + 50, cy - 40, 2, 4);
  ridge(0.84, h * 0.06, 3.7, '#0d0b0e');
  // 안개: 천천히 흐르는 띠
  for (let i = 0; i < 3; i++) {
    const y = h * (0.78 + i * 0.06), x = ((tt * (8 + i * 5)) % (w + 400)) - 200;
    const fg = c.createRadialGradient(x, y, 10, x, y, w * 0.45); fg.addColorStop(0, 'rgba(150,140,170,.10)'); fg.addColorStop(1, 'rgba(0,0,0,0)');
    c.fillStyle = fg; c.fillRect(0, h * 0.6, w, h * 0.4);
  }
  const vg = c.createRadialGradient(w / 2, h / 2, Math.min(w, h) * 0.3, w / 2, h / 2, Math.max(w, h) * 0.75); vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,.7)');
  c.fillStyle = vg; c.fillRect(0, 0, w, h);
}
// 별의 심장 문장: 하트 모양 수정 안에 여덟 갈래 별, 바깥에 철 고리와 룬 점. 맥박처럼 빛남
function drawEmblem() {
  const cv = $('titleEmblem'); if (!cv || $('title').classList.contains('hidden')) return;
  const c = cv.getContext('2d'), S = 200, m = S / 2, tt = performance.now() / 1000, beat = 0.5 + 0.5 * Math.pow(Math.sin(tt * 2.1), 6) + 0.25 * Math.sin(tt * 0.9);
  c.clearRect(0, 0, S, S);
  const halo = c.createRadialGradient(m, m, 4, m, m, 96); halo.addColorStop(0, `rgba(255,220,150,${0.35 + 0.35 * beat})`); halo.addColorStop(0.45, `rgba(255,140,80,${0.12 + 0.12 * beat})`); halo.addColorStop(1, 'rgba(0,0,0,0)');
  c.fillStyle = halo; c.fillRect(0, 0, S, S);
  // 철 고리
  c.lineWidth = 7; c.strokeStyle = '#3a342e'; c.beginPath(); c.arc(m, m, 78, 0, 6.283); c.stroke();
  c.lineWidth = 1.5; c.strokeStyle = '#7a6a54'; c.beginPath(); c.arc(m, m, 81.5, 0, 6.283); c.stroke(); c.beginPath(); c.arc(m, m, 74.5, 0, 6.283); c.stroke();
  for (let i = 0; i < 12; i++) { const a = i / 12 * 6.283 + tt * 0.05, x = m + Math.cos(a) * 78, y = m + Math.sin(a) * 78; c.fillStyle = i % 3 ? '#8a7a62' : `rgba(255,214,140,${0.5 + 0.5 * beat})`; c.fillRect(x - 1.5, y - 1.5, 3, 3); }
  // 하트 모양 수정
  const heart = () => { c.beginPath(); c.moveTo(m, m + 46); c.bezierCurveTo(m - 58, m + 4, m - 46, m - 52, m, m - 22); c.bezierCurveTo(m + 46, m - 52, m + 58, m + 4, m, m + 46); c.closePath(); };
  heart(); const hg = c.createLinearGradient(m, m - 50, m, m + 46); hg.addColorStop(0, '#5a1a22'); hg.addColorStop(0.5, '#a8303a'); hg.addColorStop(1, '#2a0a12');
  c.fillStyle = hg; c.fill(); c.lineWidth = 3; c.strokeStyle = '#c8a060'; c.stroke();
  c.save(); heart(); c.clip(); c.globalAlpha = 0.25; c.fillStyle = '#fff'; c.beginPath(); c.moveTo(m - 40, m - 30); c.lineTo(m - 10, m - 30); c.lineTo(m - 34, m + 6); c.closePath(); c.fill(); c.restore();
  // 여덟 갈래 별(가운데에서 빛이 뿜어짐)
  c.save(); c.translate(m, m - 2); c.rotate(tt * 0.15);
  c.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 8; i++) {
    const L = i % 2 ? 18 : 30 + 6 * beat; c.rotate(Math.PI / 4);
    const g = c.createLinearGradient(0, 0, 0, -L); g.addColorStop(0, `rgba(255,250,220,${0.9})`); g.addColorStop(1, 'rgba(255,200,120,0)');
    c.fillStyle = g; c.beginPath(); c.moveTo(-4, 0); c.lineTo(0, -L); c.lineTo(4, 0); c.closePath(); c.fill();
  }
  const core = c.createRadialGradient(0, 0, 1, 0, 0, 14 + 4 * beat); core.addColorStop(0, '#fffef4'); core.addColorStop(0.4, `rgba(255,224,150,${0.8 + 0.2 * beat})`); core.addColorStop(1, 'rgba(255,150,80,0)');
  c.fillStyle = core; c.beginPath(); c.arc(0, 0, 18, 0, 6.283); c.fill();
  c.restore();
}
function titleLoop() { if ($('title').classList.contains('hidden')) return; drawTitleBg(); drawEmblem(); requestAnimationFrame(titleLoop); }""")
# 클래스 고르기: 이름 확인과 함께 시작 버튼 갱신
rep("      $('start').disabled = false; $('start').textContent = `${c.label}(으)로 시작`;",
    "      startReady();")
rep("  $('start').addEventListener('click', () => { if (chosen) startGame(chosen); });",
    """  $('start').addEventListener('click', () => { startReady(); if (chosen && nickOk) startGame(chosen, null, nickOk); });
  $('nick').addEventListener('input', startReady);
  $('nick').addEventListener('keydown', e => { e.stopPropagation(); if (e.key === 'Enter') { e.preventDefault(); $('nick').blur(); if (!$('start').disabled) $('start').click(); } });
  startReady(); requestAnimationFrame(titleLoop);""")
rep("    c.textContent = `이어하기 · ${CLASSES[sv.cls].label} Lv ${sv.lv}`;",
    "    c.textContent = `이어하기 · ${sv.name ? sv.name + ' · ' : ''}${CLASSES[sv.cls].label} Lv ${sv.lv}`;")
rep("function startGame(cls, sv) {", "function startGame(cls, sv, nick) {")
rep("  $('pname').textContent = CLASSES[cls].label;",
    """  // 캐릭터 이름: 새로 시작하면 입력한 이름, 이어하기면 저장된 이름(예전 저장은 직업 이름)
  P.name = (sv && sv.name && nickCheck(sv.name).ok) ? sv.name : (nick && nickCheck(nick).ok ? nickCheck(nick).s : CLASSES[cls].label);
  $('pname').textContent = P.name; $('pcls').textContent = CLASSES[cls].label; $('invName').textContent = P.name;""")
rep("  const d = { v: 1, cls: P.cls, lv: P.lv,", "  const d = { v: 1, name: P.name, cls: P.cls, lv: P.lv,")
# 능력치 탭 맨 위에 이름·직업 줄
rep("""    <div class="row"><span>다음 레벨</span>""", """    <div class="row"><span>이름</span><span>${P.name || ''} · ${CLASSES[P.cls].label}</span></div>
    <div class="row"><span>다음 레벨</span>""")
rep("window.__game = {\n", "window.__game = {\n  nickCheck, startReady,\n")
open(P, 'w', encoding='utf-8').write(t)
print('적용 완료')
