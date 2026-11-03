"""시작 화면 2차 수정(휴대폰 우선):
- 로그인 칸을 화면 정중앙에, '이름'·'직업' 글자 없앰
- 로고: 영어 필기체 Erden / Heart of the Stars
- 배경: 그림 위에서 기사·요정·마법사 군대와 오크·해골·고블린 군대가 맞붙는 움직이는 대전투
  (게임 스프라이트를 원근에 맞춰 크기·투명도 조절, 화살 비·불덩이·폭발·칼날 불꽃·번개)
실행: python3 forgotten-forge/tools/lineage/patch_battle.py
"""
import os
import sys

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'game_template.html')
t = open(P, encoding='utf-8').read()
if 'BATTLE_KIT' in t:
    sys.exit('이미 적용됨')


def rep(old, new):
    global t
    n = t.count(old)
    if n != 1:
        sys.exit(f'앵커 {n}개: {old[:70]!r}')
    t = t.replace(old, new)


# ── 글꼴: 필기체(인터넷 연결 시 Great Vibes·Pinyon Script, 아이폰은 없어도 Snell Roundhand로 대체) ──
rep("family=Nanum+Myeongjo:wght@700;800&", "family=Great+Vibes&family=Pinyon+Script&family=Nanum+Myeongjo:wght@700;800&")

# ── 화면 틀 ──
rep('<h1 aria-label="에르덴 : 별의 심장"><span class="logo">에르덴</span><span class="sub">별 의 심 장</span></h1>',
    '<h1 aria-label="에르덴 : 별의 심장"><span class="logo">Erden</span><span class="sub">Heart of the Stars</span></h1>')
rep('''      <div class="frow"><label for="nick">이름</label>
        <input id="nick" type="text" maxlength="8" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="한글·영문 2~8자" enterkeyhint="done"></div>''',
    '''      <input id="nick" type="text" maxlength="8" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="캐릭터 이름 (한글·영문 2~8자)" enterkeyhint="done" aria-label="캐릭터 이름">''')
rep('      <div class="frow"><span class="lbl">직업</span><div class="classes" id="classes"></div></div>',
    '      <div class="classes" id="classes" role="group" aria-label="직업"></div>')

# ── 모양 ──
rep("#title .inner { position: relative; min-height: 100dvh; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; gap: 14px;",
    "#title .inner { position: relative; min-height: 100dvh; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px;")
rep("#title .crest { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0; margin-top: 4vh; }",
    "#title .crest { flex: none; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0; }")
rep("#title .logo { font-family: var(--display), \"Noto Serif KR\", serif; font-weight: 900; font-size: clamp(64px, 19vw, 120px); letter-spacing: .02em;",
    "#title .logo { font-family: \"Great Vibes\", \"Snell Roundhand\", \"Apple Chancery\", \"URW Chancery L\", \"Segoe Script\", cursive; font-weight: 400; font-size: clamp(84px, 27vw, 150px); letter-spacing: 0; padding: 0 .18em; line-height: 1.05;")
rep("#title .sub { margin-top: 6px; font: 700 clamp(13px, 3.6vw, 18px) var(--display), \"Noto Serif KR\", serif; letter-spacing: .5em; padding-left: .5em; color: #e8c88a;",
    "#title .sub { margin-top: -4px; font: 400 clamp(24px, 7.2vw, 36px) \"Pinyon Script\", \"Snell Roundhand\", \"Apple Chancery\", \"URW Chancery L\", cursive; letter-spacing: .02em; color: #f0d08e;")
rep("#title .login { width: min(360px, 100%); display: grid; gap: 9px; }",
    """#title .login { width: min(330px, 100%); display: grid; gap: 9px; margin-top: 6px; }
/* 가운데 글자·버튼이 잘 읽히게 뒤에 은은한 어둠 */
#title .inner::before { content: ''; position: fixed; inset: 0; pointer-events: none; background: radial-gradient(ellipse 60% 42% at 50% 50%, rgba(6,4,3,.62), rgba(6,4,3,0) 72%); }
#title .crest, #title .login, #title .ver { position: relative; }
#title .ver { position: fixed; bottom: max(10px, env(safe-area-inset-bottom, 0px)); left: 0; right: 0; text-align: center; }""")
rep("#title .nickmsg { margin: -4px 0 0 64px;", "#title .nickmsg { text-align: center; margin: -3px 0 0;")
rep("#title .cont { display: grid; gap: 8px; margin: 4px 0 0 64px; justify-self: stretch; }\n#title .chk { margin-left: 64px; }",
    "#title .cont { display: grid; gap: 8px; margin: 2px 0 0; justify-self: stretch; }")
rep("""  #title .crest { flex: none; margin-top: 12vh; }
  #title .logo { font-size: clamp(64px, 9vw, 120px); }
  #title .inner { justify-content: flex-start; gap: 18px; }
  #title .login { margin-top: 2vh; }""",
    """  #title .logo { font-size: clamp(90px, 11vw, 160px); }
  #title .sub { font-size: clamp(26px, 3vw, 40px); }""")
rep("""  #title .crest { flex: none; margin: 0; } #title .crest canvas { width: 60px; height: 60px; }
  #title .logo { font-size: 64px; } #title .login { margin: 0; width: min(340px, 52vw); gap: 6px; }""",
    """  #title .crest { flex: none; margin: 0; } #title .crest canvas { width: 54px; height: 54px; }
  #title .logo { font-size: 76px; } #title .sub { font-size: 24px; } #title .login { margin: 0; width: min(320px, 48vw); gap: 6px; }""")

# ── 움직이는 대전투 ──
a = t.index('// 시작 화면 움직임:')
b = t.index('// 별의 심장 문장:', a)
NEW = r'''// 시작 화면 대전투: 왼쪽 = 기사·요정·마법사 연합군, 오른쪽 = 오크·해골·고블린 무리.
// 게임 스프라이트를 멀리 있을수록 작고 흐리게 그려 원근을 만들고, 화살 비·불덩이·폭발·칼날 불꽃·번개를 더한다.
const BATTLE_KIT = {
  L: [['c', 'knight', 0.5], ['c', 'elf', 0.28], ['c', 'mage', 0.22]],
  R: [['m', 'orc', 0.34], ['m', 'skeleton', 0.24], ['m', 'goblin', 0.24], ['m', 'skeleton_archer', 0.1], ['m', 'wolf', 0.08]],
};
const RANGED = new Set(['elf', 'mage', 'skeleton_archer']);
const TB = { em: [], units: [], shots: [], booms: [], sparks: [], flash: 0, w: 0, h: 0, hz: 0, nextVolley: 1, nextFire: 2, nextBolt: 6 };
function pickKit(side) { let r = Math.random(); for (const k of BATTLE_KIT[side]) { if ((r -= k[2]) < 0) return k; } return BATTLE_KIT[side][0]; }
function spriteOf(k) { return k[0] === 'c' ? META.characters[k[1]] : META.monsters[k[1]]; }
// 앞뒤 깊이 z(0=멀리 ~ 1=코앞) → 화면 높이·크기
const bY = z => TB.hz + (TB.h - TB.hz) * (0.04 + 0.98 * Math.pow(z, 1.25));
const bS = z => (0.32 + 2.2 * Math.pow(z, 1.5)) * Math.min(1.25, TB.h / 760);
const frontX = (z, tt) => TB.w * 0.5 + Math.sin(z * 9 + tt * 0.15) * TB.w * 0.05;
function newUnit(side, z, fresh) {
  const kit = pickKit(side), s = spriteOf(kit);
  const u = { side, kit, s, z, dir: side === 'L' ? [2, 1, 3][Math.random() * 3 | 0] : [6, 7, 5][Math.random() * 3 | 0],
    state: 'walk', t: Math.random() * 2, f: 0, fight: 0, ranged: RANGED.has(kit[1]), speed: 30 + Math.random() * 40, hp: 2 + (Math.random() * 4 | 0) };
  const fx = frontX(z, 0), back = TB.w * (0.15 + Math.random() * 0.45);
  u.x = side === 'L' ? fx - (fresh ? TB.w * 0.55 + Math.random() * 80 : back) : fx + (fresh ? TB.w * 0.55 + Math.random() * 80 : back);
  if (u.ranged) u.stand = (side === 'L' ? -1 : 1) * TB.w * (0.18 + Math.random() * 0.2);
  return u;
}
function battleInit(w, h) {
  TB.w = w; TB.h = h; TB.hz = h * (h > w ? 0.47 : 0.56);
  const n = Math.round(Math.min(120, Math.max(60, w * h / 5200)));
  TB.units = [];
  for (let i = 0; i < n; i++) TB.units.push(newUnit(i % 2 ? 'L' : 'R', Math.pow(Math.random(), 0.8), false));
  TB.em = Array.from({ length: Math.round(Math.min(80, w * h / 10000)) }, () => ({ x: Math.random() * w, y: h * (0.4 + Math.random() * 0.6), v: 18 + Math.random() * 40, s: Math.random() * 6.28, r: 0.8 + Math.random() * 1.8, life: Math.random() }));
}
function battleStep(dt, tt) {
  for (const u of TB.units) {
    u.t += dt;
    const fx = frontX(u.z, tt), sc = bS(u.z), dirSign = u.side === 'L' ? 1 : -1;
    const goal = u.ranged ? fx + u.stand : fx - dirSign * 14 * sc;
    if (u.state === 'walk') {
      const d = goal - u.x;
      if (Math.abs(d) < 8 * sc) { u.state = 'fight'; u.t = 0; u.fight = 2 + Math.random() * 5; }
      else u.x += Math.sign(d) * u.speed * dt * (0.5 + sc * 0.5);
    } else if (u.state === 'fight') {
      u.fight -= dt;
      if (!u.ranged && Math.random() < dt * 1.2) {   // 칼날이 부딪히는 불꽃
        TB.sparks.push({ x: u.x + dirSign * 18 * sc, y: bY(u.z) - 34 * sc, t: 0, s: sc });
      }
      if (u.fight <= 0) { if (Math.random() < 0.45) { u.state = 'death'; u.t = 0; } else { u.fight = 2 + Math.random() * 4; } }
    } else if (u.state === 'death' && u.t > 2.4) {   // 쓰러진 뒤 뒤쪽에서 새 병사가 달려옴
      Object.assign(u, newUnit(u.side, Math.pow(Math.random(), 0.8), true));
    }
  }
  // 화살 비: 요정 쪽에서 오른쪽 무리로, 해골 궁수 쪽에서 왼쪽으로
  if ((TB.nextVolley -= dt) <= 0) {
    TB.nextVolley = 1.6 + Math.random() * 2.2;
    const side = Math.random() < 0.6 ? 'L' : 'R', n = 6 + (Math.random() * 8 | 0);
    for (let i = 0; i < n; i++) {
      const sx = side === 'L' ? TB.w * (0.05 + Math.random() * 0.25) : TB.w * (0.7 + Math.random() * 0.25), sy = TB.hz + (TB.h - TB.hz) * (0.2 + Math.random() * 0.4);
      const tx = side === 'L' ? TB.w * (0.55 + Math.random() * 0.4) : TB.w * (0.05 + Math.random() * 0.4), ty = TB.hz + (TB.h - TB.hz) * (0.1 + Math.random() * 0.6);
      TB.shots.push({ k: 'arrow', sx, sy, tx, ty, t: -i * 0.06, dur: 1.1 + Math.random() * 0.4, arc: TB.h * (0.18 + Math.random() * 0.1) });
    }
  }
  // 불덩이: 마법사·투석기에서 날아가 터짐
  if ((TB.nextFire -= dt) <= 0) {
    TB.nextFire = 1.2 + Math.random() * 2.4;
    const side = Math.random() < 0.5 ? 'L' : 'R';
    const sx = side === 'L' ? -20 : TB.w + 20, sy = TB.hz - TB.h * 0.05;
    const tx = side === 'L' ? TB.w * (0.55 + Math.random() * 0.4) : TB.w * (0.05 + Math.random() * 0.4), ty = TB.hz + (TB.h - TB.hz) * (0.08 + Math.random() * 0.55);
    TB.shots.push({ k: 'fire', sx, sy, tx, ty, t: 0, dur: 1.5 + Math.random() * 0.6, arc: TB.h * (0.22 + Math.random() * 0.12) });
  }
  // 하늘 번개
  if ((TB.nextBolt -= dt) <= 0) { TB.nextBolt = 7 + Math.random() * 9; TB.flash = 1; TB.boltX = TB.w * (0.15 + Math.random() * 0.7); }
  TB.flash = Math.max(0, TB.flash - dt * 3);
  for (const s of TB.shots) s.t += dt;
  for (const s of TB.shots) if (s.k === 'fire' && s.t >= s.dur && !s.done) {
    s.done = true; TB.booms.push({ x: s.tx, y: s.ty, t: 0, r: (28 + 50 * ((s.ty - TB.hz) / (TB.h - TB.hz))) * Math.min(1.3, TB.h / 760) });
    for (const u of TB.units) if (u.state !== 'death' && Math.hypot(u.x - s.tx, bY(u.z) - s.ty) < 40 && Math.random() < 0.6) { u.state = 'death'; u.t = 0; }
  }
  TB.shots = TB.shots.filter(s => s.t < s.dur + 0.05);
  for (const b of TB.booms) b.t += dt; TB.booms = TB.booms.filter(b => b.t < 1.1);
  for (const s of TB.sparks) s.t += dt; TB.sparks = TB.sparks.filter(s => s.t < 0.35);
}
function drawUnit(c, u, tt) {
  const s = u.s; if (!s) return; const im = img(s.sheet); if (!im.complete || !im.naturalWidth) return;
  let an, fps = 9;
  if (u.state === 'walk') an = 'walk';
  else if (u.state === 'death') an = 'death';
  else an = (Math.floor(u.t * 1.3) % 3 === 2) ? 'idle' : 'attack', fps = 11;
  const [st, n] = s.anims[an] || s.anims.idle;
  const f = an === 'death' ? Math.min(n - 1, Math.floor(u.t * 8)) : Math.floor(u.t * fps) % n;
  const sc = bS(u.z), y = bY(u.z);
  const sp = s.scale || 1;
  c.globalAlpha = (0.45 + 0.55 * Math.min(1, u.z * 1.4)) * (u.state === 'death' && u.t > 1.6 ? Math.max(0, 1 - (u.t - 1.6) / 0.8) : 1);
  c.drawImage(im, (st + f) * s.fw, u.dir * s.fh, s.fw, s.fh, Math.round(u.x - s.ax * sc * sp), Math.round(y - s.ay * sc * sp), Math.round(s.fw * sc * sp), Math.round(s.fh * sc * sp));
}
function drawTitleBg() {
  const cv = $('titleBg'); if (!cv || $('title').classList.contains('hidden')) return;
  const w = cv.clientWidth, h = cv.clientHeight, dpr = Math.min(2, window.devicePixelRatio || 1);
  if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); battleInit(w, h); TB.last = performance.now(); }
  const c = cv.getContext('2d'); c.setTransform(dpr, 0, 0, dpr, 0, 0); c.clearRect(0, 0, w, h); c.imageSmoothingEnabled = false;
  const now2 = performance.now(), dt = Math.min(0.05, (now2 - (TB.last || now2)) / 1000), tt = now2 / 1000; TB.last = now2;
  battleStep(dt, tt);
  // 번개: 하늘이 번쩍 + 갈라지는 빛줄기
  if (TB.flash > 0) {
    c.fillStyle = `rgba(200,210,255,${0.22 * TB.flash})`; c.fillRect(0, 0, w, TB.hz);
    if (TB.flash > 0.6) { c.strokeStyle = `rgba(235,240,255,${TB.flash})`; c.lineWidth = 2; c.beginPath(); let x = TB.boltX, y = 0; c.moveTo(x, y); while (y < TB.hz * 0.8) { x += (Math.random() - 0.5) * 40; y += 20 + Math.random() * 30; c.lineTo(x, y); } c.stroke(); }
  }
  // 군대: 먼 쪽부터 차례로
  const list = TB.units.slice().sort((a, b) => a.z - b.z);
  for (const u of list) drawUnit(c, u, tt);
  c.globalAlpha = 1;
  // 화살·불덩이
  for (const s of TB.shots) {
    if (s.t < 0) continue;
    const k = Math.min(1, s.t / s.dur), x = s.sx + (s.tx - s.sx) * k, y = s.sy + (s.ty - s.sy) * k - Math.sin(k * Math.PI) * s.arc;
    const k2 = Math.max(0, k - 0.03), x2 = s.sx + (s.tx - s.sx) * k2, y2 = s.sy + (s.ty - s.sy) * k2 - Math.sin(k2 * Math.PI) * s.arc;
    if (s.k === 'arrow') { c.strokeStyle = 'rgba(30,24,18,.9)'; c.lineWidth = 1.5; c.beginPath(); c.moveTo(x2, y2); c.lineTo(x, y); c.stroke(); }
    else {
      c.globalCompositeOperation = 'lighter';
      const g = c.createRadialGradient(x, y, 0, x, y, 22); g.addColorStop(0, 'rgba(255,240,180,.95)'); g.addColorStop(0.35, 'rgba(255,140,40,.7)'); g.addColorStop(1, 'rgba(255,60,0,0)');
      c.fillStyle = g; c.beginPath(); c.arc(x, y, 22, 0, 6.283); c.fill();
      c.strokeStyle = 'rgba(255,120,30,.35)'; c.lineWidth = 6; c.beginPath(); c.moveTo(x2 - (x - x2) * 3, y2 - (y - y2) * 3); c.lineTo(x, y); c.stroke();
      c.globalCompositeOperation = 'source-over';
    }
  }
  // 폭발·칼날 불꽃
  c.globalCompositeOperation = 'lighter';
  for (const b of TB.booms) {
    const k = b.t / 1.1, r = b.r * (0.4 + k * 1.4);
    const g = c.createRadialGradient(b.x, b.y, 0, b.x, b.y, r); g.addColorStop(0, `rgba(255,236,170,${0.9 * (1 - k)})`); g.addColorStop(0.4, `rgba(255,120,30,${0.7 * (1 - k)})`); g.addColorStop(1, 'rgba(120,20,0,0)');
    c.fillStyle = g; c.beginPath(); c.arc(b.x, b.y, r, 0, 6.283); c.fill();
  }
  for (const s of TB.sparks) {
    const k = s.t / 0.35; c.strokeStyle = `rgba(255,240,200,${1 - k})`; c.lineWidth = 1;
    for (let i = 0; i < 4; i++) { const a = i * 1.57 + s.x; c.beginPath(); c.moveTo(s.x, s.y); c.lineTo(s.x + Math.cos(a) * 8 * s.s * (0.4 + k), s.y + Math.sin(a) * 8 * s.s * (0.4 + k)); c.stroke(); }
  }
  // 불티
  for (const e of TB.em) {
    e.y -= e.v * dt; e.s += dt * 2; e.x += Math.sin(e.s) * 12 * dt; e.life += dt * 0.25;
    if (e.y < h * 0.15 || e.life > 1) { e.x = Math.random() * w; e.y = h * (0.6 + Math.random() * 0.4); e.life = 0; }
    const a = Math.sin(Math.min(1, e.life) * Math.PI) * (0.5 + 0.5 * Math.sin(e.s * 3));
    c.fillStyle = `rgba(255,${150 + (e.r * 30 | 0)},70,${0.75 * a})`; c.beginPath(); c.arc(e.x, e.y, e.r, 0, 6.283); c.fill();
  }
  c.globalCompositeOperation = 'source-over';
  // 앞쪽 아래는 어둡게(코앞 병사들이 그림자처럼)
  const fg = c.createLinearGradient(0, h * 0.78, 0, h); fg.addColorStop(0, 'rgba(8,6,5,0)'); fg.addColorStop(1, 'rgba(8,6,5,.85)');
  c.fillStyle = fg; c.fillRect(0, h * 0.78, w, h * 0.22);
}
'''
t = t[:a] + NEW + t[b:]
# 시작 화면에서 쓰는 군대 그림을 미리 불러 둠
rep("function titleLoop() {", "function battlePreload() { for (const side of ['L', 'R']) for (const k of BATTLE_KIT[side]) { const s = spriteOf(k); if (s) img(s.sheet); } }\nfunction titleLoop() {")
rep("  startReady(); requestAnimationFrame(titleLoop);", "  startReady(); battlePreload(); requestAnimationFrame(titleLoop);")
rep("window.__game = {\n  nickCheck, startReady,\n", "window.__game = {\n  nickCheck, startReady, get TB() { return TB; },\n")
open(P, 'w', encoding='utf-8').write(t)
print('적용 완료')
