"""에르덴 시스템 확장 패치(한 번만 적용): 재료·채집·들개/고블린 궁수·드로간 제작·강화 규칙 개편.
game_template.html 의 정해진 자리(앵커)를 찾아 코드를 끼워 넣는다. 앵커를 못 찾으면 아무것도 바꾸지 않고 멈춘다.
실행: python3 forgotten-forge/tools/lineage/patch_systems.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, 'game_template.html')
t = open(P, encoding='utf-8').read()
if 'const MATERIALS = {' in t:
    sys.exit('이미 적용됨')


def rep(old, new, count=1):
    global t
    n = t.count(old)
    if n != count:
        sys.exit(f'앵커 {n}개(기대 {count}): {old[:80]!r}')
    t = t.replace(old, new)


# ───── 1. 몬스터: 들개 · 고블린 궁수 ─────
rep("  goblin:   { name: '고블린', hp: 80,",
    "  dog:      { name: '들개', hp: 100, atk: [8, 13], def: 0, speed: 3.1, range: 1.2, aggro: 6, xp: 20, cd: 1.3 },\n"
    "  goblin_archer: { name: '고블린 궁수', hp: 75, atk: [8, 12], def: 1, speed: 2.4, range: 5.2, aggro: 7, xp: 22, cd: 2.0, ranged: true, sheet: 'goblin' },\n"
    "  goblin:   { name: '고블린', hp: 80,")
rep("const MLV = { goblin: 1,", "const MLV = { dog: 3, goblin_archer: 3, goblin: 1,")
rep("  wolf:     { leash: 16, combo: 2, comboGap: 0.35, hurtRes: 0.4, sep: 0.8, dash: 1.35 },",
    "  wolf:     { leash: 16, combo: 2, comboGap: 0.35, hurtRes: 0.4, sep: 0.8, dash: 1.35 },\n"
    "  dog:      { leash: 14, combo: 2, comboGap: 0.4, hurtRes: 0.45, sep: 0.8, dash: 1.25 },\n"
    "  goblin_archer: { leash: 13, combo: 1, hurtRes: 0.55, sep: 0.85, keep: [3.0, 4.8] },")
rep("  wolf:     { equip: 0.06, odds: [70, 25, 5, 0, 0], gold: [6, 14], red: 0.22,",
    "  dog:      { equip: 0.06, odds: [70, 25, 5, 0, 0], gold: [6, 14], red: 0.2, blue: 0.07, sw: 0.03, sa: 0.04, gem: 0.01 },\n"
    "  goblin_archer: { equip: 0.07, odds: [70, 26, 4, 0, 0], gold: [7, 15], goldP: 0.9, red: 0.16, blue: 0.1, sw: 0.04, sa: 0.04, gem: 0.01 },\n"
    "  wolf:     { equip: 0.06, odds: [70, 25, 5, 0, 0], gold: [6, 14], red: 0.22,")
rep("const MONSTER_EL = { goblin: 'earth',", "const MONSTER_EL = { dog: 'earth', goblin_archer: 'storm', goblin: 'earth',")
rep("  goblin: ['고블린의 녹슨 귀걸이',",
    "  dog: ['들개 송곳니', 'bone', 20, 'sepia(.6)'], goblin_archer: ['고블린 화살깃', 'arrows', 22, 'sepia(.5) hue-rotate(60deg)'],\n  goblin: ['고블린의 녹슨 귀걸이',")
rep("group: 'monsters', sheet: s.type, x: s.x,", "group: 'monsters', sheet: d.sheet || s.type, x: s.x,")
rep("const hy = s.y - (e.type === 'ooze' ? 30 : e.type === 'goblin' ? 46 : 58);", "const hy = s.y - (e.type === 'ooze' ? 30 : e.sheet === 'goblin' ? 46 : 58);")
rep("const my = s.y - (e.type === 'ooze' ? 36 : e.type === 'goblin' ? 52 : 64);", "const my = s.y - (e.type === 'ooze' ? 36 : e.sheet === 'goblin' ? 52 : 64);")
# 들판 배치: 농장 남쪽 들개(퀘스트 '농장의 비명'), 고블린 야영지 옆 궁수
rep("  zone('goblin', 24, 20, 5, 3); zone('goblin', 22, 30, 4, 3);",
    "  zone('goblin', 24, 20, 5, 3); zone('goblin', 22, 30, 4, 3);\n  zone('dog', 21, 37, 3, 2); zone('dog', 31, 41, 4, 3); zone('goblin_archer', 27, 24, 3, 2); zone('goblin_archer', 38, 33, 2, 2);")

# ───── 2. 재료 · 강화석 ─────
rep("XITEMS.scroll_teleport = { name: '이동 포탈 스크롤', icon: 'scroll_teleport', grade: 'rare' };",
    r"""XITEMS.scroll_teleport = { name: '이동 포탈 스크롤', icon: 'scroll_teleport', grade: 'rare' };
// ── 에르덴 재료 ──
// [이름, 아이콘(숫자 = items/materials.png 칸 번호, 글자 = 기존 아이콘), 판매가, 색 필터, 나는 지역, 등급, 얻는 곳]
const MAT_SHEET = 'items/materials.png';
const MATERIALS = {
  mat_iron_ore:       ['철광석', 0, 6, null, 'ardel', 'common', '철광석 광맥 채집 · 고블린 무리'],
  mat_herb:           ['야생 약초', 1, 4, null, 'ardel', 'common', '야생 약초 채집'],
  mat_slime_gel:      ['녹색 슬라임의 점액', 2, 5, null, 'ardel', 'common', '녹색 슬라임 (70%)'],
  mat_dog_hide:       ['들개의 가죽', 3, 8, null, 'ardel', 'common', '들개 (60%)'],
  mat_old_bow:        ['고블린의 낡은 활', 'bow', 14, 'sepia(.9) brightness(.75)', 'ardel', 'uncommon', '고블린 궁수'],
  mat_vine:           ['질긴 넝쿨', 4, 6, null, 'ardel', 'common', '고블린 무리'],
  mat_ring_wood:      ['고대 나무의 나이테', 5, 40, null, 'elasia', 'uncommon', '엘라시아 숲 채집'],
  mat_moon_essence:   ['달빛의 정수', 'pot_white', 120, 'hue-rotate(190deg) saturate(2) brightness(1.2)', 'elasia', 'rare', '엘라시아 숲 채집(밤)'],
  mat_spirit_breath:  ['정령의 숨결', 'pot_green', 60, 'hue-rotate(60deg) brightness(1.3)', 'elasia', 'uncommon', '숲 정령 · 트렌트'],
  mat_soft_bark:      ['유연한 나무껍질', 6, 30, null, 'elasia', 'common', '숲 정령 · 트렌트'],
  mat_assassin_strap: ['암살자의 가죽끈', 'bracelet', 300, 'brightness(.55) saturate(.5)', 'elasia', 'rare', '다크 엘프 정찰병(정예)'],
  mat_iron_ore_hi:    ['상급 철광석', 10, 30, null, 'kardum', 'uncommon', '카르둠 산맥 채집'],
  mat_lava_stone:     ['마력 깃든 용암석', 7, 90, null, 'kardum', 'rare', '카르둠 산맥 채집'],
  mat_orichalcum:     ['오리하르콘 원석', 11, 400, null, 'kardum', 'heroic', '카르둠 산맥 채집'],
  mat_silver_ore:     ['은 광석', 12, 40, null, 'kardum', 'uncommon', '카르둠 산맥 채집'],
  mat_hard_stone:     ['단단한 돌조각', 8, 20, null, 'kardum', 'common', '돌골렘 · 화염의 하수인'],
  mat_mana_shard:     ['마나의 파편', 'gem_ruby', 80, 'hue-rotate(210deg) saturate(1.6) brightness(1.2)', 'kardum', 'rare', '돌골렘 · 화염의 하수인'],
  mat_flame_dust:     ['불꽃의 가루', 'gold', 50, 'hue-rotate(-25deg) saturate(2.4)', 'kardum', 'uncommon', '돌골렘 · 화염의 하수인'],
  mat_flame_heart:    ['화염의 심장 파편', 'gem_ruby', 5000, 'hue-rotate(20deg) saturate(2) brightness(1.3)', 'kardum', 'heroic', '필드 보스 불꽃의 파괴자'],
  mat_ruin_shard:     ['고대 유적의 파편', 9, 150, null, 'arcana', 'rare', '아르카나 폐허'],
};
for (const [id, [name, ic, price, hue, region, grade, src]] of Object.entries(MATERIALS))
  XITEMS[id] = { name, icon: typeof ic === 'string' ? ic : null, ico: typeof ic === 'number' ? ic : null, price, hue, mat: true, region, grade, src };
// 아직 맵이 없는 지역의 몬스터(데이터만 · 지역 맵을 만들 때 그대로 쓴다)
const FUTURE_MOBS = {
  elasia: [{ name: '숲 정령', lv: [16, 25], drops: ['mat_spirit_breath', 'mat_soft_bark'] }, { name: '트렌트', lv: [18, 25], drops: ['mat_spirit_breath', 'mat_soft_bark'] },
    { name: '다크 엘프 정찰병', lv: [24, 28], elite: true, drops: ['mat_assassin_strap'] }],
  kardum: [{ name: '돌골렘', lv: [28, 36], drops: ['mat_hard_stone', 'mat_mana_shard'] }, { name: '화염의 하수인', lv: [30, 40], drops: ['mat_mana_shard', 'mat_flame_dust'] },
    { name: '불꽃의 파괴자', lv: [42, 42], boss: true, drops: ['mat_flame_heart'] }],
};
// 몬스터별 재료 드롭 [재료, 확률, 개수]
const MAT_DROPS = {
  ooze: [['mat_slime_gel', 0.7, 1]], dog: [['mat_dog_hide', 0.6, 1]],
  goblin: [['mat_iron_ore', 0.3, 1], ['mat_vine', 0.35, 1], ['mat_old_bow', 0.04, 1]],
  goblin_archer: [['mat_iron_ore', 0.3, 1], ['mat_vine', 0.4, 1], ['mat_old_bow', 0.15, 1]],
  orc: [['mat_iron_ore', 0.45, 2], ['mat_vine', 0.25, 1]],
};
// ── 강화석(에르덴 강화 규칙) ──
// 일반·고급 장비 = 별빛 강화석(무기용/방어구용, 기존 주문서 id 그대로), 희귀 이상 = 정제된 별의 파편, 축복받은 강화석 = 파괴 방지 + 대성공
XITEMS.scroll_weapon = { name: '별빛 강화석(무기)', icon: 'gem_ruby', hue: 'hue-rotate(185deg) saturate(1.3) brightness(1.35)', grade: 'uncommon' };
XITEMS.scroll_armor = { name: '별빛 강화석(방어구)', icon: 'gem_ruby', hue: 'hue-rotate(140deg) saturate(1.1) brightness(1.25)', grade: 'uncommon' };
XITEMS.star_shard = { name: '정제된 별의 파편', icon: 'gem_ruby', hue: 'hue-rotate(40deg) saturate(.6) brightness(1.7)', grade: 'rare' };
XITEMS.blessed_stone = { name: '축복받은 강화석', icon: 'gem_ruby', hue: 'hue-rotate(60deg) saturate(2.2) brightness(1.5)', grade: 'legend', skill: true };
""")
# 아이콘: 재료 묶음 그림 칸 번호 지원
rep("""  const ic = itemIcon(xi ? xi.icon : id); if (!ic) return false;""",
    """  if (xi && xi.ico != null) {   // 에르덴 재료 아이콘 묶음(items/materials.png, 32칸 8열)
    const im = img(MAT_SHEET); if (!im.complete || !im.naturalWidth) return false;
    c.drawImage(im, (xi.ico % 8) * 32, Math.floor(xi.ico / 8) * 32, 32, 32, x, y, size, size); return true;
  }
  const ic = itemIcon(xi ? xi.icon : id); if (!ic) return false;""")
rep("  META.tiles.sheet, META.item_atlas.sheet, META.enchant_icons.sheet,\n];",
    "  META.tiles.sheet, META.item_atlas.sheet, META.enchant_icons.sheet, MAT_SHEET,\n  ...(META.npcs && META.npcs.npc_drogan ? [META.npcs.npc_drogan.sheet] : []),\n];")
# 가방: 재료는 전리품 칸에 함께
rep("const filters = [['all', '전체'], ['weapon', '무기'], ['armor', '방어구'], ['acc', '장신구'], ['use', '소모품'], ['loot', '전리품']];",
    "const filters = [['all', '전체'], ['weapon', '무기'], ['armor', '방어구'], ['acc', '장신구'], ['use', '소모품'], ['loot', '전리품·재료']];")
rep("(bagFilter === 'all' || (bagFilter === 'loot') === id.startsWith('loot_'))",
    "(bagFilter === 'all' || (bagFilter === 'loot') === (id.startsWith('loot_') || id.startsWith('mat_')))")
rep("s: `+${d.n} G`, c: '#ffd65a' });", "s: `+${d.n} 에테르`, c: '#ffd65a' });")
# 상점: 정제된 별의 파편
rep("  { id: 'scroll_weapon', price: 450, desc: '무기 강화 +1 시도' }, { id: 'scroll_armor', price: 320, desc: '방어구 강화 +1 시도' },",
    "  { id: 'scroll_weapon', price: 450, desc: '일반·고급 무기 강화 +1 시도' }, { id: 'scroll_armor', price: 320, desc: '일반·고급 방어구 강화 +1 시도' },\n"
    "  { id: 'star_shard', price: 2400, desc: '희귀 등급 이상 장비 강화 +1 시도' },")

# ───── 3. 드롭: 재료 · 강화석 ─────
rep("  roll('scroll_return', DEV() ? 0.3 : 0.03); roll('scroll_teleport', DEV() ? 0.2 : 0.015);",
    "  roll('scroll_return', DEV() ? 0.3 : 0.03); roll('scroll_teleport', DEV() ? 0.2 : 0.015);\n"
    "  for (const [id, p, n] of (MAT_DROPS[m.type] || [])) roll(id, p, n);\n"
    "  roll('star_shard', m.d.boss ? 1 : m.type.startsWith('skeleton') ? 0.01 : 0.004, m.d.boss ? 3 : 1);\n"
    "  roll('blessed_stone', m.d.boss ? 0.08 : 0.0005);")
rep("  for (const [id, n] of [['pot_red', 8], ['pot_blue', 6], ['scroll_weapon', 3], ['scroll_armor', 3], ['gem_ruby', 2]]) drops.push(Object.assign({ id, n }, at()));",
    "  for (const [id, n] of [['pot_red', 8], ['pot_blue', 6], ['scroll_weapon', 3], ['scroll_armor', 3], ['gem_ruby', 2], ['star_shard', 4]]) drops.push(Object.assign({ id, n }, at()));\n"
    "  if (Math.random() < (DEV() ? 1 : 0.25)) { drops.push(Object.assign({ id: 'blessed_stone', n: 1 }, at())); got.push('축복받은 강화석'); }")
rep("  const got = [];\n  drops.push(Object.assign({ id: 'loot_' + m.type, n: 1 }, at()));", "  drops.push(Object.assign({ id: 'loot_' + m.type, n: 1 }, at()));")
rep("  const W = WORLD_BOSS[MAP.id];\n  STATE.wbKill[MAP.id] = Date.now();", "  const W = WORLD_BOSS[MAP.id], got = [];\n  STATE.wbKill[MAP.id] = Date.now();")

# ───── 4. 채집 지점 ─────
rep("  // 우리 안을 돌아다니는 동물: pen = 움직일 수 있는 사각형(타일)",
    """  // 채집 지점: 철광석 광맥(바위 곁·폐허), 야생 약초(늪 가장자리·숲)
  const nodes = [
    ['ore', 34, 13], ['ore', 45, 22], ['ore', 50, 27], ['ore', 39, 35], ['ore', 26, 9], ['ore', 47, 16],
    ['herb', 12, 36], ['herb', 25, 38], ['herb', 21, 45], ['herb', 31, 18], ['herb', 44, 41], ['herb', 15, 33], ['herb', 28, 33],
  ].map(([kind, i, j], k) => ({ id: `n${k}`, kind, x: i + 0.5, y: j + 0.5, ready: true, t: 0 }));
  for (const n of nodes) { const name = n.kind === 'ore' ? 'node_ore' : 'node_herb'; if (META.props[name]) props.push({ name, x: n.x, y: n.y, frame: 0, node: n }); }
  // 드로간의 대장간(화로 옆)
  const smith = META.npcs && META.npcs.npc_drogan ? { id: 'smith', sprite: 'npc_drogan', name: '드로간', x: 12.4, y: 18.6 } : null;
  // 우리 안을 돌아다니는 동물: pen = 움직일 수 있는 사각형(타일)""")
rep("  return { id: 'field', name: '아르델 평원', N, g, props, spawns, npcs, critters,",
    "  return { id: 'field', name: '아르델 평원', N, g, props, spawns, npcs, critters, nodes, smith,")
rep("  ruin_wall: 0.8,", "  node_ore: 0.5, node_herb: 0,\n  ruin_wall: 0.8,")
# 채집 동작
rep("// ───────── 마을 동물(돼지·닭)",
    r"""// ───────── 채집: 광맥·약초를 눌러(또는 F) 1.4초 동안 캐면 재료, 45초 뒤 다시 자람 ─────────
const GATHER = { ore: { item: 'mat_iron_ore', n: [1, 2], dur: 1.6, verb: '캐는 중', sfx: 'hit_blunt', respawn: 45 },
  herb: { item: 'mat_herb', n: [1, 3], dur: 1.2, verb: '뜯는 중', sfx: 'step_grass', respawn: 40 } };
const nearNode = (r = 1.7) => P && MAP && MAP.nodes ? MAP.nodes.find(n => n.ready && dist(P, n) < r) : null;
function startGather(n) {
  if (!n || !n.ready || P.dead) return false;
  if (dist(P, n) > 1.7) { P.target = null; P.goal = safeSpot(n.x + 0.9, n.y + 0.9); P.gatherGo = n; P.autoHold = 6; return false; }
  P.goal = null; P.target = null; P.gatherGo = null;
  P.gathering = { n, t: 0, dur: GATHER[n.kind].dur }; P.dir = dirOf(n.x - P.x, n.y - P.y); setAnim(P, 'attack', true);
  sfx(GATHER[n.kind].sfx, { gain: 0.45 });
  return true;
}
function updateNodes(dt) {
  if (!MAP || !MAP.nodes) return;
  for (const n of MAP.nodes) if (!n.ready && (n.t -= dt) <= 0) n.ready = true;
  if (P.gatherGo && dist(P, P.gatherGo) < 1.7) startGather(P.gatherGo);
  const g = P.gathering;
  if (g) {
    if (P.goal || P.target || P.dead || !g.n.ready) { P.gathering = null; }
    else if ((g.t += dt) >= g.dur) {
      const G = GATHER[g.n.kind], n = irnd(G.n[0], G.n[1]);
      P.inv[G.item] = (P.inv[G.item] || 0) + n; g.n.ready = false; g.n.t = G.respawn; P.gathering = null;
      log(`${itemName(G.item)} ×${n}을(를) 얻었습니다.`, 'sys'); lootLog(`${itemName(G.item)} ×${n}`, 'common'); sfx('arrow_hit', { gain: 0.35 });
      texts.push({ who: P, x: P.x, y: P.y, z: 60, t: 0, s: `+${n} ${itemName(G.item)}`, c: '#c8f0a0' });
      renderInv(); save();
    }
  }
  const nn = nearNode();
  $('gatherBtn').classList.toggle('hidden', !nn || !!P.gathering || !running || !$('craft').classList.contains('hidden'));
  if (nn) $('gatherBtn').textContent = nn.kind === 'ore' ? '⛏ 철광석 캐기 (F)' : '✿ 약초 뜯기 (F)';
  // 대장간: 다가가면 '드로간과 대화' 버튼, 걸어가서 닿으면 제작 창
  const sm = MAP.smith, nearSm = sm && dist(P, sm) < 2.4;
  $('smithBtn').classList.toggle('hidden', !nearSm || !$('craft').classList.contains('hidden') || !running);
  if (P.smithGo && nearSm) { P.smithGo = false; P.goal = null; openCraft(); }
}
// ───────── 마을 동물(돼지·닭)""")
rep("    updatePet(dt); updateWaypoints(dt); updateCritters(dt);", "    updatePet(dt); updateWaypoints(dt); updateCritters(dt); updateNodes(dt);")
# 그리기: 다 캔 지점은 흐리게, 캐는 중이면 진행 막대, 드로간
rep("""      const fr = pm.frames > 1 ? (Math.floor(now * 7) + o.p.frame) % pm.frames : 0;
      ctx.drawImage(img(pm.sheet), fr * pm.fw, 0, pm.fw, pm.fh, Math.round(o.s.x - pm.ax), Math.round(o.s.y + TH / 2 - pm.ay), pm.fw, pm.fh);""",
    """      const fr = pm.frames > 1 ? (Math.floor(now * 7) + o.p.frame) % pm.frames : 0;
      if (o.p.node && !o.p.node.ready) ctx.globalAlpha = 0.28;
      ctx.drawImage(img(pm.sheet), fr * pm.fw, 0, pm.fw, pm.fh, Math.round(o.s.x - pm.ax), Math.round(o.s.y + TH / 2 - pm.ay), pm.fw, pm.fh);
      ctx.globalAlpha = 1;
      if (o.p.node && o.p.node.ready && dist(P, o.p.node) < 4) {   // 가까우면 반짝임 표시
        const a = 0.45 + 0.35 * Math.sin(now * 4); ctx.fillStyle = `rgba(255,236,170,${a})`; ctx.fillRect(Math.round(o.s.x) - 1, Math.round(o.s.y + TH / 2 - pm.ay) - 6, 2, 4);
      }""")
rep("  for (const n of MAP.npcs || []) list.push({ d: n.x + n.y, kind: 'npc', e: n });",
    "  for (const n of MAP.npcs || []) list.push({ d: n.x + n.y, kind: 'npc', e: n });\n  if (MAP.smith) list.push({ d: MAP.smith.x + MAP.smith.y, kind: 'smith', e: MAP.smith });")
rep("""    } else if (o.kind === 'npc') {""",
    """    } else if (o.kind === 'smith') {   // 드로간: 대기 동작, 플레이어 쪽을 바라봄
      const n = o.e, sm = META.npcs[n.sprite], s = toScr(n.x, n.y), im = img(sm.sheet);
      shadow(s.x, s.y, 13);
      if (im.complete && im.naturalWidth) {
        const d8 = dist(P, n) < 6 ? dirOf(P.x - n.x, P.y - n.y) : 1, fr = Math.floor(now * 6) % sm.anims.idle[1];
        ctx.drawImage(im, (sm.anims.idle[0] + fr) * sm.fw, d8 * sm.fh, sm.fw, sm.fh, Math.round(s.x - sm.ax), Math.round(s.y - sm.ay), sm.fw, sm.fh);
      }
      const ty = s.y - 52;
      ctx.font = '700 8px "Noto Sans KR", sans-serif'; ctx.textAlign = 'center';
      ctx.fillStyle = '#000'; ctx.fillText(n.name, s.x + 0.5, ty + 0.5); ctx.fillStyle = '#ffd9a0'; ctx.fillText(n.name, s.x, ty);
      ctx.font = '700 7px "Noto Sans KR", sans-serif'; ctx.fillStyle = '#000'; ctx.fillText('제작·대장간', s.x + 0.5, ty - 8.5); ctx.fillStyle = '#ff9a4a'; ctx.fillText('제작·대장간', s.x, ty - 9);
    } else if (o.kind === 'npc') {""")
rep("      drawSprite(e, s.x, s.y);\n      ctx.globalAlpha = 1;",
    """      drawSprite(e, s.x, s.y);
      ctx.globalAlpha = 1;
      if (e === P && P.gathering) {   // 채집 진행 막대
        const g = P.gathering, k = Math.min(1, g.t / g.dur), bx = Math.round(s.x - 16), by = Math.round(s.y - 66);
        ctx.fillStyle = '#000'; ctx.fillRect(bx - 1, by - 1, 34, 6); ctx.fillStyle = '#3a2f22'; ctx.fillRect(bx, by, 32, 4);
        ctx.fillStyle = '#c8f0a0'; ctx.fillRect(bx, by, Math.round(32 * k), 4);
        ctx.font = '700 7px "Noto Sans KR", sans-serif'; ctx.textAlign = 'center'; ctx.fillStyle = '#000'; ctx.fillText(GATHER[g.n.kind].verb, s.x + 0.5, by - 2.5); ctx.fillStyle = '#e8f8d0'; ctx.fillText(GATHER[g.n.kind].verb, s.x, by - 3);
      }""")
# 누르기: 드로간 · 채집 지점
rep("""  // 세리아(상점) 탭 → 다가가서 상점 열기
  for (const n of MAP.npcs || []) {""",
    """  // 드로간 탭 → 다가가서 제작 창
  if (MAP.smith) { const s = toScr(MAP.smith.x, MAP.smith.y); if (Math.abs(sx - s.x) < 22 && sy < s.y + 8 && sy > s.y - 70) { if (dist(P, MAP.smith) < 2.4) openCraft(); else { P.target = null; P.goal = safeSpot(MAP.smith.x + 1, MAP.smith.y + 1); P.smithGo = true; P.autoHold = 6; } return; } }
  // 채집 지점 탭 → 다가가서 캐기
  for (const n of (MAP.nodes || [])) { if (!n.ready) continue; const s = toScr(n.x, n.y); if (Math.abs(sx - s.x) < 20 && sy < s.y + 12 && sy > s.y - 44) { startGather(n); return; } }
  // 세리아(상점) 탭 → 다가가서 상점 열기
  for (const n of MAP.npcs || []) {""")
rep("  if (e.code === 'KeyF') { if (!$('wpMenu').classList.contains('hidden')) closeWp(); else if (nearWp()) openWp(nearWp()); else",
    "  if (e.code === 'KeyF') { if (!$('wpMenu').classList.contains('hidden')) closeWp(); else if (!$('craft').classList.contains('hidden')) closeCraft(); else if (nearWp()) openWp(nearWp()); else if (MAP.smith && dist(P, MAP.smith) < 2.4) openCraft(); else if (nearNode()) startGather(nearNode()); else")
rep("['shop', 'inv', 'opt', 'gacha', 'wpMenu', 'cmp', 'wmap'].forEach(id => $(id).classList.add('hidden'));",
    "['shop', 'inv', 'opt', 'gacha', 'wpMenu', 'cmp', 'wmap', 'craft'].forEach(id => $(id).classList.add('hidden'));")
rep("const panelOpen = () => ['inv', 'shop', 'opt', 'gacha', 'wpMenu', 'wmap'].some(",
    "const panelOpen = () => ['inv', 'shop', 'opt', 'gacha', 'wpMenu', 'wmap', 'craft'].some(")

# ───── 5. 드로간 제작 ─────
rep('<button class="hud hidden" id="wpBtn" type="button">',
    '''<button class="hud hidden" id="gatherBtn" type="button">⛏ 채집 (F)</button>
<button class="hud hidden" id="smithBtn" type="button">⚒ 드로간과 대화 (F)</button>
<div class="hud hidden" id="craft" role="dialog" aria-label="드로간의 대장간">
  <div class="shead"><canvas id="craftNpc" width="96" height="104"></canvas>
    <div class="sinfo"><small>아르델 마을 · 대장간</small><b>드로간</b><span class="ssay" id="craftSay"></span></div>
    <button type="button" id="craftClose" class="wclose" aria-label="대장간 닫기">✕</button></div>
  <div class="tabs" id="craftTabs"><button type="button" data-ct="mine" aria-pressed="true">내 직업</button><button type="button" data-ct="all" aria-pressed="false">전체 제작법</button></div>
  <div id="craftList"></div>
  <div class="note" id="craftGold"></div>
</div>
<button class="hud hidden" id="wpBtn" type="button">''')
rep("</style>", r"""/* 드로간 대장간(제작) — 상점 창과 같은 틀 */
#craft { left: 50%; top: 50%; transform: translate(-50%, -50%); width: min(600px, calc(100vw - 20px)); max-height: calc(100vh - 24px); overflow-y: auto; padding: 12px; display: grid; gap: 10px;
  background: linear-gradient(var(--stone-a, #2c2620), var(--stone-b, #17140f)); border: 2px solid var(--bronze, #8a6a3a); border-radius: 4px; box-shadow: inset 0 0 0 1px #0c0a07, 0 0 0 1px #0c0a07, 0 10px 30px rgba(0,0,0,.6); z-index: 30; }
#craft .shead { display: grid; grid-template-columns: 72px 1fr auto; gap: 10px; align-items: center; }
#craft .shead canvas { width: 72px; height: 78px; image-rendering: pixelated; }
#craft .sinfo { display: grid; gap: 2px; } #craft .sinfo small { color: var(--muted); font-size: 11px; } #craft .sinfo b { font: 900 18px "Noto Serif KR", var(--display), serif; color: #ffd9a0; }
#craft .ssay { font-size: 12px; color: #e8dcc0; }
#craft .tabs { display: flex; gap: 6px; } #craft .tabs button { flex: 1; min-height: 34px; background: #1c160f; border: 1px solid var(--line); color: var(--muted); border-radius: 3px; cursor: pointer; font-weight: 700; }
#craft .tabs button[aria-pressed="true"] { color: #ffe9b0; border-color: var(--bronze-hi, #c9a25a); background: #2a2118; }
.crow { display: grid; grid-template-columns: 40px 1fr auto; gap: 10px; align-items: center; padding: 9px 10px; background: rgba(8,6,4,.55); border: 1px solid #3a2f22; border-radius: 4px; }
.crow canvas { width: 40px; height: 40px; image-rendering: pixelated; }
.crow .cn { font-weight: 800; font-size: 14px; } .crow .cm { color: var(--muted); font-size: 11px; margin-top: 1px; }
.crow .cfx { font-size: 11px; color: #c8e8ff; margin-top: 2px; }
.crow .mats { display: flex; flex-wrap: wrap; gap: 4px 8px; margin-top: 5px; font-size: 11px; }
.crow .mats span { display: inline-flex; align-items: center; gap: 3px; } .crow .mats canvas { width: 18px; height: 18px; }
.crow .mats .lack { color: #ff9a7a; } .crow .mats .ok { color: #b8f0a0; }
.crow .lockr { font-size: 11px; color: #d8b07a; margin-top: 4px; }
.crow .cbtn { display: grid; gap: 4px; justify-items: end; font-size: 11px; color: var(--muted); }
.crow .cbtn button { min-width: 84px; min-height: 38px; background: linear-gradient(#6a4a16, #3a280c); border: 1px solid #f0cf7a; color: #fff1c8; border-radius: 3px; font-weight: 800; cursor: pointer; }
.crow .cbtn button:disabled { opacity: .35; cursor: default; }
.crow.other { opacity: .62; }
#gatherBtn, #smithBtn { left: 50%; transform: translateX(-50%); bottom: max(150px, calc(env(safe-area-inset-bottom, 0px) + 146px)); background: linear-gradient(#2a4a1a, #16280c); border: 1px solid #a8e07a; color: #eaffd8; padding: 10px 20px; border-radius: 20px; font-weight: 700; cursor: pointer; }
#smithBtn { background: linear-gradient(#5a3216, #301a0a); border-color: #ffb06a; color: #fff0e0; }
@media (hover: hover) and (pointer: fine) and (min-width: 960px) and (min-height: 600px) { #gatherBtn, #smithBtn { bottom: 190px; } }
</style>""")
rep("$('btnMap').addEventListener('click', () => { if (running) toggleWorldMap(); });",
    r"""$('btnMap').addEventListener('click', () => { if (running) toggleWorldMap(); });
// ───────────────────────── 드로간의 대장간: 직업별 무기 제작 ─────────────────────────
// 실패하면 재료와 에테르가 모두 사라진다. 결과물은 일반 드롭 장비보다 특수 옵션이 붙는다.
const CRAFT_GEAR = {
  cr_iron_short:   { key: 'cr_iron_short', name: '철제 숏소드', icon: 'longsword', grade: 'uncommon', slot: 'weapon', base: 'blade', lv: 10, atk: 10, acc: 1, fx: '명중 +1 · 공격력 +2 보정' },
  cr_hunter_bow:   { key: 'cr_hunter_bow', name: '헌터스의 숏보우', icon: 'bow', grade: 'uncommon', slot: 'weapon', base: 'bow', lv: 12, atk: 9, acc: 2, fx: '원거리 명중 +2' },
  cr_spirit_staff: { key: 'cr_spirit_staff', name: '정령의 마력 지팡이', icon: 'staff', grade: 'uncommon', slot: 'weapon', base: 'staff', lv: 20, atk: 12, mp: 50, mpRegen: 0.5, fx: '마법 공격력 +4 · 최대 MP +50 · MP 자연 회복 +50%' },
  cr_silver_bow:   { key: 'cr_silver_bow', name: '요정의 은빛 활', icon: 'bow', grade: 'rare', slot: 'weapon', base: 'bow', lv: 25, atk: 14, acc: 3, undead: 0.25, fx: '원거리 명중 +3 · 언데드에게 피해 +25%' },
  cr_flame_great:  { key: 'cr_flame_great', name: '화염의 대검', icon: 'greatsword', grade: 'heroic', slot: 'weapon', base: 'blade', lv: 40, atk: 19, flame: 0.2, fx: '공격 시 20% 확률로 주변에 화염 폭발' },
  cr_circle_staff: { key: 'cr_circle_staff', name: '대마법사의 서클 스태프', icon: 'staff', grade: 'heroic', slot: 'weapon', base: 'staff', lv: 40, atk: 19, mp: 30, cdr: 0.05, critDmg: 0.15, chain: 0.25, fx: '스킬 재사용 대기 -5% · 치명타 피해 +15% · 25% 확률 연쇄 피해' },
};
Object.assign(GEAR, CRAFT_GEAR);
const RECIPES = [
  { item: 'cr_iron_short', cost: 5000, ch: 85, mats: { mat_iron_ore: 10, mat_slime_gel: 15, mat_dog_hide: 5 } },
  { item: 'cr_hunter_bow', cost: 7000, ch: 80, mats: { mat_vine: 10, mat_old_bow: 2, mat_iron_ore: 5 } },
  { item: 'cr_spirit_staff', cost: 12000, ch: 75, mats: { mat_mana_shard: 5, mat_iron_ore: 8, mat_herb: 20 } },
  { item: 'cr_silver_bow', cost: 50000, ch: 60, mats: { mat_moon_essence: 3, mat_ring_wood: 8, mat_silver_ore: 20 } },
  { item: 'cr_flame_great', cost: 300000, ch: 35, mats: { mat_flame_heart: 1, mat_lava_stone: 15, mat_orichalcum: 5 } },
  { item: 'cr_circle_staff', cost: 350000, ch: 30, mats: { mat_lava_stone: 15, mat_flame_heart: 1, mat_ruin_shard: 10 } },
];
const BASE_LABEL = { blade: '기사', bow: '요정', staff: '마법사' };
const SMITH_SAY = ['쇠는 거짓말을 안 하지. 재료를 가져오면 두드려 주마.', '실패하면 재료도 돈도 불길 속으로 사라진다. 각오는 됐나?',
  '들개 가죽은 질기고 슬라임 점액은 담금질에 좋아. 아르델에서 다 구할 수 있다.', '카르둠의 용암석만 있으면… 아, 그 길은 아직 닫혀 있지.'];
let craftTab = 'mine';
const craftMatOk = r => Object.entries(r.mats).every(([id, n]) => (P.inv[id] || 0) >= n);
function craftBlock(r) {   // 제작할 수 없는 까닭(없으면 null)
  const d = CRAFT_GEAR[r.item];
  const locked = Object.keys(r.mats).map(id => XITEMS[id].region).filter(g => g && !regionOpen(g));
  if (locked.length) return `재료가 나는 ${[...new Set(locked)].map(g => REGIONS[g].name).join(' · ')}이(가) 아직 열리지 않았습니다`;
  if (d.base !== P.c.base) return `${BASE_LABEL[d.base]} 전용 무기입니다`;
  if (!craftMatOk(r)) return '재료가 모자랍니다';
  if (P.gold < r.cost) return '에테르가 모자랍니다';
  if (P.bag.length >= BAG_MAX) return '가방이 가득 찼습니다';
  return null;
}
function renderCraft() {
  const list = $('craftList'); list.innerHTML = '';
  document.querySelectorAll('#craftTabs button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.ct === craftTab)));
  for (const r of RECIPES) {
    const d = CRAFT_GEAR[r.item], mine = d.base === P.c.base;
    if (craftTab === 'mine' && !mine) continue;
    const why = craftBlock(r), row = document.createElement('div'); row.className = 'crow' + (mine ? '' : ' other');
    const ic = document.createElement('canvas'); ic.width = 40; ic.height = 40; row.append(ic); gradeFrame(ic, d.grade, d.icon, 0);
    const info = document.createElement('div');
    info.innerHTML = `<div class="cn g-${d.grade}">[${GRADE_LABEL[d.grade]}] ${d.name}</div><div class="cm">${BASE_LABEL[d.base]} 전용 · Lv ${d.lv} · 공격력 ${d.atk}${d.mp ? ` · MP +${d.mp}` : ''}</div><div class="cfx">${d.fx}</div>`;
    const mats = document.createElement('div'); mats.className = 'mats';
    for (const [id, n] of Object.entries(r.mats)) {
      const have = P.inv[id] || 0, sp = document.createElement('span'); sp.className = have >= n ? 'ok' : 'lack'; sp.title = `${itemName(id)} — ${XITEMS[id].src}`;
      const c = document.createElement('canvas'); c.width = 18; c.height = 18; sp.append(c); iconTo(c, id);
      sp.append(document.createTextNode(`${itemName(id)} ${have}/${n}`)); mats.append(sp);
    }
    info.append(mats);
    if (why) { const l = document.createElement('div'); l.className = 'lockr'; l.textContent = why; info.append(l); }
    row.append(info);
    const bx = document.createElement('div'); bx.className = 'cbtn';
    bx.innerHTML = `<span>${r.cost.toLocaleString()} 에테르</span><span>성공 ${DEV() ? 100 : r.ch}%</span>`;
    const b = document.createElement('button'); b.type = 'button'; b.textContent = '제작'; b.disabled = !!why; b.onclick = () => craftItem(r);
    bx.append(b); row.append(bx); list.append(row);
  }
  $('craftGold').textContent = `보유 ${P.gold.toLocaleString()} 에테르 · 실패하면 재료와 에테르가 모두 사라집니다`;
}
function craftItem(r) {
  if (!r || craftBlock(r)) return false;
  const d = CRAFT_GEAR[r.item];
  for (const [id, n] of Object.entries(r.mats)) P.inv[id] -= n;
  P.gold -= r.cost;
  const ok = Math.random() * 100 < (DEV() ? 100 : r.ch);
  if (ok) {
    const e = makeEquip(d.key, 0, { bias: 1.5 }); P.bag.push(e);
    log(`[${GRADE_LABEL[d.grade]}] ${d.name} 제작 성공!`, 'sys'); banner(`${d.name} 제작 성공`, d.fx); sfx('enchant_ok');
    vfx.push({ k: 'beam', x: P.x, y: P.y, t: 0, life: 1.0, col: GRADE_RGB[d.grade] });
    $('craftSay').textContent = '좋은 쇠다. 아껴 써라.';
  } else {
    log(`${d.name} 제작 실패 — 재료와 ${r.cost.toLocaleString()} 에테르가 사라졌습니다.`, 'bad'); sfx('enchant_fail'); shake = 4;
    $('craftSay').textContent = '…불길이 쇠를 삼켰군. 다시 모아 오게.';
  }
  renderCraft(); renderInv(); save();
  return ok;
}
function drawCraftNpc() {
  const cv = $('craftNpc'), c = cv.getContext('2d'), sm = META.npcs && META.npcs.npc_drogan; c.clearRect(0, 0, cv.width, cv.height); c.imageSmoothingEnabled = false;
  if (!sm) return; const im = img(sm.sheet); if (!im.complete) { im.addEventListener('load', drawCraftNpc, { once: true }); return; }
  c.drawImage(im, 0, 1 * sm.fh, sm.fw, sm.fh, (cv.width - sm.fw) / 2, 0, sm.fw, sm.fh);
}
function openCraft() {
  if (!running || !P || P.dead) return false;
  $('craft').classList.remove('hidden'); $('smithBtn').classList.add('hidden'); $('gatherBtn').classList.add('hidden');
  $('craftSay').textContent = SMITH_SAY[irnd(0, SMITH_SAY.length - 1)];
  drawCraftNpc(); renderCraft(); uiPauseCheck(); sfx('hit_blunt', { gain: 0.4 });
  return true;
}
function closeCraft() { $('craft').classList.add('hidden'); uiPauseCheck(); }
$('craftClose').addEventListener('click', closeCraft);
$('smithBtn').addEventListener('click', openCraft);
$('gatherBtn').addEventListener('click', () => startGather(nearNode()));
document.querySelectorAll('#craftTabs button').forEach(b => b.addEventListener('click', () => { craftTab = b.dataset.ct; renderCraft(); }));
// 제작 무기 특수 옵션: 장착한 무기의 값을 읽는다
const wSpec = k => { const e = P && P.eq && P.eq.weapon, d = e && equipDef(e.key); return d && d[k] ? d[k] : 0; };
const UNDEAD = new Set(['skeleton', 'skeleton_archer', 'boss', 'wb_lich']);""")
# 직업 전용 무기 착용 제한
rep("  if (!slotAllowed(slot)) { log(`${ITEM_LABEL[d.slot]}은(는) 기사만 착용할 수 있습니다.`, 'bad'); return false; }",
    "  if (!slotAllowed(slot)) { log(`${ITEM_LABEL[d.slot]}은(는) 기사만 착용할 수 있습니다.`, 'bad'); return false; }\n"
    "  if (d.base && d.base !== P.c.base) { log(`${d.name}은(는) ${BASE_LABEL[d.base]} 전용입니다.`, 'bad'); return false; }")
# 전투: 명중(빗나감) · 언데드 · 치명타 피해 · 화염 폭발 · 연쇄 · 재사용 대기 · MP 회복
rep("""  } else {
    dmg = Math.max(1, dmg - target.d.def);
    if (src && src.kind === 'player' && target.hp < target.maxhp * 0.25 && pxv('execute')) dmg *= 1 + pxv('execute') / 100;
  }""",
    """  } else {
    // 명중: 자기보다 레벨이 높은 몬스터일수록 빗나감(1레벨당 2%), 무기 명중 1당 2% 줄어듦. 같은 레벨 이하는 빗나가지 않음
    if (src && src.kind === 'player' && !opts.proc) {
      const miss = clamp(0.02 * (target.lv - P.lv) - 0.02 * wSpec('acc'), 0, 0.3);
      if (miss > 0 && Math.random() < miss) { texts.push({ who: target, x: target.x, y: target.y, z: 46, t: 0, s: 'MISS', c: '#c8c0b0' }); return 0; }
    }
    dmg = Math.max(1, dmg - target.d.def);
    if (src && src.kind === 'player' && target.hp < target.maxhp * 0.25 && pxv('execute')) dmg *= 1 + pxv('execute') / 100;
    if (src && src.kind === 'player' && UNDEAD.has(target.type)) dmg *= 1 + wSpec('undead');
  }""")
rep("  if (crit) { dmg *= 1.8; shake = Math.max(shake, 3); }", "  if (crit) { dmg *= 1.8 + (src && src.kind === 'player' ? wSpec('critDmg') : 0); shake = Math.max(shake, 3); }")
rep("""    if (target.hp <= 0) killMob(target);
    if (target.d.boss && target.phase === 0""",
    """    if (src && src.kind === 'player' && !opts.proc) {   // 제작 무기 발동 효과(발동으로 생긴 피해는 다시 발동하지 않음)
      if (wSpec('flame') && Math.random() < wSpec('flame')) {
        vfx.push({ k: 'death', x: target.x, y: target.y, t: 0, life: 0.6, big: true }); sfxAt(target, 'magic_hit', 0.6);
        texts.push({ who: target, x: target.x, y: target.y, z: 64, t: 0, s: '화염 폭발!', c: '#ff9a4a' });
        for (const o of mobs) if (!o.dead && o !== target && Math.hypot(o.x - target.x, o.y - target.y) < 2.2) damage(o, Math.round(dmg * 0.6), src, { proc: true, noKb: true });
      }
      if (wSpec('chain') && Math.random() < wSpec('chain')) {
        const o = mobs.filter(x => !x.dead && x !== target && Math.hypot(x.x - target.x, x.y - target.y) < 3.5).sort((a, b) => Math.hypot(a.x - target.x, a.y - target.y) - Math.hypot(b.x - target.x, b.y - target.y))[0];
        if (o) { vfx.push({ k: 'spark', x: o.x, y: o.y, t: 0, life: 0.25 }); damage(o, Math.round(dmg * 0.4), src, { proc: true, noKb: true }); }
      }
    }
    if (target.hp <= 0) killMob(target);
    if (target.d.boss && target.phase === 0""")
rep("  P.mp -= sk.mp; P.cds[id] = sk.cd;", "  P.mp -= sk.mp; P.cds[id] = sk.cd * (1 - wSpec('cdr'));")
rep("P.mp = Math.min(P.maxmp, P.mp + P.maxmp * 0.02 *", "P.mp = Math.min(P.maxmp, P.mp + P.maxmp * 0.02 * (1 + wSpec('mpRegen')) *")

# ───── 6. 강화 규칙 개편 ─────
rep("const encChance = (slot, lv) => DEV() ? 100 : lv < ENCHANT[slot].safe ? 100 : (ENCHANT[slot].chance[lv] || 0);",
    r"""// 에르덴 강화: 등급별 안전 구간(일반 +3 · 고급 +2 · 희귀 이상 +1)까지 100%.
// 그 뒤 +3까지는 90→82→75%이고 실패해도 단계 유지(강화석만 사라짐).
// +4부터는 실패하면 위험: +4~+6은 50% 소멸 · 50% +0 초기화, +7 이상은 소멸.
const ENC_SAFE = { common: 3, uncommon: 2, rare: 1, heroic: 1, legend: 1, unique: 1 };
const ENC_LOW = [90, 82, 75];                          // 목표 +1·+2·+3
const ENC_HIGH = { 3: 60, 4: 50, 5: 40, 6: 30, 7: 22, 8: 15, 9: 10 };   // 현재 단계 → 성공 확률
const encChance = (slot, lv, grade = 'common') => DEV() ? 100 : lv < (ENC_SAFE[grade] || 1) ? 100 : lv < 3 ? ENC_LOW[lv] : (ENC_HIGH[lv] || 0);
// 실패하면 일어나는 일: 'keep' 단계 유지 · 'risk' 소멸 50%/초기화 50% · 'break' 소멸
const encFail = (lv, grade = 'common') => lv < (ENC_SAFE[grade] || 1) ? 'none' : lv < 3 ? 'keep' : lv < 6 ? 'risk' : 'break';
const ENC_FAIL_TXT = { none: '안전', keep: '단계 유지', risk: '소멸 50% · +0 50%', break: '장비 소멸' };
// 쓰는 강화석: 희귀 이상은 정제된 별의 파편, 그 밑은 별빛 강화석(무기/방어구)
const encStone = (kind, grade) => GRADES.indexOf(grade) >= 2 ? 'star_shard' : kind === 'weapon' ? 'scroll_weapon' : 'scroll_armor';""")
rep("""function enchantItem(e) {
  const d = equipDef(e.key), kind = SLOT_KIND[d.slot];
  if (kind === 'acc') return false;
  const key = kind === 'weapon' ? 'scroll_weapon' : 'scroll_armor';
  if (!(P.inv[key] > 0) || e.enc >= 10) return false;
  P.inv[key]--;
  const ch = encChance(kind, e.enc), from = e.enc;
  const name = d.name, word = kind === 'weapon' ? '공격력' : '방어력';
  const before = statAt(e, from);
  const ok = Math.random() * 100 < ch;
  if (ok) {
    e.enc++;""",
    """// blessed = 축복받은 강화석: 일반 강화석 대신 써서 실패해도 소멸·초기화가 없고, 성공하면 30%로 +2, 10%로 +3
function enchantItem(e, blessed) {
  const d = equipDef(e.key), kind = SLOT_KIND[d.slot];
  if (kind === 'acc') return false;
  const key = blessed ? 'blessed_stone' : encStone(kind, d.grade);
  if (!(P.inv[key] > 0) || e.enc >= 10) return false;
  P.inv[key]--;
  const ch = encChance(kind, e.enc, d.grade), from = e.enc;
  const name = d.name, word = kind === 'weapon' ? '공격력' : '방어력';
  const before = statAt(e, from);
  const ok = Math.random() * 100 < ch;
  if (ok) {
    const jump = blessed ? (Math.random() < 0.1 ? 3 : Math.random() < 0.3 ? 2 : 1) : 1;
    e.enc = Math.min(10, e.enc + jump);
    if (jump > 1) { banner('대성공!', `축복의 빛 · +${from} → +${e.enc}`); texts.push({ who: P, x: P.x, y: P.y, z: 74, t: 0, s: '대성공!', c: '#fff0a0', big: true }); }""")
rep("""  } else {
    e.enc = 0;
    log(`${name} 강화 실패 (${ch}%) — +${from} → +0`, 'bad');
    encAnim(d, false, `강화 실패 · +${from} → +0`, '#ff8a7a', () => { sfx('enchant_fail'); shake = 4; });
  }""",
    """  } else {
    const fail = blessed ? 'keep' : encFail(from, d.grade);
    const broke = fail === 'break' || (fail === 'risk' && Math.random() < 0.5);
    if (broke) {
      destroyItem(e);
      log(`${name} 강화 실패 (${ch}%) — 장비가 빛을 잃고 부서져 사라졌습니다.`, 'bad');
      encAnim(d, false, `강화 실패 · +${from} ${name} 소멸`, '#ff5a4a', () => { sfx('enchant_fail'); shake = 7; });
      renderInv(); save(); return false;
    }
    if (fail === 'keep') {
      log(`${name} 강화 실패 (${ch}%) — +${from} 그대로${blessed ? ' (축복이 장비를 지켰습니다)' : ''}`, 'bad');
      encAnim(d, false, `강화 실패 · +${from} 유지`, '#ffb07a', () => { sfx('enchant_fail'); shake = 2; });
    } else {
      e.enc = 0;
      log(`${name} 강화 실패 (${ch}%) — +${from} → +0`, 'bad');
      encAnim(d, false, `강화 실패 · +${from} → +0`, '#ff8a7a', () => { sfx('enchant_fail'); shake = 4; });
    }
  }""")
rep("function enchant(kind) { return enchantItem(kind === 'w' ? P.weapon : P.armor); }",
    """function enchant(kind) { return enchantItem(kind === 'w' ? P.weapon : P.armor); }
// 강화 실패로 장비가 사라짐. 무기가 사라지면 직업 기본 무기(+0)를 대신 쥔다(무기 칸은 비울 수 없음)
function destroyItem(e) {
  const bi = P.bag.findIndex(x => x.uid === e.uid); if (bi >= 0) P.bag.splice(bi, 1);
  for (const [slot, v] of Object.entries(P.eq)) if (v && v.uid === e.uid) {
    P.eq[slot] = null;
    if (slot === 'weapon') { P.eq.weapon = makeEquip(START_EQUIP[P.c.base][0], 0, { mid: true }); log(`기본 무기 ${equipDef(P.eq.weapon.key).name}을(를) 대신 쥐었습니다.`, 'sys'); }
  }
  selUid = null; applyStats();
}""")
# 가방 상세 창: 등급별 강화석·확률·실패 결과 + 축복 강화 버튼
rep("  const scroll = kind === 'weapon' ? 'scroll_weapon' : kind === 'armor' ? 'scroll_armor' : null, have = scroll ? (P.inv[scroll] || 0) : 0;\n  const ch = scroll && sel.enc < 10 ? encChance(kind, sel.enc) : 0;",
    "  const scroll = kind === 'weapon' || kind === 'armor' ? encStone(kind, d.grade) : null, have = scroll ? (P.inv[scroll] || 0) : 0;\n  const ch = scroll && sel.enc < 10 ? encChance(kind, sel.enc, d.grade) : 0, failTxt = scroll && sel.enc < 10 ? ENC_FAIL_TXT[encFail(sel.enc, d.grade)] : '';\n  const bless = P.inv.blessed_stone || 0;")
rep("      ${scroll ? `<button type=\"button\" id=\"btnEnc\" ${(!have || sel.enc >= 10) ? 'disabled' : ''}>강화 ${sel.enc < 10 ? ch + '%' : ''}</button>` : ''}",
    "      ${scroll ? `<button type=\"button\" id=\"btnEnc\" title=\"${itemName(scroll)} ${have}개 · 실패 시 ${failTxt}\" ${(!have || sel.enc >= 10) ? 'disabled' : ''}>강화 ${sel.enc < 10 ? ch + '%' : ''}</button>` : ''}\n"
    "      ${scroll && bless ? `<button type=\"button\" id=\"btnEncB\" title=\"축복받은 강화석 ${bless}개 · 실패해도 소멸·초기화 없음, 대성공 가능\" ${sel.enc >= 10 ? 'disabled' : ''}>축복 강화</button>` : ''}")
rep("  const bn = $('btnEnc'); if (bn) bn.onclick = () => enchantItem(sel);",
    "  const bn = $('btnEnc'); if (bn) bn.onclick = () => enchantItem(sel);\n  const bb = $('btnEncB'); if (bb) bb.onclick = () => enchantItem(sel, true);")
open(P, 'w', encoding='utf-8').write(t)
print('적용 완료')
