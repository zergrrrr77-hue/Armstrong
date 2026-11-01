"""아이템 아이콘 32×32 (3D 프리렌더) + 등급 테두리 + 강화 발광.

아이콘은 x-z 평면(화면과 나란한 면)에 놓고 살짝 내려다본다. 긴 물건은 왼쪽 아래 → 오른쪽 위 대각선.
"""
import math

import numpy as np
from PIL import Image, ImageDraw

import sdf as S
from sdf import V, Item, Mat

IW = IH = 32
DG = S.nrm(V(1, 0, 1))         # 대각선(오른쪽 위)
NX = S.nrm(V(1, 0, -1))        # 대각선의 수직(오른쪽 아래)
FRONT = V(0, -1, 0)            # 카메라 쪽

IM = {
    'steel': Mat(['#1e2128', '#3a3f4a', '#5d6470', '#8a919c', '#c4c9d0'], metal=True, hi='#f4f7fa'),
    'steel_dk': Mat(['#15171c', '#23262d', '#353a44', '#4c525e', '#666d79'], metal=True, hi='#a8b0bc'),
    'iron': Mat(['#1b1c1f', '#2e3034', '#46494f', '#63676e', '#83878e'], metal=True, hi='#c0c3c8'),
    'gold': Mat(['#4a2e0c', '#7c5316', '#b07d22', '#d9a83a', '#f2d36b'], metal=True, hi='#fff2b8'),
    'silver': Mat(['#3a3c44', '#5e626c', '#8a8e98', '#b4b8c0', '#dfe2e8'], metal=True, hi='#ffffff'),
    'leather': Mat(['#20140d', '#3a2416', '#55361f', '#70492b', '#8a5e3a']),
    'leather_lt': Mat(['#3a2617', '#5a3d25', '#7a5634', '#9a7045', '#b58a58']),
    'wood': Mat(['#21150c', '#3a2614', '#56391e', '#73502b', '#8f683b']),
    'cloth_r': Mat(['#2c0607', '#4a0c0e', '#6c1416', '#8f1f1f', '#b0302a']),
    'cloth_b': Mat(['#0e1426', '#172243', '#22335f', '#304679', '#3f5a92']),
    'cloth_p': Mat(['#160b1e', '#251334', '#371d4c', '#4b2965', '#61367f']),
    'cloth_g': Mat(['#0d1a10', '#16291a', '#213b25', '#2e5032', '#3d6740']),
    'paper': Mat(['#5e5038', '#857356', '#a99676', '#c8b796', '#e2d4b4'],
                 tex=lambda P, n: 0.35 * S.vnoise(P * 0.9, 3)),
    'glass': Mat(['#3a4650', '#5a6a76', '#7d8f9c', '#a6b8c4', '#d2e2ea'], gloss=1.0, hi='#ffffff'),
    'cork': Mat(['#3a2414', '#5a3a20', '#7a522e', '#986a3e', '#b2844f']),
    'p_red': Mat(['#3a0408', '#68080e', '#9a1018', '#cc2028', '#ee5a5a'], gloss=1.0, hi='#ffd0d0'),
    'p_orange': Mat(['#4a1a02', '#7a3006', '#b0500c', '#e07818', '#ffaa48'], gloss=1.0, hi='#ffe8c0'),
    'p_blue': Mat(['#04103a', '#0a2068', '#14389a', '#2a5acc', '#5a8aee'], gloss=1.0, hi='#d8e8ff'),
    'p_green': Mat(['#04260a', '#0a4414', '#146a20', '#2a9634', '#5ac25e'], gloss=1.0, hi='#d8ffd8'),
    'p_white': Mat(['#4a4a52', '#76767e', '#a2a2aa', '#cacad0', '#ececf0'], gloss=1.0, hi='#ffffff'),
    'seal_r': Mat(['#3a0408', '#68080e', '#9a1018', '#cc2028', '#ee5a5a'], gloss=0.6),
    'seal_b': Mat(['#04103a', '#0a2068', '#14389a', '#2a5acc', '#5a8aee'], gloss=0.6),
    'seal_g': Mat(['#04260a', '#0a4414', '#146a20', '#2a9634', '#5ac25e'], gloss=0.6),
    'seal_w': Mat(['#4a4a52', '#76767e', '#a2a2aa', '#cacad0', '#ececf0'], gloss=0.6),
    'ruby': Mat(['#5a0a14', '#8e1222', '#c41e34', '#e84a5a', '#ff9aa2'], gloss=1.0, hi='#ffffff'),
    'sapph': Mat(['#0a1a5a', '#12308e', '#1e4ac4', '#4a7ae8', '#9ac0ff'], gloss=1.0, hi='#ffffff'),
    'emer': Mat(['#04361a', '#0a5a2a', '#14843e', '#2ab25a', '#7ae29a'], gloss=1.0, hi='#ffffff'),
    'orb': Mat(['#2a6fbf', '#4f9be0', '#7cc3f5', '#b5e4ff', '#e8f8ff'], emit=True),
    'bone': Mat(['#3e3829', '#6a614b', '#958a6e', '#bdb294', '#dcd3b6']),
    'feather': Mat(['#5a5a5e', '#7e7e84', '#a4a4aa', '#c8c8ce', '#e8e8ec']),
    'fur': Mat(['#3c3630', '#5e554b', '#81766a', '#a3978a', '#c2b6a8'], tex=lambda P, n: 0.5 * S.vnoise(P * 1.5, 3)),
}

ICONS = []   # (id, 이름, 분류, 등급, 빌더, 강화 가능 여부)


def icon(iid, name, cat, grade='common', enchant=False):
    def deco(fn):
        ICONS.append(dict(id=iid, name=name, cat=cat, grade=grade, fn=fn, enchant=enchant))
        return fn
    return deco


def M_diag(extra=0.0):
    """로컬 z=대각선, x=수직, y=카메라 반대."""
    return np.stack([NX, -FRONT, DG], 1) if extra == 0 else (S.ry(extra) @ np.stack([NX, -FRONT, DG], 1))


def blade(c0, length, width, mat, thick=0.6, d=DG, tag='blade'):
    tip = c0 + d * length
    M = np.stack([S.nrm(np.cross(d, FRONT)) * -1, -FRONT, d], 1)
    f = S.inter(S.box(c0 + d * length / 2, V(width, thick, length / 2), M, 0.15), S.capsule(c0 - d * 2, tip, width * 1.3, 0.1))
    return Item(f, mat, tag), M


# ── 무기 ──────────────────────────────────────────

def _sword(L=22, W=1.8, guard='steel_dk', grip='leather', pom='gold', mat='steel', gw=5.0):
    o = -DG * 13
    b, M = blade(o + DG * 6, L, W, mat)
    return [b, Item(S.box(o + DG * 5.5, V(gw, 1.0, 0.9), M, 0.4), guard),
            Item(S.capsule(o, o + DG * 5, 1.0), grip), Item(S.sphere(o - DG * 0.6, 1.5), pom)]


@icon('dagger', '단검', '무기', 'common', True)
def i_dagger():
    o = -DG * 9
    b, M = blade(o + DG * 5, 12, 1.6, 'steel')
    return [b, Item(S.box(o + DG * 4.5, V(3.2, 0.9, 0.8), M, 0.3), 'iron'), Item(S.capsule(o, o + DG * 4, 1.0), 'leather'),
            Item(S.sphere(o - DG * 0.5, 1.2), 'iron')]


@icon('longsword', '롱소드', '무기', 'uncommon', True)
def i_longsword():
    return _sword()


@icon('greatsword', '투핸드 소드', '무기', 'rare', True)
def i_great():
    o = -DG * 15
    b, M = blade(o + DG * 8, 24, 2.6, 'steel')
    return [b, Item(S.box(o + DG * 7.5, V(6.5, 1.2, 1.1), M, 0.5), 'steel_dk'), Item(S.capsule(o, o + DG * 7, 1.1), 'leather'),
            Item(S.sphere(o - DG * 0.8, 1.7), 'steel_dk'),
            Item(S.capsule(o + DG * 10, o + DG * 26, 0.5), 'steel_dk', 'blade')]


@icon('rune_blade', '룬의 검', '무기', 'heroic', True)
def i_rune():
    it = _sword(L=22, W=2.0, guard='gold', grip='cloth_p', pom='ruby', mat='steel')
    o = -DG * 13
    it.append(Item(S.capsule(o + DG * 8, o + DG * 24, 0.55), 'orb', 'blade'))
    return it


@icon('kingsword', '왕의 검', '무기', 'legend', True)
def i_king():
    it = _sword(L=23, W=2.0, guard='gold', grip='cloth_r', pom='ruby', mat='silver', gw=6.0)
    o = -DG * 13
    it.append(Item(S.sphere(o + DG * 5.5 + FRONT * 1.0, 1.1), 'sapph'))
    return it


@icon('axe', '전투 도끼', '무기', 'common', True)
def i_axe():
    o = -DG * 13
    top = o + DG * 26
    it = [Item(S.capsule(o, top, 1.2, 1.0), 'wood')]
    c = top - DG * 4 + NX * -4.5
    M = np.stack([NX, -FRONT, DG], 1)
    it.append(Item(S.inter(S.ellipsoid(c, V(6.5, 0.9, 6.0), M), S.halfspace(NX, np.dot(NX, top) - 1)), 'iron', 'blade'))
    it.append(Item(S.box(top - DG * 4, V(1.8, 1.6, 2.6), M, 0.3), 'iron'))
    return it


@icon('battleaxe', '양날 도끼', '무기', 'rare', True)
def i_baxe():
    o = -DG * 13
    top = o + DG * 26
    M = np.stack([NX, -FRONT, DG], 1)
    it = [Item(S.capsule(o, top, 1.2, 1.0), 'wood')]
    for sg in (-1, 1):
        c = top - DG * 5 + NX * sg * 4.5
        it.append(Item(S.inter(S.ellipsoid(c, V(6, 0.9, 7), M), S.halfspace(-NX * sg, -np.dot(NX * sg, top) + 1)), 'steel', 'blade'))
    it.append(Item(S.cone(top - DG * 1, top + DG * 4, 1.2), 'steel'))
    return it


@icon('spear', '창', '무기', 'uncommon', True)
def i_spear():
    o = -DG * 16
    top = o + DG * 26
    M = np.stack([NX, -FRONT, DG], 1)
    return [Item(S.capsule(o, top, 0.9), 'wood'),
            Item(S.inter(S.ellipsoid(top + DG * 4, V(2.4, 0.6, 6), M), S.halfspace(-DG, -np.dot(DG, top) + 0)), 'steel', 'blade'),
            Item(S.cylinder(top, 1.4, 1.2, M), 'iron'),
            Item(S.capsule(top - DG * 1, top - DG * 5 + NX * 1.5, 0.5), 'cloth_r')]


@icon('mace', '철퇴', '무기', 'common', True)
def i_mace():
    o = -DG * 12
    top = o + DG * 18
    it = [Item(S.capsule(o, top, 1.1), 'leather'), Item(S.sphere(top + DG * 2.5, 4.2), 'iron', 'blade')]
    for k in range(8):
        a = math.radians(k * 45)
        dvec = NX * math.cos(a) + DG * math.sin(a)
        it.append(Item(S.cone(top + DG * 2.5 + dvec * 3, top + DG * 2.5 + dvec * 6.5, 1.3), 'iron', 'blade'))
    return it


@icon('bow', '장궁', '무기', 'uncommon', True)
def i_bow():
    it = []
    n = 8
    pts = []
    for k in range(n + 1):
        t = k / n * 2 - 1
        pts.append(DG * t * 14 + NX * -(1 - t * t) * 6)
    for k in range(n):
        it.append(Item(S.capsule(pts[k], pts[k + 1], 1.2 if abs(k - n / 2) < 1.5 else 0.9), 'wood', 'blade'))
    it.append(Item(S.capsule(pts[0], pts[-1], 0.3), 'feather'))
    it.append(Item(S.capsule(NX * -6 - DG * 1.5, NX * -6 + DG * 1.5, 1.4), 'leather'))
    return it


@icon('staff', '마법 지팡이', '무기', 'rare', True)
def i_staff():
    o = -DG * 15
    top = o + DG * 25
    it = [Item(S.capsule(o, top, 1.0, 1.3), 'wood'), Item(S.sphere(top + DG * 3, 2.8), 'orb', 'blade')]
    for k in range(3):
        a = math.radians(k * 120)
        it.append(Item(S.capsule(top, top + DG * 3 + (NX * math.cos(a) + FRONT * math.sin(a)) * 3, 0.5), 'gold'))
    return it


@icon('arrows', '화살 묶음', '무기', 'common')
def i_arrows():
    it = []
    for k, off in enumerate((-2.2, 0, 2.2)):
        o = -DG * 13 + NX * off
        it.append(Item(S.capsule(o, o + DG * 24, 0.45), 'wood'))
        it.append(Item(S.cone(o + DG * 24, o + DG * 27, 1.0), 'iron'))
        for sg in (-1, 1):
            it.append(Item(S.box(o + DG * 2 + NX * sg * 0.9, V(0.9, 0.2, 2.6), np.stack([NX, -FRONT, DG], 1)), 'cloth_r'))
    return it


# ── 방어구 ─────────────────────────────────────────

@icon('helm', '기사 투구', '방어구', 'uncommon', True)
def i_helm():
    c = V(0, 0, 0)
    return [Item(S.ellipsoid(c, V(9, 9, 10)), 'steel'),
            Item(S.box(c + V(0, -8.6, 0.5), V(6, 1, 0.8), None, 0.3), 'steel_dk'),
            Item(S.box(c + V(0, -8.8, -3.5), V(0.6, 1, 3), None, 0.2), 'steel_dk'),
            Item(S.box(c + V(0, 0, 9), V(1, 9, 1.4), None, 0.5), 'steel'),
            Item(S.capsule(c + V(0, -2, 10), c + V(0, 9, 4), 2.0, 1.2), 'cloth_r')]


@icon('plate', '판금 갑옷', '방어구', 'rare', True)
def i_plate():
    return [Item(S.ellipsoid(V(0, 0, 2), V(9.5, 5, 10)), 'steel'),
            Item(S.ellipsoid(V(-9, 0, 8), V(4.5, 5, 3.6)), 'steel'),
            Item(S.ellipsoid(V(9, 0, 8), V(4.5, 5, 3.6)), 'steel'),
            Item(S.box(V(0, 0, -8), V(7.5, 4.4, 2.5), None, 1.0), 'steel_dk'),
            Item(S.box(V(0, -4.8, 3), V(0.5, 0.4, 7)), 'gold'),
            Item(S.box(V(0, -4.9, 5), V(4.5, 0.4, 0.5)), 'gold'),
            Item(S.cylinder(V(0, 0, 11.5), 3.6, 1.2, None, 0.4), 'steel_dk')]


@icon('leather_armor', '가죽 갑옷', '방어구', 'common', True)
def i_leather():
    return [Item(S.ellipsoid(V(0, 0, 1), V(9, 5, 10.5)), 'leather_lt'),
            Item(S.ellipsoid(V(-8.5, 0, 7.5), V(4.2, 4.6, 3.2)), 'leather'),
            Item(S.ellipsoid(V(8.5, 0, 7.5), V(4.2, 4.6, 3.2)), 'leather'),
            Item(S.box(V(0, 0, -8), V(7.2, 4.3, 2.4), None, 1.0), 'leather'),
            Item(S.box(V(0, -4.9, -2), V(8.0, 0.6, 1.0), None, 0.3), 'leather'),
            Item(S.box(V(0, -4.9, 2), V(8.0, 0.6, 1.0), None, 0.3), 'leather'),
            Item(S.sphere(V(0, -5.6, -2), 1.1), 'iron'), Item(S.sphere(V(0, -5.6, 2), 1.1), 'iron'),
            Item(S.cylinder(V(0, 0, 11.0), 3.4, 1.4, None, 0.4), 'leather')]


@icon('robe', '마법사 로브', '방어구', 'rare', True)
def i_robe():
    return [Item(S.capsule(V(0, 0, 9), V(0, 0, -11), 6.0, 10), 'cloth_p'),
            Item(S.inter(S.shell(S.capsule(V(0, 0, 9), V(0, 0, -11), 6.0, 10), 0.4), S.halfspace(V(0, 0, 1), -9)), 'gold'),
            Item(S.cylinder(V(0, 0, -1), 7.6, 0.9), 'gold'),
            Item(S.capsule(V(-6, 0, 7), V(-11, 0, -4), 2.8, 3.6), 'cloth_p'),
            Item(S.capsule(V(6, 0, 7), V(11, 0, -4), 2.8, 3.6), 'cloth_p')]


@icon('kite_shield', '연 방패', '방어구', 'uncommon', True)
def i_kite():
    M = np.stack([V(1, 0, 0), V(0, 0, 1), V(0, -1, 0)], 1)
    face = S.ellipsoid(V(0, 0, 1), V(10, 1.6, 13))
    cut = S.inter(face, S.halfspace(S.nrm(V(0.8, 0, -0.6)), 5.0), S.halfspace(S.nrm(V(-0.8, 0, -0.6)), 5.0))
    rim = S.sub(S.inter(S.ellipsoid(V(0, 0.3, 1), V(10.8, 1.5, 13.8)), S.halfspace(S.nrm(V(0.8, 0, -0.6)), 5.6),
                        S.halfspace(S.nrm(V(-0.8, 0, -0.6)), 5.6)), S.halfspace(V(0, -1, 0), 0.5))
    return [Item(cut, 'cloth_b'), Item(rim, 'steel'),
            Item(S.box(V(0, -1.7, 1), V(0.9, 0.5, 8)), 'gold'), Item(S.box(V(0, -1.7, 3.5), V(5, 0.5, 0.9)), 'gold')]


@icon('round_shield', '원형 방패', '방어구', 'common', True)
def i_round():
    M = S.frame_from(V(0, -1, 0))
    return [Item(S.cylinder(V(0, 0, 0), 12, 1.0, M, 0.3), 'wood'),
            Item(S.sub(S.cylinder(V(0, 0, 0), 12.8, 1.3, M, 0.3), S.cylinder(V(0, 0, 0), 11.4, 3, M)), 'iron'),
            Item(S.sphere(V(0, -1, 0), 3.0), 'iron'),
            Item(S.box(V(0, -1.0, 0), V(0.6, 0.4, 11)), 'iron')]


@icon('boots', '철 장화', '방어구', 'common', True)
def i_boots():
    it = []
    for sx, dz in ((-5, 1), (5, -1)):
        it.append(Item(S.capsule(V(sx, 0, 10 + dz), V(sx, 0, -4 + dz), 3.4, 3.2), 'leather'))
        it.append(Item(S.box(V(sx + 2.5, 0, -7 + dz), V(5.0, 3.2, 2.4), None, 1.4), 'leather'))
        it.append(Item(S.cylinder(V(sx, 0, 10 + dz), 3.8, 1.0, None, 0.3), 'iron'))
        it.append(Item(S.box(V(sx + 3, 0, -5.5 + dz), V(3.4, 3.4, 1.4), None, 0.8), 'iron'))
    return it


@icon('gauntlet', '건틀릿', '방어구', 'uncommon', True)
def i_gaunt():
    it = [Item(S.capsule(V(-2, 0, -12), V(-1, 0, -2), 4.0, 3.8), 'steel'),
          Item(S.box(V(0, 0, 2), V(4.4, 2.6, 3.6), None, 1.2), 'steel')]
    for k in range(4):
        x = -3.3 + k * 2.2
        it.append(Item(S.capsule(V(x, 0, 5), V(x + 0.5, -0.6, 11 - abs(k - 1.5)), 1.05), 'steel_dk'))
    it.append(Item(S.capsule(V(4, 0, 1), V(7.5, -0.5, 6), 1.2), 'steel_dk'))
    return it


@icon('cloak', '망토', '방어구', 'uncommon', True)
def i_cloak():
    f = S.inter(S.capsule(V(0, 0, 10), V(0, 0, -12), 5, 12), S.halfspace(V(0, -1, 0), 0.5), S.halfspace(V(0, 0, -1), 12))
    f = S.shell(f, 1.0)
    return [Item(S.inter(f, S.halfspace(V(0, 1, 0), 3)), 'cloth_g'),
            Item(S.torus(V(0, 0, 10), S.frame_from(V(0, 0, 1)), 5, 1.6), 'fur'),
            Item(S.sphere(V(0, -4.5, 9), 1.6), 'gold')]


# ── 장신구 ─────────────────────────────────────────

@icon('ring_ruby', '루비 반지', '장신구', 'rare')
def i_ring():
    return [Item(S.torus(V(0, 0, -2), S.frame_from(V(0, -0.4, 1)), 7, 1.6), 'gold'),
            Item(S.box(V(0, 0, 6), V(2.6, 2.6, 1.4), None, 0.4), 'gold'), Item(S.sphere(V(0, -0.5, 7.5), 2.6), 'ruby')]


@icon('ring_sapph', '사파이어 반지', '장신구', 'heroic')
def i_ring2():
    return [Item(S.torus(V(0, 0, -2), S.frame_from(V(0, -0.4, 1)), 7, 1.6), 'silver'),
            Item(S.box(V(0, 0, 6), V(2.6, 2.6, 1.4), None, 0.4), 'silver'), Item(S.sphere(V(0, -0.5, 7.5), 2.6), 'sapph')]


@icon('amulet', '수호 목걸이', '장신구', 'heroic')
def i_amulet():
    it = []
    for k in range(13):
        a = math.radians(200 + k * 11.5)
        it.append(Item(S.sphere(V(math.cos(a) * 11, 0, 4 + math.sin(a) * -11 * -1 + 0), 1.0), 'gold'))
    it.append(Item(S.cylinder(V(0, 0, -6), 5.4, 0.9, S.frame_from(V(0, -1, 0)), 0.4), 'gold'))
    it.append(Item(S.sphere(V(0, -0.8, -6), 3.0), 'emer'))
    return it


@icon('bracelet', '전사의 팔찌', '장신구', 'uncommon')
def i_bracelet():
    M = S.frame_from(S.nrm(V(0.25, -1, 0.35)))
    band = S.sub(S.cylinder(V(0, 0, 0), 9.5, 3.0, M, 0.8), S.cylinder(V(0, 0, 0), 7.2, 5, M))
    it = [Item(band, 'silver')]
    for k in range(6):
        a = math.radians(k * 60 + 30)
        p = M @ V(math.cos(a) * 9.6, math.sin(a) * 9.6, 0)
        it.append(Item(S.sphere(p, 1.6), 'gold'))
    it.append(Item(S.sphere(M @ V(0, -9.8, -1.2), 2.4), 'ruby'))
    return it


# ── 소모품 ─────────────────────────────────────────

def _potion(liq, shape='round'):
    if shape == 'round':
        body = S.sphere(V(0, 0, -3), 8.5)
    elif shape == 'tall':
        body = S.cylinder(V(0, 0, -3), 6.0, 8.0, None, 2.0)
    else:
        body = S.box(V(0, 0, -3), V(7, 4.5, 8), None, 2.5)
    it = [Item(body, liq),
          Item(S.cylinder(V(0, 0, 8), 2.6, 3.5, None, 0.5), 'glass'),
          Item(S.cylinder(V(0, 0, 11.8), 3.6, 0.8, None, 0.4), 'glass'),
          Item(S.cylinder(V(0, 0, 13.5), 2.4, 1.8, None, 0.6), 'cork')]
    # 유리 윗부분(빈 공간)
    it.append(Item(S.inter(S.shell(body, 0.4), S.halfspace(V(0, 0, -1), -3.5)), 'glass'))
    return it


@icon('pot_red', '체력 회복제', '소모품', 'common')
def i_p1():
    return _potion('p_red')


@icon('pot_orange', '강력 체력 회복제', '소모품', 'uncommon')
def i_p2():
    return _potion('p_orange', 'tall')


@icon('pot_white', '고급 체력 회복제', '소모품', 'rare')
def i_p3():
    return _potion('p_white', 'flat')


@icon('pot_blue', '마나 회복제', '소모품', 'uncommon')
def i_p4():
    return _potion('p_blue', 'round')


@icon('pot_green', '속도 향상 물약', '소모품', 'uncommon')
def i_p5():
    return _potion('p_green', 'tall')


def _scroll(seal):
    M = S.frame_from(DG)
    a, b = -DG * 11, DG * 11
    it = [Item(S.capsule(a, b, 5.0), 'paper'),
          Item(S.cylinder(a - DG * 0.8, 5.6, 0.9, M, 0.3), 'wood'), Item(S.cylinder(b + DG * 0.8, 5.6, 0.9, M, 0.3), 'wood'),
          Item(S.cylinder(V(0, 0, 0), 5.3, 1.2, M, 0.2), seal),
          Item(S.ellipsoid(V(0, -5.0, 0) + NX * 1.5, V(2.6, 1.0, 2.6)), seal)]
    return it


@icon('scroll_weapon', '무기 마법 주문서', '소모품', 'rare')
def i_s1():
    return _scroll('seal_r')


@icon('scroll_armor', '갑옷 마법 주문서', '소모품', 'rare')
def i_s2():
    return _scroll('seal_b')


@icon('scroll_teleport', '순간이동 주문서', '소모품', 'common')
def i_s3():
    return _scroll('seal_g')


@icon('scroll_return', '귀환 주문서', '소모품', 'common')
def i_s4():
    return _scroll('seal_w')


# ── 기타 ──────────────────────────────────────────

@icon('gold', '금화 더미', '기타', 'common')
def i_gold():
    it = []
    rng = np.random.default_rng(3)
    coins = [(0, 0, -8), (-6, 1, -8), (6, 1, -8), (-3, 0, -6), (3, 0, -6), (0, 0, -4), (-8, 2, -9.5), (8, 2, -9.5), (1, -1, -2)]
    for x, y, z in coins:
        tilt = S.frame_from(S.nrm(V(rng.uniform(-0.3, 0.3), -0.8, 1)))
        it.append(Item(S.cylinder(V(x, y - 2, z + 4), 4.0, 0.8, tilt, 0.3), 'gold'))
    it.append(Item(S.cylinder(V(9, -4, 5), 4.0, 0.8, S.frame_from(V(0.3, -1, 0.1)), 0.3), 'gold'))
    return it


@icon('gem_ruby', '루비', '기타', 'rare')
def i_gem():
    f = S.inter(S.box(V(0, 0, 0), V(7, 7, 9), S.rz(45) @ S.rx(0)), S.box(V(0, 0, 0), V(9, 9, 6.5)),
                S.halfspace(S.nrm(V(0, -1, 1)), 7), S.halfspace(S.nrm(V(0, -1, -1)), 7), S.halfspace(S.nrm(V(1, 0, 1)), 8),
                S.halfspace(S.nrm(V(-1, 0, 1)), 8), S.halfspace(S.nrm(V(1, 0, -1)), 8), S.halfspace(S.nrm(V(-1, 0, -1)), 8))
    return [Item(f, 'ruby')]


@icon('key', '던전 열쇠', '기타', 'uncommon')
def i_key():
    o = -DG * 8
    M = np.stack([NX, -FRONT, DG], 1)
    return [Item(S.torus(o - DG * 4, np.stack([NX, DG, -FRONT], 1) @ np.eye(3), 4.0, 1.2), 'gold'),
            Item(S.capsule(o, o + DG * 18, 1.1), 'gold'),
            Item(S.box(o + DG * 15 + NX * 2.5, V(2.4, 0.9, 1.0), M, 0.2), 'gold'),
            Item(S.box(o + DG * 11.5 + NX * 2.0, V(1.8, 0.9, 0.9), M, 0.2), 'gold')]


@icon('spellbook', '마법서', '기타', 'heroic')
def i_book():
    M = S.ry(-12)
    return [Item(S.box(V(0, 0, 0), V(9, 2.6, 11.5), M, 0.6), 'paper'),
            Item(S.sub(S.box(V(0, 0, 0), V(9.6, 3.2, 12), M, 0.8), S.box(V(1.4, 0, 0), V(9.2, 2.4, 11.2), M)), 'cloth_p'),
            Item(S.box(V(-9.4, 0, 0) @ M.T, V(1.4, 3.4, 12), M, 0.8), 'cloth_p'),
            Item(S.sphere(V(0.5, -3.5, 0) @ M.T, 2.6), 'orb'),
            Item(S.torus(V(0.5, -3.3, 0) @ M.T, S.frame_from(M @ V(0, -1, 0)), 3.6, 0.6), 'gold')]


@icon('bone', '해골 뼈', '기타', 'common')
def i_bone():
    a, b = -DG * 10, DG * 10
    it = [Item(S.capsule(a, b, 1.8), 'bone')]
    for e in (a, b):
        for sg in (-1, 1):
            it.append(Item(S.sphere(e + NX * sg * 2.0, 2.6), 'bone'))
    return it


GRADES = [
    ('common', '일반', '#7e7a72'),
    ('uncommon', '고급', '#4f9a4a'),
    ('rare', '희귀', '#3f7fd0'),
    ('heroic', '영웅', '#9a52d8'),
    ('legend', '전설', '#e0901c'),
]

ENCHANTS = [
    (0, None, 0, 0),
    (7, (225, 235, 255), 1, 0.8),
    (8, (90, 165, 255), 2, 0.7),
    (9, (185, 105, 255), 2, 0.85),
    (10, (255, 70, 50), 2, 1.0),
]


def render_icon(d, enchant=None, size=IW):
    items = d['fn']()
    im, depth, matid, itemid = S.render(items, IM, size * 2, size * 2, size, size, yaw=180, elev=22, scale=1.25 * size / 32 * 0.86 * 2,
                                        return_buffers=True, outline=False, inner_lines=True)
    # 2배로 그린 뒤 1/2로 줄이고(가장 가까운 픽셀) 외곽선을 다시 그어 또렷하게
    im = im.resize((size, size), Image.NEAREST)
    ids = itemid[::2, ::2]
    a = np.array(im)
    alpha = a[:, :, 3] > 0
    edge = np.zeros_like(alpha)
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        edge |= alpha & ~np.roll(np.roll(alpha, dy, 0), dx, 1)
    a[edge, :3] = (a[edge, :3] * 0.45 + np.array(S.OUTLINE_INK) * 0.55).astype(np.uint8)
    im = Image.fromarray(a, 'RGBA')
    if enchant and enchant[1] is not None:
        tagged = np.array([it.tag == 'blade' for it in items])
        mask = np.zeros(ids.shape, bool)
        valid = ids >= 0
        mask[valid] = tagged[ids[valid]]
        if not mask.any():
            mask = alpha
        im = S.glow(im, color=enchant[1], radius=enchant[2], strength=enchant[3], mask=mask)
    return im


def slot_frame(grade_hex, size=36):
    """등급 테두리 슬롯(어두운 베벨 + 색 테두리)."""
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = S.hexrgb(grade_hex)
    d.rectangle([0, 0, size - 1, size - 1], fill=(14, 12, 11, 255))
    d.rectangle([1, 1, size - 2, size - 2], fill=(26, 23, 21, 255))
    for k in range(2, size - 2):
        t = k / size
        d.line([(2, k), (size - 3, k)], fill=(int(30 - 10 * t), int(27 - 9 * t), int(25 - 8 * t), 255))
    d.rectangle([0, 0, size - 1, size - 1], outline=tuple(int(v * 0.55) for v in c) + (255,))
    d.rectangle([1, 1, size - 2, size - 2], outline=c + (255,))
    d.line([(2, 2), (size - 3, 2)], fill=tuple(min(255, int(v * 1.35)) for v in c) + (255,))
    for (x, y) in ((1, 1), (size - 2, 1), (1, size - 2), (size - 2, size - 2)):
        d.point((x, y), fill=(255, 240, 200, 255))
    return im
