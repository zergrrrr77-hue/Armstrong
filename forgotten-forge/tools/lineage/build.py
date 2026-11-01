"""리니지풍 에셋 전체 생성.

실행:  python3 forgotten-forge/tools/lineage/build.py            (전체, 4코어 기준 약 3~5분)
       python3 forgotten-forge/tools/lineage/build.py --quick    (캐릭터·몬스터를 남쪽 방향만, 빠른 확인용)
출력:  forgotten-forge/lineage-assets/
"""
import argparse
import io
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import sdf as S          # noqa: E402
import humanoid as Hm    # noqa: E402
import monsters as Mo    # noqa: E402
import field as F        # noqa: E402
import items as I        # noqa: E402

OUT = os.path.normpath(os.path.join(HERE, '..', '..', 'lineage-assets'))
DIRS = ['S', 'SE', 'E', 'NE', 'N', 'NW', 'W', 'SW']      # yaw = 45° × 번호
CHAR_FRAME = (112, 104, 56, 70)
NA = dict(Hm.ANIMS)


def entities():
    ents = {}
    for cl in Hm.CLASSES:
        ents[cl['name']] = dict(kind='class', label=cl['label'], frame=CHAR_FRAME, scale=1.0, src=cl)
    for mo in Mo.MONSTERS:
        ents[mo['name']] = dict(kind='monster', label=mo['label'], frame=mo['frame'], scale=mo.get('scale', 1.0), src=mo)
    return ents


def anims_for(ent):
    if ent['kind'] == 'class' and ent['src']['weapon'] == 'blade':
        return Hm.ANIMS + Hm.SKILLS
    return Hm.ANIMS


def build_scene(ent, anim, f, n):
    src = ent['src']
    if ent['kind'] == 'class':
        p = Hm.skill_pose(anim, f, n) if anim.startswith('skill_') else Hm.pose_for(src['weapon'], anim, f, n)
        r = Hm.Rig(p, src['build'])
        it = Hm.body_items(r, p, src['parts'], src['opts'])
        src['gear'](r, p, it)
        M = t = None
        if anim == 'death':
            M, t = (Hm.death_xform_forward if src['weapon'] == 'blade' else Hm.death_xform)(f, n)
        elif anim.startswith('skill_'):
            M, t = Hm.skill_xform(anim, f, n)
        return it, src['mats'], M, t
    it, M, t = src['build'](anim, f, n)
    return it, src['mats'], M, t


def render_frame(args):
    name, d, anim, f, n, enchant = args
    ent = entities()[name]
    it, mats, M, t = build_scene(ent, anim, f, n)
    yaw = d * 45
    if t is not None:
        t = S.rz(180 + yaw) @ t
    W, H, ax, ay = ent['frame']
    if enchant is None:
        im = S.render(it, mats, W, H, ax, ay, yaw=yaw, M_obj=M, t_obj=t, scale=ent['scale'])
    else:
        im, _, _, ids = S.render(it, mats, W, H, ax, ay, yaw=yaw, M_obj=M, t_obj=t, scale=ent['scale'], return_buffers=True)
        tagged = np.array([x.tag == 'blade' for x in it])
        mask = np.zeros(ids.shape, bool)
        ok = ids >= 0
        mask[ok] = tagged[ids[ok]]
        im = S.glow(im, color=enchant[1], radius=enchant[2], strength=enchant[3], mask=mask)
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    return (name, d, anim, f, enchant[0] if enchant else 0), buf.getvalue()


def trim(im, pad=1):
    bb = im.getbbox()
    if not bb:
        return im, (0, 0)
    x0, y0, x1, y1 = bb
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(im.width, x1 + pad), min(im.height, y1 + pad)
    return im.crop((x0, y0, x1, y1)), (x0, y0)


def save(im, *path):
    p = os.path.join(OUT, *path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    im.save(p, optimize=True)
    return os.path.relpath(p, OUT)


def gif(frames, path, dur=120, bg=(46, 50, 40), scale=2):
    out = []
    for fr in frames:
        b = Image.new('RGBA', fr.size, bg + (255,))
        b.alpha_composite(fr)
        out.append(b.convert('RGB').resize((fr.width * scale, fr.height * scale), Image.NEAREST))
    p = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    out[0].save(p, save_all=True, append_images=out[1:], duration=dur, loop=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--only', nargs='*')
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 2)
    args = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    ents = entities()
    names = [n for n in ents if not args.only or n in args.only]
    dirs = [0] if args.quick else list(range(8))
    anims = Hm.ANIMS
    tasks = []
    for nm in names:
        for d in dirs:
            for an, n in anims_for(ents[nm]):
                for f in range(n):
                    tasks.append((nm, d, an, f, n, None))
    # 강화 무기 쇼케이스: 기사 대기(남쪽) × 강화 단계
    for e in I.ENCHANTS[1:]:
        for f in range(NA['idle']):
            tasks.append(('knight', 0, 'idle', f, NA['idle'], e))
    print(f'프레임 {len(tasks)}개 렌더링 ({args.jobs}코어)…', flush=True)
    frames = {}
    with Pool(args.jobs) as pool:
        for k, (key, png) in enumerate(pool.imap_unordered(render_frame, tasks, chunksize=4)):
            frames[key] = Image.open(io.BytesIO(png)).convert('RGBA')
            if (k + 1) % 200 == 0:
                print(f'  {k + 1}/{len(tasks)}  {time.time() - t0:.0f}s', flush=True)

    meta = dict(version=1, style='리니지풍 프리렌더 도트 (쿼터뷰 30°, 2:1 타일)', tile=dict(w=F.TW, h=F.TH, world=F.CELL),
                dirs=DIRS, dir_note='행 = 방향(yaw 45°씩: S, SE, E, NE, N, NW, W, SW). 좌우 반전 없이 8방향을 모두 렌더링.',
                anims=[dict(name=a, frames=n) for a, n in Hm.ANIMS], hit_frame=Hm.HIT_FRAME, skill_hit=Hm.SKILL_HIT, characters={}, monsters={}, props={}, tiles={}, items={})
    for nm in names:
        ent = ents[nm]
        anims = anims_for(ent)
        ncol = sum(n for _, n in anims)
        W, H, ax, ay = ent['frame']
        sheet = Image.new('RGBA', (W * ncol, H * len(dirs)))
        for ri, d in enumerate(dirs):
            c = 0
            for an, n in anims:
                for f in range(n):
                    sheet.alpha_composite(frames[(nm, d, an, f, 0)], (c * W, ri * H))
                    c += 1
        group = 'characters' if ent['kind'] == 'class' else 'monsters'
        rel = save(sheet, group, f'{nm}.png')
        starts, c = {}, 0
        for an, n in anims:
            starts[an] = [c, n]
            c += n
        meta[group][nm] = dict(label=ent['label'], sheet=rel, fw=W, fh=H, ax=ax, ay=ay, cols=ncol,
                               rows=[DIRS[d] for d in dirs], anims=starts,
                               skills=[a for a, _ in anims if a.startswith('skill_')])
        # 미리보기 GIF (남동 방향 또는 첫 방향의 걷기·공격)
        dsel = 1 if 1 in dirs else dirs[0]
        seq = [frames[(nm, dsel, 'walk', f, 0)] for f in range(NA['walk'])] + [frames[(nm, dsel, 'attack', f, 0)] for f in range(NA['attack'])]
        gif(seq, os.path.join('preview', f'{nm}.gif'), 110)

    # 강화 쇼케이스
    ek = Image.new('RGBA', (CHAR_FRAME[0] * 5, CHAR_FRAME[1]))
    ek.alpha_composite(frames[('knight', 0, 'idle', 0, 0)], (0, 0))
    for j, e in enumerate(I.ENCHANTS[1:]):
        ek.alpha_composite(frames[('knight', 0, 'idle', 0, e[0])], ((j + 1) * CHAR_FRAME[0], 0))
    meta['enchant_showcase'] = dict(sheet=save(ek, 'characters', 'knight_enchant.png'), fw=CHAR_FRAME[0], fh=CHAR_FRAME[1],
                                    levels=[0] + [e[0] for e in I.ENCHANTS[1:]])
    for e in I.ENCHANTS[1:]:
        gif([frames[('knight', 0, 'idle', f, e[0])] for f in range(NA['idle'])], os.path.join('preview', f'knight_plus{e[0]}.gif'), 180)
    print(f'캐릭터·몬스터 완료 {time.time() - t0:.0f}s', flush=True)

    # ── 스킬 이펙트 (가산 혼합용 2층 시트: 0행 under, 1행 over)
    import effects as EF
    meta['effects'] = {}
    for key, e in EF.build_all().items():
        n = len(e['under'])
        sh = Image.new('RGBA', (e['fw'] * n, e['fh'] * 2))
        for i in range(n):
            sh.alpha_composite(e['under'][i], (i * e['fw'], 0))
            sh.alpha_composite(e['over'][i], (i * e['fw'], e['fh']))
        meta['effects'][key] = dict(label=e['label'], sheet=save(sh, 'effects', f'{key}.png'), fw=e['fw'], fh=e['fh'],
                                    ax=e['ax'], ay=e['ay'], frames=n, anim=e['anim'], loop=bool(e.get('loop')),
                                    blend='lighter', rows=['under', 'over'], color=e['color'])

    # ── 필드
    tiles, rows = F.build_tiles(4)
    meta['tiles'] = dict(sheet=save(tiles, 'field', 'tiles.png'), w=F.TW, h=F.TH, cols=4,
                         rows=[dict(name=n, label=l) for n, l in rows], note='행 = 지형, 열 = 변형 4종 (물은 애니메이션 4프레임)')
    props = F.build_props()
    for nm, imgs in props.items():
        d = F.PROPS[nm]
        W, H, ax, ay = d['frame']
        bbs = [im.getbbox() for im in imgs]
        x0 = max(0, min(b[0] for b in bbs) - 1)
        y0 = max(0, min(b[1] for b in bbs) - 1)
        x1 = min(W, max(b[2] for b in bbs) + 1)
        y1 = min(H, max(b[3] for b in bbs) + 1)
        fw, fh = x1 - x0, y1 - y0
        sheet = Image.new('RGBA', (fw * len(imgs), fh))
        for k, im in enumerate(imgs):
            sheet.alpha_composite(im.crop((x0, y0, x1, y1)), (k * fw, 0))
        meta['props'][nm] = dict(label=d['label'], group=d.get('group') or '기타', sheet=save(sheet, 'field', 'props', f'{nm}.png'), fw=fw, fh=fh,
                                 ax=ax - x0, ay=ay - y0, frames=len(imgs))
    print(f'필드 완료 {time.time() - t0:.0f}s', flush=True)

    # ── 아이템
    n = len(I.ICONS)
    cols = 10
    atlas = Image.new('RGBA', (cols * I.IW, math.ceil(n / cols) * I.IH))
    for k, d in enumerate(I.ICONS):
        atlas.alpha_composite(I.render_icon(d), ((k % cols) * I.IW, (k // cols) * I.IH))
        meta['items'][d['id']] = dict(name=d['name'], cat=d['cat'], grade=d['grade'], index=k, enchantable=d['enchant'])
    meta['item_atlas'] = dict(sheet=save(atlas, 'items', 'icons.png'), w=I.IW, h=I.IH, cols=cols)
    gr = Image.new('RGBA', (36 * len(I.GRADES), 36))
    for k, (gid, lab, hx) in enumerate(I.GRADES):
        gr.alpha_composite(I.slot_frame(hx), (k * 36, 0))
    meta['grades'] = dict(sheet=save(gr, 'items', 'grade_frames.png'), w=36, h=36,
                          list=[dict(id=g, label=l, color=h) for g, l, h in I.GRADES])
    ench_ids = [d for d in I.ICONS if d['enchant'] and d['cat'] == '무기']
    en = Image.new('RGBA', (I.IW * len(I.ENCHANTS), I.IH * len(ench_ids)))
    for r, d in enumerate(ench_ids):
        for c, e in enumerate(I.ENCHANTS):
            en.alpha_composite(I.render_icon(d, e), (c * I.IW, r * I.IH))
    meta['enchant_icons'] = dict(sheet=save(en, 'items', 'enchant_weapons.png'), w=I.IW, h=I.IH,
                                 levels=[e[0] for e in I.ENCHANTS], rows=[d['id'] for d in ench_ids])
    print(f'아이템 완료 {time.time() - t0:.0f}s', flush=True)

    with open(os.path.join(OUT, 'meta.json'), 'w', encoding='utf-8') as fp:
        json.dump(meta, fp, ensure_ascii=False, indent=1)

    if not args.quick:
        import scene
        scene.compose(OUT, meta)
        scene.compose_dungeon(OUT, meta)
    import gallery
    gallery.write(OUT)
    print(f'완료 {time.time() - t0:.0f}s → {OUT}')


if __name__ == '__main__':
    main()
