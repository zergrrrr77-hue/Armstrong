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
        parts = dict(skin='skin', hair='hair', eyes='eyes', torso='gambeson', pelvis='gambeson', legs='leather', shin='leather',
                     boots='leather', arms='gambeson', farm='leather', hands='leather')
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
            # 견습 기사: 누빔 갑옷 + 사슬 두건 + 가죽 허리띠 + 녹슨 롱소드 + 참나무 버클러
            it += coif(r, 'gambeson')                                                          # 누빔 천 두건
            it.append(Item(S.box(r.waist + r.up * 0.4 * s, V(5.4 * s, 4.4 * s, 0.9 * s), R, 0.4), 'leather'))
            it.append(Item(S.box(r.waist + r.up * 0.4 * s + r.fwd * 4.3 * s, V(1.0 * s, 0.4 * s, 0.9 * s), R, 0.2), 'iron'))
            it += Hm.skirt(r, 'gambeson', 5.2, 6.4, 8.0)
            for el, ha in ((r.lel, r.lha), (r.rel, r.rha)):                                   # 가죽 팔목 보호대
                it.append(Item(S.capsule(el + (ha - el) * 0.3, ha - (ha - el) * 0.15, 2.0 * s, 1.8 * s), 'leather'))
            it += Hm.sword(r, ['rust'], length=19, width=1.3, guard='rust', grip='leather', blade='rust')
            it += Hm.round_shield(r, 'oak', 'iron', 'iron', size=5.0)
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


TIERS = {'knight': [_knight(t) for t in (1, 2, 3, 4)]}
