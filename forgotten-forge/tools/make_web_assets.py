#!/usr/bin/env python3
"""《잊혀진 대장간》 웹 버전용 메이플풍 고해상도 에셋 생성기.

주인공(키 약 48px, 남/여), 몬스터 3종을 도트 시트 PNG로 뽑고, 프레임 정보(JSON)와 함께
forgotten-forge/index.html 안의 WEB_ASSETS 블록에 data URI로 주입한다.

커스터마이징은 "열쇠 색"으로 한다. 머리·피부·눈·옷 부위를 정해진 기본색으로 그려 두면
게임이 그 색을 선택한 색의 명암으로 바꿔 끼운다. (JS의 shade()와 같은 규칙으로 계산)

실행:  python3 forgotten-forge/tools/make_web_assets.py
"""
import base64
import io
import json
import math
import os
import re
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_assets as MA  # noqa: E402  (픽셀 캔버스 Cv 재사용)

Cv = MA.Cv
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'web-assets')
PREVIEW = os.path.join(ROOT, 'assets-preview', 'web')
HTML = os.path.join(ROOT, 'index.html')


def shade(hexc, amt):
    """JS shade(hex, amt)와 똑같이 각 채널에 amt를 더하고 0~255로 자른다."""
    n = int(hexc[1:], 16)
    r = max(0, min(255, (n >> 16) + amt))
    g = max(0, min(255, ((n >> 8) & 255) + amt))
    b = max(0, min(255, (n & 255) + amt))
    return '#%02x%02x%02x' % (r, g, b)


# ───────── 열쇠 색 (부위별 명암 단계) ─────────
# 단계 이름 → 기본색에서 더할 밝기. JS의 KEY_STEPS와 같아야 한다.
KEY_STEPS = {
    'hair':   {'H0': 45, 'H1': 0, 'H2': -40, 'H3': -70, 'HX': -100},
    'skin':   {'S0': 14, 'S1': 0, 'S2': -30, 'S3': -52, 'SX': -95},
    'eye':    {'E0': 50, 'E1': 0, 'E2': -48},
    'outfit': {'O0': 38, 'O1': 0, 'O2': -42, 'O3': -72, 'OX': -100},
}
KEY_DEFAULT = {'hair': '#6b3e26', 'skin': '#f6cfa8', 'eye': '#4a3020', 'outfit': '#3b6db0'}

WPAL = {
    'ol': '#1a1220', 'w': '#ffffff', 'shine': '#f4f2ff', 'lash': '#1c1420', 'pupil': '#120c18',
    'mouth': '#b0505a', 'mouthD': '#6a2028', 'blush': '#f4a0a8', 'tongue': '#e86a7a',
    'SC0': '#e86a5a', 'SC1': '#c8383a', 'SC2': '#a02a34', 'SCX': '#5a1018',
    'P1': '#3d3448', 'P2': '#2c2536', 'PX': '#16121c',
    'B0': '#7a5236', 'B1': '#5a3a26', 'B2': '#3a2418', 'BX': '#1c120c',
    'BL1': '#6a4426', 'BL2': '#4a2e18', 'GD0': '#fff0a0', 'GD1': '#e8c060', 'GD2': '#a8802a',
    'RB0': '#ff9ab0', 'RB1': '#ff6a8a', 'RB2': '#c8405e',
}
for part, steps in KEY_STEPS.items():
    for k, amt in steps.items():
        WPAL[k] = shade(KEY_DEFAULT[part], amt)
# 열쇠 색끼리, 그리고 다른 색과 겹치면 바꿔 끼울 때 엉뚱한 곳이 물든다
_vals = list(WPAL.values())
assert len(set(_vals)) == len(_vals), '팔레트에 중복 색이 있음'
MA.RGB.update({k: tuple(int(v[i:i + 2], 16) for i in (1, 3, 5)) for k, v in WPAL.items()})

class _AutoRGB(dict):
    """'#rrggbb' 이름은 등록 없이도 바로 색으로 쓴다."""

    def __missing__(self, k):
        if isinstance(k, str) and k.startswith('#') and len(k) == 7:
            v = tuple(int(k[i:i + 2], 16) for i in (1, 3, 5))
            self[k] = v
            return v
        raise KeyError(k)


MA.RGB = _AutoRGB(MA.RGB)

# 외곽선: 안쪽 색에 맞춘 어두운 색(셀아웃). 열쇠 부위는 열쇠 외곽선 색으로.
OUTLINE_OF = {}
for k in WPAL:
    if k[0] == 'H':
        OUTLINE_OF[k] = 'HX'
    elif k[0] == 'S' and k[1].isdigit():
        OUTLINE_OF[k] = 'SX'
    elif k[0] == 'O':
        OUTLINE_OF[k] = 'OX'
    elif k.startswith('SC'):
        OUTLINE_OF[k] = 'SCX'
    elif k[0] == 'P':
        OUTLINE_OF[k] = 'PX'
    elif k[0] == 'B' and k[1].isdigit():
        OUTLINE_OF[k] = 'BX'


def selout(c, mapping=None, default='ol'):
    mapping = OUTLINE_OF if mapping is None else mapping
    add = {}
    for y in range(c.h):
        for x in range(c.w):
            if (x, y) in c.p:
                continue
            best = None
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                col = c.p.get((x + dx, y + dy))
                if col is not None and (x + dx, y + dy) not in c.ol:
                    best = mapping.get(col, default)
                    if dy == -1:   # 아래쪽 외곽선은 항상 가장 진하게
                        best = default if best not in ('HX', 'SX', 'OX') else best
                    break
            if best:
                add[(x, y)] = best
    for q, col in add.items():
        c.p[q] = col
        c.ol.add(q)
    return c


def thick_line(c, x0, y0, x1, y1, col, w=2):
    for ox in range(-(w // 2), w - w // 2):
        for oy in range(-(w // 2), w - w // 2):
            c.line(x0 + ox, y0 + oy, x1 + ox, y1 + oy, col)


# ───────── 주인공 ─────────
HW, HH, HAX, HAY = 48, 56, 24, 54   # 프레임 크기 · 발 기준점

HERO_POSES = {'idle0': dict(bob=0, hair=0), 'idle1': dict(bob=0, hair=1), 'idle2': dict(bob=1, hair=2), 'idle3': dict(bob=1, hair=1)}
for i in range(6):
    a = i / 6 * math.pi * 2
    HERO_POSES['run%d' % i] = dict(bob=1 if i % 3 == 0 else 0, fx=round(math.sin(a) * 4), bx=-round(math.sin(a) * 4),
                                   fl=max(0, round(math.cos(a) * 3)), bl=max(0, round(-math.cos(a) * 3)),
                                   arm=-round(math.sin(a) * 2), hair=i)
HERO_POSES['jump'] = dict(bob=-1, fl=4, bl=3, fx=2, bx=-1, arm=-2, hair=3)
HERO_POSES['fall'] = dict(bob=0, fl=1, bl=1, fx=4, bx=-4, arm=1, hair=5)
HERO_POSES['hurt'] = dict(bob=1, lean=-2, hurt=True, arm=2, hair=4)


def hero(gender, pose_name):
    p = dict(bob=0, lean=0, fx=0, bx=0, fl=0, bl=0, arm=0, hair=0, hurt=False)
    p.update(HERO_POSES[pose_name])
    fem = gender == 'f'
    c = Cv(HW, HH)
    b, L, hs = p['bob'], p['lean'], p['hair']

    # 목도리 꼬리 (가장 뒤)
    for i in range(9):
        y = 31 + b + round(math.sin(hs * 1.1 + i * 0.75)) + i // 3
        c.rect(17 - i + L // 2, y, 1, 3 if i < 6 else 2, 'SC1' if i % 2 == 0 else 'SC2')
        if i % 3 == 0:
            c.px(17 - i + L // 2, y, 'SC0')

    # 긴 머리 뒤쪽 (여)
    if fem:
        sway = (hs % 3) - 1
        c.poly([(13 + L, 14 + b), (24 + L, 12 + b), (23 + L, 42 + b), (17 + L + sway, 46 + b), (11 + L + sway, 40 + b), (11 + L, 26 + b)], 'H2')
        c.poly([(14 + L, 16 + b), (21 + L, 15 + b), (20 + L, 40 + b), (15 + L + sway, 42 + b)], 'H1')
        for y in range(20 + b, 40 + b, 3):
            c.px(16 + L + (y % 2), y, 'H0')

    # 다리
    def leg(x, lift, back):
        pc = 'P2' if back else 'P1'
        for y in range(43, 50 - lift):
            c.rect(x, y, 3, 1, pc)
        if not back:
            c.rect(x, 43, 1, 50 - lift - 43, 'P2')
        c.rect(x - 1, 50 - lift, 5, 3, 'B2' if back else 'B1')
        c.rect(x + 1, 50 - lift, 3, 1, 'B1' if back else 'B0')
        c.rect(x - 1, 53 - lift, 6, 1, 'B2' if back else 'B1')
        c.rect(x + 3, 51 - lift, 2, 2, 'B2' if back else 'B1')
    leg(20 + p['bx'], p['bl'], True)

    # 뒷팔
    thick_line(c, 20, 31 + b, 19 - p['arm'], 37 + b, 'O2', 3)
    c.rect(18 - p['arm'], 38 + b, 2, 2, 'S2')

    leg(25 + p['fx'], p['fl'], False)

    # 몸통 (튜닉 / 원피스)
    c.rect(18, 29 + b, 12, 10, 'O1')
    c.rect(18, 29 + b, 3, 10, 'O2')
    c.rect(28, 31 + b, 1, 6, 'O0')
    c.rect(23, 31 + b, 1, 6, 'O2')
    if fem:
        c.poly([(17, 37.5 + b), (31, 37.5 + b), (34, 45.5 + b), (14, 45.5 + b)], 'O1')
        for x in (18, 22, 26, 30):
            c.line(x, 40 + b, x - (1 if x < 24 else -1), 44 + b, 'O2')
        c.rect(15, 45 + b, 19, 1, 'O2')
        c.rect(19, 39 + b, 10, 1, 'O0')
    else:
        c.rect(17, 38 + b, 14, 5, 'O1')
        c.rect(17, 42 + b, 14, 1, 'O2')
        c.rect(17, 38 + b, 3, 5, 'O2')
        c.px(27, 41 + b, 'O3'); c.px(27, 42 + b, 'O3')
        c.rect(29, 39 + b, 1, 3, 'O0')
    c.rect(18, 37 + b, 12, 2, 'BL1')
    c.rect(18, 38 + b, 12, 1, 'BL2')
    c.rect(26, 37 + b, 2, 2, 'GD1'); c.px(26, 37 + b, 'GD0')

    # 목도리 (목 둘레)
    c.rect(19, 28 + b, 11, 3, 'SC1')
    c.rect(19, 30 + b, 11, 1, 'SC2')
    c.rect(21, 28 + b, 5, 1, 'SC0')

    # 머리 뒤쪽 덩어리 (남)
    hx, hy = L, b
    if not fem:
        c.ell(22 + hx, 17 + hy, 11, 11, 'H2')

    # 얼굴
    c.ell(25 + hx, 20 + hy, 10, 9.5, 'S1')
    c.poly([(19 + hx, 25 + hy), (34 + hx, 24 + hy), (30 + hx, 30 + hy), (23 + hx, 30 + hy)], 'S1')
    for y in range(12 + hy, 30 + hy):
        for x in range(14 + hx, 18 + hx):
            if c.get(x, y) == 'S1':
                c.px(x, y, 'S2')
    c.rect(23 + hx, 30 + hy, 6, 1, 'S2')
    c.px(33 + hx, 15 + hy, 'S0'); c.px(34 + hx, 16 + hy, 'S0')
    # 귀
    c.ell(18.5 + hx, 21.5 + hy, 2, 3, 'S1')
    c.px(18 + hx, 21 + hy, 'S2'); c.px(18 + hx, 22 + hy, 'S3')

    # 눈 (가까운 눈은 크게 + 흰자, 먼 눈은 좁게)
    def eye(x0, wdt, near):
        top = 18 + hy
        if p['hurt']:
            for i in range(3):
                c.px(x0 + i, top + 2 + (i if i < 2 else 4 - i - 1), 'lash')
                c.px(x0 + i, top + 2 + i, 'lash') if i < 2 else c.px(x0 + i, top + 3, 'lash')
            return
        c.rect(x0 - 1, top, wdt + 2, 1, 'lash')
        c.rect(x0, top + 1, wdt, 1, 'lash')
        c.rect(x0, top + 2, wdt, 5, 'E1')
        c.rect(x0, top + 5, wdt, 1, 'E0')
        c.rect(x0, top + 6, wdt, 1, 'E1')
        c.rect(x0 + (1 if wdt > 3 else 0), top + 2, 2, 3, 'E2')
        c.px(x0 + (1 if wdt > 3 else 1), top + 3, 'pupil')
        c.rect(x0, top + 2, 2 if near else 1, 2 if near else 1, 'w')
        c.px(x0 + wdt - 1, top + 5, 'w')
        c.rect(x0, top + 7, wdt, 1, 'E2') if near else c.px(x0 + 1, top + 7, 'E2')
        if near:
            c.rect(x0 + wdt, top + 2, 1, 4, 'shine')
        if fem:
            c.px(x0 + wdt + 1, top - 1, 'lash')
            c.px(x0 + wdt + 2, top - 2, 'lash') if near else None
    eye(28 + hx, 4, True)
    eye(21 + hx, 3, False)
    # 눈썹 · 코 · 입 · 볼
    c.line(21 + hx, 16 + hy, 23 + hx, 15 + hy, 'H3')
    c.line(28 + hx, 15 + hy, 31 + hx, 15 + hy, 'H3')
    c.px(35 + hx, 23 + hy, 'S2')
    if p['hurt']:
        c.rect(29 + hx, 26 + hy, 3, 2, 'mouthD'); c.px(30 + hx, 27 + hy, 'tongue')
    else:
        c.rect(29 + hx, 27 + hy, 2, 1, 'mouth'); c.px(31 + hx, 26 + hy, 'mouth')
    if fem:
        c.rect(20 + hx, 25 + hy, 2, 1, 'blush'); c.rect(32 + hx, 26 + hy, 2, 1, 'blush')

    # 앞머리 · 머리 윗부분
    dome = Cv(HW, HH)
    dome.ell(24 + hx, 13 + hy, 12.5, 8.5, 'H1')
    for (x, y), col in dome.p.items():
        if y <= 14 + hy:
            c.px(x, y, col)
    if fem:
        c.poly([(15 + hx, 13 + hy), (37 + hx, 13 + hy), (36 + hx, 18 + hy), (31 + hx, 16 + hy), (27 + hx, 19 + hy), (22 + hx, 16 + hy), (18 + hx, 20 + hy)], 'H1')
        c.poly([(15 + hx, 14 + hy), (20 + hx, 14 + hy), (20 + hx, 34 + hy), (17 + hx, 37 + hy), (14 + hx, 31 + hy)], 'H1')
        c.line(17 + hx, 18 + hy, 17 + hx, 33 + hy, 'H2')
        # 리본
        c.poly([(13 + hx, 6 + hy), (18 + hx, 9 + hy), (13 + hx, 12 + hy)], 'RB1')
        c.poly([(23 + hx, 6 + hy), (18 + hx, 9 + hy), (23 + hx, 12 + hy)], 'RB1')
        c.px(14 + hx, 8 + hy, 'RB0'); c.px(22 + hx, 8 + hy, 'RB0')
        c.rect(17 + hx, 8 + hy, 2, 2, 'RB2')
    else:
        for tri in ([(16, 13), (21, 13), (18, 20)], [(20, 13), (26, 13), (23, 19)], [(25, 13), (31, 13), (29, 20)], [(30, 13), (36, 13), (35, 18)]):
            c.poly([(x + hx, y + hy) for x, y in tri], 'H1')
        c.poly([(16 + hx, 13 + hy), (20 + hx, 13 + hy), (19 + hx, 21 + hy), (17 + hx, 21 + hy)], 'H1')
        for tri in ([(15, 9), (19, 7), (12, 4)], [(21, 6), (26, 5), (25, 0)], [(28, 6), (33, 8), (35, 2)], [(11, 15), (14, 10), (8, 12)]):
            c.poly([(x + hx, y + hy) for x, y in tri], 'H1')
        c.line(23 + hx, 15 + hy, 23 + hx, 18 + hy, 'H2')
        c.line(29 + hx, 15 + hy, 29 + hx, 19 + hy, 'H2')
    # 머리 하이라이트 (윗머리 둥근 광택)
    for x in range(18, 31):
        y = round(8 + ((x - 24) / 7.0) ** 2 * 2.2)
        c.px(x + hx, y + hy, 'H0')
        if 20 <= x <= 27:
            c.px(x + hx, y + 1 + hy, 'H0')
    c.px(33 + hx, 11 + hy, 'H0')
    for (x, y), col in list(c.p.items()):
        if col == 'H1' and c.get(x, y + 1) in ('S1', 'S2', 'S0'):
            c.px(x, y, 'H2')

    # 앞팔 + 손 (손 위치를 메타데이터로 내보낸다)
    hand = (31 + p['arm'], 38 + b)
    thick_line(c, 28, 31 + b, hand[0] - 1, hand[1] - 1, 'O1', 3)
    c.px(28, 31 + b, 'O0')
    c.rect(hand[0] - 1, hand[1] - 1, 3, 3, 'S1')
    c.px(hand[0] + 1, hand[1] + 1, 'S2')

    selout(c)
    return c, (hand[0] - HAX, hand[1] - HAY), b


# ───────── 몬스터 공용: 크기만 키운 좌표계 + 굵은 선 ─────────
def H(hexc):
    """임의의 #색을 팔레트에 등록하고 그대로 이름으로 쓴다."""
    if hexc not in MA.RGB:
        MA.RGB[hexc] = tuple(int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    return hexc


class Scaled:
    """옛 v0.3 좌표(작은 캔버스)를 큰 캔버스로 옮겨 그리는 래퍼."""

    def __init__(self, c, k, src_anchor, dst_anchor):
        self.c, self.k, self.sa, self.da = c, k, src_anchor, dst_anchor

    def t(self, x, y):
        return ((x - self.sa[0]) * self.k + self.da[0], (y - self.sa[1]) * self.k + self.da[1])

    def R(self, x, y, w, h_, col):
        x0, y0 = self.t(x, y)
        self.c.rect(x0, y0, max(1, round(w * self.k)), max(1, round(h_ * self.k)), H(col))

    def P(self, x, y, col):
        x0, y0 = self.t(x, y)
        n = max(1, round(self.k))
        self.c.rect(x0, y0, n, n, H(col))

    def ell(self, cx, cy, rx, ry, col):
        x0, y0 = self.t(cx, cy)
        self.c.ell(x0, y0, rx * self.k, ry * self.k, H(col))

    def poly(self, pts, col):
        self.c.poly([self.t(pts[i], pts[i + 1]) for i in range(0, len(pts), 2)], H(col))

    def stroke(self, pts, col, w):
        q = [self.t(pts[i], pts[i + 1]) for i in range(0, len(pts), 2)]
        stamp_path(self.c, q, H(col), w * self.k)

    def curve(self, x0, y0, cx, cy, x1, y1, col, w):
        pts = []
        for i in range(17):
            t = i / 16
            pts += [(1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1, (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1]
        self.stroke(pts, col, w)


def stamp_path(c, pts, col, w):
    r = max(0.5, w / 2)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) * 2))
        for i in range(n + 1):
            x, y = x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n
            for yy in range(int(y - r) - 1, int(y + r) + 2):
                for xx in range(int(x - r) - 1, int(x + r) + 2):
                    if (xx + 0.5 - x) ** 2 + (yy + 0.5 - y) ** 2 <= r * r:
                        c.px(xx, yy, col)


def selout_mono(c, col):
    return selout(c, mapping={}, default=H(col))


# ───────── 초록 슬라임 (40×32) ─────────
SW_, SH_, SAX, SAY = 40, 32, 20, 31


def slime(rx, ry, blink=False):
    c = Cv(SW_, SH_)
    cx, by = 20, 31
    cy = by + 1 - ry
    G0, G1, G2, G3, G4 = H('#c8f898'), H('#8fe070'), H('#5cbf4c'), H('#3e9836'), H('#2a6e26')
    for y in range(SH_):
        for x in range(SW_):
            if y > by:
                continue
            nx, ny = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
            d = nx * nx + ny * ny
            if d > 1:
                continue
            col = G2
            if ny > 0.72 or (d > 0.8 and ny > 0.25):
                col = G4
            elif ny > 0.32 or nx > 0.7:
                col = G3
            elif (nx + 0.35) ** 2 + (ny + 0.4) ** 2 < 0.2:
                col = G1
            if d > 0.86 and nx > 0.45 and ny < 0.1:   # 오른쪽 윤곽 반사광
                col = G1
            c.px(x, y, col)
    # 광택 + 기포
    sx, sy = round(cx - rx * 0.42), round(cy - ry * 0.55)
    c.rect(sx, sy, 3, 2, 'w'); c.px(sx + 3, sy + 1, G0); c.px(sx - 1, sy + 2, G0)
    for (bx, bym) in ((0.45, 0.25), (0.3, 0.45), (-0.2, 0.5)):
        c.px(round(cx + rx * bx), round(cy + ry * bym), G1)
    # 얼굴 (오른쪽을 봄)
    ex, ey = round(cx + rx * 0.08), round(cy - ry * 0.12)
    for e in (ex - 2, ex + 4):
        if blink:
            c.rect(e, ey + 2, 3, 1, H('#143214'))
        else:
            c.rect(e, ey, 3, 4, H('#143214'))
            c.px(e, ey, 'w'); c.px(e + 1, ey, 'w') if ry > 8 else None
            c.px(e + 2, ey + 3, H('#3a6a34'))
    my = ey + 5
    if ry > 6:
        c.px(ex + 1, my, H('#1e4a1a')); c.px(ex + 2, my + 1, H('#1e4a1a')); c.px(ex + 3, my, H('#1e4a1a'))
        c.rect(ex - 3, my - 1, 2, 1, H('#f4a0a8')); c.rect(ex + 6, my - 1, 2, 1, H('#f4a0a8'))
    return selout_mono(c, '#143214')


# ───────── 숲 고블린 (56×56) ─────────
GW, GH_, GAX, GAY = 56, 56, 26, 55


def goblin(pose):
    c = Cv(GW, GH_)
    g = Scaled(c, 1.5, (16, 35), (GAX, GAY))
    S, SD, SL, TU, TD = '#74a84a', '#4f7a30', '#9bd067', '#7a5230', '#54361e'
    b = 1 if pose in ('idle1', 'walk1') else 0
    lean = {'windup': -2, 'strike': 2, 'hurt': -2}.get(pose, 0)
    st = {'walk0': -2, 'walk1': 2, 'strike': 2}.get(pose, 0)
    # 다리 · 각반 · 발
    g.R(12 + st, 27, 3, 6, '#5a6a3a'); g.R(17 - st, 27, 3, 6, '#4a5a2e')
    g.R(12 + st, 29, 3, 1, '#c9b48a'); g.R(17 - st, 29, 3, 1, '#a8946a'); g.R(12 + st, 31, 3, 0.7, '#c9b48a')
    g.R(11 + st, 33, 5, 2, '#3a2618'); g.R(16 - st, 33, 5, 2, '#2a1c12')
    tx, ty = 11 + lean, 17 + b
    hand, tip = {
        'windup': ((tx + 7, ty + 1), (tx - 6, ty - 13)),
        'strike': ((tx + 11, ty + 5), (tx + 24, ty + 10)),
        'hurt': ((tx + 9, ty + 6), (tx + 15, ty - 6)),
    }.get(pose, ((tx + 9, ty + 5), (tx - 5, ty - 9)))

    def club():
        g.stroke([hand[0], hand[1], tip[0], tip[1]], '#7a4c28', 2.6)
        mx, my = MA_lerp(hand[0], tip[0], 0.68), MA_lerp(hand[1], tip[1], 0.68)
        g.stroke([mx, my, tip[0], tip[1]], '#8a5a30', 5.2)
        g.stroke([mx, my, MA_lerp(mx, tip[0], 0.6), MA_lerp(my, tip[1], 0.6)], '#a8703c', 1.4)
        for f_ in (0.35, 0.7):
            g.P(MA_lerp(mx, tip[0], f_) + 1.4, MA_lerp(my, tip[1], f_), '#d0ccc4')
    if pose != 'strike':
        club()
    # 뒷팔
    g.stroke([12 + lean, 20 + b, 9 + lean, 26 + b], SD, 3)
    # 튜닉 (찢어진 밑단) + 허리띠 + 주머니
    g.R(tx, ty, 10, 11, TU); g.R(tx, ty, 2, 11, TD); g.R(tx + 8, ty + 1, 1, 8, '#94683e')
    g.poly([tx - 1, ty + 9, tx + 11, ty + 9, tx + 10, ty + 12, tx + 8, ty + 10, tx + 6, ty + 13, tx + 4, ty + 10, tx + 2, ty + 12, tx, ty + 10], TU)
    g.R(tx, ty + 6, 10, 2, '#3a2618'); g.R(tx + 6, ty + 6, 2, 2, '#c9a050'); g.R(tx + 2, ty + 8, 2.5, 2, '#5e3c1e')
    g.R(tx + 3, ty + 1, 1, 4, TD)
    g.P(tx + 1, ty + 1, '#e8e0c8'); g.P(tx + 3, ty + 0.5, '#e8e0c8'); g.P(tx + 5, ty + 1, '#e8e0c8')   # 뼈 목걸이
    # 머리 (큰 귀 · 찡그린 눈썹 · 코 · 송곳니)
    hx, hy = 15 + round(lean * 1.3), 10 + b
    g.poly([hx - 4, hy - 1, hx - 13, hy - 5, hx - 4, hy + 3], SD); g.poly([hx - 5, hy, hx - 10, hy - 3, hx - 5, hy + 2], '#c98a6a')
    g.ell(hx, hy, 6.5, 6, S); g.ell(hx - 1, hy - 2, 4.5, 3, SL); g.ell(hx - 1, hy + 3, 5.5, 2.5, SD)
    g.poly([hx + 4, hy - 2, hx + 14, hy - 7, hx + 5, hy + 2], S); g.poly([hx + 5, hy - 1, hx + 11, hy - 5, hx + 5, hy + 1], '#c98a6a')
    angry = pose in ('windup', 'strike')
    g.stroke([hx - 1, hy - 3.2, hx + 4.5, hy - 1.2], '#2a3a18', 1.2)
    if pose == 'hurt':
        for q in ((0, 0), (1, 1), (2, 0), (0, 1.5), (2, 1.5)):
            g.P(hx + 1.5 + q[0] * 0.7, hy - 1.5 + q[1], '#1a1a10')
    else:
        g.R(hx + 1, hy - 1.3, 3.2, 2.4, '#ff3b2f' if angry else '#ffdc4a')
        g.P(hx + 2.6, hy - 1, '#1a1010'); g.P(hx + 1.2, hy - 1.3, '#ffffff')
    g.ell(hx + 6, hy + 1, 1.8, 1.6, SD); g.P(hx + 6.4, hy + 0.4, SL)
    g.R(hx + 1, hy + 3, 5, 1, '#2a1a10'); g.P(hx + 2, hy + 2.2, '#f4f0e0'); g.P(hx + 4.6, hy + 2.2, '#f4f0e0')
    # 앞팔 + 옹이 몽둥이
    if pose == 'strike':
        club()
    g.stroke([tx + 8, ty + 2, hand[0], hand[1]], S, 3)
    g.ell(hand[0], hand[1], 1.7, 1.7, SL)
    return selout_mono(c, '#14200c')


def MA_lerp(a, b_, t):
    return a + (b_ - a) * t


# ───────── 폐허의 수호자 (112×104) ─────────
BW, BH_, BAX, BAY = 136, 126, 64, 123


def boss(pose):
    c = Cv(BW, BH_)
    g = Scaled(c, 1.35, (38, 75), (BAX, BAY))
    B, BD, BL, BEL, HORN, HD, CLAW = '#6a3590', '#47206a', '#8d52b8', '#c45ad8', '#c77ff0', '#8a42b8', '#ecd8ff'
    crouch = {'wind_c': 4, 'charge': 3, 'melee': 2}.get(pose, 0)
    lean = {'wind_c': 5, 'charge': 8, 'hurt': -4, 'melee': 4}.get(pose, 0)
    br = 1 if pose == 'idle1' else 0
    step = {'walk0': -3, 'walk1': 3, 'charge': 5}.get(pose, 0)
    cx, cy = 38, 44 + crouch + br
    # 꼬리
    g.curve(cx - 14, cy + 14, cx - 34, cy + 22, cx - 30, cy + 4, BD, 5)
    g.poly([cx - 30, cy + 4, cx - 35, cy - 3, cx - 26, cy + 2], HD)

    def leg(x, s_, col):
        g.stroke([x, cy + 12, x + s_, cy + 24, x + s_, 70], col, 9)
        g.R(x + s_ - 6, 69, 12, 4, col)
        for dx, y in ((-6, 72), (-1, 73), (4, 72)):
            g.poly([x + s_ + dx, y, x + s_ + dx + 2.5, y + 2.5, x + s_ + dx - 1, y + 2.5], CLAW)
    leg(cx - 10, -step, BD)
    leg(cx + 9, step, B)
    arm_up = {'wind_m': 2, 'melee': -1, 'charge': -0.5, 'wind_c': -0.5, 'idle1': 1.1}.get(pose, 1)

    def arm(side, col):
        sx, sy = cx + side * 18 + lean * 0.6, cy - 12
        if arm_up >= 2:
            ex, ey, hx, hy = sx + side * 10, sy - 14, sx + side * 6, sy - 30
        elif arm_up <= -1:
            ex, ey, hx, hy = sx + 14, sy + 6, sx + 26, sy + 16
        elif arm_up < 0:
            ex, ey, hx, hy = sx + side * 4 + 8, sy + 8, sx + 16, sy + 14
        else:
            ex, ey, hx, hy = sx + side * 14, sy - 2 * arm_up, sx + side * 16, sy - 16 * arm_up
        g.stroke([sx, sy, ex, ey, hx, hy], col, 8)
        g.stroke([sx, sy, ex, ey], shade(col, 25), 3)
        for i in (-1, 0, 1):
            a = math.atan2(hy - ey, hx - ex) + i * 0.5
            g.stroke([hx, hy, hx + math.cos(a) * 6.5, hy + math.sin(a) * 6.5], CLAW, 2)
    arm(-1, BD)
    L_ = lean
    g.ell(cx + L_, cy - 4, 21, 22, B)
    g.ell(cx + L_ - 6, cy - 12, 12, 10, BL)
    g.ell(cx + L_ + 8, cy + 6, 14, 12, BD)
    g.poly([cx + L_ - 9, cy - 2, cx + L_ + 9, cy - 2, cx + L_ + 5, cy + 10, cx + L_, cy + 15, cx + L_ - 5, cy + 10], BEL)
    g.poly([cx + L_ - 5, cy, cx + L_ + 4, cy, cx + L_, cy + 9], '#e58aef')
    for vx in ((-14, -2, -8, 6), (13, -6, 10, 4), (-4, 12, 2, 16)):
        g.stroke([cx + L_ + vx[0], cy + vx[1], cx + L_ + vx[2], cy + vx[3]], '#b070e0', 0.9)
    hy = cy - 24
    for side in (-1, 1):
        g.curve(cx + L_ + side * 10, hy + 2, cx + L_ + side * 30, hy - 2, cx + L_ + side * 24, hy - 22, HD, 6)
        g.curve(cx + L_ + side * 10, hy + 1, cx + L_ + side * 28, hy - 4, cx + L_ + side * 24, hy - 21, HORN, 3)
        g.poly([cx + L_ + side * 4, hy, cx + L_ + side * 6, hy - 9, cx + L_ + side * 1, hy], HORN)
    glow = pose in ('wind_c', 'wind_m', 'charge')
    eye_c = '#ff5a3a' if glow else '#ffe24a'
    g.poly([cx + L_ - 12, cy - 18, cx + L_ - 3, cy - 15, cx + L_ - 4, cy - 12, cx + L_ - 11, cy - 14], eye_c)
    g.poly([cx + L_ + 12, cy - 18, cx + L_ + 3, cy - 15, cx + L_ + 4, cy - 12, cx + L_ + 11, cy - 14], eye_c)
    g.R(cx + L_ - 7, cy - 15, 2, 2, '#2a0a10'); g.R(cx + L_ + 6, cy - 15, 2, 2, '#2a0a10')
    g.P(cx + L_ - 10, cy - 16, '#fff6c0'); g.P(cx + L_ + 9, cy - 16, '#fff6c0')
    g.stroke([cx + L_ - 13, cy - 20, cx + L_ - 3, cy - 17], BD, 2)
    g.stroke([cx + L_ + 13, cy - 20, cx + L_ + 3, cy - 17], BD, 2)
    mo = 4 if pose in ('wind_m', 'wind_c', 'hurt') else 2
    g.ell(cx + L_, cy - 6, 10, mo + 2, '#2a0f30')
    for i in range(-8, 9, 3):
        g.poly([cx + L_ + i - 1, cy - 8 - mo * 0.5, cx + L_ + i + 1, cy - 8 - mo * 0.5, cx + L_ + i, cy - 5 - mo * 0.4], '#ffffff')
    for i in range(-6, 7, 4):
        g.poly([cx + L_ + i - 1, cy - 3 + mo * 0.6, cx + L_ + i + 1, cy - 3 + mo * 0.6, cx + L_ + i, cy - 6 + mo * 0.5], '#f0e6ff')
    if mo > 2:
        g.ell(cx + L_, cy - 4, 4, 1.5, '#c8405e')
    arm(1, B)
    return selout_mono(c, '#1e0a2a')


SLIME_POSES = {'idle0': (13, 10), 'idle1': (13.6, 9.4), 'blink': (13, 10, True), 'jump': (11, 12.5), 'land': (15.5, 7.5)}
GOBLIN_POSES = ['idle0', 'idle1', 'walk0', 'walk1', 'windup', 'strike', 'hurt']
BOSS_POSES = ['idle0', 'idle1', 'walk0', 'walk1', 'wind_m', 'melee', 'wind_c', 'charge', 'hurt']


def build_monsters():
    sheets, meta = {}, {}
    fr = [slime(*v) for v in SLIME_POSES.values()]
    sheets['slime'] = pack(fr, SW_, SH_)
    meta['slime'] = {'fw': SW_, 'fh': SH_, 'ax': SAX, 'ay': SAY, 'poses': list(SLIME_POSES.keys())}
    sheets['goblin'] = pack([goblin(p_) for p_ in GOBLIN_POSES], GW, GH_)
    meta['goblin'] = {'fw': GW, 'fh': GH_, 'ax': GAX, 'ay': GAY, 'poses': GOBLIN_POSES}
    sheets['boss'] = pack([boss(p_) for p_ in BOSS_POSES], BW, BH_)
    meta['boss'] = {'fw': BW, 'fh': BH_, 'ax': BAX, 'ay': BAY, 'poses': BOSS_POSES}
    return sheets, meta


# ───────── 2단계: 무기 · 장비 아이콘 ─────────
def img_outline(im, dark=0.32):
    """이미지 단위 셀아웃: 바깥 테두리를 이웃 색의 어두운 버전으로."""
    im = im.copy()
    px = im.load()
    W_, H_ = im.size
    add = {}
    for y in range(H_):
        for x in range(W_):
            if px[x, y][3]:
                continue
            for dx, dy in ((0, 1), (1, 0), (-1, 0), (0, -1)):
                xx, yy = x + dx, y + dy
                if 0 <= xx < W_ and 0 <= yy < H_ and px[xx, yy][3]:
                    r, g, b_, _ = px[xx, yy]
                    k = dark * (0.7 if dy == -1 else 1.0)
                    add[(x, y)] = (int(r * k) + 8, int(g * k) + 6, int(b_ * k) + 12, 255)
                    break
    for q, c_ in add.items():
        px[q] = c_
    return im


def rot45(im):
    """도트를 45° 돌리기: 4배로 키워 돌린 뒤 4×4 칸마다 다수결로 줄인다."""
    big = im.resize((im.width * 4, im.height * 4), Image.NEAREST).rotate(45, Image.NEAREST, expand=True)
    W_, H_ = big.width // 4, big.height // 4
    out = Image.new('RGBA', (W_, H_), (0, 0, 0, 0))
    bp, op = big.load(), out.load()
    for y in range(H_):
        for x in range(W_):
            cols = {}
            n = 0
            for yy in range(4):
                for xx in range(4):
                    c_ = bp[x * 4 + xx, y * 4 + yy]
                    if c_[3]:
                        n += 1
                        cols[c_] = cols.get(c_, 0) + 1
            if n >= 7:
                op[x, y] = max(cols, key=cols.get)
    bb = out.getbbox()
    return out.crop(bb) if bb else out


def fit_icon(im, size=32):
    im = im.crop(im.getbbox()) if im.getbbox() else im
    out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    out.alpha_composite(im, ((size - im.width) // 2, (size - im.height) // 2))
    return out


WEAPONS = {
    # id: 계열, 색 정의
    'rusty':    ('sword', dict(edge='#c4ccd8', blade='#8a94a8', shadow='#5a6278', guard=('#5a6278', '#3a4050'), grip=('#8a5a34', '#5e3a20'), pommel='#5a6278', L=18, rust=True)),
    'squire':   ('sword', dict(edge='#eef2f6', blade='#c4ccd8', shadow='#8a94a8', guard=('#8a94a8', '#5a6278'), grip=('#5e3a20', '#3a2414'), pommel='#8a94a8', L=19)),
    'hunter':   ('sword', dict(edge='#ffffff', blade='#d8dee6', shadow='#9aa4b6', guard=('#e8c060', '#a8802a'), grip=('#3e9038', '#276028'), pommel='#e8c060', gem='#6cc048', L=20, fuller='#a8b0c0')),
    'thorn':    ('sword', dict(edge='#d8f0b8', blade='#8fc86a', shadow='#4f8a3a', guard=('#5e3a20', '#3a2414'), grip=('#3e9038', '#276028'), pommel='#4f8a3a', gem='#c8f088', L=21, thorns=True)),
    'moon':     ('sword', dict(edge='#f0fbff', blade='#a8e0ff', shadow='#6ab8f0', guard=('#eef2f6', '#8a94a8'), grip=('#284080', '#1a2a58'), pommel='#c4ccd8', gem='#2a5ad8', L=22, fuller='#2a5ad8', crescent=True)),
    'ember':    ('sword', dict(edge='#fff0a0', blade='#ffb030', shadow='#f06020', guard=('#f0c850', '#b88a2a'), grip=('#3a2414', '#b88a2a'), pommel='#f0c850', gem='#e03030', L=24, fuller='#a02818', flames=True)),
    'shortbow': ('bow', dict(wood='#a06a3c', dark='#6a4426', light='#c8905a', grip='#5e3a20', string='#e8e0d0')),
    'bonebow':  ('bow', dict(wood='#e8dcc0', dark='#b0a080', light='#fff8e8', grip='#7a5236', string='#d8d0c0', bands=True)),
    'windbow':  ('bow', dict(wood='#5fb8a0', dark='#2f7868', light='#a8ecd8', grip='#3a2414', string='#f0fff8', feathers=True)),
    'starbow':  ('bow', dict(wood='#a888f0', dark='#6a4ab0', light='#e0d0ff', grip='#2a1a48', string='#fff6c0', stars=True)),
    'rustspear':   ('spear', dict(head='#a89a88', headD='#6e6456', headL='#d0c4b0', shaft='#7a5230', shaftD='#54361e', ring='#5a6278')),
    'knightspear': ('spear', dict(head='#d8dee6', headD='#8a94a8', headL='#ffffff', shaft='#6a4426', shaftD='#3a2414', ring='#e8c060', tassel='#d03838')),
    'guardspear':  ('spear', dict(head='#b98cff', headD='#7a4ad0', headL='#efe0ff', shaft='#3a2a4a', shaftD='#22182e', ring='#e8c060', wings=True)),
    'club':     ('mace', dict(shape='club', head='#8a5a30', headD='#5e3c1e', headL='#b07a48', handle='#6b4526')),
    'morning':  ('mace', dict(shape='spike', head='#8d9096', headD='#5a5e66', headL='#d0d4dc', handle='#5e3a20')),
    'earth':    ('mace', dict(shape='hammer', head='#c08a4a', headD='#7a5428', headL='#e8b878', handle='#4a2e18', rune='#c06bff')),
}


def draw_weapon(kind, d, short=False):
    """손잡이를 기준점으로 오른쪽을 향한 무기. 반환: (Cv, 기준점, 길이, 활 시위 정보)."""
    c = Cv(64, 44)
    string = None
    if kind == 'sword':
        ax, ay = 9, 22
        L = d['L'] - (2 if short else 0)
        c.rect(2, 21, 3, 3, d['pommel']); c.px(2, 21, shade(d['pommel'], 40))
        for x in range(5, 12):
            c.rect(x, 21, 1, 3, d['grip'][(x // 2) % 2])
        c.rect(12, 15, 3, 13, d['guard'][0]); c.rect(12, 15, 3, 1, d['guard'][1]); c.rect(12, 27, 3, 1, d['guard'][1])
        c.rect(14, 16, 1, 11, d['guard'][1])
        if d.get('crescent'):
            c.rect(11, 13, 2, 3, d['guard'][0]); c.rect(11, 27, 2, 3, d['guard'][0]); c.px(10, 12, d['guard'][0]); c.px(10, 30, d['guard'][0])
        if d.get('gem'):
            c.rect(12, 20, 3, 3, d['gem']); c.px(12, 20, '#ffffff')
        x0 = 15
        for i in range(L):
            x = x0 + i
            taper = max(0, i - (L - 4))
            top, bot = 19 + taper // 2 + (1 if taper >= 3 else 0), 24 - (taper + 1) // 2
            for y in range(top, bot):
                col = d['blade']
                if y == top:
                    col = d['edge']
                elif y == bot - 1:
                    col = d['shadow']
                c.px(x, y, col)
            if d.get('fuller') and 1 < i < L - 6:
                c.px(x, 21, d['fuller'])
        c.px(x0 + L, 21, d['edge'])
        if d.get('rust'):
            for i, col in ((3, '#a06e3c'), (7, '#7a5030'), (11, '#a06e3c'), (14, '#7a5030')):
                c.px(x0 + i, 21 + (i % 2), col)
            c.px(x0 + 9, 19, None); c.px(x0 + 10, 19, None)
        if d.get('thorns'):
            for i in range(3, L - 3, 4):
                c.px(x0 + i, 18, d['shadow']); c.px(x0 + i + 2, 24, d['shadow'])
        if d.get('flames'):
            for i in range(2, L - 2, 4):
                c.px(x0 + i, 18, d['blade']); c.px(x0 + i + 1, 17, d['edge'])
                c.px(x0 + i + 2, 24, d['shadow']); c.px(x0 + i + 3, 25, d['blade'])
        length = x0 + L - ax
    elif kind == 'spear':
        ax, ay = 18, 22
        end = 46 if not short else 34
        c.rect(2, 21, 3, 2, d['ring'])
        for x in range(5, end):
            c.px(x, 21, d['shaft']); c.px(x, 22, d['shaftD'])
            if x % 7 == 0:
                c.px(x, 21, d['shaftD'])
        c.rect(end, 20, 2, 4, d['ring'])
        hx = end + 2
        for i in range(10):
            hw = [1, 2, 3, 3, 3, 2, 2, 1, 1, 0][i]
            for o in range(-hw, hw + 1):
                c.px(hx + i, 21.5 + o, d['head'] if o < 0 else d['headD'])
            c.px(hx + i, 21, d['headL']) if i < 8 else None
        c.px(hx + 10, 21, d['headL'])
        if d.get('tassel'):
            for k_ in range(5):
                c.px(end - 1 - (k_ % 2), 24 + k_, d['tassel'])
        if d.get('wings'):
            c.poly([(hx - 1, 19), (hx - 4, 14), (hx + 2, 18)], d['head']); c.poly([(hx - 1, 24), (hx - 4, 29), (hx + 2, 25)], d['headD'])
        length = hx + 10 - ax
    elif kind == 'mace':
        ax, ay = 6, 22
        for x in range(2, 18):
            c.rect(x, 21, 1, 3, d['handle'] if x % 4 else shade(d['handle'], -25))
        c.rect(2, 20, 2, 5, shade(d['handle'], -30))
        if d['shape'] == 'club':
            c.ell(23, 22, 7, 5.5, d['head']); c.ell(22, 20.5, 4.5, 2.5, d['headL'])
            c.ell(24, 24.5, 5, 2, d['headD'])
            for q in ((20, 24), (26, 19), (24, 23)):
                c.px(q[0], q[1], d['headD'])
            for q in ((28, 20), (23, 17), (27, 26)):
                c.px(q[0], q[1], '#d0ccc4')
            length = 30 - ax
        elif d['shape'] == 'spike':
            c.ell(23, 22, 5.5, 5.5, d['head']); c.ell(21.5, 20.5, 2.5, 2.5, d['headL']); c.ell(24.5, 24, 3, 2, d['headD'])
            for (sx, sy, ex, ey) in ((23, 16, 23, 13), (23, 28, 23, 31), (29, 22, 32, 22), (19, 18, 17, 16), (27, 18, 29, 16), (19, 26, 17, 28), (27, 26, 29, 28)):
                c.line(sx, sy, ex, ey, '#e8ecf0')
            length = 32 - ax
        else:
            c.rect(17, 14, 12, 17, d['head']); c.rect(17, 14, 12, 2, d['headL']); c.rect(17, 29, 12, 2, d['headD'])
            c.rect(27, 16, 2, 13, d['headD']); c.rect(17, 16, 1, 13, d['headL'])
            c.rect(21, 19, 4, 7, d['rune']); c.rect(22, 20, 2, 5, shade(d['rune'], 60))
            length = 29 - ax
    else:  # bow
        ax, ay = 12, 22
        top, bot = 4, 40
        for y in range(top, bot + 1):
            dy = (y - 22) / 18
            x = round(12 - 7 * dy * dy)
            w_ = 3 if abs(dy) < 0.5 else 2
            for k_ in range(w_):
                c.px(x + k_, y, d['light'] if k_ == w_ - 1 else (d['wood'] if k_ else d['dark']))
            if d.get('bands') and y % 5 == 0:
                c.rect(x, y, w_, 1, d['dark'])
        c.rect(11, 19, 4, 7, d['grip']); c.px(14, 19, shade(d['grip'], 40))
        c.line(5, top + 1, 5, bot - 1, d['string'])
        c.px(5, top, d['dark']); c.px(5, bot, d['dark'])
        if d.get('feathers'):
            c.line(6, 6, 9, 9, '#ffffff'); c.line(6, 38, 9, 35, '#ffffff')
        if d.get('stars'):
            for (sx, sy) in ((9, 9), (9, 35), (15, 22)):
                c.px(sx, sy, '#ffffff'); c.px(sx - 1, sy, '#fff6c0'); c.px(sx + 1, sy, '#fff6c0'); c.px(sx, sy - 1, '#fff6c0'); c.px(sx, sy + 1, '#fff6c0')
        length = 6
        string = [5 - ax, top + 1 - ay, bot - 1 - ay]
    return c, (ax, ay), length, string


def armor_icon(kind):
    c = Cv(32, 32)
    if kind == 'cloth':
        b0, b1, b2 = '#a08a6a', '#7d6a55', '#5a4a3a'
        c.poly([(7, 7), (12, 5), (20, 5), (25, 7), (27, 15), (23, 15), (23, 27), (9, 27), (9, 15), (5, 15)], b1)
        c.rect(9, 7, 14, 2, b0); c.poly([(13, 5), (16, 9), (19, 5)], b2)
        c.rect(11, 17, 5, 5, '#8a7a5a'); c.rect(11, 17, 5, 1, '#b0a080'); c.px(12, 19, b2); c.px(14, 20, b2)
        c.rect(18, 22, 4, 3, '#6a5a44')
        c.rect(9, 25, 14, 2, b2)
    elif kind == 'leather':
        b0, b1, b2 = '#b07a48', '#8a5a33', '#5e3a20'
        c.poly([(8, 6), (13, 5), (16, 9), (19, 5), (24, 6), (25, 27), (7, 27)], b1)
        c.rect(8, 6, 3, 21, b2); c.rect(22, 7, 2, 20, b0)
        for y in range(10, 25, 3):
            c.px(15, y, '#e8d8b0'); c.px(17, y + 1, '#e8d8b0')
        c.line(16, 9, 16, 26, b2)
        c.rect(7, 25, 18, 2, '#3a2414')
    elif kind == 'cloak':
        b0, b1, b2 = '#6cc048', '#3f6b3a', '#244a24'
        c.poly([(16, 3), (24, 8), (27, 28), (5, 28), (8, 8)], b1)
        c.ell(16, 9, 6, 6, b2); c.ell(16, 10, 4, 4, '#14200c')
        c.line(10, 14, 7, 27, b2); c.line(22, 14, 25, 27, b0); c.line(16, 16, 16, 27, b2)
        c.rect(14, 15, 4, 2, '#e8c060')
    elif kind == 'plate':
        b0, b1, b2 = '#b0b4bc', '#6d6f73', '#45474c'
        c.poly([(6, 8), (12, 5), (20, 5), (26, 8), (25, 20), (16, 27), (7, 20)], b1)
        c.poly([(9, 9), (16, 7), (16, 24), (9, 19)], b0)
        c.line(16, 7, 16, 25, b2)
        for (x, y) in ((8, 10), (24, 10), (10, 18), (22, 18), (16, 23)):
            c.px(x, y, '#e8ecf0')
        c.rect(12, 13, 3, 2, '#8a5030'); c.rect(18, 15, 3, 2, '#8a5030')   # 고블린식 덧댄 판
    elif kind == 'shadow':
        b0, b1, b2 = '#5a7ac8', '#2f4f86', '#1a2a58'
        c.poly([(5, 8), (12, 5), (20, 5), (27, 8), (26, 20), (16, 28), (6, 20)], b1)
        c.poly([(8, 9), (16, 7), (16, 25), (8, 18)], b0)
        c.ell(16, 15, 4, 4, '#e0f8ff'); c.ell(17.5, 14, 3.5, 3.5, b1)   # 초승달 문장
        c.line(16, 7, 16, 26, b2)
        c.rect(5, 8, 3, 3, '#a8e0ff'); c.rect(24, 8, 3, 3, '#a8e0ff')
    else:  # shell
        b0, b1, b2 = '#a060d0', '#5b2f7a', '#3a1a52'
        c.poly([(4, 10), (10, 4), (22, 4), (28, 10), (26, 22), (16, 29), (6, 22)], b1)
        for y in (9, 15, 21):
            c.line(8, y, 24, y, b2)
            c.line(9, y - 1, 23, y - 1, b0)
        c.poly([(4, 10), (1, 4), (8, 7)], '#e8d0ff'); c.poly([(28, 10), (31, 4), (24, 7)], '#e8d0ff')
        c.rect(14, 12, 4, 4, '#c45ad8'); c.px(14, 12, '#ffd0ff')
    return c


def ring_icon(kind):
    c = Cv(32, 32)
    band = {'copper': ('#e8a060', '#b06a30', '#7a4418'), 'wind': ('#eef2f6', '#a8b0c0', '#6a7488'), 'shade': ('#6a6a88', '#3a3a52', '#22222e'),
            'life': ('#fff0a0', '#e8c060', '#a8802a'), 'seal': ('#fff0a0', '#e8c060', '#a8802a')}[kind]
    for a in range(0, 360, 4):
        r_ = math.radians(a)
        for rr, col in ((8.5, band[2]), (7.5, band[1]), (6.6, band[0] if 200 < a < 340 else band[1])):
            c.px(16 + math.cos(r_) * rr, 19 + math.sin(r_) * rr * 0.8, col)
    gem = {'copper': None, 'wind': '#7fe0c0', 'shade': '#6a5ae0', 'life': '#ff4a6a', 'seal': None}[kind]
    if gem:
        c.ell(16, 10, 4.5, 4, shade(gem, -50)); c.ell(16, 9.5, 3.5, 3, gem); c.rect(14, 8, 2, 2, '#ffffff')
        c.rect(12, 12, 8, 2, band[1])
    if kind == 'seal':
        c.rect(11, 6, 10, 8, band[1]); c.rect(11, 6, 10, 1, band[0]); c.rect(12, 13, 8, 1, band[2])
        c.line(13, 11, 18, 8, '#5e3a20'); c.rect(17, 7, 3, 2, '#5a6278')   # 망치 문양
    if kind == 'copper':
        c.px(10, 15, '#ffd0a0'); c.px(11, 14, '#ffd0a0')
    if kind == 'wind':
        c.line(22, 8, 27, 6, '#bff0ff'); c.line(23, 11, 28, 10, '#bff0ff')
    if kind == 'life':
        c.px(16, 6, '#ffffff'); c.px(22, 7, '#ff9ab0'); c.px(9, 8, '#ff9ab0')
    if kind == 'shade':
        for q in ((24, 9), (8, 12), (23, 26)):
            c.px(q[0], q[1], '#9a8af0')
    return c


def misc_icon(kind):
    c = Cv(32, 32)
    if kind == 'key':
        for a in range(0, 360, 5):
            r_ = math.radians(a)
            c.px(10 + math.cos(r_) * 5, 11 + math.sin(r_) * 5, '#e8c060')
            c.px(10 + math.cos(r_) * 4, 11 + math.sin(r_) * 4, '#fff0a0' if a > 180 else '#e8c060')
        c.px(10, 11, '#c06bff'); c.px(9, 11, '#c06bff')
        thick_line(c, 14, 15, 26, 27, '#e8c060', 2)
        c.line(14, 14, 26, 26, '#fff0a0')
        c.rect(20, 23, 2, 4, '#e8c060'); c.rect(23, 26, 2, 4, '#e8c060')
    elif kind == 'gel':
        c.ell(16, 20, 8, 6, '#5cbf4c'); c.ell(14, 18, 4, 2.5, '#8fe070'); c.rect(12, 16, 2, 2, '#ffffff')
    elif kind == 'iron':
        c.poly([(8, 22), (13, 13), (22, 12), (25, 20), (18, 25)], '#8d8a86'); c.poly([(13, 13), (22, 12), (19, 17)], '#c4c0bc')
        c.px(17, 20, '#a06e3c'); c.px(20, 22, '#7a5030')
    elif kind == 'coal':
        c.poly([(8, 21), (12, 13), (20, 11), (25, 18), (20, 25), (11, 25)], '#2e2830'); c.poly([(12, 13), (20, 11), (17, 16)], '#5a5262')
        c.px(18, 20, '#ff7a30'); c.px(14, 22, '#ffb030')
    elif kind == 'gold':
        c.ell(16, 16, 7, 7, '#a8802a'); c.ell(16, 16, 6, 6, '#e8c060'); c.ell(15, 15, 3, 3, '#fff0a0'); c.rect(15, 12, 2, 8, '#a8802a')
    return c


ARMOR_IDS = ['cloth', 'leather', 'cloak', 'plate', 'shadow', 'shell']
RING_IDS = ['copper', 'wind', 'shade', 'life', 'seal']
MISC_IDS = ['key', 'gel', 'iron', 'coal', 'gold']


def build_items():
    # 손에 든 무기: 64×44 칸에 하나씩, 기준점·길이·시위 정보 기록
    cells, wmeta = [], {}
    icons, order = [], []
    for wid, (kind, d) in WEAPONS.items():
        cv, (ax, ay), length, string = draw_weapon(kind, d)
        im = img_outline(cv.image())
        cells.append(im)
        wmeta[wid] = {'i': len(cells) - 1, 'ax': ax, 'ay': ay, 'len': length, 'kind': kind}
        if string:
            wmeta[wid]['string'] = string
        icv, _, _, _ = draw_weapon(kind, d, short=True)
        raw = icv.image()
        icon = rot45(raw) if kind != 'bow' else rot45(raw)
        icons.append(img_outline(fit_icon(icon, 32)))
        order.append(wid)
    wsheet = Image.new('RGBA', (64 * len(cells), 44), (0, 0, 0, 0))
    for i, im in enumerate(cells):
        wsheet.alpha_composite(im, (i * 64, 0))
    for aid in ARMOR_IDS:
        icons.append(img_outline(armor_icon(aid).image())); order.append(aid)
    for rid in RING_IDS:
        icons.append(img_outline(ring_icon(rid).image())); order.append(rid)
    for mid in MISC_IDS:
        icons.append(img_outline(misc_icon(mid).image())); order.append(mid)
    isheet = Image.new('RGBA', (32 * len(icons), 32), (0, 0, 0, 0))
    for i, im in enumerate(icons):
        isheet.alpha_composite(im, (i * 32, 0))
    # 화살
    ar = Cv(22, 7)
    ar.rect(0, 3, 17, 1, '#c9a070'); ar.poly([(16, 0.5), (22, 3.5), (16, 6.5)], '#d8dce0'); ar.px(18, 3, '#ffffff')
    ar.rect(0, 1, 4, 1, '#f0f0f0'); ar.rect(0, 5, 4, 1, '#f0f0f0'); ar.rect(1, 2, 3, 1, '#d03838'); ar.rect(1, 4, 3, 1, '#d03838')
    arrow = img_outline(ar.image())
    return wsheet, wmeta, isheet, order, arrow


def build_portraits(mon_sheets):
    """HUD 초상화: 새 몬스터 스프라이트의 얼굴 부분을 48×48로 자른다."""
    crops = {'slime': (0, 0, 40, 32), 'goblin': (6, 2, 48, 44), 'boss': (22, 12, 106, 96)}
    out = Image.new('RGBA', (48 * 3, 48), (0, 0, 0, 0))
    for i, k in enumerate(('slime', 'goblin', 'boss')):
        fr = mon_sheets[k].crop(crops[k])
        if fr.width > 48 or fr.height > 48:
            fr = fr.resize((48, round(48 * fr.height / fr.width)), Image.NEAREST)
        out.alpha_composite(fr, (i * 48 + (48 - fr.width) // 2, (48 - fr.height) // 2))
    return out


# ───────── 공용: 시트 저장 · 메타데이터 ─────────
def pack(frames, fw, fh):
    im = Image.new('RGBA', (fw * len(frames), fh), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        im.paste(f.image(), (i * fw, 0))
    return im


def data_uri(im):
    buf = io.BytesIO()
    im.save(buf, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def recolor_preview(im, look):
    """게임과 같은 규칙으로 열쇠 색을 바꿔 미리보기를 만든다."""
    table = {}
    for part, steps in KEY_STEPS.items():
        for k, amt in steps.items():
            src = MA.RGB[k]
            dst = shade(look[part], amt)
            table[src] = tuple(int(dst[i:i + 2], 16) for i in (1, 3, 5))
    out = im.copy()
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b_, a = px[x, y]
            if a and (r, g, b_) in table:
                px[x, y] = table[(r, g, b_)] + (a,)
    return out


def build_hero():
    sheets, meta = {}, {'fw': HW, 'fh': HH, 'ax': HAX, 'ay': HAY, 'poses': list(HERO_POSES.keys()), 'hand': {}, 'bob': {}}
    for g in ('m', 'f'):
        frames = []
        for name in HERO_POSES:
            fr, hand, bob = hero(g, name)
            frames.append(fr)
            meta['hand'][name] = list(hand)
            meta['bob'][name] = bob
        sheets[g] = pack(frames, HW, HH)
    return sheets, meta


def inject(payload):
    """index.html의 WEB_ASSETS 블록을 새 데이터로 바꾼다."""
    html = open(HTML, encoding='utf-8').read()
    new, n = re.subn(r'/\*WEB_ASSETS_BEGIN\*/.*?/\*WEB_ASSETS_END\*/',
                     lambda m: '/*WEB_ASSETS_BEGIN*/' + json.dumps(payload, separators=(',', ':')) + '/*WEB_ASSETS_END*/', html, flags=re.S)
    assert n == 1, 'index.html에 WEB_ASSETS 블록이 없음'
    open(HTML, 'w', encoding='utf-8').write(new)


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(PREVIEW, exist_ok=True)
    hero_sheets, hero_meta = build_hero()
    for g, im in hero_sheets.items():
        im.save(os.path.join(OUT, f'hero_{g}.png'))
    # 미리보기: 기본색 + 다른 조합 두 가지
    looks = [KEY_DEFAULT, {'hair': '#f08ab8', 'skin': '#ffe3cc', 'eye': '#2f62d0', 'outfit': '#6a4aa8'},
             {'hair': '#e8c050', 'skin': '#c4875a', 'eye': '#2e9a58', 'outfit': '#b0403b'}]
    rows = []
    for g in ('m', 'f'):
        for lk in looks:
            rows.append(recolor_preview(hero_sheets[g], lk))
    W = max(r.width for r in rows)
    sheet = Image.new('RGBA', (W, HH * len(rows)), (60, 52, 70, 255))
    for i, r in enumerate(rows):
        sheet.alpha_composite(r, (0, i * HH))
    sheet.resize((sheet.width * 4, sheet.height * 4), Image.NEAREST).save(os.path.join(PREVIEW, 'hero_preview.png'))
    mon_sheets, mon_meta = build_monsters()
    for k, im in mon_sheets.items():
        im.save(os.path.join(OUT, f'{k}.png'))
        big = Image.new('RGBA', im.size, (60, 52, 70, 255)); big.alpha_composite(im)
        big.resize((im.width * 3, im.height * 3), Image.NEAREST).save(os.path.join(PREVIEW, f'{k}_preview.png'))
    wsheet, wmeta, isheet, iorder, arrow = build_items()
    portraits = build_portraits(mon_sheets)
    for name, im in (('weapons', wsheet), ('icons', isheet), ('arrow', arrow), ('portraits', portraits)):
        im.save(os.path.join(OUT, f'{name}.png'))
        big = Image.new('RGBA', im.size, (60, 52, 70, 255)); big.alpha_composite(im)
        big.resize((im.width * 3, im.height * 3), Image.NEAREST).save(os.path.join(PREVIEW, f'{name}_preview.png'))
    meta = {'hero': hero_meta, **mon_meta, 'weapons': {'cw': 64, 'ch': 44, 'items': wmeta}, 'icons': iorder}
    json.dump(meta, open(os.path.join(OUT, 'meta.json'), 'w'))
    inject({'hero_m': data_uri(hero_sheets['m']), 'hero_f': data_uri(hero_sheets['f']),
            **{k: data_uri(im) for k, im in mon_sheets.items()},
            'weapons': data_uri(wsheet), 'icons': data_uri(isheet), 'arrow': data_uri(arrow), 'portraits': data_uri(portraits), 'meta': meta})
    print('완료:', OUT)


if __name__ == '__main__':
    main()
