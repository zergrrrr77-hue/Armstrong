#!/usr/bin/env python3
"""《잊혀진 대장간》 16비트 픽셀 에셋 생성기.

모든 픽셀을 코드로 찍어서 Godot 4용 PNG·스프라이트 시트·리소스(.tres)를 만든다.
색이나 포즈를 바꾸고 다시 실행하면 같은 규격으로 전부 새로 뽑힌다.

실행:  python3 forgotten-forge/tools/make_assets.py
출력:  forgotten-forge/assets/          (게임용 에셋 — Godot 프로젝트 루트에 그대로 복사)
       forgotten-forge/assets-preview/  (확인용 확대 미리보기 — 게임에는 넣지 않음)
"""
import math
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets')
PREVIEW = os.path.join(ROOT, 'assets-preview')

# ───────────────────────── 팔레트 (모든 에셋 공용) ─────────────────────────
PAL = {
    'ol': '#1a1220', 'w': '#ffffff',
    # 피부 · 머리
    'sk0': '#f8dcc0', 'sk1': '#f2c8a0', 'sk2': '#d89c74', 'sk3': '#a8664a',
    'hr0': '#c08850', 'hr1': '#8a5230', 'hr2': '#6a3a20', 'hr3': '#4a2414',
    # 모험가 복장 (파랑) · 망토 (빨강) · 가죽 · 바지
    'bl0': '#7aa8e8', 'bl1': '#5a8ad0', 'bl2': '#3a62a8', 'bl3': '#284080', 'bl4': '#1a2a58',
    'rd0': '#f07858', 'rd1': '#e05040', 'rd2': '#b83030', 'rd3': '#7a1c24',
    'lt0': '#b07a48', 'lt1': '#8a5a34', 'lt2': '#5e3a20', 'lt3': '#3a2414',
    'pt1': '#4a4460', 'pt2': '#3a3448', 'pt3': '#262234',
    # 금속 · 금
    'mt0': '#f0f4f8', 'mt1': '#c4ccd8', 'mt2': '#8a94a8', 'mt3': '#5a6278', 'mt4': '#3a4050',
    'gd0': '#f8e080', 'gd1': '#f0c850', 'gd2': '#b88a2a', 'gd3': '#7a5a1a',
    # 자연: 풀 · 흙 · 돌 · 물 · 나무 · 꽃
    'gr0': '#c8f088', 'gr1': '#a8e070', 'gr2': '#6cc048', 'gr3': '#3e9038', 'gr4': '#276028', 'gr5': '#163c1c',
    'dt0': '#d8a868', 'dt1': '#c8965a', 'dt2': '#a06e3c', 'dt3': '#7a5030', 'dt4': '#54361e', 'dt5': '#3a2414',
    'st0': '#d8d4e0', 'st1': '#b8b4c0', 'st2': '#8a8696', 'st3': '#5e5a6c', 'st4': '#3e3a4a',
    'wa0': '#e8f8ff', 'wa1': '#8ad0f0', 'wa2': '#4a98d8', 'wa3': '#2a64a8', 'wa4': '#1a3c78',
    'wd0': '#c89060', 'wd1': '#a06a3c', 'wd2': '#7a4a28', 'wd3': '#54301a',
    'fl1': '#f080a8', 'fl2': '#f8e060', 'fl3': '#a080f0', 'fl4': '#ff9050',
    # 희귀도 색: 달빛 · 불꽃
    'mo0': '#e0f8ff', 'mo1': '#a8e0ff', 'mo2': '#6ab8f0', 'mo3': '#2a5ad8',
    'fi0': '#fff0a0', 'fi1': '#ffb030', 'fi2': '#f06020', 'fi3': '#a02818',
}
RGB = {k: tuple(int(v[i:i + 2], 16) for i in (1, 3, 5)) for k, v in PAL.items()}


def h(x, y, s=0):
    """결정적 해시 노이즈 (0~1). 같은 좌표는 항상 같은 값 → 타일이 이음새 없이 반복된다."""
    n = (x * 374761393 + y * 668265263 + s * 982451653) & 0xffffffff
    n = ((n ^ (n >> 13)) * 1274126177) & 0xffffffff
    return ((n ^ (n >> 16)) & 0xffffffff) / 4294967296.0


def rnd(v):
    return int(math.floor(v + 0.5))


class Cv:
    """팔레트 이름으로 찍는 작은 픽셀 캔버스. 안티앨리어싱 없음."""

    def __init__(self, w, h_):
        self.w, self.h, self.p, self.ol = w, h_, {}, set()

    def px(self, x, y, c):
        x, y = rnd(x), rnd(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            if c is None:
                self.p.pop((x, y), None)
            else:
                self.p[(x, y)] = c

    def get(self, x, y):
        return self.p.get((x, y))

    def rect(self, x, y, w, h_, c):
        for yy in range(rnd(y), rnd(y) + rnd(h_)):
            for xx in range(rnd(x), rnd(x) + rnd(w)):
                self.px(xx, yy, c)

    def line(self, x0, y0, x1, y1, c):
        x0, y0, x1, y1 = rnd(x0), rnd(y0), rnd(x1), rnd(y1)
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.px(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def ell(self, cx, cy, rx, ry, c):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1:
                    self.px(x, y, c)

    def poly(self, pts, c):
        ys = [p[1] for p in pts]
        for y in range(int(min(ys)), int(max(ys)) + 1):
            yc = y + 0.5
            xs = []
            for i in range(len(pts)):
                (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
                if (y0 <= yc < y1) or (y1 <= yc < y0):
                    xs.append(x0 + (yc - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                for x in range(int(math.ceil(xs[i] - 0.5)), int(math.floor(xs[i + 1] - 0.5)) + 1):
                    self.px(x, y, c)

    def blit(self, o, ox=0, oy=0):
        for (x, y), c in o.p.items():
            self.px(x + ox, y + oy, c)
        for (x, y) in o.ol:
            self.ol.add((x + ox, y + oy))

    def outline(self, c='ol'):
        add = []
        for y in range(self.h):
            for x in range(self.w):
                if (x, y) in self.p:
                    continue
                if any((x + dx, y + dy) in self.p for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    add.append((x, y))
        for q in add:
            self.p[q] = c
            self.ol.add(q)
        return self

    def flash(self):
        """피격 순간용 흰색 실루엣 (외곽선은 유지)."""
        o = Cv(self.w, self.h)
        for q, c in self.p.items():
            o.p[q] = c if q in self.ol else 'w'
        o.ol = set(self.ol)
        return o

    def image(self):
        im = Image.new('RGBA', (self.w, self.h), (0, 0, 0, 0))
        px = im.load()
        for (x, y), c in self.p.items():
            px[x, y] = RGB[c] + (255,)
        return im


def rotate(cv, deg, pivot):
    """최근접 회전 (넘어지는 프레임용). 화면 기준 시계 방향이 +."""
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    out = {}
    pts = list(cv.p.items())
    xs = [p[0][0] for p in pts]
    ys = [p[0][1] for p in pts]
    # 회전 후 범위를 넉넉히 훑으며 역변환으로 원본 색을 가져온다
    for y in range(-40, 72):
        for x in range(-40, 72):
            dx, dy = x - pivot[0], y - pivot[1]
            sx = pivot[0] + dx * ca + dy * sa
            sy = pivot[1] - dx * sa + dy * ca
            q = (rnd(sx), rnd(sy))
            if q in cv.p:
                out[(x, y)] = cv.p[q]
    return out


def place(points, w, h_, bottom, center_x):
    """회전된 픽셀 묶음을 바닥선·가로 중앙에 맞춰 새 캔버스에 놓는다."""
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    ox = center_x - (min(xs) + max(xs)) // 2
    oy = bottom - max(ys)
    c = Cv(w, h_)
    for (x, y), col in points.items():
        c.px(x + ox, y + oy, col)
    return c


# ───────────────────────── 검 (손에 쥔 모습 · 아이콘 공용 색 규칙) ─────────────────────────
# 형태 규칙은 고정, 등급마다 색 슬롯만 바꾼다. README 표와 같은 순서.
SWORD_RULES = {
    'rusty':  {'name': '낡은 검',          'grade': '일반', 'edge': 'mt1', 'blade': 'mt2', 'shadow': 'mt3', 'fuller': None,  'guard': ('mt3', 'mt4'), 'grip': ('lt1', 'lt2'), 'pommel': 'mt3', 'gem': None},
    'hunter': {'name': '숲 사냥꾼의 검',   'grade': '고급', 'edge': 'mt0', 'blade': 'mt1', 'shadow': 'mt2', 'fuller': 'mt2', 'guard': ('gd1', 'gd2'), 'grip': ('gr3', 'gr4'), 'pommel': 'gd1', 'gem': 'gr2'},
    'moon':   {'name': '달빛 검',          'grade': '희귀', 'edge': 'mo0', 'blade': 'mo1', 'shadow': 'mo2', 'fuller': 'mo3', 'guard': ('mt0', 'mt2'), 'grip': ('bl3', 'bl4'), 'pommel': 'mt1', 'gem': 'mo3'},
    'ember':  {'name': '꺼지지 않는 불씨', 'grade': '전설', 'edge': 'fi0', 'blade': 'fi1', 'shadow': 'fi2', 'fuller': 'fi3', 'guard': ('gd1', 'gd2'), 'grip': ('lt3', 'gd2'), 'pommel': 'gd1', 'gem': 'rd1'},
}


def hand_sword(c, x, y, ang, rule='rusty', length=11):
    """손 위치 (x, y)에서 각도 ang(0=오른쪽, 90=아래)으로 뻗은 검."""
    r = SWORD_RULES[rule]
    a = math.radians(ang)
    dx, dy = math.cos(a), math.sin(a)
    nx, ny = -dy, dx
    for t in (-1, -2):
        c.px(x + dx * t, y + dy * t, r['grip'][0] if t == -1 else r['grip'][1])
    c.px(x - dx * 3, y - dy * 3, r['pommel'])
    t = 2.0
    while t <= length:
        c.px(x + dx * t, y + dy * t, r['blade'])
        if t < length - 1:
            c.px(x + dx * t - nx, y + dy * t - ny, r['edge'])
        t += 0.5
    for k in (-2, -1, 0, 1, 2):
        c.px(x + dx * 1 + nx * k, y + dy * 1 + ny * k, r['guard'][0] if abs(k) < 2 else r['guard'][1])


def smear(c, cx, cy, a0, a1, r1, col_out='w', col_in='mt1', maxthick=3.5):
    """초승달 모양 베기 잔상."""
    lo, hi = min(a0, a1), max(a0, a1)
    for y in range(c.h):
        for x in range(c.w):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            ang = math.degrees(math.atan2(y + 0.5 - cy, x + 0.5 - cx))
            if not lo <= ang <= hi:
                continue
            t = (ang - lo) / (hi - lo)
            th = 0.8 + maxthick * math.sin(math.pi * t)
            if r1 - th <= d <= r1:
                c.px(x, y, col_out if d > r1 - 1.2 else col_in)


# ───────────────────────── 플레이어: 이름 없는 모험가 ─────────────────────────
def player_body(pose):
    P = dict(bob=0, lean=0, bx=0, fl=(0, 0), bl=(0, 0), hand=(19, 21), ang=50, cape=0,
             face='normal', mouth=False, smear=None, kneel=False, sword=True, arm_down=False, sword_back=False)
    P.update(pose)
    c = Cv(32, 32)
    b, L, X = P['bob'], P['lean'], P['bx']

    # 짧은 붉은 망토 (몸 뒤)
    wave = P['cape']
    top, bot = 15 + b, 22 + b
    for y in range(top, bot + 1):
        k = y - top
        xl = 12 + X - (k * 5) // 8 - (wave if k > 3 else 0) - (1 if k > 5 and wave > 1 else 0)
        for x in range(xl, 14 + X):
            col = 'rd2'
            if k == 0:
                col = 'rd1'
            elif x == xl:
                col = 'rd3' if k > 2 else 'rd2'
            elif x == xl + 1 and k > 3:
                col = 'rd1'
            elif x == 13 + X:
                col = 'rd3'
            if y == bot and (x - xl) % 2 == 1:
                continue
            c.px(x, y, col)

    # 머리 뒤로 치켜든 검은 몸보다 먼저 그린다
    if P['sword'] and P['sword_back']:
        hand_sword(c, P['hand'][0] + X, P['hand'][1], P['ang'])

    # 다리 (윗몸 흔들림과 분리)
    def leg(x, lift, back):
        pc, bc = ('pt3', 'lt3') if back else ('pt2', 'lt2')
        for y in range(23, 28 - lift):
            c.rect(x, y, 2, 1, pc)
        c.rect(x, 28 - lift, 3, 2, bc)
        c.px(x + 2, 28 - lift, 'lt1' if not back else 'lt2')
        c.rect(x, 30 - lift, 3, 1, 'ol' if back else 'lt3')

    if P['kneel']:
        # 한쪽 무릎을 꿇은 자세
        c.rect(13 + X, 26, 2, 3, 'pt3'); c.rect(9 + X, 29, 5, 1, 'pt3'); c.rect(7 + X, 29, 3, 2, 'lt3')
        c.rect(15 + X, 25, 5, 2, 'pt2'); c.rect(19 + X, 27, 2, 2, 'pt2'); c.rect(19 + X, 29, 3, 2, 'lt2')
    else:
        leg(13 + X + P['bl'][0], P['bl'][1], True)
        leg(16 + X + P['fl'][0], P['fl'][1], False)

    # 뒷팔 (소매)
    c.rect(12 + X, 16 + b, 1, 4, 'bl3')
    # 몸통: 파란 모험가 튜닉 + 가죽 벨트
    c.rect(12 + X, 15 + b, 7, 7, 'bl2')
    c.rect(12 + X, 15 + b, 2, 7, 'bl3')
    c.rect(17 + X, 16 + b, 1, 4, 'bl1')
    c.rect(14 + X, 15 + b, 4, 1, 'bl1')
    c.rect(11 + X, 21 + b, 9, 2, 'bl2')
    c.rect(11 + X, 22 + b, 9, 1, 'bl3')
    c.px(18 + X, 21 + b, 'bl1')
    c.rect(12 + X, 20 + b, 7, 1, 'lt2')
    c.px(16 + X, 20 + b, 'gd1')
    c.px(13 + X, 15 + b, 'gd1')  # 망토 걸쇠

    # 머리
    hx, hy = 11 + X + L, 6 + b
    c.rect(hx + 1, hy + 2, 8, 6, 'sk1')
    c.rect(hx + 2, hy + 8, 6, 1, 'sk1')
    c.rect(hx + 1, hy + 2, 1, 6, 'sk2')
    c.px(hx + 2, hy + 8, 'sk2')
    c.px(hx + 9, hy + 5, 'sk1')
    c.px(hx + 8, hy + 2, 'sk0')
    c.px(hx + 4, hy + 5, 'sk2'); c.px(hx + 4, hy + 6, 'sk2')
    f = P['face']
    if f == 'hurt':
        c.px(hx + 6, hy + 4, 'ol'); c.px(hx + 7, hy + 5, 'ol'); c.px(hx + 6, hy + 6, 'ol')
    elif f == 'closed':
        c.rect(hx + 6, hy + 5, 2, 1, 'ol')
    elif f == 'dead':
        c.px(hx + 6, hy + 4, 'ol'); c.px(hx + 8, hy + 4, 'ol'); c.px(hx + 7, hy + 5, 'ol'); c.px(hx + 6, hy + 6, 'ol'); c.px(hx + 8, hy + 6, 'ol')
    else:
        c.px(hx + 6, hy + 4, 'w'); c.rect(hx + 7, hy + 4, 1, 2, 'ol')
        c.rect(hx + 6, hy + 3, 2, 1, 'hr3') if f != 'fierce' else (c.px(hx + 6, hy + 3, 'hr3'), c.px(hx + 7, hy + 3, 'hr3'), c.px(hx + 8, hy + 3, 'hr3'))
    if P['mouth']:
        c.rect(hx + 7, hy + 7, 2, 1, 'rd3')
    else:
        c.px(hx + 8, hy + 7, 'sk3')
    # 헝클어진 갈색 머리
    c.rect(hx, hy, 9, 2, 'hr1')
    c.rect(hx + 1, hy - 1, 7, 1, 'hr1')
    c.rect(hx - 1, hy + 1, 4, 6, 'hr1')
    c.rect(hx + 2, hy + 2, 7, 1, 'hr1')
    c.px(hx + 5, hy + 3, 'hr1'); c.px(hx + 8, hy + 3, 'hr1'); c.px(hx + 9, hy + 2, 'hr2')
    c.rect(hx + 3, hy + 3, 1, 2, 'hr2')
    for q in ((1, -2), (4, -2), (5, -3), (7, -2), (-1, 0), (-2, 1), (9, 0), (2, -2)):
        c.px(hx + q[0], hy + q[1], 'hr1')
    c.px(hx - 2, hy + 4, 'hr2'); c.px(hx - 1, hy + 7, 'hr2'); c.px(hx - 2, hy + 6, 'hr2')
    c.rect(hx + 2, hy, 4, 1, 'hr0'); c.px(hx + 6, hy - 1, 'hr0'); c.px(hx, hy + 2, 'hr0'); c.px(hx + 5, hy - 3, 'hr0')
    c.rect(hx - 1, hy + 5, 2, 2, 'hr2'); c.px(hx + 1, hy + 1, 'hr2')

    # 베기 잔상 (몸 앞)
    if P['smear']:
        a0, a1, strength = P['smear']
        smear(c, 17 + X, 16 + b, a0, a1, 14, maxthick=strength)

    # 앞팔 + 검
    sx_, sy_ = 17 + X, 16 + b
    hx_, hy_ = P['hand'][0] + X, P['hand'][1]
    if P['sword'] and not P['sword_back']:
        hand_sword(c, hx_, hy_, P['ang'])
    c.line(sx_, sy_, hx_, hy_, 'bl2')
    c.px(sx_, sy_ + 1, 'bl3')
    c.px(hx_, hy_, 'sk1')
    c.px(hx_ + (1 if P['ang'] > -90 else -1), hy_, 'sk2')
    return c


def player_frames():
    an = {}
    an['idle'] = [player_body(dict(bob=b_, cape=w_, hand=(19, 20 + b_), ang=52))
                  for b_, w_ in ((0, 0), (0, 1), (1, 1), (1, 0))]
    walk = []
    cyc = [(2, 0, -2, 1, 0), (1, 1, -1, 0, 1), (-1, 0, 1, 0, 0), (-2, 0, 2, 1, 0), (-1, 0, 1, 0, 1), (1, 1, -1, 0, 0)]
    for i, (fdx, flift, bdx, blift, b_) in enumerate(cyc):
        walk.append(player_body(dict(bob=b_, fl=(fdx, flift), bl=(bdx, blift), cape=1 + (i % 3 == 0), hand=(19 + (fdx > 0), 20 + b_), ang=48 + fdx * 3)))
    an['walk'] = walk
    an['attack'] = [
        player_body(dict(bx=-1, lean=-1, hand=(13, 12), ang=-145, face='fierce', cape=0, sword_back=True)),
        player_body(dict(bx=-1, hand=(15, 9), ang=-105, face='fierce', cape=1, fl=(1, 0), sword_back=True)),
        player_body(dict(lean=1, hand=(21, 12), ang=-25, face='fierce', mouth=True, fl=(2, 0), bl=(-1, 0), cape=2, smear=(-110, -25, 2.5))),
        player_body(dict(bx=1, lean=1, hand=(22, 18), ang=28, face='fierce', mouth=True, fl=(2, 0), bl=(-2, 0), cape=2, smear=(-70, 28, 3.5))),
        player_body(dict(bx=1, lean=1, hand=(21, 21), ang=72, face='fierce', fl=(2, 0), bl=(-2, 0), cape=1)),
        player_body(dict(hand=(20, 21), ang=58, cape=0, fl=(1, 0))),
    ]
    hurt0 = player_body(dict(bx=-1, lean=-1, hand=(18, 21), ang=75, face='hurt', mouth=True, cape=2))
    an['hurt'] = [hurt0, hurt0.flash(), player_body(dict(hand=(19, 21), ang=60, face='closed', cape=1))]
    limp = player_body(dict(face='dead', sword=False, hand=(18, 22), cape=0))
    limp.ol = set()
    death = [
        player_body(dict(bx=-1, lean=-2, hand=(17, 23), ang=95, face='hurt', mouth=True, cape=2)),
        player_body(dict(bob=4, lean=1, kneel=True, hand=(19, 25), ang=88, face='closed', cape=0)),
    ]
    for deg in (-55, -90):
        c = place(rotate(limp, deg, (15, 30)), 32, 32, 30, 15 if deg == -90 else 14)
        hand_sword(c, 22, 30, 0)  # 떨어진 검
        death.append(c)
    an['death'] = death
    for k in an:
        an[k] = [fr if fr.ol else fr.outline('ol') for fr in an[k]]
    # 첫 프레임 외 outline 누락 방지 (flash 프레임은 이미 외곽선 보유)
    return an


# ───────────────────────── 슬라임 ─────────────────────────
def slime_body(rx, ry, ox=0, oy=0, eyes='normal', mouth='smile', drops=()):
    c = Cv(32, 32)
    cx, by = 16 + ox, 30 + oy
    cy = by + 1 - ry * 0.92
    for y in range(32):
        for x in range(32):
            if y > by:
                continue
            nx, ny = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
            if nx * nx + ny * ny > 1:
                continue
            col = 'gr2'
            if ny > 0.78 or (nx * nx + ny * ny > 0.82 and ny > 0.2):
                col = 'gr4'
            elif ny > 0.42 or nx > 0.72:
                col = 'gr3'
            elif (nx + 0.38) ** 2 + (ny + 0.42) ** 2 < 0.13:
                col = 'gr1'
            c.px(x, y, col)
    # 반짝임 + 안쪽 기포
    c.px(cx - rx * 0.45, cy - ry * 0.5, 'gr0'); c.px(cx - rx * 0.45 + 1, cy - ry * 0.5, 'w') if ry > 4 else None
    if ry > 5:
        c.px(cx + rx * 0.45, cy + ry * 0.25, 'gr1')
    # 표정 (오른쪽을 바라봄)
    ex, ey = rnd(cx + rx * 0.12), rnd(cy - ry * 0.12)
    for e in (ex - 1, ex + 3):
        if eyes == 'x':
            for q in ((-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)):
                c.px(e + q[0] + 1, ey + q[1], 'gr5')
        elif ry < 4:
            c.rect(e, ey, 2, 1, 'ol')
        else:
            c.rect(e, ey, 2, 2, 'ol')
            c.px(e, ey, 'w')
    if eyes == 'angry':
        c.px(ex - 2, ey - 2, 'gr5'); c.px(ex - 1, ey - 1, 'gr5'); c.px(ex + 5, ey - 2, 'gr5'); c.px(ex + 4, ey - 1, 'gr5')
    if mouth == 'smile' and ry >= 4:
        c.px(ex + 1, ey + 3, 'gr5'); c.px(ex + 2, ey + 3, 'gr5')
    elif mouth == 'open':
        c.rect(ex, ey + 3, 4, 2, 'gr5'); c.px(ex + 1, ey + 4, 'fl1')
    elif mouth == 'wobble':
        c.px(ex, ey + 3, 'gr5'); c.px(ex + 1, ey + 4, 'gr5'); c.px(ex + 2, ey + 3, 'gr5'); c.px(ex + 3, ey + 4, 'gr5')
    for (x, y) in drops:
        c.px(x, y, 'gr2'); c.px(x, y - 1, 'gr1')
    return c.outline('gr5')


def slime_frames():
    an = {}
    an['idle'] = [slime_body(rx, ry) for rx, ry in ((10, 8), (10.5, 7.5), (11, 7), (10.5, 7.5))]
    an['move'] = [
        slime_body(12, 6), slime_body(9, 10), slime_body(8, 11, oy=-4),
        slime_body(9, 9.5, oy=-2), slime_body(12.5, 6), slime_body(10, 8),
    ]
    an['attack'] = [
        slime_body(13, 5.5, ox=-1, eyes='angry'),
        slime_body(12, 8, ox=2, oy=-1, eyes='angry', mouth='open'),
        slime_body(13, 7, ox=4, eyes='angry', mouth='open'),
        slime_body(10.5, 8, ox=1, eyes='angry'),
    ]
    h0 = slime_body(12, 6.5, ox=-2, eyes='x', mouth='wobble')
    an['hurt'] = [h0, h0.flash(), slime_body(9.5, 9, ox=-1, mouth='wobble')]
    an['death'] = [
        slime_body(12, 6, eyes='x', mouth='wobble'),
        slime_body(14, 4, eyes='x', mouth='none', drops=((6, 18), (26, 17))),
        slime_body(15, 2.2, eyes='none', mouth='none', drops=((4, 14), (28, 13), (10, 20))),
        slime_body(11, 1.4, eyes='none', mouth='none', drops=((3, 27), (29, 26))),
    ]
    return an


# ───────────────────────── 검 아이콘 32×32 ─────────────────────────
def sword_icon(rule):
    r = SWORD_RULES[rule]
    c = Cv(32, 32)
    L = 16
    for t in range(L):
        x, y = 11 + t, 20 - t
        tip = t >= L - 2
        c.px(x, y, r['blade'])
        if not tip or t == L - 2:
            c.px(x + 1, y, r['edge'])
        if not tip:
            c.px(x, y + 1, r['shadow'])
        if r['fuller'] and 1 <= t <= L - 5:
            c.px(x, y, r['fuller'])
    c.px(11 + L, 20 - L, r['edge'])
    # 가드 (칼날과 직각)
    for k in range(-3, 4):
        col = r['guard'][0] if abs(k) < 3 else r['guard'][1]
        c.px(10 + k, 21 + k, col)
        c.px(11 + k, 21 + k, r['guard'][1] if abs(k) < 3 else col)
    # 손잡이 (가죽 감기) + 폼멜
    for i, (x, y) in enumerate(((9, 22), (8, 23), (7, 24), (6, 25))):
        c.px(x, y, r['grip'][i % 2]); c.px(x + 1, y + 1, r['grip'][(i + 1) % 2]) if i < 3 else None
    c.rect(4, 26, 2, 2, r['pommel']); c.px(4, 26, PAL_HI.get(r['pommel'], r['pommel']))
    if r['gem']:
        c.px(10, 21, r['gem']); c.px(11, 22, r['gem'])

    # 등급별 디테일
    if rule == 'rusty':
        for t, col in ((3, 'dt2'), (6, 'dt3'), (10, 'dt2'), (12, 'dt3')):
            c.px(11 + t, 21 - t, col)
        c.px(11 + 9 + 1, 20 - 9, None)  # 이 빠진 날
        c.px(9, 23, 'lt0')
    elif rule == 'hunter':
        c.px(7, 18, 'gd2'); c.px(14, 25, 'gd2'); c.px(6, 18, 'gd1'); c.px(14, 26, 'gd1')
    elif rule == 'moon':
        c.px(6, 17, 'mt0'); c.px(5, 16, 'mt1'); c.px(15, 26, 'mt0'); c.px(16, 25, 'mt1')
    elif rule == 'ember':
        for t in (3, 7, 11):
            c.px(13 + t, 19 - t, 'fi1'); c.px(14 + t, 18 - t, 'fi0')
            c.px(10 + t, 22 - t, 'fi2')
        for t in range(0, 6):
            c.px(11 + t, 20 - t, 'fi3' if t < 3 else 'fi2')
    c.outline('ol')
    if rule == 'moon':
        for q in ((24, 9), (24, 11), (23, 10), (25, 10)):
            c.px(q[0] + 2, q[1] - 6, 'w')
        c.px(21, 13, 'mo0')
    if rule == 'ember':
        for q, col in (((26, 9), 'fi1'), ((22, 4), 'fi0'), ((29, 6), 'fi2'), ((19, 8), 'fi1')):
            c.px(q[0], q[1], col)
    return c


PAL_HI = {'mt3': 'mt2', 'gd1': 'gd0', 'mt1': 'mt0'}


# ───────────────────────── 숲 타일셋 (측면 시점, 32×32) ─────────────────────────
T = 32
GTOP = 3   # 풀 지면 윗면 높이 (그 위 0~2행은 풀잎이 솟는 공간)


def dirt(c, x0=0, y0=0, w=T, h_=T, variant=0):
    for y in range(y0, y0 + h_):
        for x in range(x0, x0 + w):
            v = h(x // 2, y // 2, 11 + variant)
            col = 'dt3'
            if v < 0.16:
                col = 'dt4'
            elif v > 0.88:
                col = 'dt2'
            if h(x, y, 5) < 0.04:
                col = 'dt5'
            c.px(x, y, col)
    pebbles = [(5, 12), (21, 17), (12, 26), (27, 27), (26, 8), (2, 22)] if variant != 2 else [(8, 14), (24, 24)]
    if variant == 1:
        pebbles += [(15, 10), (9, 20), (18, 29)]
    for (px_, py_) in pebbles:
        if y0 <= py_ < y0 + h_ and x0 <= px_ < x0 + w:
            c.px(px_, py_, 'st2'); c.px(px_ + 1, py_, 'st3'); c.px(px_, py_ - 1, 'st1')
            c.px(px_ + 1, py_ + 1, 'dt5')
    if variant == 2:  # 뿌리
        for (sx, sy, ln) in ((4, 6, 9), (19, 12, 12), (26, 4, 6)):
            for i in range(ln):
                xx = sx + i // 2 + (1 if h(i, sx, 3) > 0.6 else 0)
                c.px(xx, sy + i, 'wd2'); c.px(xx + 1, sy + i, 'wd3')
    if variant == 3:  # 묻힌 바위
        rk = Cv(T, T); rk.ell(16, 18, 8, 6, 'st2'); rock_shade(rk, 16, 18, 8, 6); rk.outline('st4'); c.blit(rk)


def rock_shade(c, cx, cy, rx, ry):
    for (x, y), col in list(c.p.items()):
        nx, ny = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
        if (nx + 0.35) ** 2 + (ny + 0.45) ** 2 < 0.22:
            c.p[(x, y)] = 'st1'
        elif ny > 0.35 or nx > 0.6:
            c.p[(x, y)] = 'st3'
        if h(x, y, 21) < 0.06:
            c.p[(x, y)] = 'st4'


def grass_top(c, y0=GTOP, x_from=0, x_to=T, blades=True):
    for x in range(x_from, x_to):
        if blades and h(x, 0, 8) > 0.45 and x_from + 1 < x < x_to - 1:
            hb = 1 + int(h(x, 0, 7) * 3)
            for k in range(1, hb + 1):
                c.px(x, y0 - k, 'gr1' if k == hb else 'gr2')
        c.px(x, y0, 'gr0' if h(x, 1, 1) > 0.8 else 'gr1')
        c.px(x, y0 + 1, 'gr2')
        c.px(x, y0 + 2, 'gr2' if h(x, 2, 2) > 0.35 else 'gr3')
        c.px(x, y0 + 3, 'gr3')
        dl = int(h(x, 3, 9) * 4) + (2 if h(x, 4, 9) > 0.85 else 0)
        for k in range(dl):
            c.px(x, y0 + 4 + k, 'gr3' if k < dl - 1 else 'gr4')
        c.px(x, y0 + 4 + dl, 'dt4')


def side_edge(c, side, y_from, y_to=T, grass_y=None):
    xs = (0, 1, 2) if side == 'L' else (T - 1, T - 2, T - 3)
    for y in range(y_from, y_to):
        c.px(xs[0], y, 'dt5')
        c.px(xs[1], y, 'dt4')
        if h(y, side == 'L', 4) > 0.5:
            c.px(xs[2], y, 'dt4')
    if grass_y is not None:
        # 모서리를 둥글게, 풀이 옆면으로 흘러내림
        c.px(xs[0], grass_y, None)
        for k in range(1, 6 + int(h(side == 'L', 9, 2) * 3)):
            c.px(xs[0], grass_y + k, 'gr4' if k > 3 else 'gr3')
            if k < 4:
                c.px(xs[1], grass_y + k, 'gr3')


def bottom_edge(c, x_from=0, x_to=T, base=24):
    for x in range(x_from, x_to):
        yb = base + int(h(x // 2, 0, 31) * 5)
        for y in range(yb + 1, T):
            c.px(x, y, None)
        c.px(x, yb, 'dt5')
        c.px(x, yb - 1, 'dt4')
        if h(x, 1, 32) > 0.82:  # 늘어진 뿌리
            for k in range(1, 1 + int(h(x, 2, 33) * 5)):
                c.px(x, yb + k, 'wd2' if k % 2 else 'wd3')


def cobble_top(c, y0=GTOP - 1, x_from=0, x_to=T):
    # 두 줄 자갈길
    rows = [(y0, 5), (y0 + 5, 5)]
    for ri, (ry, rh) in enumerate(rows):
        x = x_from - (4 if ri else 0)
        i = 0
        while x < x_to:
            w = 6 + int(h(i, ri, 41) * 4)
            for yy in range(ry, ry + rh):
                for xx in range(max(x, x_from), min(x + w, x_to)):
                    edge_b = yy == ry + rh - 1 or xx == x + w - 1
                    edge_t = yy == ry or xx == x
                    col = 'st4' if edge_b else ('st1' if edge_t else ('st2' if h(xx, yy, 42) > 0.2 else 'st3'))
                    c.px(xx, yy, col)
            x += w
            i += 1
    for x in range(x_from, x_to):
        c.px(x, y0 + 10, 'dt5')


def dirt_path_top(c, y0=GTOP, x_from=0, x_to=T):
    for x in range(x_from, x_to):
        c.px(x, y0, 'dt0' if h(x, 7, 1) > 0.7 else 'dt1')
        c.px(x, y0 + 1, 'dt1')
        c.px(x, y0 + 2, 'dt2')
        c.px(x, y0 + 3, 'dt2' if h(x, 8, 1) > 0.4 else 'dt3')
        if h(x, 9, 1) > 0.88:
            c.px(x, y0, 'st1'); c.px(x, y0 + 1, 'st2')
        c.px(x, y0 + 4, 'dt4')


def voronoi_rock(c, seed=0, crack=False):
    pts = [(h(i, 0, 60 + seed) * T, h(i, 1, 60 + seed) * T) for i in range(9)]

    def cell(x, y):
        best, bi = 1e9, 0
        for i, (px_, py_) in enumerate(pts):
            for ox in (-T, 0, T):
                for oy in (-T, 0, T):
                    d = (x + 0.5 - px_ - ox) ** 2 + (y + 0.5 - py_ - oy) ** 2
                    if d < best:
                        best, bi = d, i
        return bi
    ids = [[cell(x, y) for x in range(T)] for y in range(T)]
    for y in range(T):
        for x in range(T):
            i = ids[y][x]
            base = ('st2', 'st3', 'st2')[i % 3]
            if ids[(y + 1) % T][x] != i or ids[y][(x + 1) % T] != i:
                col = 'st4'
            elif ids[(y - 1) % T][x] != i or ids[y][(x - 1) % T] != i:
                col = 'st1'
            else:
                col = base if h(x // 2, y // 2, 61) > 0.15 else 'st3'
            c.px(x, y, col)
    if crack:
        x = 14
        for y in range(4, 28):
            x += (1 if h(y, 0, 62) > 0.6 else (-1 if h(y, 0, 62) < 0.25 else 0))
            c.px(x, y, 'st4'); c.px(x + 1, y, 'ol' if y % 5 == 0 else 'st4')


def water(c, phase=0, top=6, body='surface'):
    if body == 'surface':
        for x in range(T):
            crest = math.sin((x + phase) * math.pi * 2 / 16)
            c.px(x, top, 'wa0' if crest > 0.55 else 'wa1')
            if crest > 0.85:
                c.px(x, top - 1, 'wa0')
            c.px(x, top + 1, 'wa1' if crest > -0.2 else 'wa2')
            for y in range(top + 2, T):
                col = 'wa2'
                if y > 22 and (x + y) % 2 == 0:
                    col = 'wa3'
                if y > 28:
                    col = 'wa3'
                c.px(x, y, col)
        for i in range(5):
            sx, sy = int(h(i, phase, 70) * 28), top + 4 + int(h(i, 1, 70) * 14)
            c.rect(sx, sy, 2 + int(h(i, 2, 70) * 3), 1, 'wa1')
    else:
        deep = body == 'deep'
        for y in range(T):
            for x in range(T):
                col = 'wa4' if deep else 'wa3'
                if deep and y < 4 and (x + y) % 2 == 0:
                    col = 'wa3'
                c.px(x, y, col)
        for i in range(4):
            sx, sy = int(h(i, 5, 71 + deep) * 28), int(h(i, 6, 71 + deep) * 30)
            c.rect(sx, sy, 2 + int(h(i, 7, 70) * 3), 1, 'wa3' if deep else 'wa2')
        c.px(int(h(9, 9, 72) * 30), int(h(9, 8, 72) * 30), 'wa1')


def deco(kind):
    c = Cv(T, T)
    if kind == 'tuft':
        for i, (x, hh) in enumerate(((10, 6), (12, 9), (14, 7), (16, 11), (18, 8), (20, 6), (22, 9))):
            lean = 1 if i % 2 else -1
            for k in range(hh):
                c.px(x + (lean if k > hh * 0.6 else 0), 31 - k, 'gr1' if k > hh - 3 else ('gr2' if k > 2 else 'gr3'))
        c.outline('gr5')
    elif kind == 'tall':
        for i, x in enumerate(range(6, 27, 2)):
            hh = 10 + int(h(i, 0, 80) * 12)
            for k in range(hh):
                bend = int((k / hh) ** 2 * (2 if i % 2 else -2))
                c.px(x + bend, 31 - k, 'gr2' if k > hh * 0.5 else 'gr3')
                if k == hh - 1:
                    c.px(x + bend, 31 - k, 'gr0')
        c.outline('gr5')
    elif kind in ('flowers_a', 'flowers_b'):
        cols = ('fl1', 'fl2') if kind == 'flowers_a' else ('w', 'fl3')
        for i, (x, hh) in enumerate(((8, 7), (13, 11), (18, 8), (23, 10))):
            c.line(x, 31, x, 31 - hh, 'gr3')
            c.px(x + 1, 31 - hh // 2, 'gr2')
            col = cols[i % 2]
            for q in ((0, -1), (-1, 0), (1, 0), (0, 1)):
                c.px(x + q[0], 31 - hh - 1 + q[1], col)
            c.px(x, 31 - hh - 1, 'gd1' if col != 'fl2' else 'fl4')
        for x in range(6, 26):
            if h(x, 0, 81) > 0.4:
                c.px(x, 31, 'gr2'); c.px(x, 30, 'gr3') if h(x, 1, 81) > 0.5 else None
        c.outline('gr5')
    elif kind == 'stones':
        for (x, y, rx, ry) in ((10, 28, 4, 3), (19, 29, 3, 2.2), (24, 28.5, 2.5, 2)):
            r_ = Cv(T, T); r_.ell(x, y, rx, ry, 'st2'); rock_shade(r_, x, y, rx, ry); c.blit(r_)
        c.outline('st4')
    elif kind == 'bush':
        for (x, y, r) in ((10, 22, 8), (20, 20, 9), (15, 16, 7), (25, 25, 6), (7, 26, 5)):
            c.ell(x, y, r, r * 0.85, 'gr3')
        for (x, y), col in list(c.p.items()):
            if y > 26 or h(x // 2, y // 2, 82) < 0.25:
                c.p[(x, y)] = 'gr4'
            elif y < 17 or (h(x // 2, y // 2, 83) > 0.7 and y < 24):
                c.p[(x, y)] = 'gr2'
            if h(x, y, 84) > 0.96 and y < 22:
                c.p[(x, y)] = 'gr1'
        for q in ((12, 18), (22, 15), (18, 23)):
            c.px(q[0], q[1], 'rd1')
        for x in range(T):
            for y in range(28, T):
                if (x, y) in c.p:
                    c.p[(x, y)] = 'gr4'
        c.outline('gr5')
    elif kind == 'mushroom':
        for (x, hh, r, col) in ((11, 6, 4, 'rd2'), (19, 9, 5, 'rd1'), (25, 4, 3, 'rd2')):
            c.rect(x - 1, 31 - hh, 2, hh, 'sk0'); c.px(x, 31 - hh, 'sk2')
            for yy in range(r):
                c.rect(x - r + yy // 2, 31 - hh - r + yy, (r - yy // 2) * 2, 1, col)
            c.rect(x - r + 1, 31 - hh - 1, r * 2 - 2, 1, 'rd3')
            c.px(x - 1, 31 - hh - r + 1, 'w'); c.px(x + 1, 31 - hh - r + 2, 'w')
        c.outline('ol')
    elif kind == 'fern':
        for side in (-1, 1):
            for j in range(3):
                bx, by, ln = 16, 31 - j * 4, 10 - j * 2
                for k in range(ln):
                    x = bx + side * k
                    y = by - int(math.sin(k / ln * math.pi * 0.8) * (6 - j))
                    c.px(x, y, 'gr2' if k < ln - 2 else 'gr1')
                    if k % 2 == 0:
                        c.px(x, y + 1, 'gr3')
        c.line(16, 31, 16, 18, 'gr3')
        c.outline('gr5')
    return c


def tile(kind):
    c = Cv(T, T)
    k = kind
    if k in ('top_l', 'top', 'top_r', 'top_single', 'col_mid', 'left', 'right', 'inner_a', 'inner_b', 'inner_roots', 'inner_rock',
             'bot_l', 'bot', 'bot_r', 'bot_single'):
        has_top = k.startswith('top')
        variant = {'inner_b': 1, 'inner_roots': 2, 'inner_rock': 3}.get(k, 0)
        dirt(c, 0, 0, T, T, variant)
        if has_top:
            for y in range(GTOP):
                for x in range(T):
                    c.px(x, y, None)
            grass_top(c)
        L_ = k in ('top_l', 'top_single', 'col_mid', 'left', 'bot_l', 'bot_single')
        R_ = k in ('top_r', 'top_single', 'col_mid', 'right', 'bot_r', 'bot_single')
        if L_:
            side_edge(c, 'L', GTOP if has_top else 0, grass_y=GTOP if has_top else None)
        if R_:
            side_edge(c, 'R', GTOP if has_top else 0, grass_y=GTOP if has_top else None)
        if k.startswith('bot'):
            bottom_edge(c)
    elif k in ('trans_gd', 'trans_dg', 'path'):
        dirt(c)
        for y in range(GTOP):
            for x in range(T):
                c.px(x, y, None)
        bnd = lambda x: (14 + int(h(x // 3, 0, 50) * 5))
        if k == 'path':
            dirt_path_top(c)
        else:
            for x in range(T):
                is_grass = (x < bnd(x)) if k == 'trans_gd' else (x >= T - bnd(x))
                if is_grass:
                    grass_top(c, x_from=x, x_to=x + 1, blades=False)
                    if h(x, 0, 8) > 0.5:
                        c.px(x, GTOP - 1, 'gr2')
                        if h(x, 0, 7) > 0.5:
                            c.px(x, GTOP - 2, 'gr1')
                else:
                    dirt_path_top(c, x_from=x, x_to=x + 1)
    elif k.startswith('plat'):
        side = k.split('_')[1]
        for y in range(GTOP, 18):
            for x in range(T):
                c.px(x, y, 'dt3')
        dirt(c, 0, GTOP, T, 15)
        grass_top(c, x_from=2 if side in ('l', 's') else 0, x_to=T - 2 if side in ('r', 's') else T)
        for x in range(T):
            yb = 15 + int(h(x // 2, 0, 52) * 4)
            if side in ('l', 's') and x < 6:
                yb -= (6 - x)
            if side in ('r', 's') and x > T - 7:
                yb -= (x - (T - 7))
            for y in range(yb + 1, T):
                c.px(x, y, None)
            c.px(x, yb, 'dt5'); c.px(x, yb - 1, 'dt4')
        for x in range(T):
            if side in ('l', 's') and x < 2 or side in ('r', 's') and x > T - 3:
                for y in range(T):
                    c.px(x, y, None)
        if side in ('l', 's'):
            for y in range(GTOP, 16):
                if c.get(2, y):
                    c.px(2, y, 'dt5'); c.px(3, y, 'dt4')
            c.px(2, GTOP, None); c.px(2, GTOP + 1, 'gr3'); c.px(2, GTOP + 2, 'gr3')
        if side in ('r', 's'):
            for y in range(GTOP, 16):
                if c.get(T - 3, y):
                    c.px(T - 3, y, 'dt5'); c.px(T - 4, y, 'dt4')
            c.px(T - 3, GTOP, None); c.px(T - 3, GTOP + 1, 'gr3'); c.px(T - 3, GTOP + 2, 'gr3')
    elif k.startswith('stone'):
        if k == 'stone_brick':
            for y in range(T):
                row = y // 8
                for x in range(T):
                    xx = (x + (8 if row % 2 else 0)) % T
                    if y % 8 == 7 or xx % 16 == 15:
                        col = 'st4'
                    elif y % 8 == 0 or xx % 16 == 0:
                        col = 'st1'
                    else:
                        col = 'st2' if h(x // 2, y // 2, 45) > 0.2 else 'st3'
                    c.px(x, y, col)
            for (x, y) in ((3, 7), (4, 7), (20, 15), (21, 15), (22, 15), (11, 23)):
                c.px(x, y, 'gr3'); c.px(x, y - 1, 'gr2')
        else:
            dirt(c)
            for y in range(GTOP - 1):
                for x in range(T):
                    c.px(x, y, None)
            cobble_top(c)
            if k == 'stone_l':
                side_edge(c, 'L', GTOP + 9)
                for y in range(GTOP - 1, GTOP + 9):
                    c.px(0, y, 'st4')
            if k == 'stone_r':
                side_edge(c, 'R', GTOP + 9)
                for y in range(GTOP - 1, GTOP + 9):
                    c.px(T - 1, y, 'st4')
    elif k.startswith('cliff'):
        voronoi_rock(c, seed=1, crack=(k == 'cliff_crack'))
        if k in ('cliff_tl', 'cliff_t', 'cliff_tr'):
            for y in range(GTOP):
                for x in range(T):
                    c.px(x, y, None)
            grass_top(c)
        for side, keys in (('L', ('cliff_tl', 'cliff_l')), ('R', ('cliff_tr', 'cliff_r'))):
            if k in keys:
                xs = (0, 1) if side == 'L' else (T - 1, T - 2)
                for y in range(GTOP if k.endswith(('tl', 'tr')) else 0, T):
                    c.px(xs[0], y, 'ol'); c.px(xs[1], y, 'st4')
                if k.endswith(('tl', 'tr')):
                    c.px(xs[0], GTOP, None)
                    for kk in range(1, 6):
                        c.px(xs[0], GTOP + kk, 'gr4'); c.px(xs[1], GTOP + kk, 'gr3') if kk < 4 else None
        if k == 'cliff_b':
            for (x, y, rx, ry) in ((5, 28, 5, 4), (14, 29, 4, 3), (22, 27, 6, 5), (29, 29, 3, 3)):
                r_ = Cv(T, T); r_.ell(x, y, rx, ry, 'st2'); rock_shade(r_, x, y, rx, ry); r_.outline('st4'); c.blit(r_)
            for x in range(T):
                c.px(x, 31, 'dt4')
    elif k in ('water_a', 'water_b'):
        water(c, phase=0 if k == 'water_a' else 8)
    elif k in ('water_body', 'water_deep'):
        water(c, body='body' if k == 'water_body' else 'deep')
    elif k in ('shore_r', 'shore_l'):
        # 물가: 땅(풀) 쪽과 물 쪽이 만나는 둑
        water(c)
        for y in range(6):
            for x in range(T):
                c.px(x, y, None)
        edge = lambda y: min(T - 1, 14 + ((y - GTOP) * 17) // 28)
        land = Cv(T, T)
        dirt(land)
        for y in range(GTOP):
            for x in range(T):
                land.px(x, y, None)
        grass_top(land)
        for y in range(T):
            e = edge(y)
            for x in range(T):
                inside = x <= e
                if not inside:
                    land.px(x, y, None)
                elif x == e:
                    land.px(x, y, 'dt5')
                elif x == e - 1:
                    land.px(x, y, 'dt4')
                elif y > 10 and x > e - 4:
                    land.px(x, y, 'dt4')
        land.px(edge(GTOP), GTOP, None)
        for kk in range(1, 5):
            land.px(edge(GTOP + kk), GTOP + kk, 'gr4')
        if k == 'shore_l':
            mirrored = Cv(T, T)
            for (x, y), col in land.p.items():
                mirrored.px(T - 1 - x, y, col)
            land = mirrored
        c.blit(land)
        # 물결이 둑에 부딪히는 거품
        e = edge(6) if k == 'shore_r' else T - 1 - edge(6)
        for d in (1, 2, 3):
            c.px(e + (d if k == 'shore_r' else -d), 6, 'wa0')
    elif k.startswith('deco_'):
        return deco(k[5:])
    return c


TILE_LAYOUT = [
    ['top_l', 'top', 'top_r', 'top_single', 'inner_a', 'inner_b', 'left', 'right'],
    ['bot_l', 'bot', 'bot_r', 'bot_single', 'col_mid', 'trans_gd', 'trans_dg', 'path'],
    ['plat_l', 'plat_m', 'plat_r', 'plat_s', 'stone_top', 'stone_l', 'stone_r', 'stone_brick'],
    ['cliff_tl', 'cliff_t', 'cliff_tr', 'cliff_in', 'cliff_l', 'cliff_r', 'cliff_b', 'cliff_crack'],
    ['water_a', 'water_b', 'water_body', 'water_deep', 'shore_r', 'shore_l', 'inner_roots', 'inner_rock'],
    ['deco_tuft', 'deco_tall', 'deco_flowers_a', 'deco_flowers_b', 'deco_stones', 'deco_bush', 'deco_mushroom', 'deco_fern'],
]
TILE_NAMES_KO = {
    'top_l': '풀 지면 윗면 · 왼쪽 끝', 'top': '풀 지면 윗면', 'top_r': '풀 지면 윗면 · 오른쪽 끝', 'top_single': '풀 지면 윗면 · 한 칸 기둥',
    'inner_a': '흙 속', 'inner_b': '흙 속 (자갈)', 'left': '흙 옆면 · 왼쪽', 'right': '흙 옆면 · 오른쪽',
    'bot_l': '아랫면 · 왼쪽', 'bot': '아랫면', 'bot_r': '아랫면 · 오른쪽', 'bot_single': '아랫면 · 한 칸 기둥',
    'col_mid': '한 칸 기둥 · 가운데', 'trans_gd': '풀 → 흙길 경계', 'trans_dg': '흙길 → 풀 경계', 'path': '흙길 윗면',
    'plat_l': '떠 있는 발판 · 왼쪽', 'plat_m': '떠 있는 발판 · 가운데', 'plat_r': '떠 있는 발판 · 오른쪽', 'plat_s': '떠 있는 발판 · 한 칸',
    'stone_top': '돌길 윗면', 'stone_l': '돌길 · 왼쪽 끝', 'stone_r': '돌길 · 오른쪽 끝', 'stone_brick': '돌벽돌',
    'cliff_tl': '절벽 윗면 · 왼쪽', 'cliff_t': '절벽 윗면', 'cliff_tr': '절벽 윗면 · 오른쪽', 'cliff_in': '절벽 암벽',
    'cliff_l': '절벽 옆면 · 왼쪽', 'cliff_r': '절벽 옆면 · 오른쪽', 'cliff_b': '절벽 아래 · 돌무더기', 'cliff_crack': '절벽 암벽 (균열)',
    'water_a': '수면 (프레임 1)', 'water_b': '수면 (프레임 2)', 'water_body': '물 속', 'water_deep': '깊은 물',
    'shore_r': '물가 · 오른쪽이 물', 'shore_l': '물가 · 왼쪽이 물', 'inner_roots': '흙 속 (뿌리)', 'inner_rock': '흙 속 (묻힌 바위)',
    'deco_tuft': '장식 · 풀 덤불', 'deco_tall': '장식 · 키 큰 풀', 'deco_flowers_a': '장식 · 꽃 (분홍·노랑)', 'deco_flowers_b': '장식 · 꽃 (흰색·보라)',
    'deco_stones': '장식 · 작은 돌', 'deco_bush': '장식 · 덤불', 'deco_mushroom': '장식 · 버섯', 'deco_fern': '장식 · 고사리',
}


# ───────────────────────── 오브젝트 ─────────────────────────
def canopy(c, blobs):
    for (x, y, r) in blobs:
        c.ell(x, y, r, r * 0.9, 'gr3')
    for (x, y), col in list(c.p.items()):
        lit = min(((x - bx + r * 0.35) ** 2 + (y - by_ + r * 0.4) ** 2) / (r * r) for (bx, by_, r) in blobs)
        shade_ = max(((y - by_) / r) for (bx, by_, r) in blobs if (x - bx) ** 2 + (y - by_) ** 2 < r * r) if any((x - bx) ** 2 + (y - by_) ** 2 < r * r for (bx, by_, r) in blobs) else 0
        n = h(x // 2, y // 2, 90)
        if lit < 0.18:
            col = 'gr1' if n > 0.2 else 'gr2'
        elif lit < 0.42:
            col = 'gr2' if n > 0.25 else 'gr3'
        elif shade_ > 0.55:
            col = 'gr4' if n > 0.3 else 'gr3'
        else:
            col = 'gr3' if n > 0.2 else 'gr4'
        if h(x, y, 91) > 0.985:
            col = 'gr0'
        c.p[(x, y)] = col


def bark(c, x0, x1, y0, y1):
    for y in range(y0, y1):
        for x in range(x0, x1):
            t = (x - x0) / max(1, x1 - x0 - 1)
            col = 'wd1' if t < 0.25 else ('wd2' if t < 0.75 else 'wd3')
            if h(x, y // 3, 92) > 0.82:
                col = 'wd3'
            c.px(x, y, col)


def obj_tree_oak():
    c = Cv(64, 96)
    bark(c, 27, 37, 50, 92)
    for (dx, wv) in ((-1, 0), (1, 0)):
        pass
    c.poly([(22, 95), (27, 84), (27, 92)], 'wd2'); c.poly([(42, 95), (37, 84), (37, 92)], 'wd3')
    c.rect(20, 94, 25, 2, 'wd3'); c.rect(24, 92, 16, 3, 'wd2')
    c.ell(33, 70, 2, 3, 'wd3'); c.px(32, 69, 'ol')
    c.line(30, 58, 20, 46, 'wd2'); c.line(31, 58, 21, 46, 'wd2'); c.line(35, 56, 46, 44, 'wd3'); c.line(35, 57, 46, 45, 'wd3')
    leaves = Cv(64, 96)
    canopy(leaves, [(32, 30, 20), (15, 40, 12), (49, 40, 12), (23, 20, 12), (42, 19, 13), (32, 46, 14), (20, 50, 8), (45, 50, 8)])
    c.blit(leaves)
    for q in ((26, 52), (38, 50), (24, 38), (40, 34)):
        c.px(q[0], q[1], 'wd3')
    c.outline('ol')
    return c


def obj_tree_pine():
    c = Cv(48, 96)
    bark(c, 21, 27, 70, 95)
    c.rect(18, 94, 12, 2, 'wd3')
    for i in range(5):
        top = 8 + i * 13
        w = 8 + i * 4
        c.poly([(24, top), (24 + w, top + 22), (24 - w, top + 22)], 'gr3')
    for (x, y), col in list(c.p.items()):
        if col != 'gr3':
            continue
        n = h(x // 2, y // 2, 93)
        if x < 24 - 2 and n > 0.35:
            c.p[(x, y)] = 'gr2'
        elif x > 26 and n > 0.3:
            c.p[(x, y)] = 'gr4'
        if (y - 8) % 13 > 18 or (y - 8) % 13 < 1:
            pass
        if h(x, y, 94) > 0.97:
            c.p[(x, y)] = 'gr1'
    for i in range(5):
        y = 8 + i * 13 + 22
        w = 8 + i * 4
        for x in range(24 - w + 2, 24 + w - 1):
            if (x + i) % 3 == 0 and c.get(x, y - 1) and y < 92:
                c.px(x, y - 1, 'gr5')
    c.outline('ol')
    return c


def obj_stump():
    c = Cv(32, 32)
    bark(c, 8, 24, 14, 29)
    c.poly([(5, 31), (8, 24), (9, 31)], 'wd2'); c.poly([(27, 31), (24, 24), (23, 31)], 'wd3'); c.rect(6, 29, 20, 3, 'wd3')
    c.ell(16, 14, 8, 3.2, 'wd0')
    for r, col in ((6, 'wd1'), (4, 'wd0'), (2, 'wd1')):
        for a in range(0, 360, 12):
            c.px(16 + math.cos(math.radians(a)) * r, 14 + math.sin(math.radians(a)) * r * 0.4, col)
    c.px(16, 14, 'wd2')
    c.rect(9, 17, 3, 2, 'gr3'); c.px(10, 16, 'gr2'); c.px(22, 20, 'gr3')
    c.rect(20, 25, 2, 3, 'sk0'); c.rect(18, 23, 6, 2, 'rd2'); c.px(19, 23, 'w')
    c.outline('ol')
    return c


def obj_log():
    c = Cv(64, 32)
    for y in range(13, 29):
        for x in range(6, 56):
            t = (y - 13) / 15
            col = 'wd1' if t < 0.2 else ('wd2' if t < 0.7 else 'wd3')
            if h(x // 3, y, 95) > 0.8:
                col = 'wd3' if t > 0.3 else 'wd2'
            c.px(x, y, col)
    for y in range(13, 29):  # 부러진 왼쪽 끝
        c.px(6 + int(h(y, 0, 96) * 3), y, None); c.px(6, y, None)
    c.ell(56, 21, 4, 8, 'wd0')
    for r, col in ((3, 'wd1'), (1.5, 'wd0')):
        for a in range(0, 360, 15):
            c.px(56 + math.cos(math.radians(a)) * r, 21 + math.sin(math.radians(a)) * r * 2, col)
    for x in range(14, 46):
        if h(x, 0, 97) > 0.3:
            c.px(x, 13, 'gr3'); c.px(x, 12, 'gr2') if h(x, 1, 97) > 0.6 else None
    c.rect(30, 8, 2, 5, 'wd2'); c.px(31, 7, 'wd1')
    c.outline('ol')
    return c


def obj_rock(w, h_, blobs, moss=False):
    c = Cv(w, h_)
    for (x, y, rx, ry) in blobs:
        c.ell(x, y, rx, ry, 'st2')
    cx = sum(b[0] for b in blobs) / len(blobs)
    cy = sum(b[1] for b in blobs) / len(blobs)
    rx = max(b[0] + b[2] for b in blobs) - cx
    ry = max(b[1] + b[3] for b in blobs) - cy
    rock_shade(c, cx, cy, rx, ry)
    for x in range(w):
        for y in range(h_):
            if c.get(x, y) and c.get(x, y - 1) is None and moss and h(x, 0, 98) > 0.3:
                c.px(x, y, 'gr3'); c.px(x, y + 1, 'gr4') if h(x, 1, 98) > 0.5 else None
    c.outline('st4')
    for x in range(w):  # 바닥 그림자 대신 지면에 닿는 줄
        if c.get(x, h_ - 2):
            c.px(x, h_ - 1, 'ol')
    return c


def obj_fence(kind):
    c = Cv(32, 32)

    def post(x, tilt=0):
        for y in range(10, 31):
            xx = x + (tilt * (31 - y)) // 20
            c.rect(xx, y, 3, 1, 'wd2'); c.px(xx, y, 'wd1'); c.px(xx + 2, y, 'wd3')
        c.px(x + tilt, 9, 'wd2'); c.px(x + 1 + tilt, 8, 'wd1')

    def rail(x0, x1, y):
        for x in range(x0, x1):
            c.px(x, y, 'wd1'); c.px(x, y + 1, 'wd2'); c.px(x, y + 2, 'wd3')
        c.px(x0 + 2, y + 1, 'mt3')
    if kind == 'mid':
        rail(0, 32, 14); rail(0, 32, 22); post(3)
    elif kind == 'end':
        rail(0, 16, 14); rail(0, 16, 22); post(14)
    else:
        rail(0, 12, 14); rail(0, 20, 22)
        for x in range(12, 18):
            c.px(x, 14 + (x - 12) // 2, 'wd1'); c.px(x, 15 + (x - 12) // 2, 'wd3')
        post(18, tilt=3)
    c.outline('ol')
    return c


def obj_flowers():
    c = deco('flowers_a')
    extra = deco('tuft')
    out = Cv(32, 32)
    out.blit(extra, -6, 0)
    out.blit(c, 2, 0)
    return out


# ───────────────────────── 출력 ─────────────────────────
def save(cv_or_img, *path):
    full = os.path.join(OUT, *path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    im = cv_or_img.image() if isinstance(cv_or_img, Cv) else cv_or_img
    im.save(full)
    return full


def sheet(frames, fw=32, fh=32):
    im = Image.new('RGBA', (fw * len(frames), fh), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        im.paste(f.image(), (i * fw, 0))
    return im


ANIM_SPEC = {
    'player': [('idle', 6, True), ('walk', 10, True), ('attack', 14, False), ('hurt', 10, False), ('death', 8, False)],
    'slime': [('idle', 6, True), ('move', 10, True), ('attack', 10, False), ('hurt', 10, False), ('death', 8, False)],
}


def write_spriteframes(name, folder, anims):
    """Godot 4 SpriteFrames 리소스 (.tres)."""
    ext, subs, anim_txt = [], [], []
    for ai, (anim, fps, loop) in enumerate(ANIM_SPEC[name]):
        n = len(anims[anim])
        eid = f'{ai + 1}_{anim}'
        ext.append(f'[ext_resource type="Texture2D" path="res://assets/{folder}/{name}_{anim}.png" id="{eid}"]')
        frames = []
        for i in range(n):
            sid = f'AtlasTexture_{anim}_{i}'
            subs.append(f'[sub_resource type="AtlasTexture" id="{sid}"]\natlas = ExtResource("{eid}")\nregion = Rect2({i * 32}, 0, 32, 32)\n')
            frames.append(f'{{\n"duration": 1.0,\n"texture": SubResource("{sid}")\n}}')
        anim_txt.append('{\n"frames": [' + ', '.join(frames) + f'],\n"loop": {"true" if loop else "false"},\n"name": &"{anim}",\n"speed": {fps:.1f}\n}}')
    txt = f'[gd_resource type="SpriteFrames" load_steps={len(ext) + len(subs) + 1} format=3]\n\n' + '\n'.join(ext) + '\n\n' + '\n'.join(subs) + '\n[resource]\nanimations = [' + ', '.join(anim_txt) + ']\n'
    p = os.path.join(OUT, 'godot', f'{name}_frames.tres')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w').write(txt)


SOLID_TOP = {'top_l', 'top', 'top_r', 'top_single', 'trans_gd', 'trans_dg', 'path', 'cliff_tl', 'cliff_t', 'cliff_tr'}
SOLID_FULL = {'inner_a', 'inner_b', 'left', 'right', 'col_mid', 'stone_brick', 'cliff_in', 'cliff_l', 'cliff_r', 'cliff_crack', 'inner_roots', 'inner_rock', 'cliff_b'}
SOLID_BOT = {'bot_l', 'bot', 'bot_r', 'bot_single'}
STONE_TOP = {'stone_top', 'stone_l', 'stone_r'}
ONE_WAY = {'plat_l', 'plat_m', 'plat_r', 'plat_s'}


def write_tileset():
    """Godot 4 TileSet 리소스: 32×32 아틀라스 + 충돌 (발판은 한쪽 통과)."""
    lines = []
    for r, row in enumerate(TILE_LAYOUT):
        for col, name in enumerate(row):
            key = f'{col}:{r}/0'
            lines.append(f'{key} = 0')
            pts = None
            if name in SOLID_TOP:
                pts = '-16, -13, 16, -13, 16, 16, -16, 16'
            elif name in STONE_TOP:
                pts = '-16, -14, 16, -14, 16, 16, -16, 16'
            elif name in SOLID_FULL:
                pts = '-16, -16, 16, -16, 16, 16, -16, 16'
            elif name in SOLID_BOT:
                pts = '-16, -16, 16, -16, 16, 8, -16, 8'
            elif name in ONE_WAY:
                pts = '-16, -13, 16, -13, 16, -2, -16, -2'
            elif name == 'shore_r':
                pts = '-16, -13, -2, -13, 2, 16, -16, 16'
            elif name == 'shore_l':
                pts = '2, -13, 16, -13, 16, 16, -2, 16'
            if pts:
                lines.append(f'{key}/physics_layer_0/polygon_0/points = PackedVector2Array({pts})')
                if name in ONE_WAY:
                    lines.append(f'{key}/physics_layer_0/polygon_0/one_way = true')
    txt = ('[gd_resource type="TileSet" load_steps=3 format=3]\n\n'
           '[ext_resource type="Texture2D" path="res://assets/tiles/forest_tileset.png" id="1_forest"]\n\n'
           '[sub_resource type="TileSetAtlasSource" id="TileSetAtlasSource_forest"]\n'
           'texture = ExtResource("1_forest")\n'
           'texture_region_size = Vector2i(32, 32)\n' + '\n'.join(lines) + '\n\n'
           '[resource]\n'
           'tile_size = Vector2i(32, 32)\n'
           'physics_layer_0/collision_layer = 1\n'
           'sources/0 = SubResource("TileSetAtlasSource_forest")\n')
    open(os.path.join(OUT, 'godot', 'forest_tileset.tres'), 'w').write(txt)


def write_palette():
    names = list(PAL.keys())
    cols = 8
    im = Image.new('RGBA', (cols * 8, ((len(names) + cols - 1) // cols) * 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, k in enumerate(names):
        x, y = (i % cols) * 8, (i // cols) * 8
        d.rectangle([x, y, x + 7, y + 7], fill=RGB[k] + (255,))
    im.save(os.path.join(OUT, 'palette', 'forgotten_forge_palette.png'))
    with open(os.path.join(OUT, 'palette', 'forgotten_forge.gpl'), 'w') as f:
        f.write('GIMP Palette\nName: Forgotten Forge 16-bit\nColumns: 8\n#\n')
        for k in names:
            r, g, b = RGB[k]
            f.write(f'{r:3d} {g:3d} {b:3d}\t{k}\n')


def preview(anims_by_name, tiles_img, icons, objects):
    os.makedirs(PREVIEW, exist_ok=True)
    bg = (38, 32, 44, 255)
    # 애니메이션 GIF (8배)
    for name, anims in anims_by_name.items():
        for anim, fps, _ in ANIM_SPEC[name]:
            frames = []
            for f in anims[anim]:
                base = Image.new('RGBA', (32, 32), bg)
                base.alpha_composite(f.image())
                frames.append(base.resize((256, 256), Image.NEAREST).convert('P', palette=Image.ADAPTIVE))
            frames[0].save(os.path.join(PREVIEW, f'{name}_{anim}.gif'), save_all=True, append_images=frames[1:], duration=int(1000 / fps), loop=0, disposal=2)
    # 한 장짜리 전체 미리보기 (4배)
    S = 4
    rows = []
    for name, anims in anims_by_name.items():
        for anim, _, _ in ANIM_SPEC[name]:
            rows.append(sheet(anims[anim]))
    icon_row = Image.new('RGBA', (32 * len(icons) + 8 * (len(icons) - 1), 32), (0, 0, 0, 0))
    for i, ic in enumerate(icons):
        icon_row.paste(ic.image(), (i * 40, 0))
    widest = max([r.width for r in rows] + [tiles_img.width, icon_row.width])
    obj_w = sum(o.w for o in objects) + 8 * (len(objects) - 1)
    total_h = sum(r.height + 6 for r in rows) + 8 + icon_row.height + 8 + tiles_img.height + 8 + 96
    W = max(widest, obj_w)
    canvas = Image.new('RGBA', (W, total_h), bg)
    y = 0
    for r in rows:
        canvas.alpha_composite(r, (0, y)); y += r.height + 6
    y += 2
    canvas.alpha_composite(icon_row, (0, y)); y += icon_row.height + 8
    canvas.alpha_composite(tiles_img, (0, y)); y += tiles_img.height + 8
    x = 0
    for o in objects:
        canvas.alpha_composite(o.image(), (x, y + 96 - o.h)); x += o.w + 8
    canvas.resize((W * S, total_h * S), Image.NEAREST).save(os.path.join(PREVIEW, 'contact_sheet.png'))
    # 타일 조립 예시 (2배)
    demo = tile_demo()
    demo.resize((demo.width * 3, demo.height * 3), Image.NEAREST).save(os.path.join(PREVIEW, 'tileset_demo.png'))


def tile_demo():
    """타일이 서로 이어지는지 확인하는 작은 장면."""
    tiles = {name: tile(name).image() for row in TILE_LAYOUT for name in row}
    cols, rows = 16, 7
    im = Image.new('RGBA', (cols * 32, rows * 32), (150, 206, 222, 255))
    sky = ImageDraw.Draw(im)
    for y in range(rows * 32):
        t = y / (rows * 32)
        sky.line([(0, y), (cols * 32, y)], fill=(int(120 + 100 * t), int(180 + 50 * t), int(220 - 20 * t), 255))
    grid = {
        (1, 2): 'plat_l', (2, 2): 'plat_m', (3, 2): 'plat_r', (12, 1): 'plat_s',
        (0, 4): 'top_l', (1, 4): 'top', (2, 4): 'trans_gd', (3, 4): 'path', (4, 4): 'trans_dg', (5, 4): 'top', (6, 4): 'shore_r',
        (7, 4): 'water_a', (8, 4): 'water_a', (9, 4): 'shore_l', (10, 4): 'stone_top', (11, 4): 'stone_top', (12, 4): 'stone_r',
        (13, 3): 'cliff_tl', (14, 3): 'cliff_t', (15, 3): 'cliff_tr',
        (13, 4): 'cliff_l', (14, 4): 'cliff_crack', (15, 4): 'cliff_r', (13, 5): 'cliff_l', (14, 5): 'cliff_in', (15, 5): 'cliff_r',
        (13, 6): 'cliff_b', (14, 6): 'cliff_b', (15, 6): 'cliff_b',
        (1, 3): 'deco_flowers_a', (5, 3): 'deco_bush', (11, 3): 'deco_stones', (0, 3): 'deco_tuft', (3, 3): 'deco_mushroom',
        (13, 2): 'deco_fern', (14, 2): 'deco_tall', (15, 2): 'deco_flowers_b',
    }
    for x in range(13):
        grid.setdefault((x, 5), {6: 'right', 9: 'left', 0: 'left'}.get(x, 'inner_a' if x % 3 else 'inner_b'))
        if x in (7, 8):
            grid[(x, 5)] = 'water_body'
        grid.setdefault((x, 6), 'water_deep' if x in (7, 8) else ('inner_roots' if x == 2 else ('inner_rock' if x == 11 else 'inner_a')))
    grid[(6, 5)] = 'right'; grid[(9, 5)] = 'left'
    grid[(6, 6)] = 'right'; grid[(9, 6)] = 'left'
    for (x, y), name in grid.items():
        im.alpha_composite(tiles[name], (x * 32, y * 32))
    return im


def main():
    for d in ('characters', 'monsters', 'items', 'tiles', 'objects', 'godot', 'palette'):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)
    pl = player_frames()
    sl = slime_frames()
    for anim, _, _ in ANIM_SPEC['player']:
        save(sheet(pl[anim]), 'characters', f'player_{anim}.png')
    for anim, _, _ in ANIM_SPEC['slime']:
        save(sheet(sl[anim]), 'monsters', f'slime_{anim}.png')
    icons = []
    for key, fname in (('rusty', 'sword_rusty'), ('hunter', 'sword_hunter'), ('moon', 'sword_moonlight'), ('ember', 'sword_ember')):
        ic = sword_icon(key)
        icons.append(ic)
        save(ic, 'items', f'{fname}.png')
    tiles_img = Image.new('RGBA', (8 * 32, len(TILE_LAYOUT) * 32), (0, 0, 0, 0))
    for r, row in enumerate(TILE_LAYOUT):
        for col, name in enumerate(row):
            tiles_img.paste(tile(name).image(), (col * 32, r * 32))
    save(tiles_img, 'tiles', 'forest_tileset.png')
    objects = [
        ('tree_oak', obj_tree_oak()), ('tree_pine', obj_tree_pine()), ('stump', obj_stump()), ('log_fallen', obj_log()),
        ('rock_small', obj_rock(32, 32, [(15, 24, 9, 7), (20, 26, 7, 5)])),
        ('rock_large', obj_rock(64, 48, [(28, 32, 20, 14), (42, 36, 14, 10), (18, 38, 12, 8)], moss=True)),
        ('flowers', obj_flowers()), ('fence_mid', obj_fence('mid')), ('fence_end', obj_fence('end')), ('fence_broken', obj_fence('broken')),
    ]
    for name, o in objects:
        save(o, 'objects', f'{name}.png')
    write_spriteframes('player', 'characters', pl)
    write_spriteframes('slime', 'monsters', sl)
    write_tileset()
    write_palette()
    preview({'player': pl, 'slime': sl}, tiles_img, icons, [o for _, o in objects])
    print('완료:', OUT)


if __name__ == '__main__':
    sys.exit(main())
