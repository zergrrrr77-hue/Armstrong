"""에르덴 플레이어 외형 4단계 — 입은 갑옷 등급에 따라 캐릭터 시트를 바꿔 쓴다.
  단계 1: 일반·고급   단계 2: 희귀   단계 3: 영웅   단계 4: 전설·고대
뼈대·동작은 humanoid의 기사(blade)와 같으므로 스킬 동작 시트도 그대로 구울 수 있다.
시험 렌더: python3 forgotten-forge/tools/lineage/tier_preview.py 출력폴더 knight
"""
import math

import numpy as np

import sdf as S
import humanoid as Hm
from sdf import V, Item, Mat

TIER_GRADES = {1: ('common', 'uncommon'), 2: ('rare',), 3: ('heroic',), 4: ('legend', 'unique')}
TIER_NAMES = {1: '견습 기사', 2: '아르델 기사단', 3: '왕실 기사', 4: '별의 기사'}


# ───────────────────────── 공용 재질 ─────────────────────────

def _mats():
    m = dict(Hm.M_COMMON)
    m.update({
        'skin': Mat(['#4e3428', '#80583f', '#aa7c5e', '#c99a78', '#e0b896']),
        'hair': Mat(['#120c08', '#20160f', '#302116', '#402c1e', '#523a28']),
        # 단계 1: 누빔 갑옷(갬비슨)·녹슨 쇠·참나무
        'gambeson': Mat(['#2a2014', '#40321f', '#5a482c', '#74603c', '#8e7a50'],
                        tex=lambda P, n: 0.5 * (np.floor(P[:, 2] * 0.55) % 2 - 0.5)),          # 가로 누빔 줄
        'rust': Mat(['#2a1810', '#45281a', '#643c24', '#7e5232', '#946a46'], metal=True, hi='#c09070',
                    tex=lambda P, n: 0.5 * S.vnoise(P * 1.8, 11)),
        'oak': Mat(['#2a1a0c', '#422a14', '#5e3e1e', '#7a542a', '#946a38'],
                   tex=lambda P, n: 0.35 * np.sin(P[:, 0] * 3.0 + P[:, 2] * 0.4)),
        'mail': Mat(['#1d2026', '#30343c', '#474c56', '#626874', '#7d8491'], metal=True,
                    tex=lambda P, n: 0.6 * ((np.floor(P[:, 2] * 0.9) + np.floor(P[:, 0] * 0.9)) % 2 - 0.5)),
        # 단계 1 (수정): 깔끔한 견습생 — 흰 리넨 셔츠, 갈색 가죽 조끼, 짙은 녹색 바지, 단정한 강철 부품
        'linen': Mat(['#4e4a40', '#7a7466', '#a8a08e', '#cec6b2', '#ece6d4']),
        'jerkin': Mat(['#24140a', '#3c2412', '#56361c', '#704826', '#8c5c32'], gloss=0.25),
        'pants': Mat(['#10160e', '#1a2418', '#263424', '#344632', '#445a40']),
        'recruit': Mat(['#1c2840', '#2a3a5c', '#3c5280', '#5470a4', '#7090c4']),   # 견습 표식 천(옅은 청)
        # 단계 2: 아르델 기사단 청회색
        'ardel': Mat(['#0e1622', '#18243a', '#243652', '#324a6c', '#445f88']),
        # 단계 3: 왕실 진홍 + 광택 강철
        'polish': Mat(['#1c2028', '#363c48', '#5a6270', '#8c95a4', '#c4ccd8'], metal=True, hi='#ffffff'),
        'crimson': Mat(['#2c0607', '#4a0c0e', '#6c1416', '#8f1f1f', '#b0302a']),
        # 단계 4: 별의 기사 — 어두운 은 + 금 + 별빛
        'starsteel': Mat(['#161a28', '#283046', '#3e4a66', '#5e6c8c', '#8a98b8'], metal=True, hi='#f0f6ff'),
        'night': Mat(['#04060e', '#080c1c', '#10162e', '#1a2244', '#26305c'],
                     tex=lambda P, n: 0.5 * (S.vnoise(P * 2.4, 13) > 0.62)),                   # 별가루 무늬
        'starlight': Mat(['#2a4a8a', '#4a78c8', '#7aa8f0', '#b8d4ff', '#f4f8ff'], emit=True),
    })
    return m


# ───────────────────────── 조각 ─────────────────────────

def coif(r, mat):
    """사슬 두건: 머리·목을 감싸고 얼굴만 드러냄."""
    s = r.s
    H, HR = r.head, r.head_rot
    hr = r.b['head_r'] * s
    outer = S.ellipsoid(H + HR @ V(0, -0.4 * s, 0.3 * s), V(hr * 1.12, hr * 1.15, hr * 1.12), HR)
    face = S.ellipsoid(H + HR @ V(0, hr * 0.85, -0.6 * s), V(hr * 0.8, hr * 0.9, hr * 0.92), HR)   # 얼굴이 보이게 넓게 트임
    return [Item(S.sub(outer, face), mat),
            Item(S.capsule(r.neck - r.up * 2.4 * s, r.neck - r.up * 0.6 * s, 4.6 * s, 3.8 * s), mat)]   # 목·어깨 덮개(턱은 드러냄)


def open_helm(r, steel, trim, plume=None, wings=None):
    """얼굴이 트인 투구(코가리개) + 선택: 깃털, 날개 장식."""
    s = r.s
    H, HR = r.head, r.head_rot
    hr = r.b['head_r'] * s
    dome = S.ellipsoid(H + HR @ V(0, -0.2 * s, 0.5 * s), V(hr * 1.1, hr * 1.14, hr * 1.12), HR)
    face = S.ellipsoid(H + HR @ V(0, hr * 0.9, -1.0 * s), V(hr * 0.74, hr * 0.85, hr * 0.85), HR)
    it = [Item(S.sub(dome, face), steel),
          Item(S.box(H + HR @ V(0, hr * 1.06, -0.2 * s), V(0.45 * s, 0.5 * s, 2.0 * s), HR, 0.1), trim),   # 코가리개
          Item(S.torus(H + HR @ V(0, -0.3 * s, hr * 0.62), HR, hr * 1.02, 0.5 * s), trim)]               # 이마 위 테두리 띠
    if plume:
        it.append(Item(S.capsule(H + HR @ V(0, 0.6 * s, hr * 1.1), H + HR @ V(0, -hr * 1.8, hr * 0.4), 1.4 * s, 0.8 * s), plume))
    if wings:
        for sx in (-1, 1):
            for k in range(3):
                b0 = H + HR @ V(sx * hr * 1.05, -0.4 * s - k * 0.9 * s, hr * 0.5 + k * 0.6 * s)
                it.append(Item(S.capsule(b0, b0 + HR @ V(sx * (2.4 - k * 0.4) * s, -1.6 * s, (3.6 - k * 0.8) * s), (0.7 - k * 0.12) * s, 0.15 * s), wings))
    return it


def star_gem(r, c, mat, size=1.0):
    """네 갈래 별 모양 보석(앞을 향함)."""
    s = r.s
    M = r.rot
    return [Item(S.box(c, V(0.45 * s * size, 0.4 * s, 1.8 * s * size), M, 0.1), mat),
            Item(S.box(c, V(1.8 * s * size, 0.4 * s, 0.45 * s * size), M, 0.1), mat),
            Item(S.sphere(c + r.fwd * 0.2 * s, 0.8 * s * size), mat)]


def tabard(r, mat, wide=4.4, down=8.0):
    s = r.s
    top = r.chest + r.fwd * 4.7 * s + r.up * 2.6 * s
    bot = r.hip + r.fwd * 4.7 * s - r.up * down * s
    return [Item(S.box((top + bot) / 2, V(wide * s, 0.7 * s, np.linalg.norm(top - bot) / 2), r.rot, 0.5 * s), mat)]


def rune_sword(r, length=21, blade='starsteel', glow='starlight', guard='gold'):
    """별의 기사의 검: 넓은 칼날 가운데 빛나는 홈, 별 모양 코등이."""
    s = r.s
    h, w = r.rha, r.wdir
    M = S.frame_from(w, r.right)
    base = h + w * 2.6 * s
    tip = base + w * length * s
    body = S.box((base + tip) / 2, V(2.1 * s, 0.5 * s, length * s / 2), M, 0.15)
    body = S.inter(body, S.halfspace(S.nrm(w + M[:, 0] * 0.5), np.dot(S.nrm(w + M[:, 0] * 0.5), tip - M[:, 0] * 1.4 * s)),
                   S.halfspace(S.nrm(w - M[:, 0] * 0.5), np.dot(S.nrm(w - M[:, 0] * 0.5), tip + M[:, 0] * 1.4 * s)))
    it = [Item(body, blade, 'blade'),
          Item(S.box(base + w * length * s * 0.42, V(0.45 * s, 0.6 * s, length * s * 0.36), M, 0.1), glow, 'blade')]
    gc = h + w * 2.2 * s
    it.append(Item(S.box(gc, V(4.4 * s, 0.9 * s, 0.9 * s), M, 0.3), guard))
    it.append(Item(S.sphere(gc, 1.2 * s), glow))
    it.append(Item(S.capsule(h - w * 2.2 * s, h + w * 1.6 * s, 0.9 * s), 'leather'))
    it.append(Item(S.sphere(h - w * 2.9 * s, 1.1 * s), guard))
    return it


# ───────────────────────── 기사 4단계 ─────────────────────────

def _knight(tier):
    m = _mats()
    if tier == 1:
        parts = dict(skin='skin', hair='hair', eyes='eyes', torso='linen', pelvis='jerkin', legs='pants', shin='leather',
                     boots='leather', arms='linen', farm='leather', hands='leather')
    elif tier == 2:
        parts = dict(skin='skin', hair='hair', eyes='eyes', torso='steel', pelvis='mail', legs='mail', shin='steel',
                     boots='steel_dk', arms='mail', farm='steel', hands='steel_dk')
    elif tier == 3:
        parts = dict(skin='skin', hair='hair', eyes='eyes', torso='polish', pelvis='polish', legs='mail', shin='polish',
                     boots='polish', arms='polish', farm='polish', hands='steel_dk')
    else:
        parts = dict(skin='skin', hair='hair', eyes='eyes', torso='starsteel', pelvis='starsteel', legs='starsteel',
                     shin='starsteel', boots='starsteel', arms='starsteel', farm='starsteel', hands='starsteel')

    def gear(r, p, it):
        s = r.s
        R = r.rot
        if tier == 1:
            # 견습 기사(수정): 맨머리의 단정한 신참 — 가죽 조끼 + 한쪽 강철 어깨 + 강철 팔목 + 청색 견습 띠
            H, HR = r.head, r.head_rot
            for ox, oz, ln in ((-2.4, 3.4, 2.2), (-0.4, 3.9, 2.6), (1.6, 3.5, 2.2)):        # 짧게 정리한 앞머리
                a0 = H + HR @ V(ox * s, 2.0 * s, oz * s)
                it.append(Item(S.capsule(a0, a0 + HR @ V(ox * 0.2 * s, 1.4 * s, -ln * s), 1.0 * s, 0.45 * s), 'hair'))
            it.append(Item(S.ellipsoid(H + HR @ V(0, -1.2 * s, 0.4 * s), V(4.5 * s, 3.8 * s, 3.9 * s), HR), 'hair'))
            it.append(Item(S.ellipsoid(r.chest + R @ V(0, 0.4 * s, 0.4 * s), V(7.7 * s, 5.2 * s, 6.1 * s), R), 'jerkin'))   # 가죽 조끼(셔츠보다 크게 → 소매만 흰색)
            it.append(Item(S.box(r.chest + r.fwd * 4.6 * s, V(0.35 * s, 0.4 * s, 4.2 * s), R, 0.1), 'iron'))              # 조끼 여밈
            it += Hm.skirt(r, 'jerkin', 5.2, 6.2, 7.0)
            it.append(Item(S.box(r.waist + r.up * 0.4 * s, V(5.4 * s, 4.4 * s, 0.9 * s), R, 0.4), 'leather'))
            it.append(Item(S.box(r.waist + r.up * 0.4 * s + r.fwd * 4.3 * s, V(1.0 * s, 0.4 * s, 0.9 * s), R, 0.2), 'steel'))
            # 왼쪽 어깨에만 강철 견갑 + 오른쪽 어깨엔 청색 견습 띠
            c = r.lsh + r.up * 0.8 * s - r.right * 0.8 * s
            it.append(Item(S.ellipsoid(c, V(3.5 * s, 3.7 * s, 2.8 * s), R), 'steel'))
            it.append(Item(S.ellipsoid(c - r.up * 1.4 * s, V(3.7 * s, 3.9 * s, 0.6 * s), R), 'steel_dk'))
            it.append(Item(S.capsule(r.rsh + r.up * 0.6 * s, r.waist - r.right * 3.0 * s + r.fwd * 4.6 * s, 0.9 * s), 'recruit'))
            for el, ha in ((r.lel, r.lha), (r.rel, r.rha)):                                   # 강철 팔목 보호대
                it.append(Item(S.capsule(el + (ha - el) * 0.3, ha - (ha - el) * 0.15, 2.0 * s, 1.8 * s), 'steel'))
            it += Hm.sword(r, ['rust'], length=19, width=1.3, guard='iron', grip='leather', blade='steel', pommel='iron')
            it += Hm.round_shield(r, 'oak', 'steel', 'steel', size=5.0)
        elif tier == 2:
            # 아르델 기사단: 사슬 + 흉갑 + 청회색 서코트·반망토 + 강철 연 방패(기사단 문장)
            it += coif(r, 'mail')
            it += Hm.pauldrons(r, 'steel', 3.5, trim='ardel')
            it += tabard(r, 'ardel', 4.2, 8.0)
            it += Hm.cape(r, p, 'ardel', length=20, width=6.0)
            it += Hm.skirt(r, 'mail', 5.4, 6.6, 9.0)
            it.append(Item(S.box(r.waist + r.up * 0.4 * s, V(5.4 * s, 4.4 * s, 0.9 * s), R, 0.4), 'leather'))
            it += Hm.broadsword(r, 17.5, 1.9, guard='steel_dk', grip='leather', blade='steel', pommel='steel_dk')
            it += Hm.shield_kite(r, 'steel', 'steel_dk', 'steel_dk', 0.9, emblem='ardel')
        elif tier == 3:
            # 왕실 기사: 광택 판금 + 깃털 투구 + 금테 + 진홍 망토 + 금테 연 방패(왕관 문장)
            it += open_helm(r, 'polish', 'gold', plume='crimson')
            it += Hm.pauldrons(r, 'polish', 4.0, trim='gold')
            it += Hm.cape(r, p, 'crimson', length=30, width=7.0, split=True)
            it += Hm.skirt(r, 'polish', 5.6, 6.8, 9.0)
            it += tabard(r, 'crimson', 3.4, 9.0)
            it.append(Item(S.box(r.chest + r.fwd * 4.6 * s + r.up * 0.6 * s, V(4.6 * s, 0.35 * s, 0.45 * s), R, 0.1), 'gold'))
            it.append(Item(S.box(r.waist + r.up * 0.4 * s, V(5.6 * s, 4.6 * s, 1.0 * s), R, 0.4), 'g_dark'))
            it += Hm.broadsword(r, 19.0, 2.1, guard='gold', grip='crimson', blade='polish', pommel='gold')
            it += Hm.shield_kite(r, 'crimson', 'gold', 'gold', 1.0, emblem='gold')
        else:
            # 별의 기사: 어두운 은빛 판금 + 금 테 + 별빛 장식 + 날개 투구 + 별가루 망토 + 빛나는 별검 + 별 방패
            it += open_helm(r, 'starsteel', 'gold', wings='gold')
            it.append(Item(S.sphere(r.head + r.head_rot @ V(0, r.b['head_r'] * s * 1.05, 2.6 * s), 0.9 * s), 'starlight'))
            it += Hm.pauldrons(r, 'starsteel', 4.3, trim='gold')
            for sh, sx in ((r.lsh, -1), (r.rsh, 1)):                                         # 어깨의 별빛 결정
                it.append(Item(S.capsule(sh + r.up * 2.6 * s, sh + r.up * 5.2 * s + r.right * sx * 1.6 * s, 0.9 * s, 0.1 * s), 'starlight'))
            it += Hm.cape(r, p, 'night', length=33, width=7.4, split=True)
            it += Hm.skirt(r, 'starsteel', 5.8, 7.2, 9.5)
            it.append(Item(S.box(r.waist + r.up * 0.4 * s, V(5.8 * s, 4.8 * s, 1.0 * s), R, 0.4), 'gold'))
            it += star_gem(r, r.chest + r.fwd * 5.2 * s + r.up * 0.6 * s, 'starlight', 1.6)
            for j in (r.lkn, r.rkn, r.lel, r.rel):                                            # 관절의 별빛 보석
                it.append(Item(S.sphere(j + r.fwd * 1.6 * s, 0.9 * s), 'starlight'))
            it.append(Item(S.box(r.chest + r.fwd * 4.8 * s + r.up * 3.4 * s, V(5.0 * s, 0.35 * s, 0.45 * s), R, 0.1), 'gold'))
            it += rune_sword(r)
            it += Hm.shield_kite(r, 'night', 'gold', 'starlight', 1.05, emblem='starlight')

    return dict(name=f'knight_t{tier}', label=f'기사 · {TIER_NAMES[tier]}', mats=m, parts=parts, gear=gear, weapon='blade',
                build=dict(scale=1.0 + 0.02 * (tier - 1)),
                opts=dict(hair=True, eyes=True, limb=1.08 + 0.03 * tier, chest=(6.8 + 0.2 * tier, 4.4 + 0.1 * tier, 5.8 + 0.1 * tier),
                          belly=(4.8 + 0.1 * tier, 5.6 + 0.1 * tier)))


# ───────────────────────── 외형 단계 정하기 (게임 코드가 따를 규칙) ─────────────────────────
# 등급 점수: 일반 1 · 고급 2 · 희귀 3 · 영웅 4 · 전설 5 · 고대(unique) 6
# 외형 점수 = (갑옷 × 3 + 투구 + 망토 + 장갑 + 장화 [+ 방패: 기사만]) ÷ (8, 방패 없는 직업은 7)
# 빈 칸은 0점. 2.5 미만 → 1단계, 3.5 미만 → 2단계, 4.5 미만 → 3단계, 그 이상 → 4단계
GRADE_SCORE = {'common': 1, 'uncommon': 2, 'rare': 3, 'heroic': 4, 'legend': 5, 'unique': 6}
LOOK_SLOTS = ('helm', 'cloak', 'gloves', 'boots')
TIER_CUTS = (2.5, 3.5, 4.5)


def look_tier(equip, has_shield):
    """equip: {칸 이름: 등급 id}. 게임(JS)에서 같은 계산을 쓰도록 여기에 기준을 남겨 둔다."""
    total = GRADE_SCORE.get(equip.get('armor'), 0) * 3 + sum(GRADE_SCORE.get(equip.get(k), 0) for k in LOOK_SLOTS)
    n = 8 if has_shield else 7
    if has_shield:
        total += GRADE_SCORE.get(equip.get('shield'), 0)
    score = total / n
    return 1 + sum(score >= c for c in TIER_CUTS)


# ───────────────────────── 요정 4단계 ─────────────────────────

ELF_NAMES = {1: '숲의 견습 궁수', 2: '엘라시아 순찰자', 3: '정령 궁수', 4: '별빛 정령'}


def _elf(tier):
    m = _mats()
    m.update({
        'skin': Mat(['#5e443a', '#93705e', '#c09c86', '#ddc1ab', '#f2dfcd']),
        'blond': Mat(['#5a4214', '#8a6a24', '#b8923a', '#dcba5a', '#f2dc8a']),
        'silverh': Mat(['#6a7072', '#9aa2a4', '#c4ccce', '#e2e8e8', '#f6fafa']),
        'moss': Mat(['#141e0c', '#223216', '#324a20', '#44622a', '#5a7c38']),
        'tunic1': Mat(['#1a2a12', '#2a421c', '#3c5a28', '#507434', '#688e44']),
        'leafarmor': Mat(['#0f1e0c', '#1c3414', '#2c4e1c', '#3f6a26', '#588a34'], gloss=0.3),
        'leaf2': Mat(['#1c2e0c', '#2f4a14', '#48681e', '#64882a', '#86aa3a']),
        'spirit': Mat(['#0c2a22', '#164a3a', '#226a52', '#3a9070', '#68b894'], gloss=0.4),
        'whiteleaf': Mat(['#4a5a5a', '#748886', '#a0b4b0', '#cadcd6', '#f0faf6'], gloss=0.5),
        'bowwood': Mat(['#3a2410', '#5a3a18', '#7e5424', '#a27032', '#c08c44'], gloss=0.4),
        'fletch': Mat(['#2a4a14', '#3e6a1c', '#58902a', '#7ab43c', '#a6d860']),
        'gem': Mat(['#0a3a20', '#146038', '#1e8c50', '#40c078', '#a8f0c8'], gloss=1.0, emit=True),
        'glowstring': Mat(['#4a78c8', '#7aa8f0', '#b8d4ff', '#e4f0ff', '#ffffff'], emit=True),
    })
    hair = 'silverh' if tier == 4 else 'blond'
    armor = {1: 'tunic1', 2: 'leafarmor', 3: 'spirit', 4: 'whiteleaf'}[tier]
    accent = {1: 'leather', 2: 'leaf2', 3: 'gold', 4: 'gold'}[tier]
    parts = dict(skin='skin', hair=hair, eyes='eyes', torso=armor, pelvis=armor, legs='moss' if tier == 1 else 'skin',
                 shin='leather' if tier == 1 else armor, boots='leather' if tier == 1 else armor,
                 arms='linen' if tier == 1 else 'skin', farm='leather' if tier == 1 else armor, hands='leather')

    def gear(r, p, it):
        s = r.s
        R = r.rot
        H, HR = r.head, r.head_rot
        it += Hm.long_hair(r, hair, length=12 + tier * 2, width=4.2, flow=p.cape * 1.2)
        # 흉갑: 1단계는 천 튜닉 + 가죽 끈, 2단계부터 잎 흉갑
        it.append(Item(S.ellipsoid(r.chest + R @ V(0, 1.2 * s, 1.2 * s), V(6.0 * s, 4.0 * s, 3.6 * s), R), armor))
        if tier == 1:
            it.append(Item(S.capsule(r.lsh + r.up * 0.4 * s, r.waist + r.right * 3.0 * s + r.fwd * 4.2 * s, 0.7 * s), 'leather'))
        else:
            for sx in (-1, 1):
                it.append(Hm.leaf(r.chest + R @ V(sx * 2.6 * s, 4.4 * s, 1.0 * s), R @ V(sx * 0.4, 0, 1), R @ V(0, 1, 0), 3.2 * s, 2.0 * s, accent if tier >= 3 else 'leaf2'))
            for sh, sx in ((r.lsh, -1), (r.rsh, 1)):                                          # 잎 어깨
                for k in range(2 + tier // 2):
                    it.append(Hm.leaf(sh + r.up * (1.2 - k * 0.6) * s + r.right * sx * (0.6 + k * 0.9) * s,
                                      r.right * sx * 0.8 - r.up * 0.6, r.up + r.right * sx * 0.5, 2.6 * s, 1.4 * s, armor if k % 2 else accent))
        # 허리띠 + 잎 치마
        it.append(Item(S.box(r.waist + r.up * 0.2 * s, V(5.2 * s, 4.0 * s, 0.8 * s), R, 0.4), 'leather'))
        if tier == 1:
            it += Hm.skirt(r, 'tunic1', 5.0, 6.0, 7.5)                                          # 견습생: 잎 대신 천 치마
        else:
            for k in range(8):
                a = math.radians(k * 45 + 22)
                d = R @ V(math.cos(a), math.sin(a), 0)
                c = r.hip + d * 5.2 * s - r.up * 2.4 * s
                it.append(Hm.leaf(c, -r.up + d * 0.35, d, (4.0 + tier * 0.4) * s, 2.0 * s, armor if k % 2 else (accent if tier >= 3 else 'leaf2')))
        # 머리 장식: 2단계 잎 하나, 3단계 금 이마띠 + 보석, 4단계 별빛 보석 관
        if tier >= 2:
            it.append(Hm.leaf(H + HR @ V(-3.8 * s, 0.0, 3.0 * s), HR @ V(0, -0.6, 1), HR @ V(-1, 0, 0), 2.6 * s, 1.0 * s, 'leaf2'))
        if tier >= 3:
            it.append(Item(S.torus(H + HR @ V(0, 0.2 * s, 1.6 * s), HR, 4.7 * s, 0.45 * s), 'gold'))
            it.append(Item(S.sphere(H + HR @ V(0, 4.6 * s, 1.8 * s), 0.9 * s), 'gem' if tier == 3 else 'starlight'))
        if tier == 4:
            for sx in (-1, 1):
                it.append(Item(S.capsule(H + HR @ V(sx * 2.0 * s, 3.6 * s, 2.4 * s), H + HR @ V(sx * 3.4 * s, 1.2 * s, 6.0 * s), 0.5 * s, 0.1 * s), 'starlight'))
        # 망토: 1단계 짧은 천, 2 숲색 두건 망토, 3 길게, 4 별가루 밤하늘
        cape_mat = {1: 'moss', 2: 'leafarmor', 3: 'spirit', 4: 'night'}[tier]
        it += Hm.cape(r, p, cape_mat, length={1: 14, 2: 20, 3: 26, 4: 30}[tier], width=4.6 + tier * 0.3, split=tier >= 3)
        if tier == 2:
            it += Hm.hood(r, 'leafarmor', peak=True)                                              # 두건을 쓴 순찰자
        if tier == 4:                                                                          # 떠도는 빛의 잎
            for k in range(3):
                a = math.radians(k * 120 + 40)
                c = r.chest + (r.right * math.cos(a) + r.fwd * math.sin(a)) * 9.0 * s + r.up * (2 - k * 3) * s
                it.append(Hm.leaf(c, r.up, r.fwd, 1.8 * s, 0.8 * s, 'starlight'))
        it += Hm.quiver(r, 'leather', 'fletch' if tier < 4 else 'starlight')
        it += Hm.bow(r, 'bowwood' if tier < 3 else ('gold' if tier == 3 else 'whiteleaf'), 'string' if tier < 4 else 'glowstring', draw=p.draw)
        if p.draw > 0.3:
            c = r.lha
            hand = c - r.fwd * (2 + p.draw * 9) * s
            it.append(Item(S.capsule(hand, c + r.fwd * 4 * s, 0.55 * s), 'starlight' if tier == 4 else 'fletch'))

    return dict(name=f'elf_t{tier}', label=f'요정 · {ELF_NAMES[tier]}', mats=m, parts=parts, gear=gear, weapon='bow',
                build=dict(scale=0.96, sh_w=5.8, hip_w=3.2),
                opts=dict(ears=True, limb=0.86, chest=(5.6, 3.7, 5.0), belly=(3.9, 4.6), pelvis=(4.9, 3.5, 3.9)))


# ───────────────────────── 마법사 4단계 ─────────────────────────

MAGE_NAMES = {1: '견습 마법사', 2: '연구소 마법사', 3: '궁정 마법사', 4: '별의 현자'}


def _mage(tier):
    m = _mats()
    m.update({
        'skin': Mat(['#5e443a', '#93705e', '#c09c86', '#ddc1ab', '#f2dfcd']),
        'whiteh': Mat(['#5e6070', '#8a8c9c', '#b2b4c2', '#d2d4de', '#eceef4']),
        'brownh': Mat(['#2a160a', '#442410', '#60361a', '#7c4a24', '#985e30']),
        'wool': Mat(['#2a2620', '#423c32', '#5e5646', '#7a705c', '#948a74']),             # 1단계 회갈색 양모 로브
        'blue': Mat(['#0a1030', '#121c50', '#1c2c78', '#2a40a0', '#3c58c4']),
        'white': Mat(['#4e5262', '#7a7e8e', '#a6aab8', '#cdd0da', '#eceef4']),
        'royal': Mat(['#160828', '#240e42', '#36165e', '#4a227c', '#62309c']),           # 3단계 궁정 보라
        'orb_b': Mat(['#2a5fcf', '#4f8bf0', '#7cb3ff', '#b5d8ff', '#eef8ff'], emit=True),
        'orb_g': Mat(['#5a2a06', '#a04a0a', '#e08a18', '#f8c040', '#fff0a0'], emit=True),
        'crystal1': Mat(['#2a4a5a', '#4a7486', '#74a0b2', '#a4cad8', '#dcf2fa'], emit=True),
        'midnight': Mat(['#0a0e22', '#141c3c', '#20305e', '#304680', '#4460a4'],
                        tex=lambda P, n: 0.6 * (S.vnoise(P * 2.4, 13) > 0.66)),          # 별가루가 박힌 밤하늘 로브
        'rope': Mat(['#3a2c18', '#5a4426', '#7a5e36', '#9a7a48', '#b8965c']),
    })
    hair = 'brownh' if tier == 1 else 'whiteh'
    robe = {1: 'wool', 2: 'blue', 3: 'royal', 4: 'midnight'}[tier]
    trim = {1: 'rope', 2: 'white', 3: 'gold', 4: 'gold'}[tier]
    parts = dict(skin='skin', hair=hair, eyes='eyes', torso=robe, pelvis=robe, legs=robe, shin=robe,
                 boots='leather', arms=robe, farm=robe, hands='skin')

    def gear(r, p, it):
        s = r.s
        R = r.rot
        it += Hm.long_hair(r, hair, length=10 + tier * 3, width=4.4, flow=p.cape * 1.0)
        it += Hm.robe(r, p, robe, trim)
        # 넓은 소매(2단계부터 끝단 장식)
        for el, ha in ((r.lel, r.lha), (r.rel, r.rha)):
            end = ha + (ha - el) * -0.1
            it.append(Item(S.capsule(el, end, 2.2 * s, (2.8 + tier * 0.25) * s), robe))
            if tier >= 2:
                it.append(Item(S.torus(end, S.frame_from(end - el), (2.6 + tier * 0.25) * s, 0.6 * s), trim))
        it.append(Item(S.cylinder(r.waist + r.up * 0.8 * s, 5.2 * s, 0.7 * s, R, 0.3), trim))       # 허리끈
        if tier == 1:
            # 견습생: 어깨에 멘 책가방 + 투박한 나무 지팡이 끝 작은 수정
            it.append(Item(S.capsule(r.lsh + r.up * 0.6 * s, r.waist + r.right * 4.0 * s, 0.6 * s), 'leather'))
            it.append(Item(S.box(r.waist + r.right * 5.0 * s - r.up * 1.6 * s, V(1.2 * s, 2.4 * s, 2.0 * s), R, 0.4 * s), 'leather'))
            it += Hm.staff(r, 'wood', 'crystal1', 'wood', 28)
        elif tier == 2:
            # 연구소 마법사: 지금 마법사 차림(흰 앞판·높은 깃) + 푸른 구슬 지팡이
            a = r.waist + r.fwd * 4.6 * s
            b = V(a[0], a[1] + (r.lan[1] + r.ran[1]) * 0.25, 1.2 * s)
            it.append(Item(S.capsule(a, b + r.fwd * 2.0 * s, 1.9 * s, 3.0 * s), 'white'))
            it.append(Item(S.box(r.chest + r.fwd * 4.0 * s, V(2.0 * s, 0.6 * s, 4.6 * s), R, 0.4), 'white'))
            it += Hm.pauldrons(r, robe, 3.0, trim='white')
            it += Hm.cape(r, p, 'white', length=22, width=6.0)                                    # 연구소 흰 반망토
            it.append(Item(S.torus(r.neck - r.up * 1.2 * s - r.fwd * 1.0 * s, R, 4.0 * s, 1.5 * s), 'white'))   # 내린 두건
            bk = r.waist + r.right * 5.4 * s + r.fwd * 1.0 * s - r.up * 2.6 * s                    # 허리에 찬 연구 노트
            it.append(Item(S.box(bk, V(1.1 * s, 2.4 * s, 3.0 * s), R, 0.3 * s), 'leather'))
            it.append(Item(S.box(bk, V(1.25 * s, 2.55 * s, 0.4 * s), R, 0.1 * s), 'steel'))
            it += Hm.staff(r, 'g_dark', 'orb_b', 'steel', 32)
        elif tier == 3:
            # 궁정 마법사: 금테 보라 로브 + 높은 깃 + 금 어깨 + 넓은 모자 + 금빛 구슬 지팡이 + 망토
            it += Hm.wizard_hat(r, robe, 'gold')
            it += Hm.pauldrons(r, 'gold', 3.2, trim=robe)
            it += Hm.cape(r, p, robe, length=28, width=6.6, split=True)
            it.append(Item(S.box(r.chest + r.fwd * 4.0 * s, V(2.2 * s, 0.6 * s, 4.8 * s), R, 0.4), 'gold'))
            it += Hm.staff(r, 'g_dark', 'orb_g', 'gold', 34)
        else:
            # 별의 현자: 밤하늘 로브(별가루) + 금테 + 별빛 왕관 + 지팡이 주위를 도는 별 결정 + 긴 망토
            H, HR = r.head, r.head_rot
            hr = r.b['head_r'] * s
            for k in range(5):                                                              # 별빛 왕관(가시 5개)
                a = math.radians(k * 36 + 18 + 90)
                b0 = H + HR @ V(math.cos(a) * hr * 0.95, math.sin(a) * hr * 0.6, hr * 0.85)
                it.append(Item(S.capsule(b0, b0 + HR @ V(0, 0, (2.8 if k == 2 else 1.8) * s), 0.5 * s, 0.1 * s), 'starlight'))
            it += Hm.pauldrons(r, 'starsteel', 3.4, trim='gold')
            it += Hm.cape(r, p, 'night', length=32, width=7.2, split=True)
            it += star_gem(r, r.chest + r.fwd * 4.6 * s + r.up * 0.6 * s, 'starlight', 1.3)
            it += Hm.staff(r, 'starsteel', 'starlight', 'gold', 36)
            top = r.rha + r.wdir * 36 * 0.62 * s + r.wdir * 2.4 * s
            for k in range(4):
                a = math.radians(k * 90 + 30)
                c = top + (r.right * math.cos(a) + r.fwd * math.sin(a)) * 4.4 * s + r.wdir * (k % 2) * 1.6 * s
                it.append(Item(S.capsule(c - r.wdir * 1.2 * s, c + r.wdir * 1.2 * s, 0.8 * s, 0.1 * s), 'starlight'))

    return dict(name=f'mage_t{tier}', label=f'마법사 · {MAGE_NAMES[tier]}', mats=m, parts=parts, gear=gear, weapon='staff',
                build=None, opts=dict(no_legs=True, chest=(6.0, 3.9, 5.2)))


TIERS = {'knight': [_knight(n) for n in (1, 2, 3, 4)],
         'elf': [_elf(n) for n in (1, 2, 3, 4)],
         'mage': [_mage(n) for n in (1, 2, 3, 4)]}
