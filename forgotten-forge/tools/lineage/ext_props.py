"""사용자가 올린 도트 그림(ext-src/*.png)에서 소품을 잘라 게임 소품으로 등록한다.
- 잘라낸 그림은 게임의 어두운 색감에 맞게 색을 조금 낮추고(밝기·채도), lineage-assets/field/props/ext_*.png 로 저장
- meta.json 의 props 에 등록(그룹 '외부 에셋'). 막힘 반지름은 게임 코드의 BLOCK 표에서 정한다.
실행: python3 forgotten-forge/tools/lineage/ext_props.py
출처: ext-src/CREDITS.md 참고(공개·배포 전에 각 파일의 사용 조건을 확인할 것)
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
SRC = os.path.join(ROOT, 'ext-src')
OUT = os.path.join(ROOT, 'lineage-assets')

# 이름, 표시 이름, 원본 파일, 자를 상자(x0, y0, x1, y1), 배율, 그룹
CROPS = [
    ('ext_boulders', '이끼 낀 큰 바위', 'trees_plants_rocks.png', (18, 1, 125, 93), 0.75, '폐허'),
    ('ext_cairns', '돌탑', 'trees_plants_rocks.png', (5, 98, 93, 158), 0.75, '폐허'),
    ('ext_dolmen', '고인돌', 'trees_plants_rocks.png', (5, 160, 125, 253), 0.85, '폐허'),
    ('ext_log', '쓰러진 통나무', 'trees_plants_rocks.png', (288, 131, 390, 218), 0.7, '폐허'),
    ('ext_log_rune', '문양 새긴 통나무', 'trees_plants_rocks.png', (288, 224, 390, 296), 0.7, '폐허'),
    ('ext_grave', '이름 지워진 묘비', 'trees_plants_rocks.png', (2, 257, 26, 289), 1.0, '폐허'),
    ('ext_grave_broken', '깨진 묘비', 'trees_plants_rocks.png', (70, 264, 95, 290), 1.0, '폐허'),
    ('ext_stump', '그루터기', 'trees_plants_rocks.png', (245, 361, 274, 385), 1.0, '숲'),
    ('ext_trough', '물 여물통', 'trees_plants_rocks.png', (71, 340, 126, 376), 0.8, '농장'),
    ('ext_flatstones', '흩어진 바닥돌', 'trees_plants_rocks.png', (191, 287, 283, 353), 0.8, '폐허'),
    ('ext_tree_a', '옅은 잎 나무', 'trees_plants_rocks.png', (418, 0, 508, 125), 1.0, '숲'),
    ('ext_tree_b', '작은 굽은 나무', 'trees_plants_rocks.png', (330, 317, 386, 399), 1.0, '숲'),
    ('ext_bush_aut', '단풍 덤불', 'trees_plants_rocks.png', (326, 422, 408, 500), 0.7, '숲'),
    ('ext_deadtree_big', '뒤틀린 고목', 'trees_plants.png', (2, 2, 159, 189), 0.75, '폐허'),
    ('ext_deadtree_s', '검은 마른 나무', 'trees_plants.png', (417, 256, 479, 318), 1.0, '폐허'),
    ('ext_scarecrow', '허수아비', 'trees_plants.png', (257, 322, 286, 383), 0.9, '농장'),
    ('ext_pumpkins', '호박 더미', 'trees_plants.png', (230, 327, 258, 380), 0.9, '농장'),
    ('ext_well', '옛 우물', 'town.png', (70, 452, 120, 508), 0.9, '폐허'),
    ('ext_fountain', '말라붙은 분수', 'town.png', (2, 452, 64, 511), 0.9, '폐허'),
    ('ext_statue', '부서진 석상', 'town.png', (482, 257, 511, 320), 0.9, '폐허'),
    ('ext_pedestal', '빈 받침돌', 'town.png', (320, 452, 350, 510), 0.8, '폐허'),
]


def grade(im):
    """게임 색감 맞추기: 밝기 0.8배, 채도 0.82배, 아주 살짝 푸른 그늘."""
    a = np.asarray(im).astype(float)
    rgb = a[..., :3]
    gray = rgb.mean(axis=2, keepdims=True)
    rgb = gray + (rgb - gray) * 0.82
    rgb = rgb * 0.8 + np.array([0, 2, 6])
    a[..., :3] = np.clip(rgb, 0, 255)
    return Image.fromarray(a.astype(np.uint8))


def main():
    mp = os.path.join(OUT, 'meta.json')
    meta = json.load(open(mp, encoding='utf-8'))
    os.makedirs(os.path.join(OUT, 'field', 'props'), exist_ok=True)
    for name, label, fn, box, sc, group in CROPS:
        src = Image.open(os.path.join(SRC, fn)).convert('RGBA')
        im = src.crop(box)
        bb = im.getbbox()
        if not bb:
            sys.exit(f'{name}: 상자 안에 그림이 없음 {box}')
        im = im.crop(bb)
        if sc != 1.0:   # 도트가 뭉개지지 않게 가장 가까운 점으로 줄임
            im = im.resize((max(1, round(im.width * sc)), max(1, round(im.height * sc))), Image.NEAREST)
        im = grade(im)
        # 아래쪽 1/6 지점을 땅에 닿는 곳으로 본다(바닥 그림자 포함 대비)
        ax, ay = im.width // 2, im.height - max(2, im.height // 10)
        rel = os.path.join('field', 'props', f'{name}.png')
        im.save(os.path.join(OUT, rel), optimize=True)
        meta['props'][name] = dict(label=label, group=group, sheet=rel.replace(os.sep, '/'), fw=im.width, fh=im.height, ax=ax, ay=ay, frames=1, ext=fn)
        print(name, im.size)
    json.dump(meta, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    sys.path.insert(0, HERE)
    import gallery
    gallery.write(OUT)
    print(gallery.write_game(OUT))


if __name__ == '__main__':
    main()
