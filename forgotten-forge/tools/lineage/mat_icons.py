"""에르덴 재료 아이콘(32×32) 묶음 그림: lineage-assets/items/materials.png
- 바위·약초·넝쿨·그루터기 등은 사용자 제공 도트 그림(ext-src)에서 잘라 쓰고,
  슬라임 점액은 게임의 녹색 슬라임 그림, 가죽은 직접 점을 찍어 그린다.
- 칸 순서가 곧 아이콘 번호(MAT_ICON)다. 게임 코드의 MATERIALS 표가 이 번호를 쓴다.
실행: python3 forgotten-forge/tools/lineage/mat_icons.py
"""
import json
import os

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
SRC = os.path.join(ROOT, 'ext-src')
OUT = os.path.join(ROOT, 'lineage-assets', 'items', 'materials.png')
CELL = 32
rng = np.random.default_rng(7)


def crop(fn, box, fit=28):
    im = Image.open(os.path.join(SRC, fn)).convert('RGBA').crop(box)
    bb = im.getbbox()
    im = im.crop(bb)
    k = min(fit / im.width, fit / im.height)
    k = max(1, int(k)) if k >= 1 else k          # 작으면 정수배로 키워 도트 유지
    return im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.NEAREST)


def speckle(im, color, n, seed):
    """그림 안쪽(불투명한 곳)에 광맥 점을 찍는다."""
    a = np.array(im)
    ys, xs = np.nonzero(a[..., 3] > 200)
    r = np.random.default_rng(seed)
    for k in r.choice(len(xs), size=min(n, len(xs)), replace=False):
        a[ys[k], xs[k], :3] = color
        if xs[k] + 1 < a.shape[1] and a[ys[k], xs[k] + 1, 3] > 200:
            a[ys[k], xs[k] + 1, :3] = [min(255, c + 40) for c in color]
    return Image.fromarray(a)


def tint(im, mul, add=(0, 0, 0), sat=1.0):
    a = np.array(im).astype(float)
    g = a[..., :3].mean(axis=2, keepdims=True)
    a[..., :3] = np.clip((g + (a[..., :3] - g) * sat) * np.array(mul) + np.array(add), 0, 255)
    return Image.fromarray(a.astype(np.uint8))


def slime_gel():
    meta = json.load(open(os.path.join(ROOT, 'lineage-assets', 'meta.json'), encoding='utf-8'))
    s = meta['monsters']['ooze']
    sh = Image.open(os.path.join(ROOT, 'lineage-assets', s['sheet'])).convert('RGBA')
    fr = sh.crop((s['anims']['idle'][0] * s['fw'], 0, (s['anims']['idle'][0] + 1) * s['fw'], s['fh']))
    fr = fr.crop(fr.getbbox())
    fr.thumbnail((26, 22), Image.NEAREST)
    return fr


def hide():
    """들개 가죽: 네 귀퉁이가 늘어진 갈색 가죽 한 장."""
    im = Image.new('RGBA', (28, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(4, 3), (11, 6), (17, 6), (24, 3), (22, 11), (26, 20), (18, 18), (14, 22), (10, 18), (2, 20), (6, 11)], fill=(122, 82, 46, 255), outline=(40, 24, 12, 255))
    for k in range(14):     # 털 결
        x, y = rng.integers(6, 22), rng.integers(7, 18)
        d.line([(x, y), (x + 2, y + 1)], fill=(92, 58, 30, 255))
    d.line([(14, 7), (14, 19)], fill=(150, 108, 64, 255))
    return im


ICONS = [
    ('iron_ore', lambda: speckle(crop('trees_plants_rocks.png', (64, 295, 89, 320)), (196, 112, 64), 14, 1)),
    ('herb', lambda: crop('trees_plants.png', (231, 264, 252, 287))),
    ('slime_gel', slime_gel),
    ('dog_hide', hide),
    ('vine', lambda: crop('trees_plants.png', (195, 452, 222, 482))),
    ('ring_wood', lambda: crop('trees_plants_rocks.png', (245, 361, 274, 385))),
    ('soft_bark', lambda: crop('trees_plants_rocks.png', (288, 131, 330, 170))),
    ('lava_stone', lambda: speckle(crop('trees_plants_rocks.png', (160, 285, 192, 320)), (255, 214, 90), 12, 2)),
    ('hard_stone', lambda: tint(crop('trees_plants_rocks.png', (64, 295, 89, 320)), (1.35, 1.32, 1.25))),
    ('ruin_shard', lambda: crop('trees_plants_rocks.png', (70, 264, 95, 290))),
    ('iron_ore_hi', lambda: speckle(crop('trees_plants_rocks.png', (64, 295, 89, 320)), (120, 180, 255), 16, 3)),
    ('orichalcum', lambda: speckle(tint(crop('trees_plants_rocks.png', (64, 295, 89, 320)), (1.1, 1.25, 1.0), (10, 20, 0)), (240, 210, 90), 18, 4)),
    ('silver_ore', lambda: speckle(tint(crop('trees_plants_rocks.png', (64, 295, 89, 320)), (1.4, 1.4, 1.45)), (240, 244, 255), 16, 5)),
]
MAT_ICON = {name: i for i, (name, _) in enumerate(ICONS)}


def main():
    cols = 8
    rows = (len(ICONS) + cols - 1) // cols
    sheet = Image.new('RGBA', (cols * CELL, rows * CELL), (0, 0, 0, 0))
    for i, (name, fn) in enumerate(ICONS):
        im = fn()
        x, y = (i % cols) * CELL, (i // cols) * CELL
        sheet.alpha_composite(im, (x + (CELL - im.width) // 2, y + (CELL - im.height) // 2 + 1))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    sheet.save(OUT, optimize=True)
    print('ok', sheet.size, MAT_ICON)


if __name__ == '__main__':
    main()
