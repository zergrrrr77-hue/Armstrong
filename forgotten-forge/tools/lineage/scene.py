"""생성한 에셋으로 쿼터뷰 데모 장면을 조립한다(깊이 정렬). build.py가 마지막에 부른다."""
import os

import numpy as np
from PIL import Image, ImageDraw

TW, TH = 64, 32


def compose(out_dir, meta, name='scene.png', layout=None, ground=None, N=14, light=None):
    sheets = {}

    def sheet(rel):
        if rel not in sheets:
            sheets[rel] = Image.open(os.path.join(out_dir, rel)).convert('RGBA')
        return sheets[rel]

    ox, oy = N * TW // 2, 150
    W, H = N * TW, N * TH + 200
    img = Image.new('RGBA', (W, H), (10, 10, 12, 255))
    tiles = sheet(meta['tiles']['sheet'])
    rows = [r['name'] for r in meta['tiles']['rows']]

    def tile_img(kind, var):
        r = rows.index(kind)
        return tiles.crop((var * TW, r * TH, (var + 1) * TW, (r + 1) * TH))

    def scr(i, j):
        return ox + (i - j) * TW // 2, oy + (i + j) * TH // 2 + TH // 2

    for i in range(N):
        for j in range(N):
            kind, var = (ground or main_ground)(i, j)
            x, y = scr(i, j)
            img.alpha_composite(tile_img(kind, var), (x - TW // 2, y - TH // 2))

    sprites = []   # (깊이, x, y, image)

    def put_prop(nm, i, j, frame=0, dx=0, dy=0):
        p = meta['props'][nm]
        sh = sheet(p['sheet'])
        im = sh.crop((frame * p['fw'], 0, (frame + 1) * p['fw'], p['fh']))
        x, y = scr(i, j)
        sprites.append((y + dy, x - p['ax'] + dx, y - p['ay'] + dy, im))

    def put_actor(group, nm, i, j, d='S', anim='idle', f=0, dx=0, dy=0, sheet_override=None):
        a = meta[group][nm]
        sh = sheet(a['sheet'])
        r = a['rows'].index(d)
        c = a['anims'][anim][0] + f
        im = sh.crop((c * a['fw'], r * a['fh'], (c + 1) * a['fw'], (r + 1) * a['fh']))
        x, y = scr(i, j)
        # 발밑 그림자
        sd = Image.new('RGBA', (30, 12), (0, 0, 0, 0))
        ImageDraw.Draw(sd).ellipse([0, 0, 29, 11], fill=(0, 0, 0, 90))
        img.alpha_composite(sd, (x + dx - 15, y + dy - 6))
        sprites.append((y + dy + 0.5, x - a['ax'] + dx, y - a['ay'] + dy, im))

    (layout or main_layout)(put_prop, put_actor)

    for _, x, y, im in sorted(sprites, key=lambda s: s[0]):
        img.alpha_composite(im, (int(x), int(y)))

    if light:   # 던전: 전체를 어둡게 + 불빛 주위만 밝게
        dark = Image.new('RGBA', (W, H), (4, 3, 8, light['dark']))
        mask = Image.new('L', (W, H), 255)
        md = ImageDraw.Draw(mask)
        for (i, j, r) in light['lamps']:
            x, y = scr(i, j)
            for k in range(r, 0, -4):
                md.ellipse([x - k, y - 30 - k * 0.6, x + k, y - 30 + k * 0.6], fill=int(255 * (k / r) ** 1.4))
        dark.putalpha(Image.fromarray((np.array(mask, float) / 255 * light['dark']).astype('uint8')))
        img.alpha_composite(dark)
        glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        for (i, j, r) in light['lamps']:
            x, y = scr(i, j)
            for k in range(r // 2, 0, -3):
                gd.ellipse([x - k, y - 30 - k * 0.6, x + k, y - 30 + k * 0.6], fill=(255, 140, 50, int(30 * (1 - k / (r / 2)))))
        img.alpha_composite(glow)

    # 어두운 비네트(리니지풍 분위기)
    vg = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(vg)
    for k in range(60):
        a = int(150 * (1 - k / 60) ** 2)
        d.rectangle([k * 2, k * 2, W - 1 - k * 2, H - 1 - k * 2], outline=a)
    dark = Image.new('RGBA', (W, H), (6, 5, 8, 255))
    dark.putalpha(vg)
    img.alpha_composite(dark)
    img = img.crop((0, 40, W, H - 30))
    img.save(os.path.join(out_dir, name), optimize=True)
    img.resize((img.width * 2, img.height * 2), Image.NEAREST).save(os.path.join(out_dir, name.replace('.png', '@2x.png')), optimize=True)
    return name


def main_ground(i, j):
    kind = 'grass'
    if abs(i - j - 1) <= 0 or (i - j - 1) == 1 and (i + j) % 3 == 0:
        kind = 'dirt'
    if i <= 3 and j <= 5:
        kind = 'cobble'
    if i >= 10 and j >= 9:
        kind = 'swamp'
    if i >= 11 and j >= 11:
        kind = 'water'
    if j >= 11 and i <= 4:
        kind = 'dungeon' if (i + j) % 5 == 0 else 'grass'
    var = (i * 7 + j * 13) % 4
    if kind == 'water':
        var = (i + j) % 4
    return kind, var


def main_layout(put_prop, put_actor):
    for j in range(0, 6):
        if j != 3:
            put_prop('wall', 0, j)
    put_prop('gate', 0, 3)
    put_prop('tower', 0, 6)
    put_prop('torch', 2, 2, frame=1)
    put_prop('torch', 2, 4, frame=3)
    put_prop('banner_pole', 1, 5, dx=-6)
    put_prop('stall', 2, 0, dx=10)
    put_prop('lamp_post', 4, 4, dx=-10, frame=1)
    put_prop('house', 3, 9)
    put_prop('forge', 2, 7, dx=-4, frame=2)
    put_prop('anvil', 3, 7, dx=14, dy=4)
    put_prop('firewood', 1, 9, dx=-8)
    put_prop('well', 5, 3)
    put_prop('trough', 6, 2, dx=6)
    put_prop('cart', 7, 1)
    put_prop('haybale', 8, 3, dx=-6)
    put_prop('barrel', 4, 9, dx=-10)
    put_prop('crate', 4, 10, dx=-4)
    put_prop('notice_board', 6, 7, dx=10)
    put_prop('fence', 5, 8)
    put_prop('fence', 5, 9)
    put_prop('planter', 2, 10, dx=12, dy=4)
    for (i, j, nm) in ((8, 1, 'oak'), (10, 2, 'pine'), (12, 1, 'pine'), (12, 4, 'oak'), (13, 7, 'dead_tree'),
                       (7, 12, 'pine'), (9, 13, 'dead_tree'), (1, 13, 'pine')):
        put_prop(nm, i, j)
    put_prop('rock_big', 10, 6)
    put_prop('rock_small', 7, 4, dx=8)
    put_prop('bush', 9, 4)
    put_prop('bush', 6, 11)
    put_prop('campfire', 8, 8, frame=2)
    put_prop('tent', 9, 9)
    put_prop('grave', 2, 12)
    put_prop('cross_grave', 3, 12, dx=10)
    put_prop('grave', 4, 13)
    put_prop('pillar', 1, 11)
    put_prop('bones', 3, 11, dx=-8)
    put_prop('crystal', 11, 3)

    put_actor('characters', 'knight', 6, 4, 'SE', 'attack', 4)
    put_actor('monsters', 'orc', 7, 5, 'NW', 'attack', 2)
    put_actor('characters', 'lord', 5, 5, 'E', 'idle', 0)
    put_actor('characters', 'elf', 4, 6, 'SE', 'attack', 4, dx=8)
    put_actor('characters', 'mage', 5, 2, 'SE', 'attack', 4)
    put_actor('monsters', 'wolf', 8, 6, 'W', 'attack', 4, dx=6)
    put_actor('monsters', 'skeleton', 4, 11, 'N', 'walk', 1)
    put_actor('monsters', 'skeleton', 5, 12, 'NW', 'idle', 0, dx=12)
    put_actor('monsters', 'ooze', 10, 10, 'NW', 'idle', 0)
    put_actor('monsters', 'spider', 11, 6, 'W', 'walk', 2)
    put_actor('monsters', 'orc', 9, 7, 'NW', 'death', 5)
    put_actor('monsters', 'boss', 8, 11, 'NW', 'idle', 0)


def dungeon_ground(i, j):
    v = (i * 5 + j * 11) % 4
    if (i * 3 + j * 7) % 5 in (0, 3) or (i > 7 and j > 6):
        return 'dungeon_wet', v
    return 'dungeon', v


def dungeon_layout(put_prop, put_actor):
    for j in range(0, 12):
        if j == 6:
            put_prop('portcullis', 0, 6)
        elif j != 5 and j != 7:
            put_prop('dungeon_wall', 0, j)
    put_prop('wall_torch', 1, 3, frame=0, dx=-10)
    put_prop('wall_torch', 1, 9, frame=2, dx=-10)
    for (i, j) in ((3, 2), (3, 10), (8, 2), (8, 10)):
        put_prop('chain_pillar', i, j)
    put_prop('altar', 2, 6, frame=1)
    put_prop('sarcophagus', 5, 1)
    put_prop('chest_open', 6, 10, dx=6)
    put_prop('chest', 10, 8)
    put_prop('cage', 10, 3)
    put_prop('spikes', 7, 6, dx=-12)
    put_prop('bone_pile', 9, 5)
    put_prop('stairs', 11, 10)
    put_prop('bones', 4, 8)
    put_prop('torch', 6, 4, frame=1)
    put_prop('torch', 6, 8, frame=3)

    put_actor('monsters', 'boss', 4, 6, 'SE', 'attack', 2)
    put_actor('characters', 'knight', 6, 7, 'NW', 'attack', 4)
    put_actor('characters', 'mage', 8, 7, 'NW', 'attack', 3)
    put_actor('characters', 'elf', 7, 9, 'NW', 'attack', 4)
    put_actor('characters', 'lord', 7, 5, 'NW', 'hurt', 0)
    put_actor('monsters', 'skeleton', 5, 3, 'SE', 'walk', 3)
    put_actor('monsters', 'skeleton', 9, 9, 'NW', 'death', 5)
    put_actor('monsters', 'spider', 9, 2, 'W', 'idle', 0)


def compose_dungeon(out_dir, meta):
    return compose(out_dir, meta, 'scene_dungeon.png', layout=dungeon_layout, ground=dungeon_ground, N=12,
                   light=dict(dark=150, lamps=[(1, 3, 120), (1, 9, 120), (2, 6, 110), (6, 4, 120), (6, 8, 120), (6, 10, 70)]))
