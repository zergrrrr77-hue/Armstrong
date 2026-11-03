"""에르덴 시작(로그인) 화면 배경 그림: 연기 낀 하늘 · 흐린 달 · 불타는 성채 · 앞쪽 창병 실루엣.
휴대폰용 세로 그림과 PC용 가로 그림을 따로 그린다(같은 구도를 화면 모양에 맞게 배치).
- lineage-assets/ui/title_bg_portrait.jpg (1080×1920)
- lineage-assets/ui/title_bg_landscape.jpg (1920×1080)
실행: python3 forgotten-forge/tools/lineage/title_art.py
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'lineage-assets', 'ui')
SS = 2   # 도형은 2배 크기로 그린 뒤 줄여서 가장자리를 부드럽게


def noise(w, h, cell, rng):
    """부드러운 얼룩 무늬(값 노이즈): 작은 무작위 격자를 크게 늘림."""
    g = rng.random((max(2, h // cell + 2), max(2, w // cell + 2))).astype(np.float32)
    im = Image.fromarray((g * 255).astype(np.uint8)).resize((w + cell * 2, h + cell * 2), Image.BICUBIC)
    ox, oy = rng.integers(0, cell), rng.integers(0, cell)
    return np.asarray(im, np.float32)[oy:oy + h, ox:ox + w] / 255.0


def fbm(w, h, cell, rng, oct=5):
    a, tot, out = 1.0, 0.0, np.zeros((h, w), np.float32)
    for _ in range(oct):
        out += noise(w, h, max(2, cell), rng) * a
        tot += a
        a *= 0.5
        cell //= 2
    return out / tot


def lerp(a, b, t):
    return a + (b - a) * t[..., None]


def paint(W, H, portrait, seed=7, army=False):
    """army=False: 앞쪽 창병 실루엣 없이(움직이는 전투는 게임 화면에서 스프라이트로 그림)."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v, u = yy / H, xx / W
    # 성채 위치(화면 비율): 세로 화면은 위쪽 가운데, 가로 화면은 가운데
    cx, horizon = (0.5, 0.46) if portrait else (0.5, 0.60)
    # ── 하늘: 위는 탁한 청록·올리브, 지평선은 불빛 주황 ──
    top, mid, low = np.array([22, 28, 30]), np.array([66, 70, 58]), np.array([150, 104, 60])
    t = np.clip(v / horizon, 0, 1)
    sky = np.where((t < 0.6)[..., None], lerp(top, mid, t / 0.6), lerp(mid, low, (t - 0.6) / 0.4))
    cl = fbm(W, H, 260, rng)
    cl2 = fbm(W, H, 120, rng)
    smoke = np.clip((cl * 0.7 + cl2 * 0.3 - 0.42) * 2.4, 0, 1)
    sky = lerp(sky, np.array([34, 36, 32]), smoke * 0.65)
    sky = lerp(sky, np.array([120, 120, 100]), np.clip((cl2 - 0.62) * 3, 0, 1) * 0.35)
    # 달: 왼쪽 위, 구름에 반쯤 가림
    mx, my = (0.30, 0.13) if portrait else (0.33, 0.12)
    d = np.hypot((u - mx) * W, (v - my) * H) / min(W, H)
    moon = np.clip((0.045 - d) / 0.004, 0, 1)
    glow = np.exp(-(d / 0.11) ** 2)
    sky = lerp(sky, np.array([230, 228, 205]), moon * (1 - smoke * 0.55))
    sky = sky + glow[..., None] * np.array([70, 70, 55]) * (1 - smoke[..., None] * 0.4)
    # 연기 기둥: 성채에서 위로 휘어 오르는 검은 연기
    img = sky
    for k, (px, wid, lean) in enumerate([(-0.07, 0.05, 0.10), (0.06, 0.04, 0.16), (0.17, 0.035, 0.22), (-0.20, 0.03, 0.05)]):
        bx = cx + px
        hgt = np.clip((horizon - v) / horizon, 0, 1)          # 위로 갈수록 1
        center = bx + lean * hgt ** 1.6 + (fbm(W, H, 90, rng) - 0.5) * 0.06 * hgt
        width = wid * (0.5 + hgt * 2.2)
        plume = np.exp(-((u - center) / width) ** 2) * (v < horizon - 0.02) * np.clip(1.2 - hgt, 0, 1)
        plume *= 0.55 + 0.45 * fbm(W, H, 60, rng)
        img = lerp(img, np.array([28, 26, 24]), np.clip(plume * 0.85, 0, 1))
    # 먼 산맥(푸르스름하게 흐림)
    ridge = horizon - 0.06 - 0.05 * fbm(W, 1, 300, rng)[0] - 0.03 * fbm(W, 1, 70, rng)[0]
    far = (v > ridge[None, :]).astype(np.float32)
    img = lerp(img, np.array([58, 62, 60]), far * 0.75)
    # 땅: 지평선 아래는 어두운 들판(불빛이 번짐)
    gnd = np.clip((v - horizon - 0.01) / 0.06, 0, 1) * (0.75 + 0.25 * fbm(W, H, 50, rng))
    img = lerp(img, np.array([34, 28, 22]), gnd)
    base = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

    # ── 성채(2배 크기로 그림) ──
    S = SS
    lay = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    sc = (W / 1080 * 0.92 if portrait else H / 1080 * 1.05) * S
    X0, Y0 = cx * W * S, horizon * H * S
    stone_d, stone_l, roof_d, roof_l = (40, 36, 32, 255), (86, 70, 52, 255), (26, 28, 32, 255), (58, 56, 54, 255)

    def tower(dx, dy, w, h, roof, rh, win=3):
        x, y = X0 + dx * sc, Y0 + dy * sc
        dr.rectangle([x - w * sc / 2, y - h * sc, x, y], fill=stone_d)
        dr.rectangle([x, y - h * sc, x + w * sc / 2, y], fill=stone_l)
        top = y - h * sc
        if roof == 'cone':
            dr.polygon([(x - w * sc * 0.62, top), (x, top - rh * sc), (x, top)], fill=roof_d)
            dr.polygon([(x, top - rh * sc), (x + w * sc * 0.62, top), (x, top)], fill=roof_l)
            dr.line([(x, top - rh * sc), (x, top - rh * sc - 22 * sc)], fill=roof_d, width=max(1, int(2 * sc)))
            dr.polygon([(x, top - rh * sc - 22 * sc), (x + 16 * sc, top - rh * sc - 18 * sc), (x, top - rh * sc - 13 * sc)], fill=(120, 30, 26, 255))
        else:   # 톱니 성가퀴
            n = max(3, int(w / 9))
            for i in range(n):
                if i % 2 == 0:
                    bx0 = x - w * sc / 2 + i * w * sc / n
                    dr.rectangle([bx0, top - 9 * sc, bx0 + w * sc / n, top], fill=stone_d if bx0 < x else stone_l)
        for i in range(win):   # 불 켜진 창
            wy = y - h * sc * (0.3 + 0.5 * rng.random())
            wx = x + (rng.random() - 0.5) * w * sc * 0.6
            dr.rectangle([wx - 2.5 * sc, wy - 6 * sc, wx + 2.5 * sc, wy + 6 * sc], fill=(255, 178, 80, 255) if rng.random() < 0.7 else (40, 30, 24, 255))

    def wall(x0, x1, y, h):
        dr.rectangle([X0 + x0 * sc, Y0 + (y - h) * sc, X0 + x1 * sc, Y0 + y * sc], fill=(70, 58, 44, 255))
        for i in range(int((x1 - x0) / 14)):
            if i % 2 == 0:
                bx0 = X0 + (x0 + i * 14) * sc
                dr.rectangle([bx0, Y0 + (y - h - 8) * sc, bx0 + 14 * sc, Y0 + (y - h) * sc], fill=(70, 58, 44, 255))

    # 산 위의 성: 뒤쪽 높은 탑 → 앞쪽 성벽 순서
    tower(-150, -120, 52, 260, 'cone', 110, 4)
    tower(-60, -150, 70, 380, 'cone', 150, 6)          # 본성 큰 탑
    tower(30, -130, 56, 300, 'cone', 120, 5)
    tower(118, -110, 46, 230, 'cone', 95, 3)
    tower(-225, -60, 40, 160, 'flat', 0, 2)
    tower(200, -50, 44, 170, 'cone', 80, 2)
    wall(-260, 240, -40, 90)
    tower(-270, 10, 48, 150, 'flat', 0, 2)
    tower(260, 20, 52, 150, 'flat', 0, 2)
    wall(-330, 330, 40, 80)
    # 성문: 불길 비치는 아치
    gx, gy = X0 - 10 * sc, Y0 + 40 * sc
    dr.rectangle([gx - 34 * sc, gy - 70 * sc, gx + 34 * sc, gy], fill=(40, 18, 10, 255))
    dr.ellipse([gx - 34 * sc, gy - 100 * sc, gx + 34 * sc, gy - 40 * sc], fill=(40, 18, 10, 255))
    # 산(성 아래 언덕): 어두운 갈색 바위
    hill = [(X0 - 620 * sc, Y0 + 260 * sc), (X0 - 420 * sc, Y0 + 70 * sc), (X0 - 300 * sc, Y0 + 40 * sc), (X0 + 320 * sc, Y0 + 40 * sc),
            (X0 + 460 * sc, Y0 + 90 * sc), (X0 + 640 * sc, Y0 + 260 * sc)]
    dr.polygon(hill, fill=(38, 30, 24, 255))
    # 먼 들판의 군대: 작은 창 숲과 횃불 점
    for _ in range(int(W * 1.6)):
        bx = rng.random() * W * S
        by = (horizon + 0.07 + 0.16 * rng.random() ** 1.3) * H * S
        if abs(bx / (W * S) - cx) < 0.12 and by < (horizon + 0.12) * H * S:
            continue
        k = (by / (H * S) - horizon) / 0.23
        L = (8 + 26 * k) * S * W / 1080
        dr.line([(bx, by), (bx + (rng.random() - 0.5) * L * 0.3, by - L)], fill=(22, 18, 15, 255), width=max(1, int((1 + 2 * k) * S)))
        dr.ellipse([bx - 3 * S * (0.6 + k), by - 2 * S, bx + 3 * S * (0.6 + k), by + 4 * S * (0.6 + k)], fill=(22, 18, 15, 255))
        if rng.random() < 0.05:
            r = (1.5 + 2 * k) * S
            dr.ellipse([bx - r, by - L - r, bx + r, by - L + r], fill=(255, 170, 70, 255))
    castle = lay.resize((W, H), Image.LANCZOS)
    ca = np.asarray(castle, np.float32)
    # 돌 질감: 얼룩 무늬를 곱해 붓 자국처럼
    tex = 0.78 + 0.4 * fbm(W, H, 18, rng, 3)
    ca[..., :3] *= tex[..., None]
    # 아래쪽 불빛(주황 테두리 빛)
    fire_y = horizon + (0.06 if portrait else 0.08)
    fg = np.exp(-(((u - cx) * W / (0.32 * W)) ** 2) - (((v - fire_y) * H / (0.12 * H)) ** 2))
    ca[..., :3] = ca[..., :3] * (1 + fg[..., None] * np.array([0.9, 0.45, 0.1]))
    haze = np.clip(0.35 - (v - horizon) * 1.5, 0.1, 0.45) * (0.6 + 0.4 * fbm(W, H, 80, rng))
    ca[..., :3] = ca[..., :3] * (1 - haze[..., None]) + np.array([70, 70, 60]) * haze[..., None]
    castle = Image.fromarray(np.clip(ca, 0, 255).astype(np.uint8), 'RGBA')
    base.paste(castle, (0, 0), castle)
    # 안개: 성 아래로 깔리는 희뿌연 띠
    arr = np.asarray(base, np.float32)
    fogb = np.exp(-((v - (horizon + 0.10)) / 0.07) ** 2) * (0.5 + 0.5 * fbm(W, H, 140, rng))
    arr = lerp(arr, np.array([92, 86, 72]), fogb * 0.45)
    # 들판 곳곳의 불길: 전장 여기저기 타오르는 불빛
    for k in range(9):
        fx_, fy_ = rng.random(), horizon + 0.05 + rng.random() * 0.25
        r = 0.03 + rng.random() * 0.05
        gl = np.exp(-(((u - fx_) / r) ** 2) - (((v - fy_) / (r * 0.6 * W / H)) ** 2))
        arr = arr + gl[..., None] * np.array([120, 50, 8]) * (0.5 + rng.random() * 0.6)
    # 성문 주변 불꽃 빛
    arr = arr + fg[..., None] * np.array([110, 52, 10]) * 0.9

    # ── 앞쪽 군대: 창·투구·깃발 실루엣(양옆이 크고 가운데는 낮게 → 가운데에 글자·버튼) ──
    S2 = SS
    lay = Image.new('RGBA', (W * S2, H * S2), (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    WW, HH = W * S2, H * S2
    dark = (16, 13, 11, 255)

    def side(xx):   # 0(가운데)~1(가장자리)
        return min(1.0, abs(xx / WW - 0.5) * 2)
    # 창(pike): 가장자리일수록 많고 길게
    for _ in range(int(W / 12) if army else 0):
        bx = rng.random() * WW
        s = side(bx)
        if s < 0.35 or rng.random() > s ** 1.5:
            continue
        by = HH * (0.82 + 0.10 * rng.random())
        ang = math.radians(-90 + (rng.random() - 0.5) * 40 + (bx / WW - 0.5) * -40)
        L = HH * (0.10 + 0.30 * s ** 2 + 0.08 * rng.random())
        ex, ey = bx + math.cos(ang) * L, by + math.sin(ang) * L
        wdt = max(2, int((2 + 5 * s) * S2 * W / 1080))
        dr.line([(bx, by), (ex, ey)], fill=dark, width=wdt)
        hx, hy = math.cos(ang), math.sin(ang)
        px, py = -hy, hx
        hl = wdt * 5
        dr.polygon([(ex + hx * hl, ey + hy * hl), (ex + px * wdt * 1.4, ey + py * wdt * 1.4), (ex - px * wdt * 1.4, ey - py * wdt * 1.4)], fill=(30, 26, 22, 255))
    # 깃발 몇 개(찢어진 붉은 천)
    for k in range(4 if army else 0):
        bx = WW * (0.06 + 0.88 * (k / 3))
        if 0.3 < bx / WW < 0.7:
            continue
        top = HH * (0.42 + 0.08 * rng.random())
        dr.line([(bx, HH), (bx + 10 * S2, top)], fill=dark, width=6 * S2)
        fw = WW * 0.07 * (1 if bx < WW / 2 else -1)
        pts = [(bx + 10 * S2, top), (bx + fw, top + HH * 0.02), (bx + fw * 0.85, top + HH * 0.10), (bx + fw * 0.6, top + HH * 0.08), (bx + fw * 0.45, top + HH * 0.13), (bx + 10 * S2, top + HH * 0.11)]
        dr.polygon(pts, fill=(78, 20, 18, 255))
    # 병사 머리·어깨: 아래쪽에 겹겹이
    for row in range(3 if army else 0):
        ry = HH * (0.80 + row * 0.06)
        n = int(W / (26 - row * 6))
        for i in range(n):
            bx = (i + rng.random() * 0.6) / n * WW
            s = side(bx)
            r = HH * (0.018 + 0.02 * row + 0.03 * s) * (0.8 + 0.4 * rng.random())
            yb = ry - r * 0.2 + (1 - s) * HH * 0.04
            dr.ellipse([bx - r, yb - r, bx + r, yb + r * 0.9], fill=dark)                 # 투구
            dr.polygon([(bx - r * 0.9, yb - r * 0.3), (bx, yb - r * 1.5), (bx + r * 0.9, yb - r * 0.3)], fill=dark) if rng.random() < 0.3 else None   # 뾰족 투구
            dr.rectangle([bx - r * 1.6, min(HH - 1, yb + r * 0.5), bx + r * 1.6, HH], fill=dark)        # 어깨
    army = np.asarray(lay.resize((W, H), Image.LANCZOS), np.float32)
    a = army[..., 3:4] / 255
    # 실루엣 위쪽에 불빛 테두리(성 쪽을 향한 면)
    rim = np.asarray(Image.fromarray(army[..., 3].astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)), np.float32) / 255
    edge = np.clip(rim - a[..., 0], 0, 1) * (v > 0.5)
    arr = arr * (1 - a) + army[..., :3] * a
    arr = arr + edge[..., None] * np.array([150, 70, 20]) * 0.8

    # ── 마무리: 아래쪽 어둡게(글자 읽기 쉽게), 가장자리 어둡게, 색감, 알갱이 ──
    bot = np.clip((v - 0.62) / 0.38, 0, 1) ** 1.5
    arr = arr * (1 - bot[..., None] * 0.45)
    vig = np.clip(np.hypot((u - 0.5) * 1.3, (v - 0.48) * 1.1), 0, 1)
    arr = arr * (1 - vig[..., None] ** 2 * 0.75)
    g = arr.mean(axis=2, keepdims=True)
    arr = g + (arr - g) * 0.88
    arr = arr * np.array([1.0, 0.97, 0.86])
    arr = arr + (rng.random((H, W, 1)) - 0.5) * 10
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.SMOOTH)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, (w, h, p) in {'title_bg_portrait.jpg': (1080, 1920, True), 'title_bg_landscape.jpg': (1920, 1080, False)}.items():
        im = paint(w, h, p)
        path = os.path.join(OUT, name)
        im.save(path, quality=84, optimize=True, progressive=True)
        print(name, im.size, os.path.getsize(path) // 1024, 'KB')


if __name__ == '__main__':
    main()
