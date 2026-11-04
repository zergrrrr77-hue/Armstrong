"""플레이어 외형 단계 시트 굽기: 직업마다 2·3·4단계(1단계는 지금의 기본 시트를 그대로 씀).
- player_tiers.py 의 디자인을 기본 직업과 같은 동작·프레임 순서로 모두 굽는다(스킬 동작 포함)
- lineage-assets/characters/<직업>_t<단계>.png + meta.json 의 characters[<직업>_t<단계>]
실행: python3 forgotten-forge/tools/lineage/bake_tiers.py [knight_t2 elf_t3 ...]   (이름을 빼면 9장 모두)
"""
import io
import json
import os
import sys
import time
from multiprocessing import Pool

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build as B          # noqa: E402
import sdf as S            # noqa: E402
import player_tiers as T   # noqa: E402

ENTS = {}
for cls, lst in T.TIERS.items():
    for c in lst:
        ENTS[c['name']] = dict(kind='class', label=c['label'], frame=B.CHAR_FRAME, scale=1.0, src=c, base=cls)


def job(args):
    name, d, anim, f, n = args
    ent = ENTS[name]
    it, mats, M, t = B.build_scene(ent, anim, f, n)
    yaw = d * 45
    if t is not None:
        t = S.rz(180 + yaw) @ t
    W, H, ax, ay = ent['frame']
    im = S.render(it, mats, W, H, ax, ay, yaw=yaw, M_obj=M, t_obj=t, scale=ent['scale'])
    buf = io.BytesIO(); im.save(buf, 'PNG')
    return args, buf.getvalue()


def main():
    names = sys.argv[1:] or [f'{c}_t{n}' for c in ('knight', 'elf', 'mage') for n in (2, 3, 4)]
    mp = os.path.join(B.OUT, 'meta.json')
    for nm in names:
        t0 = time.time()
        base = json.load(open(mp, encoding='utf-8'))['characters'][ENTS[nm]['base']]
        anims = list(base['anims'].items())            # 기본 시트와 같은 열 순서
        tasks = [(nm, d, an, f, n) for d in range(8) for an, (st, n) in anims for f in range(n)]
        with Pool(os.cpu_count() or 2) as pool:
            res = dict((k, Image.open(io.BytesIO(v)).convert('RGBA')) for k, v in pool.imap_unordered(job, tasks, chunksize=4))
        W, H = base['fw'], base['fh']
        sheet = Image.new('RGBA', (W * base['cols'], H * 8))
        for (n2, d, an, f, n), im in res.items():
            st = base['anims'][an][0]
            sheet.alpha_composite(im, ((st + f) * W, d * H))
        rel = B.save(sheet, 'characters', f'{nm}.png')
        meta = json.load(open(mp, encoding='utf-8'))      # 굽는 동안 다른 스크립트가 바꿨을 수 있어 다시 읽음
        meta['characters'][nm] = dict(base, label=ENTS[nm]['label'], sheet=rel, tier_of=ENTS[nm]['base'])
        json.dump(meta, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'tier {nm} {time.time() - t0:.0f}s', flush=True)


if __name__ == '__main__':
    main()
