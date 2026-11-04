"""걷기(달리기) 동작만 다시 구워 기존 시트의 걷기 칸에 덮어쓴다(다른 동작·메타는 그대로).
- 플레이어 3직업 + 사람형 몬스터(같은 보행 곡선 사용)
실행: python3 forgotten-forge/tools/lineage/rebake_walk.py [이름 ...]
"""
import io
import json
import os
import sys
from multiprocessing import Pool

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build as B   # noqa: E402

HUMANOID = ['knight', 'elf', 'mage', 'orc', 'skeleton', 'goblin', 'skeleton_archer', 'boss', 'wb_warlord', 'wb_lich']


def main():
    names = sys.argv[1:] or HUMANOID
    mp = os.path.join(B.OUT, 'meta.json')
    meta = json.load(open(mp, encoding='utf-8'))
    tasks = []
    for nm in names:
        grp = 'characters' if nm in meta['characters'] else 'monsters'
        st, n = meta[grp][nm]['anims']['walk']
        tasks += [(nm, d, 'walk', f, n, None) for d in range(8) for f in range(n)]
    with Pool(os.cpu_count() or 2) as pool:
        res = {k: Image.open(io.BytesIO(v)).convert('RGBA') for k, v in pool.imap_unordered(B.render_frame, tasks, chunksize=4)}
    for nm in names:
        grp = 'characters' if nm in meta['characters'] else 'monsters'
        s = meta[grp][nm]
        path = os.path.join(B.OUT, s['sheet'])
        sheet = Image.open(path).convert('RGBA')
        st, n = s['anims']['walk']
        for d in range(8):
            for f in range(n):
                x, y = (st + f) * s['fw'], d * s['fh']
                sheet.paste((0, 0, 0, 0), (x, y, x + s['fw'], y + s['fh']))
                fr = res[(nm, d, 'walk', f, 0)]
                if fr.size != (s['fw'], s['fh']):
                    sys.exit(f'{nm}: 프레임 크기 다름 {fr.size} != {(s["fw"], s["fh"])}')
                sheet.alpha_composite(fr, (x, y))
        sheet.save(path, optimize=True)
        print('walk', nm, flush=True)


if __name__ == '__main__':
    main()
