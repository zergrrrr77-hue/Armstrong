"""NPC 시험 렌더: 플레이어 기사와 나란히, 8방향 대기 1프레임 + 걷기 8프레임을 한 장으로 만든다.
실행: python3 forgotten-forge/tools/lineage/npc_preview.py [출력 폴더]
"""
import os
import sys
from multiprocessing import Pool

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdf as S        # noqa: E402
import humanoid as Hm  # noqa: E402
import build as B      # noqa: E402
import npcs as N       # noqa: E402

W, H, AX, AY = B.CHAR_FRAME
SRC = {c['name']: c for c in Hm.CLASSES + N.NPCS}


def render(args):
    name, d, anim, f, n = args
    src = SRC[name]
    p = Hm.pose_for(src['weapon'], anim, f, n)       # 플레이어와 같은 동작 곡선
    r = Hm.Rig(p, src['build'])
    it = Hm.body_items(r, p, src['parts'], src['opts'])
    src['gear'](r, p, it)
    im = S.render(it, src['mats'], W, H, AX, AY, yaw=d * 45)
    return args, im


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    jobs = [('knight', 0, 'idle', 0, 6)] + [('npc_drogan', d, 'idle', 0, 6) for d in range(8)] + \
           [('npc_drogan', 1, 'walk', f, 8) for f in range(8)]
    with Pool(os.cpu_count() or 2) as pool:
        res = dict(pool.map(render, jobs))
    # 1줄: 기사(크기 비교) + 드로간 8방향 / 2줄: 드로간 걷기 8프레임
    sheet = Image.new('RGBA', (W * 9, H * 2), (46, 50, 40, 255))
    for i, j in enumerate(jobs[:9]):
        sheet.alpha_composite(res[j], (i * W, 0))
    for i, j in enumerate(jobs[9:]):
        sheet.alpha_composite(res[j], ((i + 1) * W, H))
    sheet.save(os.path.join(out, 'drogan_sheet_raw.png'))
    frames = [res[j].copy() for j in jobs[9:]]
    frames[0].save(os.path.join(out, 'drogan_walk.gif'), save_all=True, append_images=frames[1:], duration=110, loop=0, disposal=2)
    print('ok', sheet.size)


if __name__ == '__main__':
    main()
