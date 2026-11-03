"""NPC 시험 렌더: NPC마다 8방향 대기 1프레임 + 걷기 8프레임(GIF)을 만든다.
실행: python3 forgotten-forge/tools/lineage/npc_preview.py 출력폴더 [npc_drogan npc_arden ...]
      (이름을 빼면 npcs.NPCS 전부)
"""
import os
import sys
from multiprocessing import Pool

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdf as S        # noqa: E402
import humanoid as Hm  # noqa: E402
import build as B      # noqa: E402
import npcs as N       # noqa: E402

W, H, AX, AY = B.CHAR_FRAME
SRC = {c['name']: c for c in Hm.CLASSES + N.NPCS}
BG = (46, 50, 40, 255)


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
    names = sys.argv[2:] or [n['name'] for n in N.NPCS]
    for nm in names:
        if nm not in SRC:
            sys.exit(f'모르는 NPC 이름: {nm} (가능: {", ".join(SRC)})')
    os.makedirs(out, exist_ok=True)
    jobs = [(nm, d, 'idle', 0, 6) for nm in ['knight'] + names for d in range(8)] + \
           [(nm, 1, 'walk', f, 8) for nm in names for f in range(8)]
    with Pool(os.cpu_count() or 2) as pool:
        res = dict(pool.map(render, jobs))
    rows = ['knight'] + names
    sheet = Image.new('RGBA', (W * 8, H * len(rows)), (0, 0, 0, 0))   # 투명 바탕: 합성에 바로 쓰기
    for y, nm in enumerate(rows):
        for d in range(8):
            sheet.alpha_composite(res[(nm, d, 'idle', 0, 6)], (d * W, y * H))
    sheet.save(os.path.join(out, 'npc_idle_8dir.png'))
    for nm in names:
        frames = []
        for f in range(8):
            bg = Image.new('RGBA', (W, H), BG)
            bg.alpha_composite(res[(nm, 1, 'walk', f, 8)])
            frames.append(bg.resize((W * 3, H * 3), Image.NEAREST).convert('P'))
        frames[0].save(os.path.join(out, f'{nm}_walk.gif'), save_all=True, append_images=frames[1:], duration=110, loop=0)
    print('ok', rows)


if __name__ == '__main__':
    main()
