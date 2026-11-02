"""새 몬스터·소품만 렌더링해 기존 lineage-assets/meta.json에 합치고 게임(index.html)을 다시 만든다(전체 재빌드 없이).
실행: python3 forgotten-forge/tools/lineage/add_assets.py --monsters wb_warlord wb_lich --props shrine deity
"""
import argparse
import io
import json
import os
import sys
from multiprocessing import Pool

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build as B   # noqa: E402  (worlds 등록 포함)
import field as F   # noqa: E402
import sdf as S     # noqa: E402
import gallery      # noqa: E402


def render_prop(args):
    name, f = args
    d = F.PROPS[name]
    W, H, ax, ay = d['frame']
    im = S.render(d['fn'](f), F.PM, W, H, ax, ay, yaw=d['yaw'] + 180, scale=d['scale'])
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    return (name, f), buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--monsters', nargs='*', default=[])
    ap.add_argument('--props', nargs='*', default=[])
    a = ap.parse_args()
    ents = B.entities()
    mp = os.path.join(B.OUT, 'meta.json')
    meta = json.load(open(mp, encoding='utf-8'))
    with Pool(os.cpu_count() or 2) as pool:
        if a.monsters:
            tasks = [(nm, d, an, f, n, None) for nm in a.monsters for d in range(8) for an, n in B.anims_for(ents[nm]) for f in range(n)]
            print(f'몬스터 프레임 {len(tasks)}개', flush=True)
            frames = {}
            for k, (key, png) in enumerate(pool.imap_unordered(B.render_frame, tasks, chunksize=2)):
                frames[key] = Image.open(io.BytesIO(png)).convert('RGBA')
                if (k + 1) % 50 == 0:
                    print(f'  {k + 1}/{len(tasks)}', flush=True)
            for nm in a.monsters:
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
                                            skills=[x for x, _ in anims if x.startswith('skill_')])
                seq = [frames[(nm, 1, 'walk', f, 0)] for f in range(dict(anims)['walk'])] + [frames[(nm, 1, 'attack', f, 0)] for f in range(dict(anims)['attack'])]
                B.gif(seq, os.path.join('preview', f'{nm}.gif'), 110)
                print('monster', nm, sheet.size, flush=True)
        if a.props:
            tasks = [(nm, f) for nm in a.props for f in range(F.PROPS[nm]['frames'])]
            imgs = {}
            for key, png in pool.imap_unordered(render_prop, tasks):
                imgs[key] = Image.open(io.BytesIO(png)).convert('RGBA')
            for nm in a.props:
                d = F.PROPS[nm]
                W, H, ax, ay = d['frame']
                ims = [imgs[(nm, f)] for f in range(d['frames'])]
                bbs = [im.getbbox() for im in ims]
                x0 = max(0, min(b[0] for b in bbs) - 1)
                y0 = max(0, min(b[1] for b in bbs) - 1)
                x1 = min(W, max(b[2] for b in bbs) + 1)
                y1 = min(H, max(b[3] for b in bbs) + 1)
                fw, fh = x1 - x0, y1 - y0
                sheet = Image.new('RGBA', (fw * len(ims), fh))
                for k, im in enumerate(ims):
                    sheet.alpha_composite(im.crop((x0, y0, x1, y1)), (k * fw, 0))
                meta['props'][nm] = dict(label=d['label'], group=d.get('group') or '기타', sheet=B.save(sheet, 'field', 'props', f'{nm}.png'),
                                         fw=fw, fh=fh, ax=ax - x0, ay=ay - y0, frames=len(ims))
                print('prop', nm, sheet.size, flush=True)
    json.dump(meta, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    gallery.write(B.OUT)
    print(gallery.write_game(B.OUT))


if __name__ == '__main__':
    main()
