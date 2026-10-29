"""《잊혀진 대장간》 웹 버전 지형·소품 도트 (3단계).

지역별 지면 타일, 떠 있는 발판 조각, 마을·숲·동굴 소품, 대장간 건물, 동굴 입구 바위를 그린다.
make_web_assets.py가 불러서 시트로 묶고 index.html에 주입한다.
좌표 단위는 게임 월드 픽셀(화면에서는 2배로 보임). 빛은 왼쪽 위에서 온다.
"""
import math

from PIL import Image

import make_assets as MA

Cv = MA.Cv
h = MA.h


def sh(hexc, amt):
    """#색 밝기 조절 (채널마다 amt 더하기)."""
    v = [max(0, min(255, int(hexc[i:i + 2], 16) + amt)) for i in (1, 3, 5)]
    return '#%02x%02x%02x' % tuple(v)


def outline(c, dark=0.32):
    """캔버스를 이미지로 바꾸며 바깥 테두리를 이웃 색의 어두운 버전으로 두른다."""
    im = c.image()
    px = im.load()
    W, H = im.size
    add = {}
    for y in range(H):
        for x in range(W):
            if px[x, y][3]:
                continue
            for dx, dy in ((0, 1), (1, 0), (-1, 0), (0, -1)):
                xx, yy = x + dx, y + dy
                if 0 <= xx < W and 0 <= yy < H and px[xx, yy][3]:
                    r, g, b, _ = px[xx, yy]
                    k = dark * (0.75 if dy == -1 else 1.0)
                    add[(x, y)] = (int(r * k) + 8, int(g * k) + 6, int(b * k) + 12, 255)
                    break
    for q, col in add.items():
        px[q] = col
    return im


def shaded_ell(c, cx, cy, rx, ry, base, light=22, dark=-30, spec=True):
    """둥근 덩어리: 아래 그림자 → 본색 → 왼쪽 위 하이라이트."""
    c.ell(cx, cy, rx, ry, sh(base, dark))
    c.ell(cx - rx * 0.12, cy - ry * 0.14, rx * 0.86, ry * 0.8, base)
    c.ell(cx - rx * 0.35, cy - ry * 0.38, rx * 0.42, ry * 0.32, sh(base, light))
    if spec and rx > 3:
        c.px(cx - rx * 0.45, cy - ry * 0.5, sh(base, light + 30))


# ───────────────────────── 지면 타일 (64×66, 가로로 이음새 없이 반복) ─────────────────────────
GT_W, GT_H = 64, 66
SURF = 4  # 타일 안에서 지표면 y (게임은 GROUND-4에 그림)

ZONE_GROUND = {
    #           풀/표면     풀 밝게     흙          흙 어둡게   돌          깊은 흙     풀잎?
    'village': ('#6f8a4c', '#93ad62', '#6a4a34', '#4e3526', '#8a7a6c', '#33241a', True, 'cobble'),
    'grass':   ('#4fa04a', '#86d064', '#7a5236', '#5a3a26', '#a08a72', '#2e1d13', True, 'stones'),
    'forest':  ('#2f7a3e', '#4fa258', '#4a3424', '#34241a', '#6c6458', '#1a120c', True, 'roots'),
    'cave':    ('#4a3e5c', '#6e5e88', '#3a3048', '#2a2236', '#5a4e70', '#18141e', False, 'crystal'),
}


def ground_tile(zone):
    top, topL, dirt, dirtD, stone, deep, grass, kind = ZONE_GROUND[zone]
    c = Cv(GT_W, GT_H)
    W = GT_W
    # 흙: 위에서 아래로 세 겹 띠 + 결
    for y in range(SURF, GT_H):
        t = (y - SURF) / (GT_H - SURF)
        col = dirt if t < 0.35 else (dirtD if t < 0.72 else sh(deep, 8))
        for x in range(W):
            n = h(x, y, 7)
            cc = col
            if n > 0.93:
                cc = sh(col, 12)
            elif n < 0.06:
                cc = sh(col, -12)
            c.px(x, y, cc)
    # 지층 경계선 (물결)
    for band, col in ((0.35, dirtD), (0.72, sh(deep, 8))):
        y0 = SURF + band * (GT_H - SURF)
        for x in range(W):
            yy = y0 + math.sin(x / W * math.pi * 4) * 1.5
            c.px(x, yy, sh(col, -10))
    # 박힌 돌 / 뿌리 / 수정
    rng = [(h(i, 1, 31), h(i, 2, 31), h(i, 3, 31)) for i in range(14)]
    for i, (a, b, s) in enumerate(rng):
        x = a * W
        y = SURF + 12 + b * (GT_H - SURF - 18)
        rx, ry = 2.5 + s * 3.5, 1.8 + s * 2
        for off in (0, -W, W):  # 가로로 감싸기
            if kind == 'roots' and i % 3 == 0:
                for k in range(10):
                    c.px(x + off + k * 1.2, y - 6 + math.sin(k * 0.8 + i) * 2, '#5a3a22')
                    c.px(x + off + k * 1.2, y - 5 + math.sin(k * 0.8 + i) * 2, '#3a2416')
            elif kind == 'crystal' and i % 4 == 0:
                c.poly([(x + off - 2, y + 2), (x + off, y - 4), (x + off + 2, y + 2)], '#7a6ad8')
                c.px(x + off, y - 2, '#c8b8ff')
            else:
                shaded_ell(c, x + off, y, rx, ry, stone if b < 0.5 else sh(stone, -16), 18, -26)
    # 지표면
    if kind == 'cobble':
        # 마을: 이끼 낀 돌길 표면
        for x in range(0, W, 8):
            off = 4 if (x // 8) % 2 else 0
            c.rect(x, SURF, 8, 5, '#7c7266')
            c.rect(x, SURF, 8, 1, '#a49888')
            c.rect(x + 7, SURF, 1, 5, '#4e463e')
            c.rect(x, SURF + 4, 8, 1, '#4e463e')
            c.rect((x + off) % W, SURF + 5, 8, 4, '#6a6056')
            c.rect((x + off + 7) % W, SURF + 5, 1, 4, '#443c34')
        for x in range(W):
            if h(x, 0, 9) > 0.55:
                c.px(x, SURF - 1, top)
                c.px(x, SURF, topL if h(x, 1, 9) > 0.5 else top)
            if h(x, 3, 9) > 0.8:
                c.px(x, SURF + 1, top)
        c.rect(0, SURF + 9, W, 1, sh(dirt, -24))
    elif kind == 'crystal':
        c.rect(0, SURF, W, 5, top)
        c.rect(0, SURF, W, 1, topL)
        for x in range(W):
            if h(x, 5, 3) > 0.6:
                c.px(x, SURF + 1, sh(top, 14))
            d = 1 + int(h(x, 6, 3) * 3)
            c.rect(x, SURF + 5, 1, d, sh(top, -18))
    else:
        # 메이플풍 둥근 풀 턱: 두툼한 잔디 띠 + 아래로 늘어진 술
        c.rect(0, SURF, W, 6, top)
        c.rect(0, SURF, W, 2, topL)
        for x in range(W):
            if h(x, 7, 5) > 0.7:
                c.px(x, SURF + 2, topL)
            if h(x, 8, 5) > 0.75:
                c.px(x, SURF + 4, sh(top, -18))
        for x in range(0, W, 4):
            ln = 2 + int(h(x, 9, 5) * 4)
            for k in range(ln):
                c.px(x + 1, SURF + 6 + k, sh(top, -14 - k * 4))
                c.px(x + 2, SURF + 6 + k - 1, sh(top, -6 - k * 4))
            c.px(x, SURF + 6, sh(top, -22))
        if grass:
            for x in range(W):
                hh = int(h(x, 10, 5) * 4)
                for k in range(hh):
                    c.px(x, SURF - 1 - k, topL if (x + k) % 3 else top)
    return c.image()


# ───────────────────────── 떠 있는 발판 (높이 16, 왼끝·가운데·오른끝 8/16/8) ─────────────────────────
PL_H = 16


def plat_piece(kind, part):
    w = 16 if part == 'm' else 8
    c = Cv(w, PL_H)
    if kind == 'wood':
        plank, plankL, plankD = '#8a5e3c', '#b07e52', '#5a3a22'
        c.rect(0, 3, w, 8, plank)
        c.rect(0, 3, w, 1, plankL)
        c.rect(0, 10, w, 1, plankD)
        for x in range(w):
            if h(x, 2, 41 + (part == 'm')) > 0.82:
                c.px(x, 6, sh(plank, -16))
        if part == 'm':
            c.rect(7, 4, 1, 6, plankD)
            c.px(3, 5, '#d8c090')
            c.px(12, 5, '#d8c090')
        # 잔디 덮개
        c.rect(0, 1, w, 3, '#5aa84e')
        c.rect(0, 1, w, 1, '#8ad068')
        for x in range(w):
            if h(x, 3, 43) > 0.45:
                c.px(x, 4, '#3e8040')
            if h(x, 4, 43) > 0.6:
                c.px(x, 0, '#8ad068')
        if part == 'l':
            c.px(0, 1, None)
            c.px(0, 10, None)
        if part == 'r':
            c.px(7, 1, None)
            c.px(7, 10, None)
        # 아래로 늘어진 풀·뿌리
        for x in range(w):
            if h(x, 5, 47 + ord(part)) > 0.7:
                c.rect(x, 11, 1, 1 + int(h(x, 6, 47) * 3), '#3e8040')
    else:  # stone (동굴)
        base, baseL, baseD = '#4e4262', '#6e5e88', '#2e2440'
        c.rect(0, 2, w, 9, base)
        c.rect(0, 2, w, 2, baseL)
        c.rect(0, 10, w, 1, baseD)
        for x in range(w):
            if h(x, 7, 51) > 0.7:
                c.px(x, 6, sh(base, -14))
        if part == 'm':
            c.rect(9, 4, 1, 6, baseD)
        for x in range(1, w, 4):
            ln = 2 + int(h(x, 8, 52 + ord(part)) * 4)
            c.poly([(x - 1.5, 11), (x + 0.5, 11 + ln), (x + 2.5, 11)], baseD)
        if part == 'l':
            c.px(0, 2, None)
            c.px(0, 10, None)
        if part == 'r':
            c.px(w - 1, 2, None)
            c.px(w - 1, 10, None)
    return c


def plat_post():
    """나무 발판 기둥 (세로로 반복되는 6×8)."""
    c = Cv(6, 8)
    c.rect(1, 0, 4, 8, '#5a3a22')
    c.rect(1, 0, 1, 8, '#7a5232')
    c.rect(4, 0, 1, 8, '#3a2416')
    c.px(2, 3, '#3a2416')
    return outline(c).crop((0, 0, 6, 8))


# ───────────────────────── 소품 ─────────────────────────
# 각 소품: (캔버스, 기준점 x — 게임의 pr.x가 놓이는 캔버스 안 x)  바닥은 캔버스 맨 아래 = GROUND
def prop_lamp():
    c = Cv(16, 52)
    c.rect(6, 10, 3, 42, '#3a3036')
    c.rect(6, 10, 1, 42, '#5a4e54')
    c.rect(4, 48, 7, 4, '#2a2026')
    c.rect(2, 7, 12, 3, '#3a3036')
    c.rect(2, 7, 12, 1, '#5a4e54')
    c.rect(3, 10, 7, 10, '#2a2026')  # 등 틀
    c.rect(4, 11, 5, 8, '#ffcf70')
    c.rect(5, 12, 2, 5, '#fff2c0')
    c.rect(3, 9, 7, 1, '#4a3e44')
    c.rect(6, 4, 1, 3, '#3a3036')
    return outline(c), 7


def prop_barrel():
    c = Cv(18, 20)
    c.ell(9, 10, 8, 10, '#6a4428')
    c.rect(1, 2, 16, 16, '#7a5232')
    c.rect(3, 2, 3, 16, '#9a6a40')
    c.rect(13, 2, 3, 16, '#5a3a22')
    for y in (4, 14):
        c.rect(1, y, 16, 2, '#4a4a52')
        c.rect(1, y, 16, 1, '#7a7a84')
    c.ell(9, 2, 8, 2, '#5a3a22')
    c.ell(9, 2, 6, 1.4, '#8a5e3c')
    return outline(c), 2


def prop_cart():
    c = Cv(42, 30)
    c.rect(2, 8, 32, 10, '#7a5232')
    c.rect(2, 8, 32, 2, '#9a6a40')
    for x in range(2, 34, 8):
        c.rect(x, 10, 1, 8, '#5a3a22')
    c.rect(34, 2, 3, 16, '#5a3a22')
    c.rect(34, 2, 1, 16, '#7a5232')
    c.line(34, 14, 41, 22, '#5a3a22')
    # 바퀴 (하나는 부서짐)
    for cx, cy, r, broken in ((10, 22, 7, False), (28, 25, 5, True)):
        for a in range(0, 360, 6):
            if broken and 200 < a < 320:
                continue
            ra = math.radians(a)
            c.px(cx + math.cos(ra) * r, cy + math.sin(ra) * r, '#3a2416')
            c.px(cx + math.cos(ra) * (r - 1), cy + math.sin(ra) * (r - 1), '#6a4428')
        for a in range(0, 360, 60):
            if broken and 200 < a < 320:
                continue
            ra = math.radians(a)
            c.line(cx, cy, cx + math.cos(ra) * (r - 1), cy + math.sin(ra) * (r - 1), '#5a3a22')
        c.rect(cx - 1, cy - 1, 2, 2, '#4a4a52')
    # 짐: 자루 + 상자
    shaded_ell(c, 12, 6, 6, 4, '#c8a878', 18, -30)
    c.rect(20, 2, 9, 7, '#8a5e3c')
    c.rect(20, 2, 9, 1, '#b07e52')
    c.rect(24, 2, 1, 7, '#5a3a22')
    return outline(c), 0


def prop_well():
    c = Cv(36, 52)
    # 지붕
    c.poly([(0, 18), (18, 4), (36, 18)], '#4a3648')
    c.poly([(3, 18), (18, 6), (18, 18)], '#5e4660')
    for r in range(4):
        c.rect(3 + r * 3, 16 - r * 3, 30 - r * 6, 1, '#34263a')
    c.rect(0, 17, 36, 2, '#2e2236')
    # 기둥 + 도르래
    c.rect(5, 19, 3, 16, '#6a4428')
    c.rect(28, 19, 3, 16, '#6a4428')
    c.rect(5, 19, 1, 16, '#8a5e3c')
    c.rect(7, 23, 22, 2, '#5a3a22')
    c.rect(17, 25, 1, 9, '#c8b890')
    c.rect(15, 32, 5, 4, '#7a5232')
    # 돌 우물
    c.rect(2, 35, 32, 17, '#6a6070')
    for y in range(35, 52, 5):
        off = 4 if (y // 5) % 2 else 0
        for x in range(2 + off, 34, 9):
            c.rect(x, y, 8, 4, '#857a8a' if h(x, y, 61) > 0.4 else '#766b7c')
            c.rect(x, y, 8, 1, '#a096a6')
    c.rect(2, 35, 32, 2, '#a096a6')
    c.rect(4, 36, 28, 1, '#2a2430')
    return outline(c), 0


def prop_sign():
    c = Cv(48, 34)
    c.rect(21, 12, 4, 22, '#6a4428')
    c.rect(21, 12, 1, 22, '#8a5e3c')
    c.poly([(0, 7), (4, 2), (42, 2), (47, 8), (42, 15), (4, 15)], '#8a5e3c')
    c.rect(4, 2, 38, 2, '#b07e52')
    c.rect(4, 14, 38, 1, '#5a3a22')
    for x in (10, 24, 36):
        c.rect(x, 4, 1, 10, '#7a5232')
    c.px(3, 8, '#d8c090')
    c.px(43, 8, '#d8c090')
    return outline(c), 22


def prop_rock():
    c = Cv(32, 16)
    c.ell(16, 13, 15, 11, '#5e5868')
    c.ell(13, 11, 11, 8, '#76707e')
    c.ell(10, 8, 6, 4, '#948ea0')
    c.px(8, 6, '#b8b2c4')
    c.ell(24, 13, 6, 4, '#4a4454')
    for x in range(4, 28):
        if h(x, 0, 71) > 0.6:
            c.px(x, 4 + abs(16 - x) * 0.35 + 1, '#5aa84e')
    c.rect(0, 15, 32, 1, None)
    im = outline(c)
    return im.crop((0, 0, 32, 16)), 16


def prop_flowers():
    c = Cv(46, 14)
    cols = ['#ff9ec7', '#ffe066', '#ffffff', '#b09aff', '#ff8a6a']
    for i in range(7):
        x = 3 + i * 6 + int(h(i, 0, 81) * 3)
        stem = 5 + int(h(i, 1, 81) * 4)
        c.rect(x, 14 - stem, 1, stem, '#3a8a40')
        c.px(x + 1, 14 - stem // 2, '#5aa84e')
        fc = cols[i % 5]
        y = 14 - stem - 2
        c.rect(x - 1, y, 3, 3, fc)
        c.px(x, y - 1, fc)
        c.px(x, y + 1, '#ffd040' if fc != '#ffe066' else '#e08a20')
    for x in range(0, 46, 3):
        c.rect(x, 12, 3, 2, '#4a9a48')
        c.px(x + 1, 11, '#6ac05a')
    return outline(c, 0.45), 2


def prop_stump():
    c = Cv(24, 18)
    c.rect(3, 5, 18, 13, '#6a4428')
    c.rect(3, 5, 4, 13, '#8a5e3c')
    c.rect(17, 5, 4, 13, '#4a301c')
    c.poly([(0, 18), (3, 12), (5, 18)], '#6a4428')
    c.poly([(24, 18), (21, 12), (19, 18)], '#4a301c')
    c.ell(12, 5, 9, 3, '#d8b080')
    c.ell(12, 5, 6, 2, '#b08858')
    c.ell(12, 5, 3, 1, '#d8b080')
    c.rect(5, 9, 4, 3, '#5aa84e')
    c.px(6, 8, '#8ad068')
    return outline(c), 3


def prop_log():
    c = Cv(54, 16)
    c.rect(2, 3, 46, 12, '#4e3420')
    c.rect(2, 3, 46, 3, '#6a4a2c')
    c.rect(2, 13, 46, 2, '#34200f')
    for x in range(4, 46, 7):
        c.rect(x, 7, 4, 1, '#3a2614')
    c.ell(49, 9, 4, 6, '#b8946a')
    c.ell(49, 9, 2.5, 4, '#8a6a48')
    c.ell(49, 9, 1, 1.5, '#b8946a')
    c.rect(10, 1, 14, 3, '#3e8a48')
    c.rect(12, 0, 8, 1, '#5aa858')
    c.rect(30, 2, 6, 2, '#3e8a48')
    shaded_ell(c, 20, 3, 2, 1.5, '#e0d0b0', 10, -20, False)
    return outline(c), 2


def prop_shroom():
    c = Cv(28, 20)
    for i, (x, hgt, col) in enumerate(((5, 8, '#4ad8b0'), (13, 13, '#7fe8ff'), (21, 6, '#4ad8b0'))):
        c.rect(x - 1, 20 - hgt, 3, hgt, '#e8e0d0')
        c.rect(x - 1, 20 - hgt, 1, hgt, '#ffffff')
        r = 4 + (i == 1) * 2
        top = 20 - hgt
        c.ell(x, top, r, r * 0.7, sh(col, -50))
        c.ell(x - 0.5, top - 0.6, r - 0.6, r * 0.6, col)
        c.ell(x - r * 0.35, top - r * 0.3, r * 0.35, r * 0.2, sh(col, 60))
        c.rect(x - r + 1, top, r * 2 - 1, 1, sh(col, -70))
        c.px(x + 1, top - 2, '#ffffff')
    return outline(c), 2


def prop_torch():
    c = Cv(10, 42)
    c.rect(4, 8, 3, 34, '#4a3428')
    c.rect(4, 8, 1, 34, '#6a4e3e')
    c.rect(2, 4, 7, 4, '#5a5a66')
    c.rect(2, 4, 7, 1, '#8a8a96')
    c.rect(3, 2, 5, 2, '#3a2420')
    return outline(c), 4


def prop_crystal():
    c = Cv(24, 26)
    for x, hgt, w, col in ((5, 14, 3, '#6a8aff'), (12, 24, 4, '#a070ff'), (19, 11, 3, '#6a8aff'), (8, 8, 2, '#b8a0ff')):
        top = 26 - hgt
        c.poly([(x - w, 26), (x - w, top + w), (x, top), (x + w, top + w), (x + w, 26)], sh(col, -40))
        c.poly([(x - w, 26), (x - w, top + w), (x, top), (x, 26)], col)
        c.rect(x - w + 1, top + w + 1, 1, hgt - w - 4, sh(col, 70))
    return outline(c, 0.4), 12


def prop_bones():
    c = Cv(28, 12)
    c.rect(1, 9, 14, 2, '#e0d8c8')
    c.rect(0, 8, 2, 4, '#e0d8c8')
    c.rect(14, 8, 2, 4, '#e0d8c8')
    c.rect(6, 4, 2, 8, '#c8c0b0')
    c.rect(5, 3, 4, 2, '#c8c0b0')
    shaded_ell(c, 21, 7, 5, 4.5, '#e8e0d0', 12, -40, False)
    c.rect(18, 6, 2, 2, '#1a1424')
    c.rect(22, 6, 2, 2, '#1a1424')
    c.rect(19, 10, 4, 1, '#8a8478')
    return outline(c), 0


def prop_pillar():
    c = Cv(28, 96)
    c.rect(5, 6, 18, 84, '#3e3256')
    c.rect(5, 6, 5, 84, '#54466e')
    c.rect(19, 6, 4, 84, '#2a2240')
    for y in range(10, 88, 12):
        c.rect(5, y, 18, 1, '#2a2240')
    c.rect(1, 0, 26, 7, '#34284a')
    c.rect(1, 0, 26, 2, '#5a4c74')
    c.rect(1, 89, 26, 7, '#34284a')
    c.rect(1, 89, 26, 2, '#5a4c74')
    c.poly([(23, 34), (12, 44), (23, 52)], None)
    c.poly([(14, 60), (18, 66), (16, 72)], '#2a2240')
    c.rect(7, 20, 3, 4, '#6a5ad8')  # 희미한 룬
    c.rect(7, 28, 3, 1, '#6a5ad8')
    return outline(c), 5


PROPS = {
    'lamp': prop_lamp, 'barrel': prop_barrel, 'cart': prop_cart, 'well': prop_well, 'sign': prop_sign,
    'rock': prop_rock, 'flowers': prop_flowers, 'stump': prop_stump, 'log': prop_log, 'shroom': prop_shroom,
    'torch': prop_torch, 'crystal': prop_crystal, 'bones': prop_bones, 'pillar': prop_pillar,
}


# ───────────────────────── 대장간 (160×156) ─────────────────────────
def forge():
    W, H = 160, 156
    c = Cv(W, H)
    bx, by, bw = 18, 76, 124  # 벽 왼쪽, 벽 위, 벽 너비 / 바닥 = H
    # 굴뚝 (벽돌, 연기 구멍)
    c.rect(112, 16, 22, 70, '#4a3634')
    for y in range(16, 86, 6):
        off = 5 if (y // 6) % 2 else 0
        for x in range(112 + off - 5, 134, 10):
            c.rect(max(112, x), y, min(9, 134 - max(112, x)), 5, '#6a4a44' if h(x, y, 91) > 0.4 else '#5a3e3a')
            c.rect(max(112, x), y, min(9, 134 - max(112, x)), 1, '#7e5a52')
    c.rect(108, 10, 30, 7, '#34262a')
    c.rect(108, 10, 30, 2, '#5a4448')
    c.rect(112, 16, 2, 70, '#7e5a52')
    # 돌벽
    c.rect(bx, by, bw, H - by, '#4a3c36')
    for y in range(by, H, 8):
        off = 7 if ((y - by) // 8) % 2 else 0
        for x in range(bx - 7 + off, bx + bw, 14):
            x0 = max(bx, x)
            ww = min(13, bx + bw - x0, x + 13 - x0)
            if ww <= 0:
                continue
            col = '#64524a' if h(x, y, 92) > 0.5 else '#5a4842'
            c.rect(x0, y, ww, 7, col)
            c.rect(x0, y, ww, 1, '#7a665c')
            if h(x, y, 93) > 0.8:
                c.px(x0 + 3, y + 3, '#3a2e2a')
    # 이끼
    for x in range(bx, bx + bw):
        if h(x, 0, 94) > 0.55:
            c.rect(x, H - 2 - int(h(x, 1, 94) * 6), 1, 2 + int(h(x, 1, 94) * 6), '#4a7a3e')
    # 들보
    c.rect(bx - 5, by - 5, bw + 10, 7, '#6a4428')
    c.rect(bx - 5, by - 5, bw + 10, 2, '#9a6a40')
    c.rect(bx, by, 6, H - by, '#5a3a22')
    c.rect(bx, by, 2, H - by, '#7a5232')
    c.rect(bx + bw - 6, by, 6, H - by, '#5a3a22')
    # 지붕 (기와)
    c.poly([(bx - 16, by - 3), (bx + 54, by - 58), (bx + bw + 16, by - 3)], '#3e2c40')
    for r in range(7):
        y = by - 10 - r * 7
        x0 = bx - 12 + r * 9.5
        x1 = bx + bw + 12 - r * 9.5
        x = x0
        i = 0
        while x < x1 - 4:
            if h(int(x), r, 95) > 0.04:
                col = '#5e4660' if (i + r) % 2 else '#6a5070'
                c.rect(x, y, 9, 6, col)
                c.rect(x, y, 9, 1, '#866c8c')
                c.rect(x, y + 5, 9, 1, '#2e2032')
            x += 9
            i += 1
    # 지붕 구멍 (깨짐)
    c.poly([(bx + 74, by - 34), (bx + 96, by - 21), (bx + 80, by - 12)], None)
    c.line(bx + 74, by - 34, bx + 96, by - 21, '#2a1a12')
    c.line(bx + 75, by - 33, bx + 82, by - 14, '#5a3a22')
    c.rect(bx - 16, by - 4, bw + 32, 2, '#2e2032')
    # 문 (아치)
    dx, dw = bx + 46, 34
    c.rect(dx - 3, by + 26, dw + 6, H - by - 26, '#3a2e2a')
    c.ell(dx + dw / 2, by + 28, dw / 2 + 3, 10, '#3a2e2a')
    c.rect(dx, by + 30, dw, H - by - 30, '#5a3820')
    c.ell(dx + dw / 2, by + 30, dw / 2, 8, '#5a3820')
    for x in range(dx + 5, dx + dw, 6):
        c.rect(x, by + 24, 1, H - by - 24, '#3e2614')
    c.rect(dx, by + 26, 2, H - by - 26, '#7a5232')
    for y in (by + 40, by + 64):
        c.rect(dx, y, dw, 3, '#6a6a76')
        c.rect(dx, y, dw, 1, '#9a9aa6')
    # 간판 (모루 + 망치)
    c.rect(bx + 10, by + 10, 30, 18, '#7a5232')
    c.rect(bx + 10, by + 10, 30, 2, '#a07048')
    c.rect(bx + 10, by + 27, 30, 1, '#4a301c')
    c.rect(bx + 18, by + 18, 14, 4, '#2a1c14')
    c.rect(bx + 21, by + 22, 8, 3, '#2a1c14')
    c.rect(bx + 15, by + 19, 3, 2, '#2a1c14')
    c.line(bx + 30, by + 13, bx + 36, by + 19, '#2a1c14')
    c.rect(bx + 28, by + 12, 4, 3, '#2a1c14')
    c.rect(bx + 14, by + 4, 1, 6, '#3a3036')
    c.rect(bx + 36, by + 4, 1, 6, '#3a3036')
    # 창문 (덧문 하나 떨어짐)
    wx, wy = bx + 90, by + 24
    c.rect(wx - 2, wy - 2, 22, 20, '#3a2e2a')
    c.rect(wx, wy, 18, 16, '#1e1418')
    c.rect(wx + 8, wy, 2, 16, '#5a3a22')
    c.rect(wx, wy + 7, 18, 2, '#5a3a22')
    c.rect(wx - 8, wy, 6, 16, '#6a4428')
    c.rect(wx - 8, wy, 1, 16, '#8a5e3c')
    c.rect(wx - 3, wy + 18, 24, 3, '#6a5a50')
    c.rect(wx - 3, wy + 18, 24, 1, '#8a7a6c')
    return outline(c)


# ───────────────────────── 동굴 입구 (200×300, 바닥=GROUND) ─────────────────────────
CAVE_W, CAVE_H, CAVE_OX = 200, 300, 80  # CAVE_OX: 캔버스 안에서 CAVE_X가 놓이는 x


def cave_entrance():
    c = Cv(CAVE_W, CAVE_H)
    ox = CAVE_OX
    rock, rockL, rockD = '#2e2440', '#44385a', '#1d1626'
    # 바깥 바위 실루엣: 왼쪽 경사 + 위로 솟은 덩어리 (오른쪽 끝은 동굴 천장과 이어짐)
    outer = [(ox - 76, 300), (ox - 66, 230), (ox - 54, 150), (ox - 30, 96), (ox - 4, 60), (ox + 30, 34),
             (ox + 60, 10), (ox + 70, 0), (CAVE_W, 0), (CAVE_W, 300)]
    c.poly(outer, rock)
    # 입구 구멍 (어두운 안쪽)
    inner = [(ox - 30, 300), (ox - 26, 210), (ox - 10, 150), (ox + 20, 110), (ox + 60, 70), (ox + 90, 48), (CAVE_W, 40), (CAVE_W, 300)]
    c.poly(inner, None)
    # 안쪽 그늘 띠 (입구 두께감)
    for (x0, y0), (x1, y1) in zip(inner[:-2], inner[1:-1]):
        n = int(max(abs(x1 - x0), abs(y1 - y0)))
        for k in range(n + 1):
            x, y = x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n
            for d in range(1, 7):
                c.px(x + d * 0.7, y + d * 0.7, '#140f1c' if d > 3 else '#1d1626')
    # 바위 결: 덩어리 하이라이트
    for i in range(26):
        x = ox - 60 + h(i, 0, 101) * 150
        y = 20 + h(i, 1, 101) * 270
        if c.get(round(x), round(y)) != rock:
            continue
        rx, ry = 6 + h(i, 2, 101) * 10, 4 + h(i, 3, 101) * 6
        for yy in range(int(y - ry), int(y + ry) + 1):
            for xx in range(int(x - rx), int(x + rx) + 1):
                if ((xx + 0.5 - x) / rx) ** 2 + ((yy + 0.5 - y) / ry) ** 2 <= 1 and c.get(xx, yy) == rock:
                    up = ((xx + 0.5 - x + rx * 0.3) / rx) ** 2 + ((yy + 0.5 - y + ry * 0.4) / ry) ** 2 <= 0.45
                    c.px(xx, yy, rockL if up else (rockD if yy > y + ry * 0.55 else '#382c4e'))
    for i in range(14):
        y = 30 + i * 19 + h(i, 0, 102) * 8
        for x in range(0, CAVE_W):
            yy = y + math.sin(x / 13 + i) * 2 + (x - ox) * 0.25
            if c.get(x, round(yy)) == rock:
                c.px(x, yy, rockD)
    # 입구 테두리 밝은 선
    for (x0, y0), (x1, y1) in zip(inner[:-2], inner[1:-1]):
        n = int(max(abs(x1 - x0), abs(y1 - y0)))
        for k in range(n + 1):
            x, y = x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n
            c.px(x - 1, y - 1, rockL)
            c.px(x - 2, y - 1, '#54486c')
    # 이끼 + 늘어진 덩굴
    for x in range(ox - 70, ox + 70):
        for y in range(0, 300):
            if c.get(x, y) == rock or c.get(x, y) == rockL:
                if c.get(x - 1, y - 1) is None and c.get(x, y - 1) is None:
                    if h(x, y, 103) > 0.35:
                        c.px(x, y, '#3e6a48')
                        c.px(x, y + 1, '#2e5038')
                break
    for i in range(6):
        vx = ox - 20 + i * 18 + int(h(i, 0, 104) * 8)
        y0 = 0
        while y0 < 299 and c.get(vx, y0) is None:
            y0 += 1
        while y0 < 299 and c.get(vx, y0) is not None:
            y0 += 1
        ln = 24 + int(h(i, 1, 104) * 40)
        for k in range(ln):
            c.px(vx + math.sin(k / 6 + i) * 1.5, y0 + k, '#2e5a38')
            if k % 6 == 3:
                c.px(vx + math.sin(k / 6 + i) * 1.5 + 1, y0 + k, '#4a8a50')
    # 기둥 수정 몇 개
    for x, y in ((ox - 46, 190), (ox - 16, 120)):
        c.poly([(x - 2, y + 6), (x, y - 6), (x + 2, y + 6)], '#7a6ad8')
        c.px(x, y - 2, '#c8b8ff')
    return outline(c, 0.5)


# ───────────────────────── 시트 만들기 ─────────────────────────
def build_world():
    sheets, meta = {}, {}
    zones = list(ZONE_GROUND.keys())
    g = Image.new('RGBA', (GT_W * len(zones), GT_H), (0, 0, 0, 0))
    for i, z in enumerate(zones):
        g.paste(ground_tile(z), (i * GT_W, 0))
    sheets['ground'] = g
    meta['ground'] = {'w': GT_W, 'h': GT_H, 'zones': zones}

    pl = Image.new('RGBA', (32 * 2 + 6, PL_H), (0, 0, 0, 0))
    x = 0
    pmeta = {}
    for kind in ('wood', 'stone'):
        for part in ('l', 'm', 'r'):
            im = plat_piece(kind, part).image()
            pl.paste(im, (x, 0))
            pmeta[kind + part] = [x, im.width]
            x += im.width
    pl.paste(plat_post(), (x, 0))
    pmeta['post'] = [x, 6]
    sheets['plats'] = pl
    meta['plats'] = {'h': PL_H, 'parts': pmeta}

    ims = {k: f() for k, f in PROPS.items()}
    W = sum(im.width for im, _ in ims.values())
    H = max(im.height for im, _ in ims.values())
    ps = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    x = 0
    prm = {}
    for k, (im, ax) in ims.items():
        ps.paste(im, (x, 0))
        prm[k] = [x, im.width, im.height, ax]
        x += im.width
    sheets['props'] = ps
    meta['props'] = prm

    sheets['forge'] = forge()
    sheets['cave'] = cave_entrance()
    meta['cave'] = {'ox': CAVE_OX}
    return sheets, meta
