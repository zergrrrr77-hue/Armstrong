"""NPC 그림을 게임용 시트로 굽는다: lineage-assets/npcs/<이름>.png + meta.json의 npcs 항목.
시트 모양: 가로 = 대기 6장 + 걷기 8장, 세로 = 8방향(몬스터·캐릭터 시트와 같은 규칙).
실행: python3 forgotten-forge/tools/lineage/npc_bake.py [npc_drogan npc_arden ...]   (이름을 빼면 전부)
"""
import io
import json
import os
import sys
from multiprocessing import Pool

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build as B            # noqa: E402
import npc_preview as NP     # noqa: E402  (render 함수 재사용)
import npcs as N             # noqa: E402

ANIMS = [('idle', 6), ('walk', 8)]


def job(args):
    key, im = NP.render(args)
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    return key, buf.getvalue()


def main():
    names = sys.argv[1:] or [n['name'] for n in N.NPCS]
    W, H, AX, AY = B.CHAR_FRAME
    jobs = [(nm, d, an, f, n) for nm in names for d in range(8) for an, n in ANIMS for f in range(n)]
    with Pool(os.cpu_count() or 2) as pool:
        res = {k: Image.open(io.BytesIO(v)).convert('RGBA') for k, v in pool.imap_unordered(job, jobs, chunksize=4)}
    mp = os.path.join(B.OUT, 'meta.json')
    meta = json.load(open(mp, encoding='utf-8'))
    meta.setdefault('npcs', {})
    label = {n['name']: n['label'] for n in N.NPCS}
    ncol = sum(n for _, n in ANIMS)
    for nm in names:
        sheet = Image.new('RGBA', (W * ncol, H * 8))
        for d in range(8):
            c = 0
            for an, n in ANIMS:
                for f in range(n):
                    sheet.alpha_composite(res[(nm, d, an, f, n)], (c * W, d * H))
                    c += 1
        rel = B.save(sheet, 'npcs', f'{nm}.png')
        starts, c = {}, 0
        for an, n in ANIMS:
            starts[an] = [c, n]
            c += n
        meta['npcs'][nm] = dict(label=label[nm], sheet=rel, fw=W, fh=H, ax=AX, ay=AY, cols=ncol, rows=B.DIRS, anims=starts)
        print('npc', nm, sheet.size, flush=True)
    json.dump(meta, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    import gallery
    gallery.write(B.OUT)
    print(gallery.write_game(B.OUT))


if __name__ == '__main__':
    main()
