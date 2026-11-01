"""생성한 에셋으로 쿼터뷰 데모 장면을 조립한다(깊이 정렬). build.py가 마지막에 부른다."""
import os

from PIL import Image, ImageDraw

TW, TH = 64, 32


def compose(out_dir, meta, name='scene.png'):
    sheets = {}

    def sheet(rel):
        if rel not in sheets:
            sheets[rel] = Image.open(os.path.join(out_dir, rel)).convert('RGBA')
        return sheets[rel]

    N = 14
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

    # 지면 배치
    for i in range(N):
        for j in range(N):
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

    # 성벽(뒤쪽 j축을 따라) + 성탑 + 성문
    for j in range(0, 6):
        if j == 3:
            continue
        put_prop('wall', 0, j)
    put_prop('gate', 0, 3, dx=0)
    put_prop('tower', 0, 6)
    put_prop('torch', 2, 2, frame=1)
    put_prop('torch', 2, 4, frame=3)
    put_prop('house', 3, 9)
    put_prop('well', 5, 3)
    put_prop('barrel', 2, 7)
    put_prop('crate', 2, 8, dx=6)
    put_prop('signpost', 6, 6, dx=10)
    put_prop('fence', 5, 8)
    put_prop('fence', 5, 9)
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

    # 인물·몬스터
    put_actor('characters', 'knight', 6, 4, 'SE', 'attack', 2)
    put_actor('monsters', 'orc', 7, 5, 'NW', 'attack', 1)
    put_actor('characters', 'lord', 5, 5, 'E', 'idle', 0)
    put_actor('characters', 'elf', 4, 6, 'SE', 'attack', 2, dx=8)
    put_actor('characters', 'mage', 5, 2, 'SE', 'attack', 2)
    put_actor('monsters', 'wolf', 8, 6, 'W', 'attack', 2, dx=6)
    put_actor('monsters', 'skeleton', 4, 11, 'N', 'walk', 1)
    put_actor('monsters', 'skeleton', 5, 12, 'NW', 'idle', 0, dx=12)
    put_actor('monsters', 'ooze', 10, 10, 'NW', 'idle', 0)
    put_actor('monsters', 'spider', 11, 6, 'W', 'walk', 2)
    put_actor('monsters', 'orc', 9, 7, 'NW', 'death', 3)
    put_actor('monsters', 'boss', 8, 11, 'NW', 'idle', 0)

    for _, x, y, im in sorted(sprites, key=lambda s: s[0]):
        img.alpha_composite(im, (int(x), int(y)))

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
