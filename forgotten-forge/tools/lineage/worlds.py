"""추가 에셋: 상점 신전·화로의 신(상점 NPC)·월드보스 2종.

- 월드보스는 일반 보스(몰락한 왕) 프레임의 1.5배 해상도로 렌더링하고, 게임에서 1.33배로 그려 화면상 2배 크기가 된다.
  (2배 해상도로 굽면 시트가 너무 커져 휴대폰 메모리를 많이 먹음)
- 월드보스는 프레임 수를 줄인 동작 목록(WB_ANIMS)을 쓴다.

build.py / add_assets.py 가 import 하면 monsters.MONSTERS 와 field.PROPS 에 자동 등록된다.
"""
import math

import numpy as np

import sdf as S
import humanoid as Hm
import monsters as Mo
import field as F
from sdf import V, Item, Mat

C = Hm.M_COMMON
WB_ANIMS = [('idle', 4), ('walk', 6), ('attack', 8), ('hurt', 2), ('death', 5), ('skill_darkslash', 6), ('skill_hellfire', 6)]
WB_FRAME = (216, 192, 108, 150)


# ───────────────────────── 월드보스 1: 피의 군주 그롬마르 (마을 외곽) ─────────────────────────

def _wb_warlord():
    m = dict(C)
    m.update({
        'skin': Mat(['#220a08', '#3e1510', '#5e2218', '#7e3424', '#9c4a32']),
        'paint': Mat(['#0c0a0a', '#151212', '#1e1a19', '#2a2423', '#38302e']),
        'eyes': Mat(['#6a4a04', '#a07a0a', '#d4b01a', '#f0d840', '#fff4a0'], emit=True),
        'bone': Mat(['#3e3829', '#6a614b', '#958a6e', '#bdb294', '#dcd3b6']),
        'tusk': Mat(['#5e5442', '#857a62', '#ab9f84', '#cbc0a3', '#e3dabf']),
        'fur': Mat(['#120d09', '#21180f', '#322416', '#45321f', '#5a432a'], tex=lambda P, n: 0.6 * S.vnoise(P * V(0.8, 0.8, 1.6), 9)),
        'cloth': Mat(['#2a0c0a', '#46140f', '#661e15', '#86291c', '#a63a26']),
        'rust': Mat(['#2a1a12', '#46291b', '#674029', '#8a5a38', '#a97448'], metal=True, hi='#d4a070'),
        'blood': Mat(['#3a0404', '#640808', '#8e0e0e', '#b81a14', '#e03a20'], emit=True),
    })
    parts = dict(skin='skin', hair=None, eyes='eyes', torso='skin', pelvis='cloth', legs='skin', shin='skin',
                 boots='fur', arms='skin', farm='skin', hands='skin')
    opts = dict(limb=1.4, chest=(8.4, 5.4, 6.6), belly=(6.0, 6.6), pelvis=(6.2, 4.4, 4.6), hair=False, head_r=4.8)
    build = dict(scale=2.6, sh_w=8.2, neck=3.0, uarm=10.8, farm=9.8, torso=8.95)   # Rig는 torso에 scale을 두 번 곱함 → 보스와 같은 비율로 보정

    def gear(r, p, it):
        s = r.s
        R = r.rot
        H, HR = r.head, r.head_rot
        # 엄니·눈썹뼈·전투 문신(얼굴의 검은 줄)
        for sx in (-1, 1):
            b = H + HR @ V(sx * 1.7 * s, 3.6 * s, -2.6 * s)
            it.append(Item(S.capsule(b, b + HR @ V(sx * 0.6 * s, 0.8 * s, 3.4 * s), 1.0 * s, 0.25 * s), 'tusk'))
            it.append(Item(S.box(H + HR @ V(sx * 2.2 * s, 4.15 * s, 0.6 * s), V(0.35 * s, 0.4 * s, 2.0 * s), HR, 0.1), 'paint'))
        it.append(Item(S.box(H + HR @ V(0, 4.0 * s, 1.4 * s), V(3.8 * s, 1.0 * s, 0.7 * s), HR, 0.4), 'skin'))
        # 뼈 왕관 + 거대한 휜 뿔
        cc = H + HR @ V(0, -0.2 * s, 3.6 * s)
        it.append(Item(S.sub(S.cylinder(cc, 4.4 * s, 0.9 * s, HR, 0.2), S.cylinder(cc, 3.6 * s, 2 * s, HR)), 'bone'))
        for k in range(5):
            a = math.radians(k * 36 + 18)
            p0 = cc + HR @ V(math.cos(a) * 4.2 * s, math.sin(a) * 4.2 * s, 0.6 * s)
            it.append(Item(S.capsule(p0, p0 + HR @ V(0, 0, 2.6 * s), 0.6 * s, 0.15 * s), 'bone'))
        for sx in (-1, 1):
            a = H + HR @ V(sx * 3.8 * s, 0.4 * s, 2.6 * s)
            b = a + HR @ V(sx * 5.5 * s, -1.0 * s, 1.0 * s)
            c = b + HR @ V(sx * 2.0 * s, 0.5 * s, 5.0 * s)
            d = c + HR @ V(-sx * 1.4 * s, 2.0 * s, 2.4 * s)
            it.append(Item(S.capsule(a, b, 1.6 * s, 1.15 * s), 'bone'))
            it.append(Item(S.capsule(b, c, 1.15 * s, 0.7 * s), 'bone'))
            it.append(Item(S.capsule(c, d, 0.7 * s, 0.15 * s), 'tusk'))
        # 해골 견갑(양쪽) + 가시
        for sh, sx in ((r.lsh, -1), (r.rsh, 1)):
            c = sh + r.up * 1.4 * s + r.right * sx * 0.6 * s
            sk = S.ellipsoid(c, V(4.4 * s, 4.6 * s, 3.6 * s), R)
            sk = S.sub(sk, *[S.sphere(c + R @ V(ex * 1.6 * s, 4.0 * s, 0.6 * s), 1.2 * s) for ex in (-1, 1)])
            it.append(Item(sk, 'bone'))
            for k in range(3):
                b = c + r.up * 2.8 * s + R @ V(sx * (k - 1) * 1.6 * s, -0.6 * s, 0)
                it.append(Item(S.capsule(b, b + r.up * 3.4 * s + r.right * sx * 1.4 * s, 0.8 * s, 0.1), 'rust'))
        # 가슴 X자 가죽끈 + 뼈 목걸이 + 피 문양
        it.append(Item(S.box(r.chest + r.fwd * 5.0 * s, V(1.0 * s, 0.5 * s, 8.6 * s), R @ S.ry(35), 0.3), 'leather'))
        it.append(Item(S.box(r.chest + r.fwd * 5.0 * s, V(1.0 * s, 0.5 * s, 8.6 * s), R @ S.ry(-35), 0.3), 'leather'))
        for k in range(5):
            a = math.radians(-60 + k * 30)
            it.append(Item(S.capsule(r.neck + R @ V(math.sin(a) * 4.2 * s, 3.2 * s, -1.6 * s - abs(math.sin(a)) * 1.2 * s),
                                     r.neck + R @ V(math.sin(a) * 4.0 * s, 4.0 * s, -3.4 * s - abs(math.sin(a)) * 1.2 * s), 0.6 * s, 0.25 * s), 'tusk'))
        it.append(Item(S.box(r.chest + r.fwd * 5.4 * s + r.up * 1.6 * s, V(2.4 * s, 0.3 * s, 0.4 * s), R, 0.1), 'blood'))
        # 털 망토 + 판갑 치마
        it += Hm.cape(r, p, 'fur', length=36, width=9.0, tatter=True)
        it += Hm.skirt(r, 'cloth', 6.8, 8.4, 10.0)
        it.append(Item(S.box(r.waist - r.up * 0.4 * s, V(7.0 * s, 5.2 * s, 1.3 * s), R, 0.5), 'rust'))
        # 양날 대도끼(손잡이 길이 30, 날 2배)
        h = r.rha
        w = r.wdir
        top = h + w * 22 * s
        it.append(Item(S.capsule(h - w * 8 * s, top + w * 2.0 * s, 1.1 * s, 0.95 * s), 'wood'))
        side = S.nrm(np.cross(w, r.right))
        Mb = np.stack([r.right, side, w], 1)
        for sg in (1, -1):
            c = top - w * 3.6 * s + side * sg * 4.4 * s
            blade = S.inter(S.ellipsoid(c, V(1.0 * s, 6.4 * s, 7.2 * s), Mb),
                            S.halfspace(-side * sg, -np.dot(side * sg, top) + 0.6 * s))
            it.append(Item(blade, 'iron', 'blade'))
            it.append(Item(S.capsule(c - w * 3.0 * s + side * sg * 1.0 * s, c + w * 3.0 * s + side * sg * 1.0 * s, 0.45 * s), 'blood', 'blade'))
        it.append(Item(S.box(top - w * 3.6 * s, V(1.9 * s, 1.9 * s, 3.2 * s), Mb, 0.3), 'iron'))
        it.append(Item(S.cone(top + w * 1.0 * s, top + w * 6.0 * s, 1.4 * s), 'iron'))
    d = Mo.humanoid_monster('wb_warlord', '피의 군주 그롬마르', m, parts, opts, build, 'great', gear, WB_FRAME, lean=8)
    d['anims'] = WB_ANIMS
    return d


# ───────────────────────── 월드보스 2: 심연의 리치 군주 벨카르 (지하 묘소) ─────────────────────────

def _wb_lich():
    m = dict(C)
    bone = Mat(['#2c2a33', '#4e4b58', '#767284', '#a29db0', '#cbc7d6'])
    m.update({
        'bone': bone, 'skin': bone,
        'socket': Mat(['#040308', '#08060e', '#0c0914', '#100c1a', '#140f20']),
        'soul': Mat(['#0a3a5a', '#10608a', '#1a90c0', '#40c8f0', '#a8f0ff'], emit=True),
        'void': Mat(['#0c0614', '#160b22', '#221232', '#311a46', '#43245c']),
        'void_lt': Mat(['#1a0e2a', '#2a1642', '#3c205c', '#522c78', '#6a3a96']),
        'gold': Mat(['#4a2e0c', '#7c5316', '#b07d22', '#d9a83a', '#f2d36b'], metal=True, hi='#fff2b8'),
        'gem': Mat(['#2a0a4a', '#4a1478', '#7022a8', '#9a40d8', '#d090ff'], emit=True),
        'steel_dk': Mat(['#0e0f14', '#191b22', '#262a34', '#363b48', '#4a505e'], metal=True, hi='#9aa8c0'),
    })
    parts = dict(skin='bone', eyes=None, torso='bone', pelvis='bone', legs='bone', shin='bone',
                 boots='steel_dk', arms='bone', farm='bone', hands='bone')
    opts = dict(limb=0.62, chest=(0.1, 0.1, 0.1), belly=(1.2, 1.2), pelvis=(4.6, 2.6, 2.4), hair=False, eyes=False, jaw=False)
    build = dict(scale=2.4, sh_w=7.0, neck=3.2, torso=10.5)

    def gear(r, p, it):
        s = r.s
        R = r.rot
        it.append(Item(S.capsule(r.hip, r.neck, 1.3 * s), 'bone'))
        cage = S.shell(S.ellipsoid(r.chest, V(6.0 * s, 4.2 * s, 5.8 * s), R), 0.6 * s)
        cage = S.inter(cage, S.halfspace(r.up, np.dot(r.up, r.chest) + 4.4 * s), S.halfspace(-r.up, -np.dot(r.up, r.chest) + 4.8 * s))
        slots = [S.box(r.chest + r.up * (z * s), V(10 * s, 10 * s, 0.6 * s), R) for z in (-3.0, -1.2, 0.6, 2.4)]
        cage = S.sub(cage, *slots, S.box(r.chest + r.fwd * 4.2 * s, V(0.9 * s, 2.2 * s, 7.4 * s), R))
        it.append(Item(cage, 'bone'))
        # 갈비뼈 안에서 타오르는 영혼의 불꽃
        it.append(Item(S.ellipsoid(r.chest, V(2.6 * s, 2.2 * s, 3.0 * s), R), 'soul'))
        it.append(Item(S.capsule(r.lsh, r.rsh, 1.0 * s), 'bone'))
        H, HR = r.head, r.head_rot
        skull = S.ellipsoid(H + HR @ V(0, 0, 0.6 * s), V(4.2 * s, 4.7 * s, 4.6 * s), HR)
        jaw = S.box(H + HR @ V(0, 1.7 * s, -3.1 * s - p.mouth), V(2.7 * s, 2.5 * s, 1.1 * s), HR, 0.8)
        it.append(Item(S.sub(skull, *[S.sphere(H + HR @ V(sx * 1.8 * s, 4.1 * s, 0.4 * s), 1.5 * s) for sx in (-1, 1)]), 'bone'))
        it.append(Item(jaw, 'bone'))
        for sx in (-1, 1):
            it.append(Item(S.sphere(H + HR @ V(sx * 1.7 * s, 3.1 * s, 0.4 * s), 1.0 * s), 'socket'))
            it.append(Item(S.sphere(H + HR @ V(sx * 1.7 * s, 3.5 * s, 0.4 * s), 0.7 * s), 'soul'))
        # 높은 가시 왕관 + 보석
        cc = H + HR @ V(0, -0.2 * s, 3.5 * s)
        it.append(Item(S.sub(S.cylinder(cc, 4.5 * s, 1.0 * s, HR, 0.2), S.cylinder(cc, 3.8 * s, 2.2 * s, HR)), 'gold'))
        for k in range(7):
            a = math.radians(k * (360 / 7) + 90)
            hgt = 5.6 if k == 0 else (3.6 if k in (1, 6) else 2.6)
            p0 = cc + HR @ V(math.cos(a) * 4.3 * s, math.sin(a) * 4.3 * s, 0.6 * s)
            it.append(Item(S.capsule(p0, p0 + HR @ V(math.cos(a) * 0.6 * s, math.sin(a) * 0.6 * s, hgt * s), 0.75 * s, 0.15 * s), 'gold'))
        it.append(Item(S.sphere(cc + HR @ V(0, 4.5 * s, 0.4 * s), 1.0 * s), 'gem'))
        # 어깨 망토 깃 + 찢어진 망토 + 허리 아래 로브
        for sh, sx in ((r.lsh, -1), (r.rsh, 1)):
            c = sh + r.up * 1.0 * s + r.right * sx * 0.8 * s
            it.append(Item(S.ellipsoid(c, V(4.0 * s, 4.4 * s, 2.8 * s), R), 'steel_dk'))
            it.append(Item(S.capsule(c + r.up * 2.0 * s, c + r.up * 6.4 * s + r.right * sx * 1.6 * s - r.fwd * 1.0 * s, 1.4 * s, 0.3 * s), 'void_lt'))
        it += Hm.cape(r, p, 'void', length=40, width=9.0, tatter=True, split=True)
        it += Hm.skirt(r, 'void', 5.4, 8.4, 13.0)
        it.append(Item(S.box(r.waist, V(5.6 * s, 3.4 * s, 1.0 * s), R, 0.4), 'gold'))
        # 영혼의 대검(칼날 홈에 푸른 불꽃)
        it += Hm.greatsword(r, m, 32, 2.3, guard='gold', grip='void', blade='steel_dk')
        w = r.wdir
        b0 = r.rha + w * 5 * s
        it.append(Item(S.capsule(b0, b0 + w * 24 * s, 0.6 * s), 'soul', 'blade'))
        # 주위를 맴도는 영혼 구슬 3개(프레임마다 회전)
        ph = (p.get('cape', 0) * 0.15 + p.get('bob', 0) * 0.6)
        for k in range(3):
            a = ph + k * 2.094
            c = r.chest + V(math.cos(a) * 11 * s, math.sin(a) * 11 * s, 2.0 * s + math.sin(a * 2) * 2 * s)
            it.append(Item(S.sphere(c, 1.5 * s), 'soul'))
    d = Mo.humanoid_monster('wb_lich', '심연의 리치 군주 벨카르', m, parts, opts, build, 'great', gear, WB_FRAME, lean=2)
    d['anims'] = WB_ANIMS
    return d


Mo.MONSTERS += [_wb_warlord(), _wb_lich()]


# ───────────────────────── 상점: 천상의 화로 신전 + 화로의 신 ─────────────────────────

F.PM.update({
    'marble': Mat(['#3a3633', '#5c5752', '#837d76', '#aaa39a', '#d2cbc0'], tex=lambda P, n: 0.35 * S.vnoise(P * 0.35, 77)),
    'marble_dk': Mat(['#24211f', '#3a3532', '#524b46', '#6c645d', '#867d74']),
    'gilt': Mat(['#4a2e0c', '#7c5316', '#b07d22', '#d9a83a', '#f2d36b'], metal=True, hi='#fff2b8'),
    'gilt_dk': Mat(['#2a1a0a', '#4a3010', '#6e4b1a', '#946a28', '#b88d3d'], metal=True, hi='#e3c27a'),
    'holy': Mat(['#7a4a10', '#b0741a', '#e0a83a', '#ffd870', '#fff6c8'], emit=True),
    'holyfire': Mat(['#7a1c04', '#c04a08', '#f08a1c', '#ffc040', '#fff0a0'], emit=True),
    'crimson': Mat(['#2a0608', '#4a0c10', '#6e1418', '#922024', '#b4302e'], tex=lambda P, n: 0.3 * S.vnoise(P * V(0.3, 0.3, 2.0), 31)),
    'ivory': Mat(['#4a4236', '#77705f', '#a49c88', '#cdc6b0', '#efe9d6']),
    'bronze': Mat(['#2e1a0c', '#553114', '#7d4c20', '#a86c32', '#d09450'], metal=True, hi='#ffd6a0'),
    'potion_r': Mat(['#3a0408', '#6a0a12', '#a0141e', '#d8343a', '#ff8a80'], gloss=0.8),
    'potion_b': Mat(['#04103a', '#0a206a', '#1438a0', '#3460d8', '#90b0ff'], gloss=0.8),
    'paper2': Mat(['#5e5038', '#857356', '#a99676', '#c8b796', '#e2d4b4']),
    'g_robe': Mat(['#3a3428', '#5e5644', '#857b62', '#ab9f82', '#cfc4a4']),
    'g_sash': Mat(['#3a0608', '#640c10', '#901a18', '#b82c22', '#dc4a30']),
    'g_eye': Mat(['#a06010', '#e0a030', '#ffd860', '#fff2b0', '#ffffff'], emit=True),
})


@F.prop('shrine', '천상의 화로 신전(상점)', (150, 165, 75, 120), yaw=0, scale=2.0, group='마을 생활')
def p_shrine(f):
    it = []
    # 2단 원형 단(계단)
    it.append(Item(S.cylinder(V(0, 0, 2.0), 50, 2.0, None, 0.6), 'marble_dk'))
    it.append(Item(S.cylinder(V(0, 0, 5.5), 45, 1.6, None, 0.5), 'marble'))
    it.append(Item(S.cylinder(V(0, 0, 8.6), 41, 1.5, None, 0.5), 'marble'))
    it.append(Item(S.sub(S.cylinder(V(0, 0, 10.4), 41.6, 0.5), S.cylinder(V(0, 0, 10.4), 40.4, 1.0)), 'gilt'))
    # 앞 계단 3칸(소품은 -y가 정면 = 화면 아래)
    for k in range(3):
        it.append(Item(S.box(V(0, -(44 + k * 3.4), 6.0 - k * 2.0), V(13 - k * 0.5, 3.0, 2.0), None, 0.3), 'marble'))
    # 기둥 8개(정면 두 칸은 비워 입구)
    for k in range(8):
        a = math.radians(k * 45 + 22.5)
        x, y = math.sin(a) * 33, math.cos(a) * 33
        it.append(Item(S.cylinder(V(x, y, 12), 4.6, 1.6, None, 0.4), 'marble_dk'))
        shaft = S.cylinder(V(x, y, 36), 3.4, 24)
        fl = [S.box(V(x + math.cos(math.radians(b)) * 3.5, y + math.sin(math.radians(b)) * 3.5, 36), V(0.45, 0.45, 23.5), S.rz(b)) for b in range(0, 360, 45)]
        it.append(Item(S.sub(shaft, *fl), 'marble'))
        it.append(Item(S.cylinder(V(x, y, 61), 4.8, 1.6, None, 0.4), 'gilt'))
    # 들보(고리) + 금 띠
    it.append(Item(S.sub(S.cylinder(V(0, 0, 65), 38, 3.0, None, 0.5), S.cylinder(V(0, 0, 65), 29, 4.0)), 'marble'))
    it.append(Item(S.sub(S.cylinder(V(0, 0, 64.6), 38.5, 0.9), S.cylinder(V(0, 0, 64.6), 37.5, 2.0)), 'gilt'))
    # 금빛 돔 + 첨탑 + 성화
    dome = S.inter(S.ellipsoid(V(0, 0, 68), V(36, 36, 26)), S.halfspace(V(0, 0, -1), -68))
    ribs = [S.box(V(0, 0, 80), V(0.9, 40, 16), S.rz(k * 30)) for k in range(6)]
    it.append(Item(S.sub(dome, *ribs), 'gilt'))
    it.append(Item(S.inter(dome, S.union(*ribs)), 'gilt_dk'))
    it.append(Item(S.cylinder(V(0, 0, 96), 6, 3, None, 0.5), 'gilt_dk'))
    it.append(Item(S.cone(V(0, 0, 98), V(0, 0, 114), 4.0), 'gilt'))
    fl = 1 + 0.12 * math.sin(f * math.pi / 2)
    it.append(Item(S.ellipsoid(V(0, 0, 118), V(3.2 * fl, 3.2 * fl, 5.2 * fl)), 'holyfire'))
    # 안쪽: 신성한 화로(타오르는 불) + 뒤쪽 붉은 휘장
    it.append(Item(S.cylinder(V(0, 6, 15), 9, 4, None, 0.8), 'bronze'))
    it.append(Item(S.sub(S.cylinder(V(0, 6, 20), 10, 2.2, None, 0.5), S.cylinder(V(0, 6, 21.5), 8.5, 2.5)), 'bronze'))
    for k, (dx, dy, hh) in enumerate(((0, 0, 12), (-3, 2, 8), (3, -2, 9), (1, 3, 6))):
        hh2 = hh * (1 + 0.18 * math.sin(f * math.pi / 2 + k))
        it.append(Item(S.capsule(V(dx, 6 + dy, 20), V(dx * 0.6, 6 + dy * 0.6, 20 + hh2), 3.6 - k * 0.5, 0.4), 'holyfire'))
    for k in range(3):
        a = math.radians(-30 + k * 30)
        x, y = math.sin(a) * 31, math.cos(a) * 31
        it.append(Item(S.box(V(x, y, 40), V(7.0, 0.7, 18), S.rz(-math.degrees(a)), 0.3), 'crimson'))
        it.append(Item(S.box(V(x, y, 22.5), V(7.0, 0.8, 0.8), S.rz(-math.degrees(a)), 0.3), 'gilt'))
    # 양옆 진열대: 물약·주문서·무기
    for sx in (-1, 1):
        cx, cy = sx * 30, -30
        it.append(Item(S.box(V(cx, cy, 14.5), V(9, 4.5, 4.0), S.rz(sx * 35), 0.6), 'bronze'))
        it.append(Item(S.box(V(cx, cy, 18.8), V(9.6, 5.0, 0.5), S.rz(sx * 35), 0.3), 'crimson'))
        for k in range(3):
            q = S.rz(sx * 35) @ V((k - 1) * 5.0, 0, 0)
            mat = 'potion_r' if (k + (sx > 0)) % 2 == 0 else 'potion_b'
            it.append(Item(S.sphere(V(cx, cy, 21.4) + q, 1.8), mat))
            it.append(Item(S.capsule(V(cx, cy, 22.6) + q, V(cx, cy, 24.6) + q, 0.6, 0.5), 'ivory'))
        it.append(Item(S.capsule(V(cx, cy, 20) + S.rz(sx * 35) @ V(0, 2.6, 0), V(cx, cy, 20) + S.rz(sx * 35) @ V(0, 2.6, 0) + V(0, 0, 9), 1.4), 'paper2'))
    # 정면 금빛 화로 받침 두 개(입구 양옆)
    for sx in (-1, 1):
        bx, by = sx * 17, -47
        it.append(Item(S.cylinder(V(bx, by, 9), 2.2, 9, None, 0.4), 'gilt_dk'))
        it.append(Item(S.sub(S.sphere(V(bx, by, 20), 4.0), S.halfspace(V(0, 0, -1), -20.5)), 'bronze'))
        hh = 6 + 1.8 * math.sin(f * math.pi / 2 + sx)
        it.append(Item(S.capsule(V(bx, by, 20.5), V(bx, by, 20.5 + hh), 3.0, 0.4), 'holyfire'))
    return it


@F.prop('deity', '화로의 신 헤스카르(상점 NPC)', (230, 250, 115, 222), frames=6, yaw=180, scale=1.0, group='마을 생활')
def p_deity(f):
    n = 6
    ph = 2 * math.pi * f / n
    p = Hm.pose_for('staff', 'idle', f % 6, 6)
    # 떠 있는 신: 몸 전체가 위아래로 천천히 떠다님. 오른손엔 대장장이 망치, 왼손엔 불덩이
    p.update(bob=10.0 + 1.6 * math.sin(ph), lean=-2.0, twist=0.0, head_yaw=0.0, head=-4.0,
             rsh=30, rab=26, rel=52, wpn=150, wpn_side=-6,
             lsh=62, lab=24, lel=58, plant=0)
    r = Hm.Rig(p, dict(scale=2.15, sh_w=6.6, neck=3.4, torso=7.6))
    s = r.s
    R = r.rot
    parts = dict(skin='gilt', hair=None, eyes='g_eye', torso='g_robe', pelvis='g_robe', legs='g_robe', shin='g_robe',
                 boots='g_robe', arms='gilt', farm='gilt', hands='gilt')
    it = Hm.body_items(r, p, parts, dict(no_legs=True, hair=False, chest=(6.8, 4.4, 6.0), head_r=4.4, limb=1.05))
    # 흘러내리는 로브(다리 대신 아래로 가늘어지며 불꽃이 됨)
    top = r.waist + V(0, 0, 1.0 * s)
    bot = r.waist - V(0, 0, 15.0 * s) + V(0, 1.2 * s * math.sin(ph), 0)
    robe = S.displace(S.capsule(top, bot, 6.2 * s, 2.0 * s), 0.6 * s, 0.25, seed=f + 3)
    it.append(Item(robe, 'g_robe'))
    it.append(Item(S.inter(S.shell(S.capsule(top, bot, 6.2 * s, 2.0 * s), 0.5 * s), S.halfspace(V(0, 0, 1), bot[2] + 4.0 * s)), 'gilt'))

    for k in range(3):
        a = ph + k * 2.1
        tip = bot - V(math.cos(a) * 1.4 * s, math.sin(a) * 1.4 * s, (4.0 + k * 1.6) * s)
        it.append(Item(S.capsule(bot + V(0, 0, 1.0 * s), tip, (1.8 - k * 0.4) * s, 0.2 * s), 'holyfire'))
    # 붉은 띠(어깨→허리 대각선)
    it.append(Item(S.box(r.chest + r.fwd * 4.4 * s, V(1.1 * s, 0.5 * s, 8.2 * s), R @ S.ry(30), 0.3), 'g_sash'))
    it.append(Item(S.box(r.waist + r.fwd * 0.4 * s, V(6.2 * s, 4.6 * s, 1.0 * s), R, 0.4), 'gilt'))
    # 금빛 흉갑(가슴 앞 판) + 태양 문장
    it.append(Item(S.ellipsoid(r.chest + r.fwd * 1.2 * s + r.up * 1.0 * s, V(6.6 * s, 4.2 * s, 5.4 * s), R), 'gilt'))
    it.append(Item(S.sphere(r.chest + r.fwd * 5.2 * s + r.up * 1.4 * s, 1.3 * s), 'holy'))
    # 금 가면(얼굴 위에 매끈한 판) + 태양 관
    H, HR = r.head, r.head_rot
    it.append(Item(S.ellipsoid(H + HR @ V(0, 1.4 * s, 0.2 * s), V(3.4 * s, 3.2 * s, 4.0 * s), HR), 'gilt'))
    for sx in (-1, 1):
        it.append(Item(S.box(H + HR @ V(sx * 1.4 * s, 4.4 * s, 0.4 * s), V(0.9 * s, 0.4 * s, 0.35 * s), HR, 0.1), 'g_eye'))
    cc = H + HR @ V(0, -0.3 * s, 3.4 * s)
    it.append(Item(S.sub(S.cylinder(cc, 4.2 * s, 0.8 * s, HR, 0.2), S.cylinder(cc, 3.5 * s, 2 * s, HR)), 'gilt'))
    for k in range(9):
        a = math.radians(-80 + k * 20)
        p0 = cc + HR @ V(math.sin(a) * 4.0 * s, math.cos(a) * 4.0 * s, 0.4 * s)
        it.append(Item(S.capsule(p0, p0 + HR @ V(math.sin(a) * 1.2 * s, math.cos(a) * 1.2 * s, (3.4 if k % 2 == 0 else 2.0) * s), 0.55 * s, 0.1 * s), 'gilt'))
    # 머리 뒤 후광: 천천히 도는 빛의 고리 + 빛살
    hc = H + r.fwd * (-5.0 * s) + V(0, 0, 1.0 * s)
    Mh = S.frame_from(r.fwd, V(0, 0, 1))
    it.append(Item(S.torus(hc, Mh, 9.5 * s, 0.75 * s), 'holy'))
    it.append(Item(S.torus(hc, Mh, 6.5 * s, 0.35 * s), 'holy'))
    rot = f * (360 / n / 4)
    for k in range(12):
        a = math.radians(k * 30 + rot)
        d1 = Mh @ V(math.cos(a), math.sin(a), 0)
        it.append(Item(S.capsule(hc + d1 * 10.8 * s, hc + d1 * (13.4 if k % 2 else 12.0) * s, 0.55 * s, 0.1 * s), 'holy'))
    # 날개: 어깨 뒤에서 위로 펼쳐진 깃 5장씩(천천히 숨쉬듯 열림)
    flap = 4 * math.sin(ph)
    for sx in (-1, 1):
        root = r.chest + r.fwd * (-6.5 * s) + r.right * sx * 3.4 * s + r.up * 3.0 * s
        for k in range(6):
            ang = math.radians(-5 + k * 19 + flap)
            ln = (26 - abs(k - 2.5) * 3.0) * s
            d1 = S.nrm(r.right * sx * math.cos(ang) + r.up * math.sin(ang) - r.fwd * 0.35)
            c = root + d1 * ln * 0.5
            Mf = S.frame_from(d1, r.fwd)
            it.append(Item(S.ellipsoid(c, V(1.7 * s, 0.45 * s, ln * 0.5), Mf), 'ivory'))
            it.append(Item(S.ellipsoid(root + d1 * ln * 0.92, V(1.0 * s, 0.4 * s, 2.6 * s), Mf), 'gilt'))
    # 오른손: 대장장이 망치(머리 = 큰 금속 덩이)
    w = r.wdir
    h = r.rha
    it.append(Item(S.capsule(h - w * 6 * s, h + w * 12 * s, 0.8 * s), 'bronze'))
    hd = h + w * 13 * s
    Mw = S.frame_from(w, r.fwd)
    it.append(Item(S.box(hd, V(3.6 * s, 2.4 * s, 2.4 * s), Mw @ S.ry(90), 0.6), 'gilt_dk'))
    it.append(Item(S.box(hd, V(3.9 * s, 0.6 * s, 2.6 * s), Mw @ S.ry(90), 0.2), 'holy'))
    # 왼손 위: 타오르는 불덩이
    oc = r.lha + r.up * 4.2 * s + r.fwd * 1.0 * s
    pul = 1 + 0.12 * math.sin(ph * 2)
    it.append(Item(S.sphere(oc, 2.6 * s * pul), 'holyfire'))
    for k in range(4):
        a = ph + k * 1.57
        it.append(Item(S.sphere(oc + V(math.cos(a) * 4.0 * s, math.sin(a) * 4.0 * s, math.sin(a * 2) * 1.0 * s), 0.6 * s), 'holy'))
    return it
