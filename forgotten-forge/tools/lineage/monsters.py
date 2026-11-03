"""몬스터: 오크 전사, 해골 병사, 다이어울프, 거대 거미, 늪 점액, 보스(몰락한 왕).

각 몬스터는 build(anim, f, n) → (items, M_obj, t_obj) 를 제공한다.
"""
import math

import numpy as np

import sdf as S
import humanoid as Hm
from sdf import V, Item, Mat

C = Hm.M_COMMON


def samp(keys, f, n):
    """키 목록을 n프레임으로 부드럽게 보간(길이가 같으면 그대로). 원소는 숫자 또는 튜플."""
    if len(keys) == n:
        return keys[f]
    u = f / max(1, n - 1) * (len(keys) - 1)
    i = min(int(u), len(keys) - 2)
    w = Hm.ease(u - i)
    a, b = keys[i], keys[i + 1]
    if isinstance(a, tuple):
        return tuple(x + (y - x) * w for x, y in zip(a, b))
    return a + (b - a) * w


# ───────────────────────── 보스 스킬 ─────────────────────────
BOSS_SKILLS = [('skill_darkslash', 8), ('skill_hellfire', 8)]
BOSS_SKILL_HIT = {'skill_darkslash': 4, 'skill_hellfire': 5}


def boss_skill_pose(anim, f, n):
    st = Hm.STANCE['great']
    legs = {k: st[k] for k in Hm.LEG_KEYS}
    p = {k: v for k, v in st.items() if k not in Hm.LEG_KEYS}
    p.update(legs)
    p['plant'] = 1
    if anim == 'skill_darkslash':
        # 암흑 베기: 대검을 오른쪽 뒤로 크게 감았다가 몸 전체로 가로질러 벰
        keys = [dict(rsh=34, rel=62, wpn=145, wpn_side=-30, lsh=44, lel=74, twist=8, lean=5, sink=0.4),
                dict(rsh=70, rel=40, wpn=100, wpn_side=60, lsh=60, lel=60, twist=34, lean=0, sink=0.9),
                dict(rsh=86, rel=26, wpn=96, wpn_side=88, lsh=70, lel=50, twist=46, lean=-2, sink=1.2),
                dict(rsh=90, rel=10, wpn=94, wpn_side=30, lsh=60, lel=30, twist=10, lean=10, sink=1.6),
                dict(rsh=90, rel=4, wpn=92, wpn_side=-60, lsh=40, lel=20, twist=-30, lean=18, sink=2.2),
                dict(rsh=90, rel=4, wpn=91, wpn_side=-68, lsh=38, lel=20, twist=-33, lean=19, sink=2.3),
                dict(rsh=70, rel=12, wpn=84, wpn_side=-86, lsh=36, lel=30, twist=-36, lean=15, sink=1.8),
                dict(rsh=36, rel=56, wpn=135, wpn_side=-30, lsh=44, lel=70, twist=6, lean=6, sink=0.6)]
        p.update(Hm.keyed(keys, f, n))
        p['lhip'] = legs['lhip'] + (14 if f >= 3 else 0)
        p['rhip'] = legs['rhip'] - (12 if f >= 3 else 0)
        p['cape'] = [6, 10, 14, 18, 22, 20, 14, 8][f]
    elif anim == 'skill_hellfire':
        # 지옥불 강타: 대검을 머리 위로 치켜들고 포효 → 땅에 내리꽂음
        keys = [dict(rsh=34, rel=62, wpn=145, wpn_side=-30, lsh=44, lel=74, lean=5, head=0, sink=0.4),
                dict(rsh=120, rel=40, wpn=190, wpn_side=-6, lsh=118, lel=42, lab=10, lean=-6, head=-10, sink=0.6),
                dict(rsh=165, rel=16, wpn=200, wpn_side=0, lsh=160, lel=18, lab=8, lean=-12, head=-20, sink=0.4),
                dict(rsh=168, rel=12, wpn=202, wpn_side=0, lsh=163, lel=14, lab=8, lean=-13, head=-22, sink=0.4),
                dict(rsh=110, rel=10, wpn=120, wpn_side=0, lsh=106, lel=12, lab=8, lean=14, head=0, sink=1.6),
                dict(rsh=70, rel=12, wpn=30, wpn_side=0, lsh=66, lel=14, lab=8, lean=30, head=10, sink=3.0),
                dict(rsh=68, rel=12, wpn=28, wpn_side=0, lsh=64, lel=14, lab=8, lean=31, head=10, sink=3.1),
                dict(rsh=40, rel=50, wpn=130, wpn_side=-24, lsh=44, lel=66, lab=20, lean=8, head=0, sink=0.8)]
        p.update(Hm.keyed(keys, f, n))
        p['cape'] = [6, 4, 0, 0, 10, 22, 18, 8][f]
    return Hm.Pose(**Hm._bend(p))


# ───────────────────────── 사람형 몬스터 공통 ─────────────────────────

def humanoid_monster(name, label, mats, parts, opts, build, kind, gear, frame, lean=0.0, extra_pose=None):
    def make(anim, f, n):
        if anim.startswith('skill_'):
            p = boss_skill_pose(anim, f, n)
        else:
            p = Hm.pose_for(kind, anim, f, n)
        p['lean'] = p['lean'] + lean
        if extra_pose:
            extra_pose(p, anim, f, n)
        r = Hm.Rig(p, build)
        it = Hm.body_items(r, p, parts, opts)
        gear(r, p, it)
        M = t = None
        if anim == 'death':
            M, t = Hm.death_xform(f, n)
        return it, M, t
    return dict(name=name, label=label, mats=mats, build=make, frame=frame)


def axe_head(r, haft, head, length=16, double=False):
    s = r.s
    h = r.rha
    w = r.wdir
    top = h + w * length * s
    side = S.nrm(np.cross(w, r.right))       # 날이 향하는 방향(휘두르는 방향)
    it = [Item(S.capsule(h - w * 3 * s, top + w * 1.0 * s, 1.0 * s, 0.85 * s), haft)]
    Mb = np.stack([r.right, side, w], 1)
    for sg in ((1, -1) if double else (1,)):
        c = top - w * 2.6 * s + side * sg * 3.0 * s
        blade = S.inter(S.ellipsoid(c, V(0.8 * s, 4.0 * s, 4.6 * s), Mb),
                        S.halfspace(-side * sg, -np.dot(side * sg, top) + 0.4 * s))
        it.append(Item(blade, head, 'blade'))
    it.append(Item(S.box(top - w * 2.6 * s, V(1.5 * s, 1.5 * s, 2.4 * s), Mb, 0.3), head))
    return it


# 오크 전사 ────────────────────────────────────────────────

def _orc():
    m = dict(C)
    m.update({
        'skin': Mat(['#1c2416', '#2f3b22', '#465533', '#5f6f45', '#7a8a5a']),
        'eyes': Mat(['#5a1a08', '#8a2a0a', '#c0420e', '#e86a1c', '#ffa040'], emit=True),
        'tusk': Mat(['#5e5442', '#857a62', '#ab9f84', '#cbc0a3', '#e3dabf']),
        'hair': Mat(['#0d0b09', '#17130f', '#221c16', '#2e261e', '#3a3027']),
        'cloth': Mat(['#2a1810', '#43271a', '#5e3825', '#784a31', '#925d3e']),
        'rust': Mat(['#2a1a12', '#46291b', '#674029', '#8a5a38', '#a97448'], metal=True, hi='#d4a070'),
    })
    parts = dict(skin='skin', hair='hair', eyes='eyes', torso='skin', pelvis='cloth', legs='skin', shin='skin',
                 boots='leather', arms='skin', farm='skin', hands='skin')
    opts = dict(limb=1.25, chest=(7.8, 5.0, 6.2), belly=(5.6, 6.2), pelvis=(5.8, 4.2, 4.4), hair=False, head_r=4.6)
    build = dict(scale=1.12, sh_w=7.8, neck=3.0, uarm=10.5, farm=9.5)

    def gear(r, p, it):
        s = r.s
        H, HR = r.head, r.head_rot
        for sx in (-1, 1):
            b = H + HR @ V(sx * 1.6 * s, 3.5 * s, -2.6 * s)
            it.append(Item(S.capsule(b, b + HR @ V(sx * 0.4 * s, 0.6 * s, 2.4 * s), 0.8 * s, 0.25 * s), 'tusk'))
        it.append(Item(S.capsule(H + HR @ V(0, -1 * s, 4.2 * s), H + HR @ V(0, -4.5 * s, 6.5 * s), 1.4 * s, 0.6 * s), 'hair'))
        it.append(Item(S.box(H + HR @ V(0, 3.9 * s, 1.3 * s), V(3.6 * s, 0.9 * s, 0.7 * s), HR, 0.4), 'skin'))  # 툭 튀어나온 눈썹뼈
        # 가죽 끈 X자 + 어깨 보호대(한쪽)
        R = r.rot
        it.append(Item(S.box(r.chest + r.fwd * 4.6 * s, V(0.9 * s, 0.5 * s, 8.0 * s), R @ S.ry(35), 0.3), 'leather'))
        it.append(Item(S.ellipsoid(r.lsh + r.up * 1.2 * s, V(4.2 * s, 4.4 * s, 3.0 * s), R), 'rust'))
        for k in range(3):
            tip = r.lsh + r.up * (3.0 + k * 0.2) * s + R @ V(-1.5 * s + k * 1.5 * s, -0.5 * s, 0)
            it.append(Item(S.capsule(tip, tip + r.up * 2.6 * s - r.right * 0.8 * s, 0.7 * s, 0.1), 'iron'))
        it.append(Item(S.box(r.waist - r.up * 0.4 * s, V(6.4 * s, 4.8 * s, 1.1 * s), R, 0.5), 'leather'))
        it += Hm.skirt(r, 'cloth', 6.2, 7.0, 8.5)
        it += axe_head(r, 'wood', 'iron', 17, double=False)
    return humanoid_monster('orc', '오크 전사', m, parts, opts, build, 'axe', gear, (96, 88, 48, 66), lean=10)


# 해골 병사 ────────────────────────────────────────────────

def _skeleton(archer=False):
    m = dict(C)
    bone = Mat(['#3e3829', '#6a614b', '#958a6e', '#bdb294', '#dcd3b6'])
    m.update({
        'bone': bone,
        'skin': bone,
        'socket': Mat(['#080606', '#0e0a09', '#140f0d', '#1a1411', '#201914']),
        'eyes': Mat(['#5a0808', '#9a1010', '#d42020', '#ff5040', '#ffa090'], emit=True),
        'rust': Mat(['#2a1a12', '#46291b', '#674029', '#8a5a38', '#a97448'], metal=True, hi='#d4a070'),
        'rag': Mat(['#151613', '#22241f', '#30332c', '#3f433a', '#4f5448']),
        'oldwood': Mat(['#1e1812', '#30281e', '#463a2c', '#5c4d3a', '#736048']),
        'fletch': Mat(['#3a0c0c', '#5a1414', '#7a1e1e', '#9a2a26', '#b83a32']),
    })
    parts = dict(skin='bone', eyes=None, torso='bone', pelvis='bone', legs='bone', shin='bone',
                 boots='bone', arms='bone', farm='bone', hands='bone')
    opts = dict(limb=0.5, chest=(0.1, 0.1, 0.1), belly=(1.0, 1.0), pelvis=(4.2, 2.4, 2.2), hair=False, eyes=False, jaw=False)
    build = dict(scale=1.0, sh_w=6.2)

    def gear(r, p, it):
        s = r.s
        R = r.rot
        # 등뼈
        it.append(Item(S.capsule(r.hip, r.neck, 1.2 * s), 'bone'))
        # 갈비뼈 우리: 타원 껍질에서 가로 홈을 판다
        cage = S.shell(S.ellipsoid(r.chest, V(5.6 * s, 3.9 * s, 5.4 * s), R), 0.55 * s)
        cage = S.inter(cage, S.halfspace(r.up, np.dot(r.up, r.chest) + 4.2 * s), S.halfspace(-r.up, -np.dot(r.up, r.chest) + 4.6 * s))
        slots = [S.box(r.chest + r.up * (z * s), V(9 * s, 9 * s, 0.55 * s), R) for z in (-3.0, -1.2, 0.6, 2.4)]
        cage = S.sub(cage, *slots, S.box(r.chest + r.fwd * 4 * s, V(0.8 * s, 2 * s, 7 * s), R))
        it.append(Item(cage, 'bone'))
        it.append(Item(S.capsule(r.lsh, r.rsh, 0.9 * s), 'bone'))     # 쇄골
        # 해골
        H, HR = r.head, r.head_rot
        skull = S.ellipsoid(H + HR @ V(0, 0, 0.6 * s), V(4.0 * s, 4.5 * s, 4.4 * s), HR)
        jaw = S.box(H + HR @ V(0, 1.6 * s, -3.0 * s - p.mouth), V(2.6 * s, 2.4 * s, 1.1 * s), HR, 0.8)
        it.append(Item(S.sub(skull, *[S.sphere(H + HR @ V(sx * 1.7 * s, 3.9 * s, 0.4 * s), 1.4 * s) for sx in (-1, 1)]), 'bone'))
        it.append(Item(jaw, 'bone'))
        for sx in (-1, 1):
            it.append(Item(S.sphere(H + HR @ V(sx * 1.6 * s, 3.0 * s, 0.4 * s), 0.9 * s), 'socket'))
            it.append(Item(S.sphere(H + HR @ V(sx * 1.6 * s, 3.4 * s, 0.4 * s), 0.55 * s), 'eyes'))
        # 너덜너덜한 허리천 + 녹슨 투구 반쪽
        rag = S.displace(S.inter(S.shell(S.capsule(r.hip + V(0, 0, 2 * s), r.hip - V(0, 0, 7 * s), 4.6 * s, 6.2 * s), 0.5 * s),
                                 S.halfspace(V(0, 0, 1), r.hip[2] + 2 * s)), 1.2, 0.5, seed=4)
        it.append(Item(S.inter(rag, S.halfspace(V(0, 0, -1), -(r.hip[2] - 7.5 * s))), 'rag'))
        it.append(Item(S.inter(S.ellipsoid(H + HR @ V(0, -0.3 * s, 1.4 * s), V(4.5 * s, 4.9 * s, 4.4 * s), HR),
                               S.halfspace(-HR @ V(0, 0, 1), -np.dot(HR @ V(0, 0, 1), H) - 1.6 * s)), 'iron'))
        if archer:
            it += Hm.hood(r, 'rag', peak=True)
            it += Hm.quiver(r, 'oldwood', 'fletch')
            it += Hm.bow(r, 'oldwood', 'string', draw=p.draw)
        else:
            it += Hm.sword(r, m, 17, width=1.4, guard='rust', grip='oldwood', blade='rust', pommel='rust')
            it += Hm.round_shield(r, 'oldwood', 'rust', 'rust', 5.2)
    if archer:
        return humanoid_monster('skeleton_archer', '해골 궁수', m, parts, opts, build, 'bow', gear, (96, 88, 48, 66))
    return humanoid_monster('skeleton', '해골 병사', m, parts, opts, build, 'sword', gear, (96, 88, 48, 66))


# 고블린 ───────────────────────────────────────────────

def _goblin():
    m = dict(C)
    m.update({
        'skin': Mat(['#2a3010', '#46501c', '#64722a', '#84943a', '#a4b44e']),
        'eyes': Mat(['#5a4a04', '#8a7208', '#c0a018', '#f0d040', '#fff090'], emit=True),
        'cloth': Mat(['#2a1a10', '#43271a', '#5e3825', '#784a31', '#925d3e']),
        'rust': Mat(['#2a1a12', '#46291b', '#674029', '#8a5a38', '#a97448'], metal=True, hi='#d4a070'),
        'tooth': Mat(['#5e5442', '#857a62', '#ab9f84', '#cbc0a3', '#e3dabf']),
    })
    parts = dict(skin='skin', hair=None, eyes='eyes', torso='cloth', pelvis='cloth', legs='skin', shin='skin',
                 boots='leather', arms='skin', farm='skin', hands='skin')
    opts = dict(limb=0.95, chest=(5.6, 3.8, 4.8), belly=(4.4, 4.8), hair=False, head_r=5.2)
    build = dict(scale=0.8, sh_w=6.0, neck=3.0, uarm=9.0, farm=8.5)

    def gear(r, p, it):
        s = r.s
        H, HR = r.head, r.head_rot
        for sx in (-1, 1):   # 크고 뾰족한 귀
            b = H + HR @ V(sx * 4.4 * s, -0.4 * s, 0.8 * s)
            it.append(Item(S.capsule(b, b + HR @ V(sx * 5.4 * s, -1.6 * s, 1.8 * s), 1.4 * s, 0.2 * s), 'skin'))
        it.append(Item(S.capsule(H + HR @ V(0, 4.0 * s, 0.4 * s), H + HR @ V(0, 7.0 * s, -0.6 * s), 1.2 * s, 0.3 * s), 'skin'))  # 코
        for sx in (-1, 1):
            t0 = H + HR @ V(sx * 1.5 * s, 4.2 * s, -2.4 * s)
            it.append(Item(S.capsule(t0, t0 + HR @ V(0, 0.3 * s, 1.3 * s), 0.5 * s, 0.15 * s), 'tooth'))
        it += Hm.skirt(r, 'cloth', 5.0, 6.0, 7.0)
        it.append(Item(S.box(r.chest + r.fwd * 3.8 * s, V(0.8 * s, 0.4 * s, 6.0 * s), r.rot @ S.ry(-30), 0.3), 'leather'))
        it += Hm.sword(r, m, 11, width=2.4, guard='rust', grip='leather', blade='rust', pommel='rust')
        it += Hm.round_shield(r, 'wood', 'rust', 'rust', 3.8)
    return humanoid_monster('goblin', '고블린', m, parts, opts, build, 'sword', gear, (96, 88, 48, 66), lean=8)


# 몰락한 왕 (보스) ─────────────────────────────────────────

def _boss():
    m = dict(C)
    m.update({
        'blk': Mat(['#0b0b0e', '#15151a', '#212128', '#30303a', '#41414e'], metal=True, hi='#8a8aa0'),
        'blk2': Mat(['#100c0c', '#1c1414', '#2a1d1d', '#3b2828', '#4e3434'], metal=True, hi='#a07070'),
        'ember': Mat(['#7a1404', '#b52a06', '#e8540e', '#ff8a2a', '#ffc870'], emit=True),
        'eyes': Mat(['#7a1404', '#b52a06', '#e8540e', '#ff8a2a', '#ffc870'], emit=True),
        'cape_t': Mat(['#120608', '#1f0a0e', '#2e1015', '#40171d', '#521f26']),
        'horn': Mat(['#2a241c', '#4a4032', '#6c5e4a', '#8e7e64', '#ab9a7e']),
        'skin': Mat(['#0b0b0e', '#15151a', '#212128', '#30303a', '#41414e'], metal=True),
    })

    def cracks(P, n):
        return np.zeros(P.shape[0])
    parts = dict(skin='blk', eyes=None, torso='blk', pelvis='blk2', legs='blk2', shin='blk', boots='blk',
                 arms='blk2', farm='blk', hands='blk')
    opts = dict(limb=1.3, chest=(7.8, 5.0, 6.6), belly=(5.6, 6.4), pelvis=(6.0, 4.3, 4.6), hair=False, eyes=False, head_r=4.8)
    build = dict(scale=1.55, sh_w=7.6, neck=3.6)

    def gear(r, p, it):
        s = r.s
        R = r.rot
        H, HR = r.head, r.head_rot
        hr = 4.8 * s
        it.append(Item(S.ellipsoid(H + HR @ V(0, 0, 0.4 * s), V(hr * 1.06, hr * 1.12, hr * 1.12), HR), 'blk'))
        it.append(Item(S.box(H + HR @ V(0, hr * 1.06, 0.6 * s), V(hr * 0.7, 0.5 * s, 0.4 * s), HR, 0.1), 'ember'))
        for sx in (-1, 1):
            a = H + HR @ V(sx * hr * 0.8, 0, hr * 0.6)
            b = a + HR @ V(sx * 4.5 * s, -1.0 * s, 2.0 * s)
            c = b + HR @ V(sx * 1.0 * s, -1.5 * s, 4.5 * s)
            it.append(Item(S.capsule(a, b, 1.5 * s, 1.0 * s), 'horn'))
            it.append(Item(S.capsule(b, c, 1.0 * s, 0.2 * s), 'horn'))
        # 가시 견갑
        for sh, sx in ((r.lsh, -1), (r.rsh, 1)):
            c = sh + r.up * 1.0 * s + r.right * sx * 1.0 * s
            it.append(Item(S.ellipsoid(c, V(4.0 * s, 4.2 * s, 3.2 * s), R), 'blk'))
            for k in range(2):
                b = c + r.up * 2.2 * s + R @ V(sx * (0.5 + k * 1.6) * s, (k - 0.5) * 1.5 * s, 0)
                it.append(Item(S.capsule(b, b + r.up * 3.2 * s + r.right * sx * 1.2 * s, 0.9 * s, 0.1), 'blk2'))
        # 가슴의 불타는 균열
        it.append(Item(S.box(r.chest + r.fwd * 4.7 * s + r.up * 0.5 * s, V(0.5 * s, 0.4 * s, 3.0 * s), R @ S.ry(20), 0.1), 'ember'))
        it.append(Item(S.box(r.chest + r.fwd * 4.6 * s - r.up * 1.4 * s + r.right * 1.2 * s, V(1.8 * s, 0.4 * s, 0.4 * s), R @ S.ry(-30), 0.1), 'ember'))
        it += Hm.cape(r, p, 'cape_t', length=34, width=8.0, tatter=False)
        it += Hm.skirt(r, 'blk2', 6.6, 7.8, 10.0)
        it += Hm.greatsword(r, m, 30, 2.2, guard='blk2', grip='leather', blade='steel_dk')
        # 칼날 중앙의 불꽃 홈
        w = r.wdir
        b0 = r.rha + w * 5 * s
        it.append(Item(S.capsule(b0, b0 + w * 22 * s, 0.55 * s), 'ember', 'blade'))
    return humanoid_monster('boss', '몰락한 왕', m, parts, opts, build, 'great', gear, (144, 128, 72, 100), lean=4)


# ───────────────────────── 다이어울프 ─────────────────────────

def _wolf():
    fur_tex = lambda P, n: 0.55 * S.vnoise(P * V(0.9, 0.35, 1.4), 11) + 0.25 * S.vnoise(P * 2.6, 5)
    m = {
        'fur': Mat(['#15140f', '#25231d', '#38352d', '#4d493f', '#646054'], tex=fur_tex),
        'fur_lt': Mat(['#2a2720', '#433f35', '#5f5a4d', '#7d7767', '#9a9482'], tex=fur_tex),
        'eyes': Mat(['#6a5a04', '#a08a0a', '#d4b81a', '#f0dc40', '#fff090'], emit=True),
        'nose': Mat(['#060505', '#0c0a09', '#12100e', '#181513', '#1e1a17'], gloss=0.6),
        'fang': Mat(['#7d7562', '#a39a84', '#c4bba3', '#dcd5bf', '#efe9d6']),
        'mouth': Mat(['#2a0808', '#440d0d', '#601414', '#7c1c1c', '#962424']),
    }

    def legs(phase, k_attack=0.0, crouch=0.0):
        """다리 끝 위치(발) 계산: 트롯(대각선 쌍)."""
        out = []
        for i, (sx, sy, off) in enumerate(((-1, 9, 0.0), (1, 9, 0.5), (-1, -10, 0.5), (1, -10, 0.0))):
            ph = 2 * math.pi * (phase + off)
            swing = 6.5 * math.sin(ph)
            lift = max(0.0, math.cos(ph)) * 3.4
            out.append((sx, sy, swing, lift))
        return out

    def make(anim, f, n):
        t = f / n
        bob, pitch, head_dn, jaw, tail_up, lunge, crouch = 0, 0, 0, 0, 0, 0, 0
        phase = 0.0
        moving = False
        if anim == 'idle':
            bob = 0.4 * math.sin(2 * math.pi * t)
            jaw = 0.6 + 0.6 * math.sin(2 * math.pi * t)
        elif anim == 'walk':
            phase = t
            moving = True
            bob = 0.8 * abs(math.sin(2 * math.pi * t * 2))
        elif anim == 'attack':
            seq = [(0, 0, 0, 1, 0), (-4, 3, -3, 2, 2), (-8, 5, -6, 4, 3), (2, 0, 6, 6, 0), (9, -2, 12, 8, 6),
                   (9, -2, 12, 7, 6), (5, 0, 7, 4, 4), (1, 0, 1, 1, 1)]
            pitch, head_dn, lunge, jaw, crouch = samp(seq, f, n)
            head_dn = -head_dn
        elif anim == 'hurt':
            pitch, head_dn, lunge = samp([(-12, 10, -4), (-7, 6, -2), (-2, 2, -0.5)], f, n)
        elif anim == 'death':
            pitch = 0
        s = 1.0
        hipZ, shZ = 19.0 - crouch * 0.5 + bob, 21.0 - crouch * 0.3 + bob
        it = []
        rot = S.rx(-pitch)
        o = V(0, lunge, 0)
        hip = o + V(0, -10, hipZ)
        sh = o + rot @ V(0, 9, shZ - hipZ) + V(0, -10 * 0, hipZ) * 0 + V(0, 0, hipZ)
        sh = o + V(0, -10, hipZ) + rot @ V(0, 19, shZ - hipZ)
        neck = sh + rot @ V(0, 4, 4)
        hd = neck + rot @ S.rx(head_dn) @ V(0, 5, 2.5)
        HR = rot @ S.rx(head_dn)
        it.append(Item(S.ellipsoid(hip + rot @ V(0, 2, 0), V(5.0, 7.0, 5.4), rot), 'fur'))
        it.append(Item(S.ellipsoid(sh + rot @ V(0, -1, 0.5), V(5.8, 7.0, 6.6), rot), 'fur'))
        it.append(Item(S.capsule(hip, sh, 4.6, 5.3), 'fur'))
        it.append(Item(S.ellipsoid(sh + rot @ V(0, 1.5, -2.5), V(4.2, 4.6, 4.8), rot), 'fur_lt'))  # 가슴털
        # 갈기
        it.append(Item(S.displace(S.capsule(sh + rot @ V(0, -3, 3), neck + rot @ V(0, 0, 2.5), 4.4, 3.6), 0.9, 0.7, seed=2), 'fur'))
        it.append(Item(S.capsule(neck, hd, 3.6, 3.2), 'fur'))
        it.append(Item(S.ellipsoid(hd, V(3.6, 4.0, 3.4), HR), 'fur'))
        snout_a = hd + HR @ V(0, 2.5, -0.6)
        snout_b = hd + HR @ V(0, 7.6, -1.2)
        it.append(Item(S.capsule(snout_a, snout_b, 2.0, 1.25), 'fur_lt'))
        it.append(Item(S.sphere(snout_b + HR @ V(0, 0.6, 0.6), 0.95), 'nose'))
        ja = hd + HR @ V(0, 2.4, -2.0)
        jb = ja + HR @ S.rx(jaw * 4) @ V(0, 5.0, -0.4)
        it.append(Item(S.capsule(ja, jb, 1.4, 0.9), 'fur_lt'))
        if jaw > 2:
            it.append(Item(S.capsule(snout_a + HR @ V(0, 0, -1.4), ja + HR @ V(0, 3.8, 0.2), 1.2, 0.8), 'mouth'))
            for sx in (-1, 1):
                fb = snout_b + HR @ V(sx * 0.9, -1.0, -1.0)
                it.append(Item(S.capsule(fb, fb + HR @ V(0, 0, -1.6), 0.45, 0.1), 'fang'))
        for sx in (-1, 1):
            it.append(Item(S.sphere(hd + HR @ V(sx * 1.9, 3.0, 0.9), 0.75), 'eyes'))
            eb = hd + HR @ V(sx * 2.0, -0.8, 2.6)
            it.append(Item(S.capsule(eb, eb + HR @ V(sx * 0.6, -0.8, 3.4), 1.2, 0.2), 'fur'))
        # 꼬리
        tb = hip + rot @ V(0, -5, 2)
        prev = tb
        for k in range(3):
            a = math.radians(20 + tail_up - k * 18 + (6 * math.sin(2 * math.pi * t + k) if anim in ('idle', 'walk') else 0))
            nxt = prev + V(0, -math.cos(a) * 4.2, math.sin(a) * 4.2 - k * 1.2)
            it.append(Item(S.capsule(prev, nxt, 2.4 - k * 0.5, 2.0 - k * 0.5), 'fur'))
            prev = nxt
        # 다리
        for i, (sx, sy, swing, lift) in enumerate(legs(phase)):
            front = sy > 0
            root = (sh if front else hip) + V(sx * 3.2, 0, -2.0)
            if not moving:
                swing, lift = 0, 0
            if anim == 'attack' and front:
                swing += samp([0, -2, -4, 3, 8, 8, 5, 1], f, n)
                lift += samp([0, 0, 1, 4, 3, 3, 1.5, 0], f, n)
            foot = V(root[0] + sx * 0.3, root[1] + swing + (1.5 if front else -0.5), lift)
            # 무릎/관절: 앞다리는 뒤로, 뒷다리는 앞으로(굽은 비절)
            mid = (root + foot) / 2 + V(0, (-2.0 if front else 3.4), 0)
            r1 = 2.6 if front else 3.0
            it.append(Item(S.capsule(root, mid, r1, 1.6), 'fur'))
            it.append(Item(S.capsule(mid, foot + V(0, 0, 1.4), 1.5, 1.1), 'fur'))
            it.append(Item(S.ellipsoid(foot + V(0, 1.2, 1.0), V(1.5, 2.2, 1.1)), 'fur_lt'))
        M = tt = None
        if anim == 'death':
            ang = samp([6, 18, 44, 76, 94, 88], f, n)
            M = S.ry(ang)
            pivot = V(5.0, 0, 0)
            tt = pivot - M @ pivot + V(0, 0, -samp([0, 0.3, 1.0, 1.8, 2.7, 2.5], f, n))
        return it, M, tt
    return dict(name='wolf', label='다이어울프', mats=m, build=make, frame=(112, 96, 56, 68), scale=1.25)


# ───────────────────────── 거대 거미 ─────────────────────────

def _spider():
    hair = lambda P, n: 0.5 * S.vnoise(P * 1.8, 21)
    m = {
        'carapace': Mat(['#0c0810', '#17101d', '#241a2c', '#33263e', '#443352'], gloss=0.5, tex=hair),
        'abdomen': Mat(['#0d0a0c', '#1a1318', '#2a1f27', '#3b2c37', '#4e3b49'], gloss=0.4, tex=hair),
        'mark': Mat(['#4a0808', '#7a0e0e', '#a81818', '#d02a22', '#ee4a3a']),
        'eyes': Mat(['#6a0808', '#a01010', '#e02020', '#ff5040', '#ff9a90'], emit=True),
        'fang': Mat(['#2e2a24', '#4a443a', '#6a6252', '#8a806c', '#a89e88'], gloss=0.6),
        'leg': Mat(['#0e0a10', '#1a1320', '#281e30', '#382a42', '#4a3856'], tex=hair),
    }

    def make(anim, f, n):
        t = f / n
        it = []
        rear = 0.0
        bob = 0.0
        lunge = 0.0
        curl = 0.0
        fang = 0.0
        if anim == 'idle':
            bob = 0.4 * math.sin(2 * math.pi * t)
        elif anim == 'walk':
            bob = 0.5 * abs(math.sin(4 * math.pi * t))
        elif anim == 'attack':
            rear, lunge, fang = samp([(2, 0, 0), (14, -2, 0.5), (30, -4, 1), (8, 3, 1.5), (-8, 8, 2), (-8, 8, 2), (-3, 4, 1), (2, 0, 0)], f, n)
        elif anim == 'hurt':
            rear, lunge = samp([(-10, -4), (-6, -2), (-2, -0.5)], f, n)
        elif anim == 'death':
            curl = samp([0.1, 0.3, 0.55, 0.8, 1.0, 1.0], f, n)
            bob = -samp([0, 1, 2.5, 4.5, 6.5, 6], f, n)
        rot = S.rx(-rear)
        bodyZ = 12.0 + bob
        cep = V(0, 3 + lunge, bodyZ)
        abd = cep + rot @ V(0, -13, 3.5)
        it.append(Item(S.ellipsoid(cep, V(6.0, 6.5, 4.0), rot), 'carapace'))
        it.append(Item(S.ellipsoid(abd, V(9.0, 11.0, 8.0), rot @ S.rx(15)), 'abdomen'))
        # 배 위 붉은 문양 (모래시계)
        top = abd + rot @ V(0, 0, 7.4)
        it.append(Item(S.inter(S.ellipsoid(abd, V(9.05, 11.05, 8.05), rot @ S.rx(15)),
                               S.box(top, V(1.6, 5.0, 4.0), rot @ S.rx(15))), 'mark'))
        it.append(Item(S.inter(S.ellipsoid(abd, V(9.08, 11.08, 8.08), rot @ S.rx(15)),
                               S.box(top + rot @ V(0, 0, 0), V(4.0, 1.2, 4.0), rot @ S.rx(15))), 'mark'))
        hd = cep + rot @ V(0, 6.0, 0.6)
        it.append(Item(S.ellipsoid(hd, V(3.6, 3.0, 3.0), rot), 'carapace'))
        for sx, sy, sz, rr in ((-1.1, 2.4, 1.6, 0.85), (1.1, 2.4, 1.6, 0.85), (-2.3, 1.6, 1.3, 0.6), (2.3, 1.6, 1.3, 0.6),
                               (-0.6, 2.6, 2.4, 0.5), (0.6, 2.6, 2.4, 0.5)):
            it.append(Item(S.sphere(hd + rot @ V(sx, sy, sz), rr), 'eyes'))
        for sx in (-1, 1):
            fb = hd + rot @ V(sx * 1.3, 2.4, -1.2)
            it.append(Item(S.capsule(fb, fb + rot @ V(sx * (0.3 - fang * 0.6), 1.0 + fang, -3.0), 0.9, 0.25), 'fang'))
        # 다리 8개 (네 쌍, 교대 걸음)
        angles = [62, 28, -18, -55]
        for i, a0 in enumerate(angles):
            for sx in (-1, 1):
                alt = (i % 2 == 0) == (sx > 0)
                ph = 2 * math.pi * (t + (0.5 if alt else 0.0))
                swing = 9 * math.sin(ph) if anim == 'walk' else 0
                lift = max(0, math.cos(ph)) * 4.0 if anim == 'walk' else 0
                a = math.radians(a0 + swing)
                if anim == 'attack' and i == 0:
                    lift += samp([1, 5, 11, 6, 3, 3, 2, 1], f, n)
                root = cep + rot @ V(sx * 4.6, 1.5 * math.sin(a) * 2, -0.5)
                dirv = V(sx * math.cos(a), math.sin(a), 0)
                reach = 20 - curl * 12
                foot = V(root[0], root[1], 0) + dirv * reach + V(0, 0, lift + curl * 4)
                knee = root + dirv * (reach * 0.45) + V(0, 0, 9.0 - curl * 2)
                it.append(Item(S.capsule(root, knee, 1.5, 1.2), 'leg'))
                it.append(Item(S.capsule(knee, foot, 1.15, 0.45), 'leg'))
        return it, None, None
    return dict(name='spider', label='거대 거미', mats=m, build=make, frame=(112, 88, 56, 60))


# ───────────────────────── 늪 점액 ─────────────────────────

def _ooze():
    m = {
        'ooze': Mat(['#0d1a0c', '#1a3216', '#2c4f22', '#447230', '#62953e'], gloss=1.0, hi='#d8f0a0',
                    tex=lambda P, n: 0.35 * S.vnoise(P * 0.5, 9)),
        'core': Mat(['#3a5a08', '#5f8a10', '#8cbc22', '#b8e04a', '#e0ff90'], emit=True),
        'bone': Mat(['#3e3829', '#6a614b', '#958a6e', '#bdb294', '#dcd3b6']),
        'eyes': Mat(['#5a5a04', '#8a8a0a', '#c0c01a', '#e8e840', '#ffff9a'], emit=True),
    }

    def make(anim, f, n):
        t = f / n
        sq, fw, up, melt, side = 1.0, 0.0, 0.0, 0.0, 0.0
        if anim == 'idle':
            sq = 1.0 + 0.07 * math.sin(2 * math.pi * t)
        elif anim == 'walk':
            sq = 1.0 + 0.16 * math.sin(2 * math.pi * t)
            fw = 2.5 * math.sin(2 * math.pi * t)
        elif anim == 'attack':
            sq, fw, up = samp([(1.0, 0, 0), (0.82, -2, 0), (0.7, -3, 0), (1.4, 2, 4), (0.72, 10, 0), (0.75, 10, 0), (0.92, 5, 0), (1.0, 1, 0)], f, n)
        elif anim == 'hurt':
            sq, fw = samp([(0.65, -3), (1.12, -1), (0.94, 0)], f, n)
        elif anim == 'death':
            melt = samp([0.1, 0.3, 0.5, 0.72, 0.92, 1.0], f, n)
            sq = 1.0 - 0.75 * melt
        hz = 9.0 * sq
        rw = 11.0 / math.sqrt(sq)
        main = S.ellipsoid(V(0, fw * 0.4, hz), V(rw, rw * 0.95, hz + 0.01))
        lobe = S.ellipsoid(V(0, 3 + fw, hz * 1.35 + up), V(rw * 0.55, rw * 0.55, hz * 0.6 + 0.01))
        drip = S.capsule(V(-6, -4, hz * 0.6), V(-7, -5, 0.5), 2.2, 1.4)
        puddle = S.ellipsoid(V(0, 0, 0.6), V(rw * 1.2 + melt * 3, rw * 1.1 + melt * 3, 1.4))
        blob = S.sunion(3.5, main, lobe, drip, puddle)
        blob = S.displace(blob, 0.8, 0.35, seed=f + 3)
        blob = S.inter(blob, S.halfspace(V(0, 0, -1), 0.0))
        it = [Item(blob, 'ooze')]
        if melt < 0.9:
            it.append(Item(S.sphere(V(1.5, 0.5 + fw * 0.4, hz * 0.95), 2.4 * (1 - melt)), 'core'))
            # 안에 떠 있는 해골(먹힌 모험가)
            sk = V(-3.0, -1.0 + fw * 0.3, hz * 0.8)
            it.append(Item(S.sub(S.sphere(sk, 2.6 * (1 - melt * 0.5)), S.sphere(sk + V(0.8, 2.2, 0.2), 0.9)), 'bone'))
            for sx in (-1, 1):
                it.append(Item(S.sphere(V(sx * 3.2, 7.5 + fw * 0.8, hz * 1.35 + up), 1.0), 'eyes'))
        return it, None, None
    return dict(name='ooze', label='늪 점액', mats=m, build=make, frame=(96, 88, 48, 62))


MONSTERS = [_orc(), _skeleton(), _wolf(), _spider(), _ooze(), _boss(), _goblin(), _skeleton(archer=True)]
