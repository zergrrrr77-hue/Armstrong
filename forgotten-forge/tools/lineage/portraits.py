"""직업 초상화(상태창 동그라미용): 캐릭터를 크게 확대해 머리·어깨만 다시 그린다(같은 그림 공장, 같은 옷·색).
- 살짝 비스듬히(정면에서 25°) 바라보는 대기 자세, 4배 크기로 그린 뒤 머리 둘레를 잘라 96×96 으로
- lineage-assets/ui/portrait_<직업>.png + meta.json 의 portraits 항목
실행: python3 forgotten-forge/tools/lineage/portraits.py
"""
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build as B      # noqa: E402
import sdf as S        # noqa: E402

K = 4            # 확대 배율(도트 4배 촘촘히)
OUT_SIZE = 96


def portrait(name):
    ents = B.entities()
    if name not in ents:                       # 외형 단계(knight_t2 등)
        import bake_tiers as BT
        ents = BT.ENTS
    ent = ents[name]
    it, mats, M, t = B.build_scene(ent, 'idle', 0, 6)
    W, H, ax, ay = ent['frame']
    im = S.render(it, mats, W * K, H * K, ax * K, ay * K, yaw=-25, scale=ent['scale'] * K, shadows=False)
    bb = im.getbbox()                      # 캐릭터 전체 범위
    x0, y0, x1, y1 = bb
    hgt = y1 - y0
    import numpy as np
    a = np.asarray(im)[..., 3]
    head = a[y0:y0 + int(hgt * 0.16)] > 40          # 머리 부분(위쪽 16%)의 가운데에 맞춤
    xs = np.nonzero(head.any(axis=0))[0]
    # 지팡이 끝 같은 가는 물체는 빼고, 가장 넓게 이어진 덩어리(머리)의 가운데
    runs, s0 = [], None
    cols = head.any(axis=0)
    for x in range(len(cols) + 1):
        on = x < len(cols) and cols[x]
        if on and s0 is None:
            s0 = x
        if not on and s0 is not None:
            runs.append((x - s0, s0, x)); s0 = None
    cx = (max(runs)[1] + max(runs)[2]) // 2 if runs else (x0 + x1) // 2
    side = int(hgt * 0.38)                 # 머리·어깨가 들어가는 정사각형
    top = y0 - int(side * 0.10)
    box = (cx - side // 2, top, cx + side // 2, top + side)
    crop = im.crop(box).resize((OUT_SIZE, OUT_SIZE), Image.LANCZOS)
    return crop


def main():
    out_dir = os.path.join(B.OUT, 'ui')
    os.makedirs(out_dir, exist_ok=True)
    mp = os.path.join(B.OUT, 'meta.json')
    meta = json.load(open(mp, encoding='utf-8'))
    meta['portraits'] = {}
    for name in [c + s for c in ('knight', 'elf', 'mage') for s in ('', '_t2', '_t3', '_t4')]:
        im = portrait(name)
        rel = f'ui/portrait_{name}.png'
        im.save(os.path.join(B.OUT, rel), optimize=True)
        meta['portraits'][name] = rel
        print(name, im.size, flush=True)
    cur = json.load(open(mp, encoding='utf-8'))      # 다른 스크립트가 그사이 바꾼 내용 보존
    cur['portraits'] = meta['portraits']
    json.dump(cur, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
