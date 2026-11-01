"""필드: 64×32 마름모 지면 타일 + 쿼터뷰 소품(같은 빛·카메라로 프리렌더).

타일 1칸 = 월드 45.25 단위(정사각 칸을 45° 돌려 30°로 내려다본 것).
"""
import math

import numpy as np
from PIL import Image

import sdf as S
from sdf import V, Item, Mat, hexrgb

TW, TH = 64, 32
CELL = 64 / math.sqrt(2)


# ───────────────────────── 지면 타일 ─────────────────────────

def _pnoise(u, v, period, seed):
    """uv(0..1) 위의 주기 값노이즈 (칸 경계에서 이어짐)."""
    x = u * period
    y = v * period
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    fx = x - x0
    fy = y - y0
    fx = fx * fx * (3 - 2 * fx)
    fy = fy * fy * (3 - 2 * fy)

    def hv(ix, iy):
        return S.hash2(ix % period, iy % period, seed)
    a = hv(x0, y0)
    b = hv(x0 + 1, y0)
    c = hv(x0, y0 + 1)
    d = hv(x0 + 1, y0 + 1)
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def _pfbm(u, v, base, seed, oct=3):
    t, s, a = 0, 0, 1.0
    p = base
    for o in range(oct):
        t = t + a * _pnoise(u, v, p, seed + o * 31)
        s += a
        a *= 0.5
        p *= 2
    return t / s


def _tile_uv():
    js, is_ = np.mgrid[0:TH, 0:TW]
    x = (is_ + 0.5 - TW / 2) / (TW / 2)
    y = (js + 0.5 - TH / 2) / (TH / 2)
    inside = (np.abs(x) + np.abs(y)) <= 1.0
    u = (x + y + 1) / 2   # 0..1 (남동 축)
    v = (y - x + 1) / 2   # 0..1 (남서 축)
    return u, v, inside


def _paint(ramp, idx, inside):
    ramp = np.array([hexrgb(c) for c in ramp], np.uint8)
    idx = np.clip(idx, 0, len(ramp) - 1).astype(int)
    img = np.zeros((TH, TW, 4), np.uint8)
    img[..., :3] = ramp[idx]
    img[..., 3] = np.where(inside, 255, 0)
    return img


def _cells(u, v, n, seed, jitter=0.35):
    """주기 보로노이: (가장 가까운 거리, 두 번째와의 차이, 칸 id)."""
    best = np.full(u.shape, 9.0)
    second = np.full(u.shape, 9.0)
    cid = np.zeros(u.shape, np.int64)
    x, y = u * n, v * n
    for ox in range(-1, 2):
        for oy in range(-1, 2):
            cx = np.floor(x).astype(np.int64) + ox
            cy = np.floor(y).astype(np.int64) + oy
            px = cx + 0.5 + (S.hash2(cx % n, cy % n, seed) - 0.5) * 2 * jitter
            py = cy + 0.5 + (S.hash2(cx % n, cy % n, seed + 5) - 0.5) * 2 * jitter
            d = np.sqrt((x - px) ** 2 + (y - py) ** 2)
            closer = d < best
            second = np.where(closer, best, np.minimum(second, d))
            cid = np.where(closer, (cx % n) * 97 + (cy % n), cid)
            best = np.minimum(best, d)
    return best, second - best, cid


GROUNDS = {}


def ground(name, label):
    def deco(fn):
        GROUNDS[name] = (label, fn)
        return fn
    return deco


@ground('grass', '풀밭')
def t_grass(var):
    u, v, ins = _tile_uv()
    n = _pfbm(u, v, 4, 100 + var, 3)
    fine = _pnoise(u, v, 32, 7 + var)
    idx = 1.3 + n * 2.4 + (fine - 0.5) * 1.4
    img = _paint(['#141c0f', '#1f2b16', '#2b3a1d', '#384a25', '#46592d', '#556a36'], np.floor(idx), ins)
    rng = np.random.default_rng(10 + var)
    # 풀잎 획: 아래 어둡고 끝이 밝은 2~3px
    for _ in range(46):
        x, y = rng.integers(2, TW - 2), rng.integers(3, TH - 1)
        if not ins[y, x] or not ins[y - 2, x]:
            continue
        img[y, x, :3] = hexrgb('#1a2412')
        img[y - 1, x, :3] = hexrgb('#4a5e30')
        if rng.random() < 0.5:
            img[y - 2, x + (1 if rng.random() < 0.5 else -1) if 0 < x < TW - 1 else x, :3] = hexrgb('#62773e')
    if var == 3:  # 들꽃 몇 송이
        for _ in range(5):
            x, y = rng.integers(10, TW - 10), rng.integers(8, TH - 8)
            if ins[y, x]:
                img[y, x, :3] = hexrgb(['#b9a24a', '#a8485a', '#c8c0b0'][rng.integers(3)])
    return img


@ground('dirt', '흙길')
def t_dirt(var):
    u, v, ins = _tile_uv()
    n = _pfbm(u, v, 4, 200 + var, 3)
    fine = _pnoise(u, v, 32, 17 + var)
    idx = 1.0 + n * 2.6 + (fine - 0.5) * 1.6
    img = _paint(['#21170f', '#2f2216', '#3f2e1e', '#4f3b27', '#604931', '#70573b'], np.floor(idx), ins)
    rng = np.random.default_rng(30 + var)
    for _ in range(14):  # 자갈
        x, y = rng.integers(3, TW - 3), rng.integers(2, TH - 2)
        if ins[y, x]:
            img[y, x, :3] = hexrgb('#7b6a55')
            img[y + 1, x, :3] = hexrgb('#2a1f15')
    # 바퀴 자국 (u축 방향)
    if var in (1, 2):
        for off in (0.38, 0.62):
            m = np.abs(v - off) < 0.025
            img[m & ins, :3] = (img[m & ins, :3] * 0.72).astype(np.uint8)
    return img


@ground('cobble', '돌길')
def t_cobble(var):
    u, v, ins = _tile_uv()
    d, edge, cid = _cells(u, v, 5, 300 + var, 0.3)
    tone = S.hash2(cid, cid * 3, 11 + var)
    lit = (0.5 - (u - np.floor(u * 5) / 5) * 0) * 0
    idx = 2.2 + tone * 1.6 - d * 1.1
    idx = np.where(edge < 0.09, 0, idx)
    idx = np.where((edge >= 0.09) & (edge < 0.17), np.minimum(idx, 1.4), idx)
    img = _paint(['#16130f', '#29241d', '#3b352c', '#4f483d', '#645c4f', '#797062'], np.floor(idx), ins)
    # 이끼
    moss = _pfbm(u, v, 3, 333 + var, 2)
    mm = (moss > 0.62) & (edge < 0.2) & ins
    img[mm, :3] = hexrgb('#2b3a1d')
    return img


@ground('swamp', '늪지')
def t_swamp(var):
    u, v, ins = _tile_uv()
    n = _pfbm(u, v, 3, 400 + var, 3)
    fine = _pnoise(u, v, 24, 41 + var)
    idx = 1.0 + n * 2.4 + (fine - 0.5) * 1.2
    img = _paint(['#0f120c', '#191e13', '#232a1a', '#2f3721', '#3b4529'], np.floor(idx), ins)
    water = (_pfbm(u, v, 2, 450 + var, 2) > 0.58) & ins
    wcol = np.array(hexrgb('#1a2622'))
    img[water, :3] = wcol
    shore = water & ~np.roll(water, 1, 0)
    img[shore, :3] = hexrgb('#4a5a52')
    # 수면 반짝임
    rng = np.random.default_rng(50 + var)
    ys, xs = np.nonzero(water)
    for k in rng.choice(len(ys), size=min(5, len(ys)), replace=False) if len(ys) else []:
        img[ys[k], xs[k], :3] = hexrgb('#6a7f78')
    return img


@ground('snow', '설원')
def t_snow(var):
    u, v, ins = _tile_uv()
    n = _pfbm(u, v, 4, 500 + var, 3)
    fine = _pnoise(u, v, 32, 57 + var)
    idx = 2.0 + n * 2.2 + (fine - 0.5) * 1.0
    img = _paint(['#5a6270', '#7a8494', '#99a3b2', '#b6bfcc', '#d2d9e2', '#e6ebf1'], np.floor(idx), ins)
    rng = np.random.default_rng(60 + var)
    for _ in range(10):
        x, y = rng.integers(3, TW - 3), rng.integers(2, TH - 2)
        if ins[y, x]:
            img[y, x, :3] = hexrgb('#f6f8fb')
    if var == 2:  # 발자국
        for k in range(4):
            x, y = 20 + k * 7, 12 + (k % 2) * 4
            img[y:y + 2, x:x + 2, :3] = hexrgb('#8a94a4')
    return img


@ground('dungeon', '던전 바닥')
def t_dungeon(var):
    u, v, ins = _tile_uv()
    n = 2
    fu, fv = (u * n) % 1, (v * n) % 1
    cell = (np.floor(u * n) * 7 + np.floor(v * n) * 13).astype(np.int64)
    tone = S.hash2(cell, cell + var, 77 + var)
    grime = _pfbm(u, v, 6, 600 + var, 3)
    idx = 1.6 + tone * 1.4 + (grime - 0.5) * 1.6
    edge = (np.minimum(fu, 1 - fu) < 0.035) | (np.minimum(fv, 1 - fv) < 0.035)
    hi = (fu < 0.07) | (fv < 0.07)
    idx = np.where(hi & ~edge, idx + 0.8, idx)
    idx = np.where(edge, 0, idx)
    img = _paint(['#0c0b0e', '#17151b', '#221f27', '#2d2a33', '#3a3640', '#48434f'], np.floor(idx), ins)
    if var == 3:  # 금 간 판석 + 핏자국
        crack = (np.abs(u - v * 0.6 - 0.25) < 0.012) & (u > 0.2) & (u < 0.7)
        img[crack & ins, :3] = hexrgb('#08070a')
        blood = (_pfbm(u, v, 5, 999, 2) > 0.72) & ins
        img[blood, :3] = hexrgb('#3a0e0e')
    return img


def water_frames(n=4):
    """잔물결 물 타일(애니메이션)."""
    u, v, ins = _tile_uv()
    out = []
    for f in range(n):
        ph = f / n
        w1 = _pnoise((u + ph) % 1, v, 4, 700, )
        w2 = _pnoise(u, (v + ph) % 1, 4, 701)
        w = (w1 + w2) / 2
        idx = 1.2 + w * 2.4
        img = _paint(['#0a1418', '#10202a', '#173040', '#204256', '#2e5a70', '#5e8ea2'], np.floor(idx), ins)
        crest = (np.abs(w - 0.68) < 0.02) & ins
        img[crest, :3] = hexrgb('#8fb6c4')
        out.append(img)
    return out


def build_tiles(variants=4):
    rows = []
    for name, (label, fn) in GROUNDS.items():
        rows.append((name, label, [fn(k) for k in range(variants)]))
    rows.append(('water', '물(애니)', water_frames(4)))
    sheet = np.zeros((TH * len(rows), TW * variants, 4), np.uint8)
    for r, (_, _, imgs) in enumerate(rows):
        for c, im in enumerate(imgs):
            sheet[r * TH:(r + 1) * TH, c * TW:(c + 1) * TW] = im
    return Image.fromarray(sheet, 'RGBA'), [(n, l) for n, l, _ in rows]


# ───────────────────────── 소품 재질 ─────────────────────────

def brick_tex(P, n, bw=7.0, bh=3.4):
    row = np.floor(P[:, 2] / bh)
    along = np.where(np.abs(n[:, 0]) > np.abs(n[:, 1]), P[:, 1], P[:, 0])
    off = (row % 2) * bw * 0.5
    fu = ((along + off) / bw) % 1
    fz = (P[:, 2] / bh) % 1
    mortar = (fz < 0.16) | (fu < 0.08)
    tone = S.hash2(np.floor((along + off) / bw).astype(np.int64), row.astype(np.int64), 3) - 0.5
    return np.where(mortar & (np.abs(n[:, 2]) < 0.7), -1.6, tone * 0.9)


def plank_tex(P, n):
    k = np.floor(P[:, 2] / 2.6)
    f = (P[:, 2] / 2.6) % 1
    return np.where(f < 0.18, -1.3, (S.hash2(k.astype(np.int64), k.astype(np.int64), 8) - 0.5) * 0.8)


def roof_tex(P, n):
    s = P[:, 2] * 1.0 + np.abs(P[:, 0]) * 0
    row = np.floor(P[:, 2] / 2.2)
    f = (P[:, 2] / 2.2) % 1
    col = np.floor((P[:, 1] + (row % 2) * 2) / 4)
    tone = S.hash2(col.astype(np.int64), row.astype(np.int64), 21) - 0.5
    return np.where(f < 0.22, -1.4, tone * 0.8)


def bark_tex(P, n):
    a = np.arctan2(P[:, 1], P[:, 0])
    return 0.9 * (S.vnoise(np.stack([a * 3, a * 3, P[:, 2] * 0.35], 1), 4)) - 0.2


def leaf_tex(P, n):
    return 1.1 * S.vnoise(P * 0.55, 13) + 0.5 * S.vnoise(P * 1.7, 14)


PM = {
    'bark': Mat(['#160f0a', '#241911', '#33241a', '#433123', '#543f2e'], tex=bark_tex),
    'leaf': Mat(['#0b120a', '#132014', '#1c2e1b', '#283f22', '#36522b', '#46662f'], tex=leaf_tex),
    'leaf_pine': Mat(['#08100d', '#0f1c16', '#17291f', '#21382a', '#2d4935'], tex=leaf_tex),
    'leaf_aut': Mat(['#1e0e06', '#3a1a0a', '#5a2a10', '#7a3e18', '#985420'], tex=leaf_tex),
    'rock': Mat(['#15151a', '#24242a', '#35353b', '#47474d', '#5b5a5f', '#6f6d70'],
                tex=lambda P, n: 0.9 * S.vnoise(P * 0.35, 2) + 0.4 * S.vnoise(P * 1.2, 6)),
    'moss': Mat(['#10170c', '#1a2513', '#25341a', '#324422', '#40552b'], tex=lambda P, n: 0.8 * S.vnoise(P * 0.8, 9)),
    'wall': Mat(['#1b1a1d', '#2b292d', '#3c393d', '#4f4b4f', '#625d60', '#767073'], tex=brick_tex),
    'wall_dk': Mat(['#121114', '#1e1c20', '#2a272c', '#37343a', '#45414a'], tex=brick_tex),
    'plaster': Mat(['#4a4236', '#655a4a', '#80735f', '#9a8c75', '#b2a38a'],
                   tex=lambda P, n: 0.4 * S.vnoise(P * 0.6, 4)),
    'timber': Mat(['#130c08', '#20150e', '#2e1f15', '#3d2a1c', '#4c3624']),
    'plank': Mat(['#1c130c', '#2c1e13', '#3e2b1c', '#513925', '#644830'], tex=plank_tex),
    'roof': Mat(['#1c0e0c', '#2e1714', '#43211c', '#592c24', '#6f3a2e'], tex=roof_tex),
    'roof_sl': Mat(['#111418', '#1b2026', '#262c34', '#323a44', '#404a56'], tex=roof_tex),
    'thatch': Mat(['#2a2010', '#41321a', '#5a4724', '#745d30', '#8e743e'],
                  tex=lambda P, n: 1.0 * S.vnoise(P * V(2.5, 2.5, 0.4), 31)),
    'iron': Mat(['#151619', '#25272b', '#383b40', '#4f5258', '#686c73'], metal=True, hi='#a8acb2'),
    'fire': Mat(['#8a2004', '#c84408', '#f07818', '#ffb040', '#fff0a0'], emit=True),
    'ember': Mat(['#3a0c04', '#6a1806', '#a02a08', '#d0480c', '#f07018'], emit=True),
    'water': Mat(['#08121a', '#0f2030', '#183246', '#22465e', '#30607a'], gloss=1.0, hi='#a0c8d8'),
    'cloth': Mat(['#2a1a10', '#45301e', '#62472d', '#7e5f3e', '#98774f'],
                 tex=lambda P, n: 0.3 * S.vnoise(P * 0.8, 5)),
    'cloth_red': Mat(['#2a0807', '#47100e', '#651916', '#82231e', '#9e2f27']),
    'banner': Mat(['#0e1426', '#172243', '#22335f', '#304679', '#3f5a92']),
    'gold': Mat(['#4a2e0c', '#7c5316', '#b07d22', '#d9a83a', '#f2d36b'], metal=True, hi='#fff2b8'),
    'grave': Mat(['#1e1f22', '#2f3034', '#424348', '#56575c', '#6b6c70'],
                 tex=lambda P, n: 0.6 * S.vnoise(P * 0.7, 12)),
    'bone': Mat(['#3e3829', '#6a614b', '#958a6e', '#bdb294', '#dcd3b6']),
    'dirt': Mat(['#1e150e', '#2e2116', '#3e2e1e', '#4f3b27', '#604931']),
    'crystal': Mat(['#1a2a6a', '#2a48a0', '#3e6ad0', '#6a98f0', '#b8d8ff'], gloss=1.0, hi='#ffffff'),
}


# ───────────────────────── 소품 ─────────────────────────

PROPS = {}


def prop(name, label, frame, yaw=0.0, frames=1, scale=1.0):
    def deco(fn):
        PROPS[name] = dict(label=label, frame=tuple(int(round(v * scale)) for v in frame), yaw=yaw, fn=fn, frames=frames, scale=scale)
        return fn
    return deco


def _foliage(c, r, seed, stretch=(1, 1, 0.85)):
    return S.displace(S.ellipsoid(c, V(r * stretch[0], r * stretch[1], r * stretch[2])), r * 0.22, 0.16, seed=seed, octaves=2)


@prop('oak', '참나무', (128, 150, 64, 132), scale=1.7)
def p_oak(f):
    it = [Item(S.capsule(V(0, 0, -1), V(0, 0, 30), 5.0, 3.6), 'bark'),
          Item(S.capsule(V(0, 0, 0), V(-6, 3, -1), 3.0, 1.2), 'bark'),
          Item(S.capsule(V(0, 0, 0), V(5, -4, -1), 3.0, 1.2), 'bark'),
          Item(S.capsule(V(0, 0, 24), V(-11, 2, 40), 2.6, 1.6), 'bark'),
          Item(S.capsule(V(0, 0, 26), V(10, -3, 44), 2.4, 1.4), 'bark')]
    leaves = S.sunion(6, _foliage(V(0, 0, 54), 22, 1), _foliage(V(-15, 4, 44), 15, 2), _foliage(V(15, -4, 47), 15, 3),
                      _foliage(V(3, 10, 42), 13, 4), _foliage(V(-4, -8, 66), 13, 5))
    it.append(Item(leaves, 'leaf'))
    return it


@prop('pine', '전나무', (96, 160, 48, 146), scale=1.7)
def p_pine(f):
    it = [Item(S.capsule(V(0, 0, -1), V(0, 0, 20), 3.4, 2.6), 'bark')]
    for k, (z, r, h) in enumerate(((14, 20, 26), (30, 16, 24), (45, 12, 22), (58, 8, 20))):
        c = S.displace(S.cone(V(0, 0, z), V(0, 0, z + h), r), 1.6, 0.35, seed=k + 20)
        it.append(Item(c, 'leaf_pine'))
    return it


@prop('dead_tree', '고목', (112, 140, 56, 124), scale=1.6)
def p_dead(f):
    it = [Item(S.displace(S.capsule(V(0, 0, -1), V(2, 1, 34), 5.5, 2.6), 0.8, 0.4, seed=3), 'bark')]
    br = [((2, 1, 30), (-14, 3, 50), 2.2), ((2, 1, 24), (16, -2, 40), 2.0), ((2, 1, 34), (6, 6, 60), 1.6),
          ((-8, 2, 41), (-18, -4, 56), 1.2), ((10, -1, 34), (20, 4, 52), 1.1), ((0, 0, 2), (-8, -3, -1), 2.4), ((0, 0, 2), (7, 4, -1), 2.2)]
    for a, b, r in br:
        it.append(Item(S.capsule(V(*a), V(*b), r, r * 0.4), 'bark'))
    return it


@prop('bush', '덤불', (64, 48, 32, 40), scale=1.3)
def p_bush(f):
    return [Item(S.sunion(3, _foliage(V(0, 0, 6), 9, 30), _foliage(V(-7, 2, 4), 6, 31), _foliage(V(7, -1, 5), 7, 32)), 'leaf')]


@prop('rock_big', '큰 바위', (96, 72, 48, 58), scale=1.4)
def p_rock_big(f):
    r = S.displace(S.sunion(4, S.ellipsoid(V(0, 0, 6), V(17, 13, 13)), S.ellipsoid(V(-12, 5, 3), V(9, 8, 7)),
                            S.ellipsoid(V(10, 6, 14), V(9, 8, 8))), 2.4, 0.13, seed=40, octaves=3)
    r = S.inter(r, S.halfspace(V(0, 0, -1), 0.5))
    moss = S.inter(S.displace(S.ellipsoid(V(-2, 0, 14), V(16, 12, 7)), 2.4, 0.13, seed=40, octaves=3), r)
    return [Item(r, 'rock'), Item(S.inter(S.shell(r, 0.3), S.halfspace(V(0, 0, -1), -13)), 'moss')]


@prop('rock_small', '작은 바위', (48, 40, 24, 30))
def p_rock_small(f):
    r = S.displace(S.ellipsoid(V(0, 0, 3), V(8, 6, 6)), 1.4, 0.2, seed=41, octaves=3)
    return [Item(S.inter(r, S.halfspace(V(0, 0, -1), 0.5)), 'rock')]


@prop('wall', '성벽', (128, 128, 64, 92), yaw=45, scale=2.0)
def p_wall(f):
    L = CELL / 2
    it = [Item(S.box(V(0, 0, 18), V(L, 6.0, 18)), 'wall')]
    for k in range(-2, 3):
        it.append(Item(S.box(V(k * L / 2.5, 0, 39), V(L / 7.0, 6.6, 3.2)), 'wall'))
    it.append(Item(S.box(V(0, 0, 35.5), V(L + 0.5, 6.8, 1.0)), 'wall_dk'))
    return it


@prop('tower', '성탑', (128, 176, 64, 140), yaw=45, scale=2.0)
def p_tower(f):
    it = [Item(S.cylinder(V(0, 0, 32), 15, 32), 'wall'),
          Item(S.cylinder(V(0, 0, 65), 17.5, 2.0), 'wall_dk')]
    for k in range(8):
        a = math.radians(k * 45 + 22.5)
        it.append(Item(S.box(V(math.cos(a) * 15.5, math.sin(a) * 15.5, 70), V(3.0, 2.2, 3.6), S.rz(k * 45 + 22.5)), 'wall'))
    it.append(Item(S.cone(V(0, 0, 66), V(0, 0, 92), 14), 'roof_sl'))
    it.append(Item(S.capsule(V(0, 0, 90), V(0, 0, 100), 0.5), 'iron'))
    it.append(Item(S.box(V(3.2, 0, 97), V(3.0, 0.3, 2.0)), 'banner'))
    # 창
    it.append(Item(S.box(V(0, -14.8, 44), V(1.4, 1.0, 3.2), None, 0.6), 'timber'))
    return it


@prop('gate', '성문', (160, 140, 80, 100), yaw=45, scale=2.0)
def p_gate(f):
    L = CELL * 0.75
    body = S.box(V(0, 0, 22), V(L, 7, 22))
    arch = S.union(S.box(V(0, 0, 10), V(10, 9, 12)), S.cylinder(V(0, 0, 22), 10, 9, S.frame_from(V(0, 1, 0))))
    it = [Item(S.sub(body, arch), 'wall')]
    for k in range(-3, 4):
        it.append(Item(S.box(V(k * L / 3.5, 0, 47), V(L / 9, 7.6, 3.2)), 'wall'))
    it.append(Item(S.inter(S.box(V(0, 2, 14), V(10, 1.0, 16)), arch), 'plank'))
    for k in range(-4, 5):
        it.append(Item(S.inter(S.box(V(k * 2.4, 1.2, 14), V(0.4, 0.6, 16)), arch), 'iron'))
    for sx in (-1, 1):
        it.append(Item(S.box(V(sx * (L - 4), -7.5, 30), V(3, 0.4, 8)), 'banner'))
        it.append(Item(S.box(V(sx * (L - 4), -7.8, 31), V(0.8, 0.3, 3)), 'gold'))
    return it


@prop('house', '마을 집', (160, 150, 80, 112), yaw=45, scale=2.0)
def p_house(f):
    W_, D_, Hh = 20, 15, 18
    it = [Item(S.box(V(0, 0, Hh / 2), V(W_, D_, Hh / 2)), 'plaster')]
    # 목재 골조
    for x in (-W_, -W_ / 3, W_ / 3, W_):
        for y in (-D_, D_):
            it.append(Item(S.box(V(x, y, Hh / 2), V(1.0, 0.6, Hh / 2)), 'timber'))
    for y in (-D_, D_):
        it.append(Item(S.box(V(0, y, Hh - 0.8), V(W_, 0.7, 0.9)), 'timber'))
        it.append(Item(S.box(V(0, y, 1.0), V(W_, 0.7, 1.0)), 'timber'))
    for x in (-W_, W_):
        it.append(Item(S.box(V(x, 0, Hh - 0.8), V(0.7, D_, 0.9)), 'timber'))
    # 지붕(박공): 45° 돌린 상자를 바닥면으로 자름
    roof = S.box(V(0, 0, Hh), V(W_ + 3, (D_ + 4) / math.sqrt(2), (D_ + 4) / math.sqrt(2)), S.rx(45))
    roof = S.inter(roof, S.halfspace(V(0, 0, -1), -Hh + 0.5))
    inner = S.box(V(0, 0, Hh - 2.0), V(W_ + 1, (D_ + 1) / math.sqrt(2), (D_ + 1) / math.sqrt(2)), S.rx(45))
    it.append(Item(S.sub(roof, S.inter(inner, S.halfspace(V(1, 0, 0), W_ + 1), S.halfspace(V(-1, 0, 0), W_ + 1))), 'roof'))
    # 박공벽
    gable = S.inter(S.box(V(0, 0, Hh), V(W_ - 0.2, D_ / math.sqrt(2), D_ / math.sqrt(2)), S.rx(45)), S.halfspace(V(0, 0, -1), -Hh))
    it.append(Item(gable, 'plaster'))
    # 문, 창문, 굴뚝
    it.append(Item(S.box(V(-W_ / 1.6, -D_ - 0.4, 6), V(3.2, 0.8, 6), None, 0.3), 'plank'))
    it.append(Item(S.box(V(W_ / 1.6, -D_ - 0.3, 10), V(2.8, 0.6, 2.4), None, 0.3), 'ember'))
    it.append(Item(S.box(V(W_ / 1.6, -D_ - 0.5, 10), V(3.2, 0.5, 0.4)), 'timber'))
    it.append(Item(S.box(V(W_ / 1.6, -D_ - 0.5, 10), V(0.4, 0.5, 2.6)), 'timber'))
    it.append(Item(S.box(V(-W_ - 0.3, 6, 10), V(0.6, 2.6, 2.2), None, 0.3), 'ember'))
    it.append(Item(S.box(V(W_ * 0.55, 6, Hh + 9), V(2.8, 2.8, 7)), 'wall'))
    return it


@prop('well', '우물', (80, 88, 40, 66), scale=1.5)
def p_well(f):
    ring = S.sub(S.cylinder(V(0, 0, 4.5), 10, 4.5), S.cylinder(V(0, 0, 6), 7.5, 6))
    it = [Item(ring, 'wall'), Item(S.cylinder(V(0, 0, 6.0), 7.6, 0.6), 'water')]
    for sx in (-1, 1):
        it.append(Item(S.box(V(sx * 9, 0, 14), V(0.9, 0.9, 10)), 'timber'))
    it.append(Item(S.capsule(V(-9.5, 0, 20), V(9.5, 0, 20), 0.9), 'timber'))
    roof = S.inter(S.box(V(0, 0, 25), V(12, 9.5, 9.5), S.rx(45)), S.halfspace(V(0, 0, -1), -24))
    it.append(Item(roof, 'roof'))
    it.append(Item(S.capsule(V(0, 0, 20), V(0, 0, 11), 0.25), 'cloth'))
    it.append(Item(S.cylinder(V(0, 0, 10), 1.8, 1.6), 'plank'))
    return it


@prop('fence', '나무 울타리', (80, 56, 40, 36), yaw=45, scale=1.5)
def p_fence(f):
    L = CELL / 2
    it = []
    for x in (-L + 2, 0, L - 2):
        it.append(Item(S.box(V(x, 0, 6.5), V(1.2, 1.2, 6.5), None, 0.4), 'timber'))
    for z in (4.5, 9.5):
        it.append(Item(S.box(V(0, 0, z), V(L, 0.6, 1.0), None, 0.3), 'plank'))
    return it


@prop('torch', '화톳불 받침', (48, 80, 24, 70), frames=4, scale=1.3)
def p_torch(f):
    it = [Item(S.capsule(V(0, 0, 0), V(0, 0, 18), 1.4, 1.0), 'iron'),
          Item(S.sub(S.cylinder(V(0, 0, 21), 4.2, 2.6), S.cylinder(V(0, 0, 23), 3.4, 2.2)), 'iron'),
          Item(S.cylinder(V(0, 0, 22), 3.5, 1.4), 'ember')]
    for k in range(3):
        a = math.radians(k * 120)
        it.append(Item(S.capsule(V(0, 0, 4), V(math.cos(a) * 5, math.sin(a) * 5, 0), 0.7), 'iron'))
    it += _flame(V(0, 0, 23), 3.4, 9, f)
    return it


def _flame(base, r, h, f):
    out = []
    for k in range(3):
        ph = (f / 4 + k / 3) * 2 * math.pi
        tip = base + V(math.sin(ph) * 1.2, math.cos(ph * 1.3) * 0.8, h * (0.75 + 0.25 * math.sin(ph + k)))
        off = V(math.cos(k * 2.1) * r * 0.4, math.sin(k * 2.1) * r * 0.4, 0)
        out.append(Item(S.capsule(base + off, tip, r * (0.7 - k * 0.12), 0.2), 'fire'))
    return out


@prop('campfire', '모닥불', (64, 64, 32, 48), frames=4, scale=1.2)
def p_campfire(f):
    it = []
    for k in range(7):
        a = math.radians(k * 360 / 7)
        it.append(Item(S.ellipsoid(V(math.cos(a) * 8, math.sin(a) * 8, 1.6), V(2.6, 2.2, 2.0)), 'rock'))
    for k in range(3):
        a = math.radians(k * 60)
        it.append(Item(S.capsule(V(math.cos(a) * 6, math.sin(a) * 6, 1.2), V(-math.cos(a) * 6, -math.sin(a) * 6, 1.8), 1.2), 'timber'))
    it.append(Item(S.cylinder(V(0, 0, 1.6), 4, 0.8), 'ember'))
    it += _flame(V(0, 0, 2), 3.8, 12, f)
    return it


@prop('grave', '묘비', (48, 56, 24, 44), scale=1.3)
def p_grave(f):
    st = S.union(S.box(V(0, 0, 7), V(5, 1.6, 7), None, 0.4), S.cylinder(V(0, 0, 14), 5, 1.6, S.frame_from(V(0, 1, 0)), 0.4))
    st = S.inter(st, S.halfspace(V(0, 0, 1), 19))
    st = S.displace(st, 0.4, 0.5, seed=8)
    cross = S.union(S.box(V(0, -1.7, 12), V(0.5, 0.3, 3.5)), S.box(V(0, -1.7, 13.2), V(2.2, 0.3, 0.5)))
    return [Item(S.xform(st, S.rz(8), V(0, 0, 0)), 'grave'), Item(S.xform(cross, S.rz(8), V(0, 0, 0)), 'wall_dk'),
            Item(S.ellipsoid(V(0, -6, 0.6), V(5, 7, 1.6)), 'dirt')]


@prop('cross_grave', '나무 십자가 무덤', (48, 64, 24, 52), scale=1.3)
def p_cgrave(f):
    return [Item(S.box(V(0, 0, 9), V(0.9, 0.9, 9), None, 0.2), 'timber'),
            Item(S.box(V(0, 0, 13), V(5, 0.9, 0.9), None, 0.2), 'timber'),
            Item(S.ellipsoid(V(0, -7, 0.4), V(5.5, 8, 2.2)), 'dirt'),
            Item(S.sphere(V(2.5, -10, 1.5), 1.6), 'bone')]


@prop('barrel', '술통', (40, 48, 20, 38))
def p_barrel(f):
    body = S.inter(S.ellipsoid(V(0, 0, 7.5), V(6.4, 6.4, 11)), S.halfspace(V(0, 0, 1), 15), S.halfspace(V(0, 0, -1), 0))
    hoops = [S.inter(S.shell(S.ellipsoid(V(0, 0, 7.5), V(6.6, 6.6, 11.1)), 0.15), S.box(V(0, 0, z), V(8, 8, 0.7))) for z in (2.5, 12.5)]
    return [Item(body, 'plank'), Item(S.union(*hoops), 'iron'), Item(S.cylinder(V(0, 0, 15), 5.2, 0.3), 'timber')]


@prop('crate', '나무 상자', (48, 48, 24, 38), yaw=20)
def p_crate(f):
    b = S.box(V(0, 0, 6), V(6.5, 6.5, 6), None, 0.4)
    edges = S.sub(S.box(V(0, 0, 6), V(6.8, 6.8, 6.3), None, 0.4), S.box(V(0, 0, 6), V(5.3, 5.3, 7)),
                  S.box(V(0, 0, 6), V(5.3, 7.5, 4.8)), S.box(V(0, 0, 6), V(7.5, 5.3, 4.8)))
    return [Item(b, 'plank'), Item(edges, 'timber')]


@prop('signpost', '이정표', (56, 72, 28, 60), scale=1.3)
def p_sign(f):
    return [Item(S.box(V(0, 0, 12), V(1.0, 1.0, 12), None, 0.3), 'timber'),
            Item(S.box(V(5, 0, 19), V(7, 0.6, 2.2), S.rz(-20), 0.3), 'plank'),
            Item(S.box(V(-4, 0, 13), V(6, 0.6, 2.0), S.rz(35), 0.3), 'plank')]


@prop('tent', '야영 천막', (112, 88, 56, 62), yaw=45, scale=1.5)
def p_tent(f):
    t = S.inter(S.box(V(0, 0, 0), V(16, 14, 14), S.rx(45)), S.halfspace(V(0, 0, -1), 0))
    hole = S.inter(S.box(V(0, -14, 0), V(4, 6, 10), S.rx(45)), S.halfspace(V(0, 0, -1), 0))
    return [Item(S.sub(t, hole), 'cloth'), Item(S.capsule(V(-17, 0, 0), V(-17, 0, 22), 0.6), 'timber'),
            Item(S.capsule(V(17, 0, 0), V(17, 0, 22), 0.6), 'timber'),
            Item(S.inter(S.box(V(0, -13.5, 0), V(4.4, 1, 10), S.rx(45)), S.halfspace(V(0, 0, -1), 0)), 'cloth_red')]


@prop('pillar', '부서진 기둥', (64, 112, 32, 96), scale=1.5)
def p_pillar(f):
    shaft = S.cylinder(V(0, 0, 20), 5.5, 20)
    fl = [S.box(V(math.cos(math.radians(a)) * 5.6, math.sin(math.radians(a)) * 5.6, 20), V(0.6, 0.6, 21), S.rz(a)) for a in range(0, 360, 45)]
    shaft = S.sub(shaft, *fl)
    top = S.halfspace(S.nrm(V(0.3, -0.2, 1)), 38)
    it = [Item(S.box(V(0, 0, 2), V(8, 8, 2), None, 0.4), 'grave'),
          Item(S.inter(shaft, top), 'grave'),
          Item(S.box(V(9, -6, 1.6), V(3.5, 2.5, 1.6), S.rz(30), 0.5), 'grave'),
          Item(S.inter(S.shell(S.inter(shaft, top), 0.25), S.halfspace(V(0, 0, 1), 9)), 'moss')]
    return it


@prop('crystal', '마나 수정', (64, 88, 32, 72), frames=1, scale=1.4)
def p_crystal(f):
    it = [Item(S.displace(S.ellipsoid(V(0, 0, 2), V(9, 8, 4)), 1.2, 0.3, seed=55), 'rock')]
    for k, (x, y, h, r, lean) in enumerate(((0, 0, 22, 4.2, 0), (-5, 2, 14, 2.8, -20), (5, -2, 12, 2.6, 22), (2, 5, 9, 2.0, 12))):
        a, b = V(x, y, 2), V(x + math.sin(math.radians(lean)) * h, y, 2 + h * math.cos(math.radians(lean)))
        it.append(Item(S.capsule(a, b, r, 0.3), 'crystal'))
    return it


@prop('bones', '해골 더미', (56, 40, 28, 30))
def p_bones(f):
    it = [Item(S.sub(S.sphere(V(0, 0, 3), 3.2), S.sphere(V(1.2, -2.8, 3.4), 1.0), S.sphere(V(-1.2, -2.8, 3.4), 1.0)), 'bone')]
    for a, b in (((-8, 2, 1), (2, 6, 1)), ((4, -4, 1), (11, 1, 1)), ((-6, -4, 1), (-11, 2, 1.5))):
        it.append(Item(S.capsule(V(*a), V(*b), 0.9), 'bone'))
    return it


def build_props():
    out = {}
    for name, d in PROPS.items():
        W, H, ax, ay = d['frame']
        imgs = []
        for f in range(d['frames']):
            imgs.append(S.render(d['fn'](f), PM, W, H, ax, ay, yaw=d['yaw'] + 180, scale=d['scale']))
        out[name] = imgs
    return out
