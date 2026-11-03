"""시작 화면을 '로그인 화면' 모양으로 다시 짠다(휴대폰 우선).
- 전체 화면 배경 그림(title_art.py가 그린 세로/가로 그림) + 그 위로 불티·연기가 움직이는 캔버스
- 가운데 큰 로고(별의 심장 문장 + 에르덴), 아래에 이름 칸 · 직업 3칸 · 시작 버튼만
- 소개 글·조작키 목록은 뺌
실행: python3 forgotten-forge/tools/lineage/patch_login.py
"""
import os
import re
import sys

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'game_template.html')
t = open(P, encoding='utf-8').read()
if 'class="login"' in t:
    sys.exit('이미 적용됨')


def cut(start, end_marker):
    """start 로 시작해 end_marker 바로 앞까지를 잘라 낸 위치를 돌려줌."""
    a = t.index(start)
    b = t.index(end_marker, a)
    return a, b


# ── 1. 화면 틀(HTML): #title 전체를 새로 ──
a = t.index('<div id="title">')
b = t.index('    <div class="keys">', a)
b = t.index('  </div>\n</div>', b) + len('  </div>\n</div>')
NEW_HTML = '''<div id="title">
  <div class="tart" aria-hidden="true"></div>
  <canvas id="titleBg" aria-hidden="true"></canvas>
  <div class="inner">
    <div class="crest">
      <canvas id="titleEmblem" width="200" height="200" aria-hidden="true"></canvas>
      <h1 aria-label="에르덴 : 별의 심장"><span class="logo">에르덴</span><span class="sub">별 의 심 장</span></h1>
    </div>
    <div class="login">
      <div class="frow"><label for="nick">이름</label>
        <input id="nick" type="text" maxlength="8" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="한글·영문 2~8자" enterkeyhint="done"></div>
      <div class="nickmsg" id="nickMsg" aria-live="polite"></div>
      <div class="frow"><span class="lbl">직업</span><div class="classes" id="classes"></div></div>
      <div class="cont"><button class="start hidden" id="continue" type="button"></button><button class="start" id="start" type="button" disabled>클래스를 고르세요</button></div>
      <label class="chk"><input type="checkbox" id="devTitle"> 개발자 모드</label>
      <div class="warn hidden" id="newWarn">새로 시작하면 저장된 진행이 지워집니다.</div>
    </div>
    <div class="ver">ERDEN · HEART OF THE STARS</div>
  </div>
</div>'''
t = t[:a] + NEW_HTML + t[b:]

# ── 2. 모양(CSS): 시작 화면 관련 규칙을 통째로 바꿈 ──
a = t.index('/* 시작 화면 */')
b = t.index('/* HUD */', a)
NEW_CSS = r'''/* 시작 화면(로그인) — 휴대폰 세로가 기본, 넓은 화면은 아래 @media 에서 조정 */
#title { position: fixed; inset: 0; overflow: hidden auto; z-index: 20; background: #0b0908; }
#title .tart { position: fixed; inset: 0; background: #0b0908 url("lineage-assets/ui/title_bg_portrait.jpg") center 30% / cover no-repeat; }
#titleBg { position: fixed; inset: 0; width: 100%; height: 100%; display: block; pointer-events: none; }
#title .inner { position: relative; min-height: 100dvh; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; gap: 14px;
  padding: max(16px, env(safe-area-inset-top, 0px)) max(18px, env(safe-area-inset-right, 0px)) max(14px, env(safe-area-inset-bottom, 0px)) max(18px, env(safe-area-inset-left, 0px)); }
#title .crest { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0; margin-top: 4vh; }
#title .crest canvas { width: 86px; height: 86px; margin-bottom: -6px; filter: drop-shadow(0 0 18px rgba(255,190,120,.35)); }
#title h1 { margin: 0; display: flex; flex-direction: column; align-items: center; line-height: 1; }
#title .logo { font-family: "Noto Serif KR", var(--display), serif; font-weight: 900; font-size: clamp(64px, 19vw, 120px); letter-spacing: .02em;
  background: linear-gradient(#ffffff 0%, #e9e6e0 38%, #a9a49a 52%, #f2efe8 70%, #8a857c 100%); -webkit-background-clip: text; background-clip: text; color: transparent;
  -webkit-text-stroke: 1px rgba(30,24,18,.6); filter: drop-shadow(0 3px 0 #120e0b) drop-shadow(0 0 2px #000) drop-shadow(0 0 22px rgba(255,200,140,.28)); }
#title .sub { margin-top: 6px; font: 700 clamp(13px, 3.6vw, 18px) "Noto Serif KR", var(--display), serif; letter-spacing: .5em; padding-left: .5em; color: #e8c88a;
  text-shadow: 0 1px 0 #000, 0 0 10px rgba(255,180,90,.45); }
#title .login { width: min(360px, 100%); display: grid; gap: 9px; }
#title .frow { display: grid; grid-template-columns: 54px 1fr; align-items: center; gap: 10px; }
#title .frow label, #title .frow .lbl { font: italic 700 16px "Noto Serif KR", var(--display), serif; color: #efe6d4; text-align: right; text-shadow: 0 1px 2px #000, 0 0 6px #000; }
/* 입력 칸: 은빛 테두리 액자 안의 검은 칸 */
#nick { width: 100%; min-width: 0; font: 700 17px var(--body); color: #fbf1da; padding: 10px 12px; border-radius: 3px; outline: none;
  background: linear-gradient(#050404, #120e0c); border: 1px solid #8f8a80;
  box-shadow: 0 0 0 1px #1a1612, 0 0 0 3px #4a463e, 0 0 0 4px #0c0a08, inset 0 2px 8px rgba(0,0,0,.9); }
#nick::placeholder { color: #6e665a; font-weight: 500; }
#nick:focus { border-color: #e6d6b0; } #nick.bad { border-color: #d0604c; } #nick.good { border-color: #9ad07a; }
#title .nickmsg { margin: -4px 0 0 64px; min-height: 15px; font-size: 12px; color: #cfc4ae; text-shadow: 0 1px 2px #000; }
#title .nickmsg.bad { color: #ffaa98; } #title .nickmsg.good { color: #c4f0a8; }
/* 직업 3칸: 작은 초상 + 이름 */
#title .classes { display: grid; grid-template-columns: repeat(3, 1fr); gap: 7px; }
.cls { position: relative; display: grid; justify-items: center; gap: 0; padding: 3px 2px 5px; cursor: pointer; border-radius: 3px; color: #e8dfcc;
  background: linear-gradient(rgba(12,10,8,.82), rgba(4,3,3,.9)); border: 1px solid #6e685e; box-shadow: 0 0 0 1px #0c0a08, inset 0 0 10px rgba(0,0,0,.8); transition: border-color .15s, box-shadow .15s; }
.cls canvas { width: 100%; height: 58px; image-rendering: pixelated; }
.cls b { font: 700 13px "Noto Serif KR", var(--display), serif; }
.cls[aria-pressed="true"] { border-color: #f0d68a; color: #fff3cf; box-shadow: 0 0 0 1px #0c0a08, 0 0 12px rgba(240,200,110,.55), inset 0 0 12px rgba(240,200,110,.18); }
/* 시작 버튼: 올리브빛 바탕 + 은빛 장식 테두리(로그인 버튼 느낌) */
#title .cont { display: grid; gap: 8px; margin-top: 4px; }
.start { width: 100%; min-height: 48px; padding: 10px 16px; border-radius: 6px; cursor: pointer;
  font: italic 800 17px "Noto Serif KR", var(--display), serif; letter-spacing: .04em; color: #f4f0e0; text-shadow: 0 1px 2px #000;
  background: radial-gradient(ellipse at 50% 20%, #7c9440 0%, #4a5e1e 55%, #26320c 100%);
  border: 1px solid #c8c2b4; box-shadow: 0 0 0 2px #2a2620, 0 0 0 3px #8a847a, 0 3px 10px rgba(0,0,0,.7), inset 0 1px 0 rgba(255,255,255,.25); }
.start:disabled { cursor: default; filter: grayscale(.75) brightness(.7); }
.start.alt { min-height: 40px; font-size: 14px; background: linear-gradient(#2a2622, #151210); color: #d8cfbc; }
#title .chk { justify-self: center; display: flex; gap: 6px; align-items: center; font-size: 12px; color: #bdb3a0; text-shadow: 0 1px 2px #000; }
#title .chk input { width: 16px; height: 16px; accent-color: #9ab04a; }
#title .warn { text-align: center; font-size: 12px; color: #ffb07a; text-shadow: 0 1px 2px #000; }
#title .ver { font-size: 10px; letter-spacing: .3em; color: rgba(220,200,160,.45); }
#title .missing { width: min(360px, 100%); }
/* 넓은 화면(가로 화면·PC): 가로 그림, 로고를 성 위에, 입력은 그 아래 */
@media (orientation: landscape) and (min-width: 700px) {
  #title .tart { background-image: url("lineage-assets/ui/title_bg_landscape.jpg"); background-position: center 40%; }
  #title .crest { flex: none; margin-top: 12vh; }
  #title .logo { font-size: clamp(64px, 9vw, 120px); }
  #title .inner { justify-content: flex-start; gap: 18px; }
  #title .login { margin-top: 2vh; }
}
/* 낮은 가로 화면(휴대폰 눕힘): 문장 작게, 여백 줄임 */
@media (orientation: landscape) and (max-height: 520px) {
  #title .crest { margin-top: 2vh; } #title .crest canvas { width: 54px; height: 54px; }
  #title .logo { font-size: 48px; } #title .inner { gap: 8px; } .cls canvas { height: 40px; }
}
@media (prefers-reduced-motion: reduce) { .cls { transition: none; } }

'''
t = t[:a] + NEW_CSS + t[b:]
# 예전 제목 줄의 .chk/.cont/.warn 규칙은 게임 안에서 쓰는 곳이 있어 그대로 둔다(시작 화면은 #title 규칙이 우선)

# ── 3. 직업 칸: 이름만 남기고(설명 줄 뺌) ──
old = """    b.insertAdjacentHTML('beforeend', `<b>${c.label}</b><span class="role">${c.role}</span>
      <span class="stats"><span>HP ${c.hp}</span><span>MP ${c.mp}</span><span>공격 ${c.atk[0]}–${c.atk[1]}</span></span>
      <ul>${c.skills.map((id, i) => `<li>${i + 1}. ${SKILLS[id].name}</li>`).join('')}</ul>`);"""
if t.count(old) != 1:
    sys.exit('직업 칸 앵커 없음')
t = t.replace(old, "    b.title = `${c.label} — ${c.role} · HP ${c.hp} · MP ${c.mp}`; b.setAttribute('aria-label', `${c.label}, ${c.role}`);\n    b.insertAdjacentHTML('beforeend', `<b>${c.label}</b>`);")
# 직업 초상: 캐릭터를 크게(작은 칸 안에서도 보이게)
old = "      const sc = 1.4, fy = 140;"
if t.count(old) != 1:
    sys.exit('초상 배율 앵커 없음')
t = t.replace(old, "      const sc = 1.9, fy = 146;")

# ── 4. 배경 캔버스: 그림은 CSS가 깔고, 캔버스는 불티·흐르는 연기·달빛 깜빡임만 ──
a = t.index('// 시작 화면 배경: 밤하늘')
b = t.index('// 별의 심장 문장:', a)
NEW_BG = r'''// 시작 화면 움직임: 배경 그림 위로 불티가 올라가고 연기가 흐름(그림 자체는 CSS 배경)
const TB = { em: [], puffs: [], w: 0, h: 0 };
function drawTitleBg() {
  const cv = $('titleBg'); if (!cv || $('title').classList.contains('hidden')) return;
  const w = cv.clientWidth, h = cv.clientHeight, dpr = Math.min(2, window.devicePixelRatio || 1);
  if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) {
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); TB.w = w; TB.h = h;
    TB.em = Array.from({ length: Math.round(Math.min(90, w * h / 9000)) }, () => ({ x: Math.random() * w, y: h * (0.4 + Math.random() * 0.6), v: 18 + Math.random() * 40, s: Math.random() * 6.28, r: 0.8 + Math.random() * 1.8, life: Math.random() }));
    TB.puffs = Array.from({ length: 7 }, (_, i) => ({ x: Math.random() * w, y: h * (0.15 + Math.random() * 0.45), r: Math.max(w, h) * (0.18 + Math.random() * 0.22), v: 6 + Math.random() * 10, a: 0.05 + Math.random() * 0.07 }));
    TB.last = performance.now();
  }
  const c = cv.getContext('2d'); c.setTransform(dpr, 0, 0, dpr, 0, 0); c.clearRect(0, 0, w, h);
  const now2 = performance.now(), dt = Math.min(0.05, (now2 - (TB.last || now2)) / 1000); TB.last = now2;
  for (const p of TB.puffs) {   // 천천히 옆으로 흐르는 연기
    p.x += p.v * dt; if (p.x - p.r > w) p.x = -p.r;
    const g = c.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r); g.addColorStop(0, `rgba(24,22,20,${p.a})`); g.addColorStop(1, 'rgba(24,22,20,0)');
    c.fillStyle = g; c.fillRect(p.x - p.r, p.y - p.r, p.r * 2, p.r * 2);
  }
  c.globalCompositeOperation = 'lighter';
  for (const e of TB.em) {      // 불티: 흔들리며 위로, 올라갈수록 흐려짐
    e.y -= e.v * dt; e.s += dt * 2; e.x += Math.sin(e.s) * 12 * dt; e.life += dt * 0.25;
    if (e.y < h * 0.15 || e.life > 1) { e.x = Math.random() * w; e.y = h * (0.6 + Math.random() * 0.4); e.life = 0; }
    const a = Math.sin(Math.min(1, e.life) * Math.PI) * (0.5 + 0.5 * Math.sin(e.s * 3));
    c.fillStyle = `rgba(255,${150 + (e.r * 30 | 0)},70,${0.75 * a})`; c.beginPath(); c.arc(e.x, e.y, e.r, 0, 6.283); c.fill();
  }
  c.globalCompositeOperation = 'source-over';
}
'''
t = t[:a] + NEW_BG + t[b:]

# ── 5. 이름 안내문: 처음엔 비워 둠(화면을 깔끔하게) ──
old = "  if (!s) return { ok: false, msg: '이름을 지어 주세요', s };"
if t.count(old) != 1:
    sys.exit('이름 안내 앵커 없음')
t = t.replace(old, "  if (!s) return { ok: false, msg: '', s };")
old = "  $('start').textContent = !c ? '클래스를 고르세요' : !nickOk ? '이름을 정하세요' : `${nickOk} · ${c.label}(으)로 시작`;"
if t.count(old) != 1:
    sys.exit('시작 버튼 글자 앵커 없음')
t = t.replace(old, "  $('start').textContent = !nickOk ? '이름을 정하세요' : !c ? '직업을 고르세요' : (loadSave() ? '새로 시작' : '게임 시작');")
# 이어하기 버튼이 있으면 그것을 위 큰 버튼으로, 새로 시작은 아래 작은 버튼
old = "    $('start').classList.add('alt');"
if t.count(old) != 1:
    sys.exit('alt 앵커 없음')
t = t.replace(old, "    $('start').classList.add('alt'); if (sv.name) $('nick').placeholder = '새 캐릭터 이름';")

open(P, 'w', encoding='utf-8').write(t)
print('적용 완료')
