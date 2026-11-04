"""장비 점수에 따른 외형 4단계를 게임에 연결 (player_tiers.py 의 규칙 그대로)
- 등급 점수: 일반 1 · 고급 2 · 희귀 3 · 영웅 4 · 전설 5 · 고대 6 (빈 칸 0)
- 외형 점수 = (갑옷×3 + 투구 + 망토 + 장갑 + 장화 [+ 방패: 기사]) ÷ (8, 방패 없는 직업 7)
- 2.5 미만 1단계(기본 모습) · 3.5 미만 2단계 · 4.5 미만 3단계 · 그 이상 4단계
- 장비를 바꿀 때마다 다시 계산 → 단계가 바뀌면 빛 연출 + 알림, 캐릭터·가방 인형·초상 모두 새 모습
- 가방 장비창 아래와 착용·해제 탭에 '외형 점수 · 다음 단계까지' 표시
실행: python3 forgotten-forge/tools/lineage/patch_looks.py
"""
import os
import sys

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'game_template.html')
t = open(P, encoding='utf-8').read()
if 'LOOK_CUTS' in t:
    sys.exit('이미 적용됨')


def rep(old, new):
    global t
    n = t.count(old)
    if n != 1:
        sys.exit(f'앵커 {n}개: {old[:80]!r}')
    t = t.replace(old, new)


rep("function applyStats() { P.px = pxTotals();",
    r"""// ───────── 장비 외형 4단계(장비 점수제) ─────────
const LOOK_SCORE = { common: 1, uncommon: 2, rare: 3, heroic: 4, legend: 5, unique: 6 };
const LOOK_SLOTS = ['helm', 'cloak', 'gloves', 'boots'];
const LOOK_CUTS = [2.5, 3.5, 4.5];
const LOOK_NAMES = { knight: ['견습 기사', '아르델 기사단', '왕실 기사', '별의 기사'], elf: ['숲의 견습 궁수', '엘라시아 순찰자', '정령 궁수', '별빛 정령'],
  mage: ['견습 마법사', '연구소 마법사', '궁정 마법사', '별의 현자'] };
const gradeOfSlot = s => { const e = P.eq[s]; if (!e || e.none) return null; const d = equipDef(e.key); return d ? d.grade : null; };
function lookScore() {
  if (!P || !P.eq) return 0;
  const shield = P.cls === 'knight';
  let total = (LOOK_SCORE[gradeOfSlot('armor')] || 0) * 3 + LOOK_SLOTS.reduce((a, s) => a + (LOOK_SCORE[gradeOfSlot(s)] || 0), 0);
  if (shield) total += LOOK_SCORE[gradeOfSlot('shield')] || 0;
  return total / (shield ? 8 : 7);
}
const lookTierOf = sc => 1 + LOOK_CUTS.filter(c => sc >= c).length;
function lookInfo() {
  const sc = lookScore(), tier = lookTierOf(sc), next = LOOK_CUTS[tier - 1];
  return { sc, tier, name: (LOOK_NAMES[P.cls] || [])[tier - 1] || '', need: next != null ? next - sc : 0, next: next != null ? (LOOK_NAMES[P.cls] || [])[tier] : null };
}
// 단계 시트 이름(없거나 아직 안 구웠으면 기본 시트)
const lookSheet = tier => { const k = `${P.cls}_t${tier}`; return tier > 1 && META.characters[k] ? k : P.cls; };
function updateLook(quiet) {
  if (!P) return;
  const info = lookInfo(), old = P.lookTier || 1;
  P.lookTier = info.tier; P.sheet = lookSheet(info.tier);
  img(META.characters[P.sheet].sheet);
  if (!quiet && running && info.tier !== old) {
    const up = info.tier > old;
    banner(`외형 ${up ? '변화' : '되돌림'}: ${info.name}`, `장비 점수 ${info.sc.toFixed(2)} · ${info.tier}단계`);
    log(`외형이 ${info.tier}단계 「${info.name}」(으)로 바뀌었습니다. (장비 점수 ${info.sc.toFixed(2)})`, 'sys');
    if (up) { vfx.push({ k: 'lvup', x: P.x, y: P.y, t: 0, life: 1.4 }); vfx.push({ k: 'beam', x: P.x, y: P.y, t: 0, life: 1.2, col: GRADE_RGB[['common', 'rare', 'heroic', 'legend'][info.tier - 1]] }); sfx('enchant_ok', { gain: 0.6 }); }
  }
}
function lookText() {
  const i = lookInfo();
  return `외형 <b>${i.tier}단계 「${i.name}」</b> · 장비 점수 <b>${i.sc.toFixed(2)}</b>` + (i.next ? ` · 「${i.next}」까지 <b>${i.need.toFixed(2)}</b>` : ' · 최고 단계');
}
function applyStats() { updateLook(); P.px = pxTotals();""")

# 스프라이트: 단계 시트가 아직 안 불러졌으면 기본 시트로(캐릭터가 안 보이는 일 방지)
rep("""  const [start, n] = s.anims[anim] || s.anims.idle;
  f = Math.min(f, n - 1);
  const im = img(s.sheet);
  if (!im.complete || !im.naturalWidth) return;""",
    """  let im = img(s.sheet);
  if ((!im.complete || !im.naturalWidth) && s.tier_of) { s = META[e.group][s.tier_of]; im = img(s.sheet); }
  const [start, n] = s.anims[anim] || s.anims.idle;
  f = Math.min(f, n - 1);
  if (!im.complete || !im.naturalWidth) return;""")
# 가방 인형도 지금 외형으로
rep("  const cv = $('dollCv'), c = cv.getContext('2d'), sh = META.characters[P.cls];",
    "  const cv = $('dollCv'), c = cv.getContext('2d'), sh0 = META.characters[P.sheet] || META.characters[P.cls], sh = img(sh0.sheet).naturalWidth ? sh0 : META.characters[P.cls];")
# 표시: 가방 장비창 합계 아래 · 착용 탭 위
rep('      <div class="dsum" id="dsum"></div>', '      <div class="dsum" id="dsum"></div>\n      <div class="looksum" id="lookSum"></div>')
rep('''    <div class="sect">착용 중</div>
    <div class="wlist" id="wearList"></div>''', '''    <div class="looksum" id="lookSum2"></div>
    <div class="sect">착용 중</div>
    <div class="wlist" id="wearList"></div>''')
rep("  renderDetail(); renderBulk(); renderWear();",
    "  renderDetail(); renderBulk(); renderWear();\n  const lt = lookText(); $('lookSum').innerHTML = lt; $('lookSum2').innerHTML = lt + '<div class=\"note\">갑옷은 3배로 계산 · 투구·망토·장갑·장화' + (P.cls === 'knight' ? '·방패' : '') + '는 1배. 2.5 · 3.5 · 4.5 점에서 모습이 바뀝니다.</div>';")
rep("/* 가방: 일괄 판매 · 착용 탭 */", """.looksum { font: 12px var(--body); color: #e8e0cc; background: rgba(14,13,12,.6); border: 1px solid #8e897f; border-radius: 3px; padding: 6px 8px; line-height: 1.5; }
.looksum b { color: #ffe08a; } .looksum .note { margin-top: 2px; font-size: 11px; color: #b4aea2; }
#inv .doll { grid-template-rows: 380px auto auto; }
/* 가방: 일괄 판매 · 착용 탭 */""")
# 이어하기: 저장된 장비로 외형을 바로 맞춤
rep("  PET = null; applyStats(); devChanged();", "  PET = null; P.lookTier = 1; updateLook(true); applyStats(); devChanged();")
rep("window.__game = {\n", "window.__game = {\n  lookScore, lookInfo, updateLook, LOOK_CUTS,\n")
open(P, 'w', encoding='utf-8').write(t)
print('적용 완료')
