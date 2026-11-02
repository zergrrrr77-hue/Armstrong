"""새 몬스터만 렌더링해 기존 lineage-assets/meta.json에 합친다(전체 재빌드 없이).
실행: python3 forgotten-forge/tools/lineage/add_monsters.py goblin skeleton_archer
"""
import io
import json
import os
import sys
from multiprocessing import Pool

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build as B  # noqa: E402


def main(names):
    ents = B.entities()
    tasks = []
    for nm in names:
        for d in range(8):
            for an, n in B.anims_for(ents[nm]):
                for f in range(n):
                    tasks.append((nm, d, an, f, n, None))
    frames = {}
    with Pool(os.cpu_count() or 2) as pool:
        for key, png in pool.imap_unordered(B.render_frame, tasks, chunksize=4):
            frames[key] = Image.open(io.BytesIO(png)).convert('RGBA')
    mp = os.path.join(B.OUT, 'meta.json')
    meta = json.load(open(mp, encoding='utf-8'))
    for nm in names:
        ent = ents[nm]
        anims = B.anims_for(ent)
        W, H, ax, ay = ent['frame']
        ncol = sum(n for _, n in anims)
        sheet = Image.new('RGBA', (W * ncol, H * 8))
        for d in range(8):
            c = 0
            for an, n in anims:
                for f in range(n):
                    sheet.alpha_composite(frames[(nm, d, an, f, 0)], (c * W, d * H))
                    c += 1
        rel = B.save(sheet, 'monsters', f'{nm}.png')
        starts, c = {}, 0
        for an, n in anims:
            starts[an] = [c, n]
            c += n
        meta['monsters'][nm] = dict(label=ent['label'], sheet=rel, fw=W, fh=H, ax=ax, ay=ay, cols=ncol, rows=B.DIRS, anims=starts,
                                    skills=[a for a, _ in anims if a.startswith('skill_')])
        print('added', nm)
    json.dump(meta, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main(sys.argv[1:])
