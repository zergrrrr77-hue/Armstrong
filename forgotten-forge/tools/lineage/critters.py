"""에르덴 아르델 평원 꾸미기: 동물(돼지·닭)과 폐허·농장 소품을 기존 그림 공장(SDF)으로 굽는다.
- 동물은 몬스터와 같은 시트 형식(8방향)으로 굽지만, 게임에서는 공격할 수 없는 '마을 동물'로 쓴다.
  동작: idle(대기) · walk(걷기) · attack(먹기/쪼기 — 시트 형식 때문에 이름만 attack)
- 실행: python3 forgotten-forge/tools/lineage/add_assets.py --monsters pig chicken --props ruin_wall ruin_corner ruin_arch ruin_house pig_shed coop
"""
import math

import numpy as np

import sdf as S
import monsters as Mo
import field as F
from sdf import V, Item, Mat
from monsters import samp

CRITTER_ANIMS = [('idle', 6), ('walk', 8), ('attack', 8)]   # attack = 먹기(돼지)·쪼기(닭)


# ───────────────────────── 돼지 ─────────────────────────

def _pig():
    skin_tex = lambda P, n: 0.35 * S.vnoise(P * 0.7, 21) + 0.5 * (S.vnoise(P * 0.22, 7) > 0.62)   # 흙 묻은 얼룩
    m = {
        'pig': Mat(['#3e2622', '#663e38', '#8e5c52', '#b07a6c', '#cc9888'], tex=skin_tex),
        'pig_dk': Mat(['#2e1a18', '#4c2c28', '#6c423a', '#8c5a50', '#a87268']),
        'snout': Mat(['#5a2e2a', '#8a4a44', '#b46a60', '#d48a80', '#eaa898'], gloss=0.3),
        'hoof': Mat(['#120c0a', '#1e1612', '#2a201a', '#362a22', '#42342a']),
        'eyes': Mat(['#060505', '#0c0a09', '#12100e', '#181513', '#1e1a17'], gloss=0.8),
        'mud': Mat(['#1a120a', '#2a1e12', '#3a2a1a', '#4a3822', '#5a462c']),
    }

    def make(anim, f, n):
        t = f / n
        bob, head_dn, phase, moving, tail = 0.0, 0.0, 0.0, False, 0.0
        if anim == 'idle':
            bob = 0.35 * math.sin(2 * math.pi * t)
            head_dn = 4 * math.sin(2 * math.pi * t)              # 킁킁
            tail = 25 * math.sin(4 * math.pi * t)
        elif anim == 'walk':
            phase, moving = t, True
            bob = 0.6 * abs(math.sin(4 * math.pi * t))
            tail = 15 * math.sin(2 * math.pi * t)
        elif anim == 'attack':                                    # 바닥 냄새 맡으며 먹기
            head_dn = samp([0, 12, 22, 26, 24, 26, 18, 6], f, n)
            tail = 30 * math.sin(6 * math.pi * t)
        it = []
        body_z = 11.5 + bob
        body = V(0, 0, body_z)
        it.append(Item(S.ellipsoid(body, V(7.4, 12.0, 7.0)), 'pig'))                       # 통통한 몸
        it.append(Item(S.ellipsoid(body + V(0, 0, -2.6), V(6.6, 10.4, 5.0)), 'pig_dk'))     # 배 그늘
        HR = S.rx(head_dn)
        nk = body + V(0, 9.5, 1.4)
        hd = nk + HR @ V(0, 3.6, -0.6)
        it.append(Item(S.ellipsoid(hd, V(5.2, 5.0, 4.8), HR), 'pig'))
        sn = hd + HR @ V(0, 4.6, -1.0)
        it.append(Item(S.cylinder(sn, 2.4, 1.5, HR @ S.rx(90), 0.6), 'snout'))              # 납작한 코
        for sx in (-1, 1):
            it.append(Item(S.sphere(sn + HR @ V(sx * 0.9, 1.4, 0), 0.55), 'pig_dk'))         # 콧구멍
            it.append(Item(S.sphere(hd + HR @ V(sx * 2.2, 3.4, 1.6), 0.7), 'eyes'))
            e0 = hd + HR @ V(sx * 2.8, 0.6, 3.6)
            it.append(Item(S.capsule(e0, e0 + HR @ V(sx * 2.0, 2.4, 0.8), 1.6, 0.5), 'pig_dk'))   # 처진 귀
        # 꼬불 꼬리
        tb = body + V(0, -11.6, 2.6)
        a = math.radians(tail)
        p0 = tb
        for k in range(4):
            ang = a + k * 1.6
            p1 = p0 + V(math.sin(ang) * 1.4, -0.9, math.cos(ang) * 1.4)
            it.append(Item(S.capsule(p0, p1, 0.6), 'pig'))
            p0 = p1
        # 짧은 다리(대각선 쌍으로 걷기)
        for sx, sy, off in ((-1, 6.5, 0.0), (1, 6.5, 0.5), (-1, -7.0, 0.5), (1, -7.0, 0.0)):
            ph = 2 * math.pi * (phase + off)
            swing = 3.2 * math.sin(ph) if moving else 0
            lift = max(0.0, math.cos(ph)) * 1.6 if moving else 0
            root = V(sx * 4.0, sy, body_z - 4.0)
            foot = V(sx * 4.2, sy + swing, lift)
            it.append(Item(S.capsule(root, foot + V(0, 0, 1.6), 2.0, 1.5), 'pig'))
            it.append(Item(S.ellipsoid(foot + V(0, 0.3, 0.8), V(1.5, 1.8, 0.9)), 'hoof'))
        it.append(Item(S.ellipsoid(body + V(-3.5, -5, -4.8), V(3.0, 4.0, 1.4)), 'mud'))      # 배에 묻은 진흙
        return it, None, None

    return dict(name='pig', label='돼지', mats=m, build=make, frame=(80, 64, 40, 46), scale=1.0, anims=CRITTER_ANIMS)


# ───────────────────────── 닭 ─────────────────────────

def _chicken():
    feather_tex = lambda P, n: 0.45 * S.vnoise(P * V(1.4, 0.8, 1.8), 33)
    m = {
        'feather': Mat(['#4a4236', '#7a705e', '#a89c84', '#d0c6ae', '#eee8d6'], tex=feather_tex),
        'feather_dk': Mat(['#2a2018', '#46362a', '#64503c', '#806a50', '#9c8466'], tex=feather_tex),
        'comb': Mat(['#4a0808', '#7a1010', '#aa1c18', '#d02a22', '#ee4a3a']),
        'beak': Mat(['#5a3a08', '#8a5e10', '#b8841c', '#dcaa30', '#f0cc5a']),
        'legs': Mat(['#5a3a08', '#7c5212', '#a06c1c', '#c08a2a', '#d8a63c']),
        'eyes': Mat(['#060505', '#0c0a09', '#12100e', '#181513', '#1e1a17'], gloss=0.8),
    }

    def make(anim, f, n):
        t = f / n
        bob, peck, step, moving, look = 0.0, 0.0, 0.0, False, 0.0
        if anim == 'idle':
            look = 25 * math.sin(2 * math.pi * t)               # 고개 갸웃
            bob = 0.25 * math.sin(4 * math.pi * t)
        elif anim == 'walk':
            moving, step = True, t
            bob = 0.5 * abs(math.sin(4 * math.pi * t))
            look = 0
        elif anim == 'attack':                                   # 땅 쪼기
            peck = samp([0, 25, 60, 80, 55, 80, 40, 5], f, n)
        it = []
        bz = 8.5 + bob
        body = V(0, 0, bz)
        it.append(Item(S.ellipsoid(body, V(4.0, 5.6, 4.2)), 'feather'))
        # 꽁지깃(위로 솟음)
        it.append(Item(S.ellipsoid(body + V(0, -4.6, 3.0), V(2.2, 2.4, 3.6), S.rx(-30)), 'feather_dk'))
        for sx in (-1, 1):
            it.append(Item(S.ellipsoid(body + V(sx * 3.4, -0.4, 0.4), V(1.2, 4.0, 2.6)), 'feather_dk'))   # 날개
        HR = S.rz(look) @ S.rx(peck)
        nk = body + V(0, 3.6, 3.0)
        hd = nk + HR @ V(0, 1.6, 3.2)
        it.append(Item(S.capsule(nk, hd, 1.9, 1.6), 'feather'))
        it.append(Item(S.sphere(hd, 2.2), 'feather'))
        it.append(Item(S.cone(hd + HR @ V(0, 1.8, -0.2), hd + HR @ V(0, 3.6, -0.6), 0.9), 'beak'))
        for k in range(3):                                      # 볏
            it.append(Item(S.sphere(hd + HR @ V(0, 0.6 - k * 1.0, 2.2 + (k == 1) * 0.5), 0.9), 'comb'))
        it.append(Item(S.ellipsoid(hd + HR @ V(0, 1.6, -1.8), V(0.6, 0.6, 1.0), HR), 'comb'))     # 턱 볏
        for sx in (-1, 1):
            it.append(Item(S.sphere(hd + HR @ V(sx * 1.5, 0.9, 0.5), 0.45), 'eyes'))
        for sx, off in ((-1, 0.0), (1, 0.5)):
            ph = 2 * math.pi * (step + off)
            sw = 2.2 * math.sin(ph) if moving else 0
            lift = max(0.0, math.cos(ph)) * 1.2 if moving else 0
            hip = body + V(sx * 1.6, 0.4, -3.2)
            foot = V(sx * 1.7, sw + 0.4, lift)
            it.append(Item(S.capsule(hip, foot + V(0, 0, 0.6), 0.55, 0.4), 'legs'))
            for a in (-35, 0, 35):
                d = S.rz(a) @ V(0, 1.6, 0)
                it.append(Item(S.capsule(foot + V(0, 0, 0.3), foot + d + V(0, 0, 0.2), 0.3), 'legs'))
        return it, None, None

    return dict(name='chicken', label='닭', mats=m, build=make, frame=(48, 44, 24, 34), scale=1.0, anims=CRITTER_ANIMS)


Mo.MONSTERS += [_pig(), _chicken()]


# ───────────────────────── 폐허·농장 소품 ─────────────────────────

L = F.CELL / 2


def _jagged_top(base, top_z, seed, width, steps=7):
    """벽 윗부분을 계단처럼 무너뜨린다: 높이가 들쭉날쭉한 상자들로 깎아 낸다."""
    rng = np.random.default_rng(seed)
    cut = []
    for k in range(steps):
        x = -width + (k + 0.5) * (2 * width / steps)
        h = top_z * (0.35 + 0.65 * rng.random())
        cut.append(S.box(V(x, 0, h + 30), V(width / steps + 0.4, 12, 30)))
    return S.sub(base, *cut)


def _wall_seg(cx, cy, half_len, thick, height, seed, along_y=False, steps=7):
    """원점에서 x축으로 뻗은 벽을 만들어 위를 무너뜨린 뒤, (cx, cy)로 옮긴다(along_y면 y축 방향으로 돌림)."""
    w = _jagged_top(S.box(V(0, 0, height / 2), V(half_len, thick, height / 2)), height, seed, half_len, steps)
    return S.xform(w, S.rz(90) if along_y else np.eye(3), V(cx, cy, 0))


def _rubble(seed, n, spread, z=1.5):
    rng = np.random.default_rng(seed)
    it = []
    for _ in range(n):
        x, y = rng.uniform(-spread, spread), rng.uniform(-spread, spread)
        s = rng.uniform(1.6, 3.4)
        it.append(Item(S.box(V(x, y, z * s * 0.5), V(s, s * 0.8, s * 0.6), S.rz(rng.uniform(0, 90)), 0.5), 'wall'))
    return it


@F.prop('ruin_wall', '무너진 돌담', (128, 112, 64, 84), yaw=45, scale=1.6, group='폐허')
def p_ruin_wall(f):
    wall = S.box(V(0, 0, 16), V(L, 4.8, 16))
    wall = _jagged_top(wall, 32, 11, L)
    it = [Item(wall, 'wall'),
          Item(S.inter(S.shell(wall, 0.3), S.halfspace(V(0, 0, 1), 6)), 'moss'),          # 아래쪽 이끼
          Item(S.box(V(L * 0.55, 0, 2.6), V(L * 0.25, 5.4, 2.6), None, 0.6), 'wall')]
    it += _rubble(12, 7, L * 0.9)
    return it


@F.prop('ruin_corner', '무너진 집 모서리', (128, 128, 64, 96), yaw=45, scale=1.6, group='폐허')
def p_ruin_corner(f):
    a = S.sub(_wall_seg(-L * 0.4, -L * 0.6, L * 0.75, 4.2, 40, 21), S.box(V(-L * 0.4, -L * 0.6, 22), V(3.2, 6, 4.4)))   # 창틀 구멍
    b = _wall_seg(-L * 1.15 + 4.2, 0, L * 0.75, 4.2, 40, 22, along_y=True)
    it = [Item(a, 'wall'), Item(b, 'wall'),
          Item(S.inter(S.shell(S.union(a, b), 0.3), S.halfspace(V(0, 0, 1), 8)), 'moss'),
          # 쓰러진 서까래(불에 그을린 나무)
          Item(S.box(V(2, 4, 3), V(L * 0.8, 1.4, 1.4), S.rz(28) @ S.ry(8), 0.4), 'timber'),
          Item(S.box(V(-4, 10, 2), V(L * 0.5, 1.2, 1.2), S.rz(-50), 0.4), 'timber')]
    it += _rubble(23, 9, L * 0.8)
    return it


@F.prop('ruin_arch', '부서진 아치문', (112, 128, 56, 104), yaw=45, scale=1.6, group='폐허')
def p_ruin_arch(f):
    left = S.box(V(-12, 0, 18), V(4.2, 4.2, 18))
    right = S.box(V(12, 0, 12), V(4.2, 4.2, 12))                          # 오른쪽은 반쯤 무너짐
    arch = S.sub(S.box(V(-3, 0, 38), V(13, 4.0, 4.2)), S.cylinder(V(0, 0, 32), 8.4, 6, S.rx(90)))
    arch = S.inter(arch, S.halfspace(S.nrm(V(1, 0, 0.35)), 16))              # 아치 오른쪽 끝이 깨짐
    it = [Item(left, 'wall'), Item(right, 'wall'), Item(arch, 'wall'),
          Item(S.box(V(-12, 0, 37.5), V(5.0, 5.0, 1.2), None, 0.3), 'wall_dk'),
          Item(S.inter(S.shell(left, 0.3), S.halfspace(V(0, 0, 1), 10)), 'moss')]
    it += _rubble(31, 8, 14)
    return it


@F.prop('ruin_house', '불탄 옛 집터', (176, 128, 88, 96), yaw=45, scale=1.6, group='폐허')
def p_ruin_house(f):
    W2, D2 = L * 1.25, L * 0.95
    floor = Item(S.box(V(0, 0, 0.8), V(W2, D2, 0.8), None, 0.2), 'grave')   # 남은 바닥돌
    back = _wall_seg(0, -D2, W2, 3.6, 28, 41, steps=9)
    side = _wall_seg(-W2, 0, D2, 3.6, 20, 42, along_y=True, steps=6)
    stub = S.box(V(W2, D2 * 0.4, 4), V(3.6, D2 * 0.5, 4))
    it = [floor, Item(back, 'wall'), Item(side, 'wall'), Item(stub, 'wall'),
          Item(S.inter(S.shell(back, 0.3), S.halfspace(V(0, 0, 1), 8)), 'moss'),
          # 화로 자리와 무너진 굴뚝
          Item(S.box(V(-W2 * 0.55, -D2 * 0.75, 14), V(4.4, 4.4, 14), None, 0.4), 'wall_dk'),
          # 무너져 내린 지붕 들보
          Item(S.box(V(2, 0, 4.5), V(W2 * 0.85, 1.5, 1.5), S.rz(18) @ S.ry(-14), 0.4), 'timber'),
          Item(S.box(V(-6, 6, 2.2), V(W2 * 0.6, 1.3, 1.3), S.rz(-35), 0.4), 'timber'),
          Item(S.box(V(10, -6, 2.0), V(W2 * 0.4, 1.2, 1.2), S.rz(70), 0.4), 'timber')]
    it += _rubble(43, 12, W2 * 0.8)
    return it


@F.prop('pig_shed', '돼지우리 지붕', (112, 88, 56, 66), yaw=45, scale=1.5, group='농장')
def p_pig_shed(f):
    it = []
    for x, y, h in ((-L * 0.8, -6, 18), (L * 0.8, -6, 18), (-L * 0.8, 8, 11), (L * 0.8, 8, 11)):
        it.append(Item(S.box(V(x, y, h / 2), V(1.3, 1.3, h / 2), None, 0.3), 'timber'))
    roof = S.box(V(0, 1, 15.5), V(L * 0.95, 9.5, 0.9), S.rx(-21), 0.3)                  # 외쪽 경사 지붕
    it.append(Item(roof, 'thatch'))
    it.append(Item(S.box(V(0, -7, 6), V(L * 0.85, 0.8, 6), None, 0.2), 'plank'))           # 뒤 판자벽
    it.append(Item(S.ellipsoid(V(-4, 2, 0.6), V(9, 6, 1.0)), 'hay'))                       # 깔짚
    return it


@F.prop('coop', '닭장', (96, 104, 48, 82), yaw=45, scale=1.5, group='농장')
def p_coop(f):
    it = []
    for x in (-8, 8):
        for y in (-6, 6):
            it.append(Item(S.box(V(x, y, 3.5), V(0.9, 0.9, 3.5)), 'timber'))              # 기둥(바닥에서 띄움)
    hut = S.box(V(0, 0, 13), V(9.5, 7.5, 6), None, 0.4)
    it.append(Item(hut, 'plank'))
    it.append(Item(S.box(V(0, 7.6, 12), V(2.4, 0.4, 2.8), None, 0.2), 'timber'))           # 문 구멍(어두운 판)
    roof = S.union(S.box(V(0, -4, 21.5), V(10.8, 5.4, 0.8), S.rx(28), 0.2), S.box(V(0, 4, 21.5), V(10.8, 5.4, 0.8), S.rx(-28), 0.2))
    it.append(Item(roof, 'roof'))
    ramp = S.box(V(0, 12.5, 4.5), V(2.0, 6.0, 0.5), S.rx(-38), 0.1)                        # 오르내리는 경사판
    it.append(Item(ramp, 'plank'))
    for k in range(3):
        it.append(Item(S.box(V(0, 9.8 + k * 2.2, 2.8 + k * 1.6), V(2.0, 0.25, 0.3), S.rx(-38)), 'timber'))
    it.append(Item(S.ellipsoid(V(5, 9, 0.5), V(5, 3.5, 0.8)), 'hay'))
    return it


@F.prop('fence_v', '나무 울타리(세로)', (80, 56, 40, 36), yaw=-45, scale=1.5, group='농장')
def p_fence_v(f):
    """기존 '나무 울타리'와 같은 모양을 다른 축 방향으로 세운 것(우리·닭장 옆면용)."""
    return F.p_fence(f)
