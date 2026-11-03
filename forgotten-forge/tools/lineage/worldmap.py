"""에르덴 월드맵(양피지 세계지도)을 그린다.
결과(lineage-assets/ui/):
  worldmap_base.png    양피지 + 대륙 + 지역별 기후 색 + 지형 기호(산·숲·폐허…) + 테두리·나침반
  worldmap_labels.png  지역 이름·기후 설명 글자(투명 바탕, 맨 위에 겹침)
  worldmap_fog_<id>.png  잠긴 지역을 덮는 안개(투명 바탕) — 지역이 열리면 게임이 숨긴다
  worldmap.json        지역 중심 좌표(0~1), 아르델 마을·묘소 위치(현재 위치 핀용)
실행: python3 forgotten-forge/tools/lineage/worldmap.py
같은 SEED면 언제나 같은 지도가 나온다.
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'lineage-assets', 'ui')
W, H = 1600, 1040
SEED = 2026
RNG = np.random.default_rng(SEED)
SERIF_B = ('/usr/share/fonts/opentype/noto/NotoSerifCJK-Black.ttc', 1)
SERIF_M = ('/usr/share/fonts/opentype/noto/NotoSerifCJK-SemiBold.ttc', 1)


def font(spec, size):
    return ImageFont.truetype(spec[0], size, index=spec[1])


# ───────────────────────── 노이즈 ─────────────────────────

def value_noise(cells, seed):
    """cells×cells 무작위 격자를 부드럽게 늘린 값 노이즈(0~1)."""
    g = np.random.default_rng(seed).random((cells + 3, int(cells * W / H) + 3))
    z = ndimage.zoom(g, (H / cells, H / cells), order=3)
    return np.clip(z[:H, :W], 0, 1)


def fbm(seed, octaves=5, base=4):
    out = np.zeros((H, W))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        out += value_noise(base * 2 ** o, seed + o * 17) * amp
        tot += amp
        amp *= 0.5
    return out / tot


YY, XX = np.mgrid[0:H, 0:W]
U, V = XX / W, YY / H

# ───────────────────────── 지역 정의 ─────────────────────────
# 위치는 0~1 비율. 아르델(남쪽 평원) → 엘라시아(동쪽 숲) → 카르둠(북쪽 설산) → 검은 황무지(서쪽) → 아르카나(중앙 폐허), 천공의 성역(하늘 섬)
REGIONS = [
    dict(id='ardel', name='아르델 평원', sub='온화한 들판과 옛 왕국의 폐허', lv='Lv 1–15', seed=(0.50, 0.80), wt=0.85,
         tint=(178, 168, 70), ink=(92, 84, 30)),
    dict(id='elasia', name='엘라시아 숲', sub='안개 낀 고대 숲 · 요정의 땅', lv='Lv 15–30', seed=(0.82, 0.52), wt=0.75,
         tint=(40, 120, 92), ink=(18, 64, 48)),
    dict(id='kardum', name='카르둠 산맥', sub='만년설과 드워프의 대장간', lv='Lv 25–40', seed=(0.50, 0.20),
         tint=(150, 160, 178), ink=(58, 64, 82)),
    dict(id='blackwaste', name='검은 황무지', sub='잿빛 바람이 부는 마족의 땅', lv='Lv 35–50', seed=(0.18, 0.50),
         tint=(96, 64, 58), ink=(56, 24, 20)),
    dict(id='arcana', name='아르카나 폐허', sub='별의 몰락이 남긴 마법 왕국', lv='Lv 45–60', seed=(0.47, 0.48), wt=2.6,
         tint=(124, 92, 168), ink=(60, 34, 96)),
]
SANCTUM = dict(id='sanctum', name='천공의 성역', sub='하늘에 떠 있는 별의 심장', lv='Lv 60+', c=(0.84, 0.22), r=(0.08, 0.05),
               tint=(214, 186, 96), ink=(110, 84, 20))
TOWN = (0.47, 0.80)        # 아르델 마을
CRYPT = (0.58, 0.86)       # 왕실 기사단 묘소


def by_id(i):
    return [r['id'] for r in REGIONS].index(i)


def continent_mask():
    """흔들리는 해안선을 가진 대륙(참/거짓)."""
    n = fbm(11, 6, 3)
    n2 = fbm(23, 3, 2)
    # 가운데가 높은 타원 + 큰 굴곡(만·반도) + 잔 노이즈
    d = np.sqrt(((U - 0.47) / 0.46) ** 2 + ((V - 0.53) / 0.45) ** 2)
    h = 1.12 - d + (n - 0.5) * 0.85 + (n2 - 0.5) * 0.5
    m = h > 0.5
    m = ndimage.binary_opening(m, iterations=3)
    lab, k = ndimage.label(m)
    sizes = ndimage.sum(m, lab, range(1, k + 1))
    keep = np.zeros(k + 1, bool)
    keep[1:] = sizes > 900           # 너무 작은 섬만 지운다(작은 섬 몇 개는 남김)
    m = keep[lab]
    return ndimage.binary_fill_holes(m)


def region_map(land):
    """지역 번호(0~4, 바다 = -1). 좌표를 노이즈로 휘게 한 뒤 가장 가까운 지역 씨앗을 고른다."""
    wx = (fbm(31, 4, 3) - 0.5) * 0.22
    wy = (fbm(47, 4, 3) - 0.5) * 0.22
    best = np.full((H, W), 9.0)
    idx = np.zeros((H, W), int)
    for i, r in enumerate(REGIONS):
        sx, sy = r['seed']
        dd = ((U + wx - sx) * 1.35) ** 2 + (V + wy - sy) ** 2
        dd *= r.get('wt', 1.0)            # 값이 크면 지역이 작아진다
        sel = dd < best
        best[sel] = dd[sel]
        idx[sel] = i
    idx[~land] = -1
    return idx


# ───────────────────────── 기호 그리기 ─────────────────────────

def poisson_points(mask, n, min_d, seed):
    """mask 안에서 서로 min_d 이상 떨어진 점 n개(가능한 만큼)."""
    rng = np.random.default_rng(seed)
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return []
    pts = []
    for _ in range(n * 12):
        k = rng.integers(len(xs))
        p = (xs[k], ys[k])
        if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 >= min_d * min_d for q in pts):
            pts.append(p)
            if len(pts) >= n:
                break
    return sorted(pts, key=lambda p: p[1])   # 위에서 아래로(앞의 것이 뒤에 그려지도록)


def mountain(d, x, y, s, ink, snow=True):
    pk = (x, y - s)
    l, r = (x - s * 0.95, y), (x + s * 0.95, y)
    d.polygon([l, pk, (x + s * 0.12, y)], fill=(236, 226, 200))                 # 밝은 쪽
    d.polygon([pk, r, (x + s * 0.12, y)], fill=(ink[0] + 60, ink[1] + 60, ink[2] + 60))   # 그늘 쪽
    if snow:
        d.polygon([pk, (x - s * 0.36, y - s * 0.62), (x - s * 0.1, y - s * 0.55), (x + s * 0.06, y - s * 0.66), (x + s * 0.34, y - s * 0.6)], fill=(250, 250, 246))
    d.line([l, pk, r], fill=ink, width=2)
    for k in range(3):                                                          # 그늘 빗금
        t = 0.3 + k * 0.2
        d.line([(x + s * 0.12 + (s * 0.83) * t * 0.5, y - s * (1 - t) * 0.9), (x + s * 0.2 + s * 0.6 * t, y - 2)], fill=ink, width=1)


def tree(d, x, y, s, ink, fill):
    d.line([(x, y), (x, y - s * 0.5)], fill=ink, width=2)
    d.ellipse([x - s * 0.55, y - s * 1.45, x + s * 0.55, y - s * 0.35], fill=fill, outline=ink, width=2)
    d.arc([x - s * 0.3, y - s * 1.25, x + s * 0.2, y - s * 0.75], 200, 300, fill=ink, width=1)


def pine(d, x, y, s, ink, fill):
    d.polygon([(x, y - s * 1.6), (x - s * 0.55, y - s * 0.3), (x + s * 0.55, y - s * 0.3)], fill=fill, outline=ink)
    d.line([(x, y - s * 0.3), (x, y)], fill=ink, width=2)


def dead_tree(d, x, y, s, ink):
    d.line([(x, y), (x, y - s * 1.2)], fill=ink, width=2)
    d.line([(x, y - s * 0.7), (x - s * 0.5, y - s * 1.15)], fill=ink, width=1)
    d.line([(x, y - s * 0.9), (x + s * 0.45, y - s * 1.3)], fill=ink, width=1)


def pillar(d, x, y, s, ink, fill):
    w = s * 0.32
    h = s * (0.8 + 0.6 * ((x * 7 + y * 3) % 5) / 5)
    d.rectangle([x - w, y - h, x + w, y], fill=fill, outline=ink, width=2)
    d.line([(x - w, y - h), (x - w * 0.2, y - h - s * 0.2), (x + w, y - h)], fill=ink, width=2)   # 부서진 꼭대기
    d.line([(x - w * 1.5, y), (x + w * 1.5, y)], fill=ink, width=2)


def crack(d, x, y, s, ink, rng):
    px, py = x, y
    for _ in range(4):
        nx, ny = px + rng.uniform(-s, s), py + rng.uniform(-s * 0.4, s * 0.4)
        d.line([(px, py), (nx, ny)], fill=ink, width=1)
        px, py = nx, ny


def field(d, x, y, s, ink):
    for k in range(4):
        d.line([(x - s + k * 2, y - k * 3), (x + s + k * 2, y - k * 3 - 2)], fill=ink, width=1)


def house(d, x, y, s, ink, roof):
    d.rectangle([x - s * 0.6, y - s * 0.7, x + s * 0.6, y], fill=(232, 216, 182), outline=ink, width=2)
    d.polygon([(x - s * 0.8, y - s * 0.65), (x, y - s * 1.35), (x + s * 0.8, y - s * 0.65)], fill=roof, outline=ink)


# ───────────────────────── 그리기 ─────────────────────────

def parchment():
    n1, n2 = fbm(1, 6, 3), fbm(5, 4, 12)
    base = np.array([228, 208, 164], float)
    img = base[None, None, :] * (0.86 + 0.18 * n1[..., None]) + (n2[..., None] - 0.5) * 18
    # 얼룩(찻물 자국)
    for _ in range(5):
        cx, cy, rr = RNG.uniform(0, W), RNG.uniform(0, H), RNG.uniform(80, 240)
        dd = np.sqrt((XX - cx) ** 2 + (YY - cy) ** 2) * (0.85 + 0.3 * n2)
        ring = np.exp(-((dd - rr) / 10) ** 2) * 0.045 + np.exp(-(dd / rr) ** 2) * 0.035
        img *= (1 - ring[..., None] * np.array([0.25, 0.45, 0.75]))
    # 가장자리 어둡게 + 그을린 느낌
    e = np.minimum.reduce([U, 1 - U, V, 1 - V])
    burn = np.clip(1 - e / 0.09, 0, 1) ** 2 * (0.55 + 0.45 * fbm(9, 4, 10))
    img *= (1 - burn[..., None] * np.array([0.55, 0.62, 0.72]))
    return np.clip(img, 0, 255)


def main():
    os.makedirs(OUT, exist_ok=True)
    land = continent_mask()
    reg = region_map(land)
    img = parchment()

    # 바다: 옅은 청회색 + 해안을 따라 겹치는 물결 줄
    sea = ~land
    dist_sea = ndimage.distance_transform_edt(sea)
    img[sea] = img[sea] * np.array([0.86, 0.92, 0.98])
    ripple = sea & (dist_sea < 46) & (np.abs(((dist_sea + 2) % 11) - 5.5) < 0.7)
    img[ripple] = img[ripple] * 0.84

    # 지역 기후 색(양피지에 물감이 스민 느낌: 곱하기 + 노이즈 얼룩)
    wash = fbm(77, 5, 6)
    for i, r in enumerate(REGIONS):
        m = reg == i
        t = np.array(r['tint'], float) / 255
        a = (0.42 + 0.22 * (wash[m] - 0.5))[:, None]
        img[m] = img[m] * (1 - a) + img[m] * t * a + (t * 255 * 0.18) * a
    # 해안 안쪽 그늘(언덕처럼 볼록해 보이게)
    dist_land = ndimage.distance_transform_edt(land)
    shade = np.clip(1 - dist_land / 14, 0, 1) * land
    img *= (1 - shade[..., None] * 0.18)
    im = Image.fromarray(img.astype(np.uint8)).convert('RGBA')
    d = ImageDraw.Draw(im)

    # 해안선(먹선)
    edge = land ^ ndimage.binary_erosion(land, iterations=2)
    ea = np.zeros((H, W, 4), np.uint8)
    ea[edge] = (58, 40, 22, 235)
    im.alpha_composite(Image.fromarray(ea))
    # 지역 경계(붉은 갈색 점선)
    bd = np.zeros((H, W), bool)
    bd[:, 1:] |= (reg[:, 1:] != reg[:, :-1]) & (reg[:, 1:] >= 0) & (reg[:, :-1] >= 0)
    bd[1:, :] |= (reg[1:, :] != reg[:-1, :]) & (reg[1:, :] >= 0) & (reg[:-1, :] >= 0)
    bd = ndimage.binary_dilation(bd, iterations=1)
    dash = ((XX + YY) // 7) % 2 == 0
    ba = np.zeros((H, W, 4), np.uint8)
    ba[bd & dash] = (120, 40, 26, 210)
    im.alpha_composite(Image.fromarray(ba))
    d = ImageDraw.Draw(im)

    inner = {i: ndimage.binary_erosion(reg == i, iterations=16) for i in range(len(REGIONS))}
    # 글자 자리를 비워 둔다(기호가 이름을 덮지 않게)
    lab_box = {}
    for i, r in enumerate(REGIONS):
        ys, xs = np.nonzero(reg == i)
        cx, cy = ndimage.center_of_mass(reg == i)[::-1]
        lab_box[r['id']] = (cx, cy)
        clear = (np.abs(XX - cx) < 135) & (YY - cy > -40) & (YY - cy < 72)
        inner[i] &= ~clear
    ard_in = ndimage.binary_erosion(reg == by_id('ardel'), iterations=28)
    def snap(pt):
        ys, xs = np.nonzero(ard_in)
        k = np.argmin((xs - pt[0] * W) ** 2 + (ys - pt[1] * H) ** 2)
        return (float(xs[k]), float(ys[k]))
    town_px, crypt_px = snap(TOWN), snap(CRYPT)
    for i in inner:
        inner[i] &= ~((np.abs(XX - town_px[0]) < 46) & (np.abs(YY - town_px[1]) < 36))
        inner[i] &= ~((np.abs(XX - crypt_px[0]) < 30) & (np.abs(YY - crypt_px[1]) < 30))

    rng = np.random.default_rng(SEED + 3)
    by = {r['id']: i for i, r in enumerate(REGIONS)}
    # 카르둠: 설산 + 대장간 연기
    for x, y in poisson_points(inner[by['kardum']], 70, 34, 1):
        mountain(d, x, y, rng.uniform(20, 34), REGIONS[by['kardum']]['ink'])
    # 엘라시아: 빽빽한 고대 숲
    for x, y in poisson_points(inner[by['elasia']], 230, 17, 2):
        (tree if rng.random() < 0.6 else pine)(d, x, y, rng.uniform(9, 14), REGIONS[by['elasia']]['ink'], (46, 104, 72) if rng.random() < .5 else (64, 124, 82))
    # 아르델: 들판 줄무늬 + 듬성한 나무 + 언덕
    for x, y in poisson_points(inner[by['ardel']], 60, 30, 3):
        if rng.random() < 0.55:
            field(d, x, y, 12, (124, 112, 44))
        else:
            tree(d, x, y, rng.uniform(8, 11), (80, 74, 30), (128, 136, 60))
    # 검은 황무지: 갈라진 땅 + 죽은 나무 + 잿빛 바위
    for x, y in poisson_points(inner[by['blackwaste']], 90, 26, 4):
        k = rng.random()
        if k < 0.45:
            crack(d, x, y, 12, (70, 30, 24), rng)
        elif k < 0.8:
            dead_tree(d, x, y, rng.uniform(12, 18), (52, 30, 26))
        else:
            mountain(d, x, y, rng.uniform(12, 18), (60, 34, 30), snow=False)
    # 아르카나: 부서진 기둥 + 마법진
    acx, acy = lab_box['arcana']
    for rr in (64, 52):
        d.ellipse([acx - rr * 1.6, acy + 96 - rr * 0.6, acx + rr * 1.6, acy + 96 + rr * 0.6], outline=(96, 60, 150, 200), width=2)
    for k in range(8):
        a = k * math.pi / 4
        d.line([(acx + math.cos(a) * 82, acy + 96 + math.sin(a) * 31), (acx + math.cos(a) * 102, acy + 96 + math.sin(a) * 38)], fill=(96, 60, 150, 200), width=2)
    for x, y in poisson_points(inner[by['arcana']], 30, 24, 5):
        pillar(d, x, y, rng.uniform(12, 18), (60, 34, 96), (196, 184, 214))

    # 아르델 마을(집 3채) + 길 + 기사단 묘소 입구
    tx, ty = town_px
    d.line([(tx, ty), (tx + 60, ty + 30), crypt_px], fill=(120, 84, 40), width=3)
    d.line([(tx, ty), (tx - 40, ty - 70), (tx - 20, ty - 160)], fill=(120, 84, 40), width=3)   # 북쪽으로 난 옛길
    for ox, oy in ((-16, 4), (14, 0), (-2, 16)):
        house(d, tx + ox, ty + oy, 16, (60, 40, 20), (150, 64, 40))
    cx_, cy_ = crypt_px
    d.polygon([(cx_ - 14, cy_ + 8), (cx_, cy_ - 14), (cx_ + 14, cy_ + 8)], fill=(90, 80, 70), outline=(40, 30, 20))
    d.rectangle([cx_ - 5, cy_ - 2, cx_ + 5, cy_ + 8], fill=(30, 22, 16))

    # 천공의 성역: 구름 위 떠 있는 섬 + 빛줄기 + 아르카나로 이어진 점선
    scx, scy = SANCTUM['c'][0] * W, SANCTUM['c'][1] * H
    rx, ry = SANCTUM['r'][0] * W, SANCTUM['r'][1] * H
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for k in range(9):
        a = math.pi * (0.15 + 0.7 * k / 8)
        gd.polygon([(scx, scy), (scx + math.cos(a) * 260 - 10, scy - math.sin(a) * 200), (scx + math.cos(a) * 260 + 10, scy - math.sin(a) * 200)], fill=(255, 226, 140, 46))
    gd.ellipse([scx - rx * 1.8, scy - ry * 2.2, scx + rx * 1.8, scy + ry * 2.2], fill=(255, 230, 160, 40))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(im)
    # 섬 아래 바위 뿌리: 들쭉날쭉한 역삼각형 + 지층 줄무늬
    root = [(scx - rx * 1.02, scy + 4)]
    for k in range(1, 12):
        f = k / 12
        x = scx - rx + f * rx * 2
        depth = (1 - abs(f - 0.48) * 2) ** 1.4 * ry * 3.4 + rng.uniform(-6, 6)
        root.append((x, scy + depth))
    root.append((scx + rx * 1.02, scy + 4))
    d.polygon(root, fill=(132, 104, 70), outline=(70, 50, 30))
    for k in range(1, 4):
        d.line([(scx - rx * (1 - k * 0.18), scy + ry * 0.55 * k), (scx + rx * (1 - k * 0.2), scy + ry * 0.5 * k)], fill=(96, 72, 46), width=2)
    d.line([(scx + rx * 0.3, scy + 6), (scx + rx * 0.32, scy + ry * 2.1)], fill=(150, 196, 220), width=3)   # 섬에서 떨어지는 물줄기
    # 윗면: 노이즈로 흔들린 타원
    top = []
    for k in range(48):
        a = 2 * math.pi * k / 48
        j = 1 + 0.07 * math.sin(a * 5 + 1) + 0.04 * math.sin(a * 9)
        top.append((scx + math.cos(a) * rx * j, scy + math.sin(a) * ry * j))
    d.polygon(top, fill=(222, 204, 140), outline=(110, 84, 20))
    d.ellipse([scx - rx * 0.35, scy - ry * 0.35, scx + rx * 0.35, scy + ry * 0.35], outline=(200, 150, 50), width=2)   # 별의 심장 제단
    for k in range(5):   # 성역 탑
        x = scx - rx * 0.62 + k * rx * 0.31
        hh = 22 + (k % 2) * 10 + (k == 2) * 22
        d.rectangle([x - 5, scy - hh, x + 5, scy + 2], fill=(244, 236, 210), outline=(110, 84, 20))
        d.polygon([(x - 7, scy - hh), (x, scy - hh - 12), (x + 7, scy - hh)], fill=(214, 170, 60), outline=(110, 84, 20))
    d.polygon([(scx, scy - 78), (scx - 6, scy - 66), (scx + 6, scy - 66)], fill=(255, 236, 160), outline=(170, 120, 30))   # 별
    # 구름: 뭉게뭉게 겹친 원(아래쪽 그늘)
    for k in range(16):
        x = scx - rx * 1.4 + k * rx * 0.19 + rng.uniform(-8, 8)
        y = scy + ry * (0.75 + 0.35 * math.sin(k * 1.7)) + rng.uniform(-4, 4)
        r0 = rng.uniform(16, 30)
        d.ellipse([x - r0, y - r0 * 0.7, x + r0, y + r0 * 0.7], fill=(214, 206, 192), outline=(150, 132, 108))
        d.ellipse([x - r0 * 0.8, y - r0 * 0.75, x + r0 * 0.75, y + r0 * 0.35], fill=(248, 244, 232))
    ax_, ay_ = lab_box['arcana']
    pts = [(ax_ + 70, ay_ - 30), (scx - rx * 0.6, scy + ry * 2.6)]
    n_d = 26
    for k in range(n_d):
        if k % 2 == 0:
            p0 = (pts[0][0] + (pts[1][0] - pts[0][0]) * k / n_d, pts[0][1] + (pts[1][1] - pts[0][1]) * k / n_d)
            p1 = (pts[0][0] + (pts[1][0] - pts[0][0]) * (k + 1) / n_d, pts[0][1] + (pts[1][1] - pts[0][1]) * (k + 1) / n_d)
            d.line([p0, p1], fill=(170, 130, 40), width=2)

    # 나침반(왼쪽 아래 바다)
    ccx, ccy, cr = 150, H - 160, 70
    d.ellipse([ccx - cr, ccy - cr, ccx + cr, ccy + cr], outline=(90, 60, 30), width=2)
    d.ellipse([ccx - cr + 8, ccy - cr + 8, ccx + cr - 8, ccy + cr - 8], outline=(90, 60, 30), width=1)
    for k in range(8):
        a = k * math.pi / 4 - math.pi / 2
        L = cr - 4 if k % 2 == 0 else cr * 0.55
        tip = (ccx + math.cos(a) * L, ccy + math.sin(a) * L)
        l = (ccx + math.cos(a + 1.57) * 9, ccy + math.sin(a + 1.57) * 9)
        r = (ccx + math.cos(a - 1.57) * 9, ccy + math.sin(a - 1.57) * 9)
        d.polygon([l, tip, (ccx, ccy)], fill=(120, 40, 26) if k == 0 else (90, 60, 30))
        d.polygon([r, tip, (ccx, ccy)], fill=(236, 220, 186))
    d.text((ccx, ccy - cr - 18), '북', font=font(SERIF_B, 22), fill=(90, 40, 20), anchor='mm')

    # 테두리(이중선 + 모서리 장식)
    for k, wdt in ((14, 4), (24, 1)):
        d.rectangle([k, k, W - k, H - k], outline=(80, 52, 26), width=wdt)
    for x, y in ((14, 14), (W - 14, 14), (14, H - 14), (W - 14, H - 14)):
        d.ellipse([x - 12, y - 12, x + 12, y + 12], fill=(160, 110, 50), outline=(80, 52, 26), width=2)
    im.convert('RGB').save(os.path.join(OUT, 'worldmap_base.png'), optimize=True)

    # ── 글자 층 ──
    lab = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lab)
    title_f, name_f, sub_f, small_f = font(SERIF_B, 46), font(SERIF_B, 34), font(SERIF_M, 17), font(SERIF_M, 15)

    def label(x, y, r, name_size=None):
        nf = font(SERIF_B, name_size) if name_size else name_f
        ld.text((x, y), r['name'], font=nf, fill=(r['ink'][0], r['ink'][1], r['ink'][2], 255), anchor='mm', stroke_width=5, stroke_fill=(240, 226, 194, 230))
        ld.text((x, y + 30), r['sub'], font=sub_f, fill=(70, 50, 30, 255), anchor='mm', stroke_width=3, stroke_fill=(240, 226, 194, 220))
        ld.text((x, y + 52), r['lv'], font=small_f, fill=(120, 40, 26, 255), anchor='mm', stroke_width=3, stroke_fill=(240, 226, 194, 220))
    for r in REGIONS:
        x, y = lab_box[r['id']]
        label(x, y, r)
    label(scx, scy - ry - 70, SANCTUM, 30)
    ld.text((town_px[0] - 30, town_px[1] - 24), '아르델 마을', font=font(SERIF_B, 18), fill=(60, 30, 14, 255), anchor='rm', stroke_width=3, stroke_fill=(240, 226, 194, 230))
    ld.text((crypt_px[0] + 20, crypt_px[1] + 2), '기사단 묘소', font=font(SERIF_B, 16), fill=(60, 30, 14, 255), anchor='lm', stroke_width=3, stroke_fill=(240, 226, 194, 230))
    # 제목 두루마리
    tx0, ty0 = 70, 60
    ld.rounded_rectangle([tx0, ty0, tx0 + 380, ty0 + 96], radius=10, fill=(236, 218, 176, 235), outline=(90, 60, 30, 255), width=3)
    ld.text((tx0 + 190, ty0 + 40), '에르덴 대륙', font=title_f, fill=(70, 34, 16, 255), anchor='mm')
    ld.text((tx0 + 190, ty0 + 78), '별의 몰락 이후 300년, 재건의 시대', font=small_f, fill=(110, 60, 30, 255), anchor='mm')
    lab.save(os.path.join(OUT, 'worldmap_labels.png'), optimize=True)

    # ── 잠긴 지역 안개 ──
    meta = {'w': W, 'h': H, 'regions': {}, 'town': [round(town_px[0] / W, 4), round(town_px[1] / H, 4)], 'crypt': [round(crypt_px[0] / W, 4), round(crypt_px[1] / H, 4)]}
    fogn = fbm(101, 5, 8)
    for i, r in enumerate(REGIONS + [SANCTUM]):
        if r['id'] == 'sanctum':
            m = ((XX - scx) / (rx * 2.0)) ** 2 + ((YY - (scy + ry * 0.6)) / (ry * 3.6)) ** 2 < 1
        else:
            m = reg == i
        soft = ndimage.gaussian_filter(m.astype(float), 6)
        a = np.clip(soft * (0.58 + 0.3 * fogn), 0, 1)
        fog = np.zeros((H, W, 4), np.uint8)
        fog[..., 0], fog[..., 1], fog[..., 2] = 214, 200, 170
        fog[..., 3] = (a * 255).astype(np.uint8)
        f_im = Image.fromarray(fog)
        bb = f_im.getbbox()
        if r['id'] != 'ardel' and bb:
            f_im.crop(bb).save(os.path.join(OUT, f'worldmap_fog_{r["id"]}.png'), optimize=True)
        cx, cy = (lab_box[r['id']] if r['id'] != 'sanctum' else (scx, scy))
        meta['regions'][r['id']] = {'name': r['name'], 'sub': r['sub'], 'lv': r['lv'], 'c': [round(cx / W, 4), round(cy / H, 4)],
                                    'fog': [bb[0], bb[1], bb[2], bb[3]] if (bb and r['id'] != 'ardel') else None}
    json.dump(meta, open(os.path.join(OUT, 'worldmap.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # 미리보기(글자 겹친 완성본)
    prev = Image.open(os.path.join(OUT, 'worldmap_base.png')).convert('RGBA')
    prev.alpha_composite(lab)
    prev.convert('RGB').save(os.path.join(OUT, 'worldmap_preview.png'), optimize=True)
    print('ok', OUT)


if __name__ == '__main__':
    main()
