"""플레이어 외형 4단계 시험 렌더: 단계마다 정면·비스듬히 대기 + 공격 타격 순간 + 걷기 GIF.
실행: python3 forgotten-forge/tools/lineage/tier_preview.py 출력폴더 knight
"""
import os
import sys
from multiprocessing import Pool

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdf as S           # noqa: E402
import humanoid as Hm     # noqa: E402
import build as B         # noqa: E402
import player_tiers as T  # noqa: E402

W, H, AX, AY = B.CHAR_FRAME
SRC = {c['name']: c for c in Hm.CLASSES}
for lst in T.TIERS.values():
    SRC.update({c['name']: c for c in lst})
BG = (46, 50, 40, 255)


def render(args):
    name, d, anim, f, n = args
    src = SRC[name]
    p = Hm.pose_for(src['weapon'], anim, f, n)
    r = Hm.Rig(p, src['build'])
    it = Hm.body_items(r, p, src['parts'], src['opts'])
    src['gear'](r, p, it)
    M = t = None
    if anim == 'death':
        M, t = Hm.death_xform_forward(f, n)
    if t is not None:
        t = S.rz(180 + d * 45) @ t
    return args, S.render(it, src['mats'], W, H, AX, AY, yaw=d * 45, M_obj=M, t_obj=t)


def main():
    out = sys.argv[1]
    cls = sys.argv[2] if len(sys.argv) > 2 else 'knight'
    names = [cls] + [c['name'] for c in T.TIERS[cls]]
    os.makedirs(out, exist_ok=True)
    poses = [(0, 'idle', 0, 6), (1, 'idle', 0, 6), (7, 'idle', 0, 6), (1, 'attack', Hm.HIT_FRAME, 8)]
    jobs = [(nm,) + ps for nm in names for ps in poses] + [(nm, 1, 'walk', f, 8) for nm in names[1:] for f in range(8)]
    with Pool(os.cpu_count() or 2) as pool:
        res = dict(pool.map(render, jobs))
    sheet = Image.new('RGBA', (W * len(poses), H * len(names)), (0, 0, 0, 0))
    for y, nm in enumerate(names):
        for x, ps in enumerate(poses):
            sheet.alpha_composite(res[(nm,) + ps], (x * W, y * H))
    sheet.save(os.path.join(out, f'{cls}_tiers.png'))
    for nm in names[1:]:
        frames = []
        for f in range(8):
            bg = Image.new('RGBA', (W, H), BG)
            bg.alpha_composite(res[(nm, 1, 'walk', f, 8)])
            frames.append(bg.resize((W * 3, H * 3), Image.NEAREST).convert('P'))
        frames[0].save(os.path.join(out, f'{nm}_walk.gif'), save_all=True, append_images=frames[1:], duration=110, loop=0)
    print('ok', names)


if __name__ == '__main__':
    main()
