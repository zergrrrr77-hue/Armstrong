"""에르덴 NPC 정의 — 플레이어 직업과 같은 그림 공장(humanoid.Rig + SDF)으로 굽는다.
NPC는 싸우지 않으므로 동작은 대기 6 · 걷기 8 프레임 × 8방향만 쓴다.
시험 렌더: python3 forgotten-forge/tools/lineage/npc_preview.py
"""
import math

import numpy as np

import sdf as S
import humanoid as Hm
from sdf import V, Item, Mat

NPC_ANIMS = [('idle', 6), ('walk', 8)]   # NPC가 쓰는 동작


def smith_hammer(r, length=9.5, handle='wood', head='iron', band='g_dark'):
    """대장장이 망치: 손에서 무기 방향(r.wdir)으로 자루, 끝에 네모난 쇠머리."""
    s = r.s
    h, w = r.rha, r.wdir
    M = S.frame_from(w, r.right)                  # 로컬 z = 자루 방향
    tip = h + w * length * s
    it = [Item(S.capsule(h - w * 2.0 * s, tip, 0.85 * s, 0.75 * s), handle)]   # 자루
    it.append(Item(S.box(tip, V(3.4 * s, 1.9 * s, 1.9 * s), M, 0.35 * s), head))   # 쇠머리(자루와 직각)
    it.append(Item(S.box(tip - w * 0.2 * s, V(1.2 * s, 2.15 * s, 2.15 * s), M, 0.2 * s), band))  # 머리 고정 띠
    return it


def beard(r, mat, length=9.0, width=4.2):
    """턱에서 가슴까지 내려오는 넓은 수염 + 땋은 두 가닥."""
    s = r.s
    H, HR = r.head, r.head_rot
    hr = r.b['head_r'] * s
    it = []
    chin = H + HR @ V(0, hr * 0.55, -hr * 0.55)
    # 볼~턱을 덮는 큰 덩어리
    it.append(Item(S.ellipsoid(chin, V(width * 0.95 * s, 2.6 * s, 3.2 * s), HR), mat))
    # 가슴으로 내려오는 몸통 수염(아래로 갈수록 가늘게)
    low = chin - r.up * length * 0.62 * s + r.fwd * 1.4 * s
    it.append(Item(S.capsule(chin, low, width * 0.8 * s, width * 0.45 * s), mat))
    # 땋은 두 가닥: 마디 3개씩
    for sx in (-1, 1):
        p0 = low + r.right * sx * 1.4 * s
        for k in range(3):
            c = p0 - r.up * (1.5 + k * 1.6) * s
            it.append(Item(S.sphere(c, (1.05 - k * 0.12) * s), mat))
    # 콧수염
    it.append(Item(S.capsule(H + HR @ V(-2.4 * s, hr * 0.9, -0.9 * s), H + HR @ V(2.4 * s, hr * 0.9, -0.9 * s), 0.9 * s), mat))
    return it


def _npc_drogan():
    """드로간 — 드워프 대장장이. 짧고 굵은 몸, 넓은 어깨, 붉은 땋은 수염, 가죽 앞치마, 대장장이 망치."""
    m = dict(Hm.M_COMMON)
    m.update({
        'skin': Mat(['#4e2e22', '#7e4e38', '#a86e52', '#c88d6c', '#deab88']),   # 화로에 그을린 피부
        'beard': Mat(['#3a1306', '#5e200c', '#8a3414', '#b04a1e', '#d0682c'],
                     tex=lambda P, n: 0.45 * np.sin(P[:, 2] * 2.6 + P[:, 0] * 0.8)),  # 결 무늬
        'tunic': Mat(['#1a1e14', '#2a3120', '#3c462e', '#52603e', '#6a7a50']),  # 올리브 작업복
        'apron': Mat(['#1c1009', '#33200f', '#4c3018', '#674223', '#82562f'],
                     tex=lambda P, n: 0.35 * S.vnoise(P * 0.9, 2)),               # 그을린 두꺼운 가죽
        'eyes': Mat(['#0c0806', '#140e0a', '#1c140e', '#241a12', '#2c2016']),
    })
    parts = dict(skin='skin', hair='beard', eyes='eyes', torso='tunic', pelvis='leather', legs='tunic', shin='leather',
                 boots='iron', arms='tunic', farm='skin', hands='skin')        # 걷어붙인 소매 → 팔뚝은 맨살

    def gear(r, p, it):
        s = r.s
        H, HR = r.head, r.head_rot
        R = r.rot
        it += beard(r, 'beard', length=10.0, width=4.6)
        # 정수리는 대머리, 옆·뒤로만 머리 → 뒤통수 띠
        it.append(Item(S.ellipsoid(H + HR @ V(0, -2.2 * s, -0.6 * s), V(4.6 * s, 2.6 * s, 3.3 * s), HR), 'beard'))
        # 굵은 눈썹
        for sx in (-1, 1):
            it.append(Item(S.capsule(H + HR @ V(sx * 0.6 * s, 4.1 * s, 1.5 * s), H + HR @ V(sx * 2.8 * s, 3.7 * s, 1.9 * s), 0.7 * s), 'beard'))
        # 가죽 앞치마: 가슴부터 무릎까지, 앞쪽에만
        top = r.chest + r.fwd * 4.9 * s + r.up * 1.0 * s
        bot = r.hip + r.fwd * 5.0 * s - r.up * 9.0 * s
        mid = (top + bot) / 2
        ln = np.linalg.norm(top - bot) / 2
        it.append(Item(S.box(mid, V(5.2 * s, 0.8 * s, ln), R, 0.5 * s), 'apron'))   # 몸 방향(R) 그대로: 가로 = 어깨 방향
        # 앞치마 끈(목·허리)
        it.append(Item(S.torus(r.neck - r.up * 1.4 * s, R, 3.6 * s, 0.55 * s), 'leather'))
        it.append(Item(S.cylinder(r.waist + r.up * 0.6 * s, 6.0 * s, 0.9 * s, R, 0.3), 'leather'))
        it.append(Item(S.box(r.waist + r.up * 0.6 * s + r.fwd * 6.0 * s, V(1.3 * s, 0.5 * s, 1.1 * s), R, 0.2), 'gold'))  # 버클
        # 걷어 올린 소매 주름(팔꿈치 위)
        for sh, el in ((r.lsh, r.lel), (r.rsh, r.rel)):
            c = sh + (el - sh) * 0.8
            it.append(Item(S.torus(c, S.frame_from(S.nrm(el - sh)), 2.4 * s, 0.9 * s), 'tunic'))
        # 무쇠 팔찌(왼손)
        it.append(Item(S.torus(r.lha + (r.lel - r.lha) * 0.25, S.frame_from(S.nrm(r.lel - r.lha)), 1.9 * s, 0.6 * s), 'iron'))
        it += smith_hammer(r)

    return dict(name='npc_drogan', label='드로간', mats=m, parts=parts, gear=gear, weapon='staff',   # 지팡이 동작 곡선: 망치를 세워 든 채 걷기
                # 드워프 체형: 짧은 다리·짧은 몸통·넓은 어깨·큰 머리
                build=dict(thigh=8.0, shin=7.0, torso=12.5, sh_w=7.6, hip_w=3.9, uarm=8.4, farm=7.6, head_r=4.9, neck=3.2),
                opts=dict(limb=1.3, chest=(8.4, 5.4, 6.0), belly=(6.4, 7.0), pelvis=(6.2, 4.4, 4.2), jaw=False))


def backpack(r, bag, roll, strap):
    """상인의 등짐: 네모난 짐 + 위에 말아 얹은 담요 + 어깨끈."""
    s = r.s
    R = r.rot
    back = -r.fwd
    c = r.chest + back * 6.2 * s - r.up * 1.0 * s
    it = [Item(S.box(c, V(4.6 * s, 2.6 * s, 5.4 * s), R, 0.8 * s), bag)]
    it.append(Item(S.capsule(c + r.up * 6.4 * s - r.right * 5.6 * s, c + r.up * 6.4 * s + r.right * 5.6 * s, 1.9 * s), roll))
    for sx in (-1, 1):
        it.append(Item(S.capsule(r.chest + r.up * 4.2 * s + r.right * sx * 3.0 * s + r.fwd * 2.0 * s,
                                 r.chest - r.up * 3.0 * s + r.right * sx * 3.4 * s + r.fwd * 3.8 * s, 0.6 * s), strap))
    return it


def _npc_arden():
    """아르덴 — 몰락한 기사단장. 희끗한 짧은 머리·수염, 낡고 어두운 갑옷, 금장식 없는 해진 남색 망토."""
    m = dict(Hm.M_COMMON)
    m.update({
        'skin': Mat(['#4e3428', '#7c5440', '#a2765c', '#c09276', '#d8ae90']),
        'grey': Mat(['#2a2a2c', '#4a4a4e', '#6e6e72', '#929296', '#b8b8ba']),          # 희끗한 머리·수염
        'navy': Mat(['#0a0e18', '#121a2a', '#1c283e', '#283852', '#364866'],
                    tex=lambda P, n: 0.4 * S.vnoise(P * 0.8, 3)),                       # 바랜 남색 천
        'oldsteel': Mat(['#17191d', '#272a30', '#3a3e46', '#525760', '#6c727c'], metal=True, hi='#a4abb6',
                        tex=lambda P, n: 0.35 * S.vnoise(P * 1.6, 5)),                  # 흠집 난 강철
        'mail': Mat(['#1a1c20', '#2a2d33', '#3e424a', '#565b64', '#6e747e'], metal=True,
                    tex=lambda P, n: 0.6 * ((np.floor(P[:, 2] * 0.9) + np.floor(P[:, 0] * 0.9)) % 2 - 0.5)),
    })
    parts = dict(skin='skin', hair='grey', eyes='eyes', torso='oldsteel', pelvis='mail', legs='mail', shin='oldsteel',
                 boots='steel_dk', arms='mail', farm='oldsteel', hands='leather')

    def gear(r, p, it):
        s = r.s
        H, HR = r.head, r.head_rot
        R = r.rot
        # 짧게 친 희끗한 머리 + 짧은 수염(턱·볼)
        it.append(Item(S.ellipsoid(H + HR @ V(0, -1.0 * s, 1.0 * s), V(4.5 * s, 4.4 * s, 4.0 * s), HR), 'grey'))
        it.append(Item(S.ellipsoid(H + HR @ V(0, 2.2 * s, -2.4 * s), V(3.6 * s, 2.4 * s, 2.0 * s), HR), 'grey'))
        it += Hm.pauldrons(r, 'oldsteel', 3.6, trim=None)                                   # 금테 없는 어깨
        it += Hm.cape(r, p, 'navy', length=30, width=6.8, tatter=True)                  # 해진 망토
        it += Hm.skirt(r, 'mail', 5.4, 6.6, 9.0)
        # 갑옷 위에 걸친 남색 겉옷(기사단 서코트): 가슴부터 무릎까지, 플레이어 기사와 구별되는 실루엣
        top = r.chest + r.fwd * 4.6 * s + r.up * 2.6 * s
        bot = r.hip + r.fwd * 4.6 * s - r.up * 8.0 * s
        it.append(Item(S.box((top + bot) / 2, V(4.4 * s, 0.7 * s, np.linalg.norm(top - bot) / 2), R, 0.5 * s), 'navy'))
        # 가슴의 옛 기사단 문장(빛바랜 은색 방패꼴)
        it.append(Item(S.box(r.chest + r.fwd * 5.4 * s + r.up * 0.2 * s, V(1.6 * s, 0.4 * s, 1.6 * s), R @ S.ry(45), 0.3 * s), 'grey'))
        it.append(Item(S.box(r.waist + r.up * 0.4 * s, V(5.4 * s, 4.4 * s, 0.9 * s), R, 0.4), 'leather'))
        it += Hm.broadsword(r, 18.0, 2.0, guard='steel_dk', grip='leather', blade='oldsteel', pommel='steel_dk')

    return dict(name='npc_arden', label='아르덴', mats=m, parts=parts, gear=gear, weapon='blade',
                build=dict(scale=1.02), opts=dict(limb=1.1, chest=(7.0, 4.5, 5.9), belly=(4.9, 5.7)))


def _npc_seria():
    """세리아 — 정체불명의 상인. 상아빛 후드 로브, 은발, 등짐, 따뜻한 빛의 등불 지팡이."""
    m = dict(Hm.M_COMMON)
    m.update({
        'skin': Mat(['#6a5450', '#9c827a', '#c6aca2', '#e2cec4', '#f6ebe4']),           # 창백한 피부
        'ivory': Mat(['#4a4038', '#7a6e62', '#a89a8a', '#d0c4b2', '#ece4d6']),
        'lilac': Mat(['#241a30', '#3a2c4c', '#54426a', '#6e5a88', '#8c78a6']),
        'silver': Mat(['#5a5c66', '#868892', '#aeb0ba', '#d0d2da', '#eeeff4']),
        'lamp': Mat(['#8a3a0a', '#c8641a', '#f09a34', '#ffc866', '#fff0c0'], emit=True),
        'brass': Mat(['#3a2a10', '#5e4418', '#8a6626', '#b88c3a', '#dcb460'], metal=True, hi='#fff0b8'),
    })
    parts = dict(skin='skin', hair='silver', eyes='eyes', torso='lilac', pelvis='ivory', legs='ivory', shin='ivory',
                 boots='leather', arms='ivory', farm='ivory', hands='skin')

    def gear(r, p, it):
        s = r.s
        it += Hm.long_hair(r, 'silver', length=12, width=3.6, flow=p.cape * 0.6)
        it += Hm.robe(r, p, 'ivory', 'lilac')
        it += Hm.hood(r, 'ivory', peak=True)
        it += Hm.cape(r, p, 'ivory', length=26, width=6.4)
        it += backpack(r, 'leather_lt', 'lilac', 'leather')
        # 허리끈 + 주머니
        it.append(Item(S.cylinder(r.waist + r.up * 0.8 * s, 5.0 * s, 0.7 * s, r.rot, 0.3), 'lilac'))
        it.append(Item(S.box(r.waist + r.right * 4.6 * s + r.fwd * 1.5 * s - r.up * 1.6 * s, V(1.3 * s, 1.0 * s, 1.6 * s), r.rot, 0.4 * s), 'leather'))
        it += Hm.staff(r, 'wood', 'lamp', 'brass', 30)                                    # 등불 지팡이

    return dict(name='npc_seria', label='세리아', mats=m, parts=parts, gear=gear, weapon='staff',
                build=dict(scale=0.97, sh_w=5.9, hip_w=3.2), opts=dict(no_legs=True, chest=(5.6, 3.7, 5.0)))


def _npc_belos():
    """벨로스 — 추방된 대마법사. 300년 전 금지 의식의 대가로 왼팔이 별의 파편처럼 결정화됐다.
    두건 없이 드러난 민머리와 이마의 봉인 문양, 끊어진 족쇄, 사슬로 묶은 금서, 파편이 떠도는 갈고리 지팡이."""
    m = dict(Hm.M_COMMON)
    m.update({
        'skin': Mat(['#4a3a34', '#76605a', '#9e8680', '#bca49c', '#d4bfb6']),
        'ash': Mat(['#3e3e42', '#646468', '#8c8c90', '#b2b2b4', '#d4d4d4']),             # 잿빛 머리·수염
        'robe': Mat(['#141416', '#222226', '#34343a', '#48484f', '#5e5e66'],
                    tex=lambda P, n: 0.45 * S.vnoise(P * 0.7, 9)),                      # 재가 앉은 회흑색 겉로브
        'crimson': Mat(['#1e0408', '#36080e', '#520e16', '#701820', '#8e242a']),        # 안감·허리띠: 검붉은 색
        'shard': Mat(['#1a0636', '#3a1270', '#6a2cc0', '#a46cf0', '#e8d0ff'], emit=True, gloss=1.0),  # 결정화된 별의 파편
        'rune': Mat(['#3a0a6a', '#6a20b0', '#9a50e8', '#c890ff', '#f0e0ff'], emit=True),
        'tome': Mat(['#160c0a', '#281612', '#3c221a', '#523024', '#6a402e']),
        'gnarl': Mat(['#140c08', '#22160e', '#342216', '#48301e', '#5c3e28'],
                     tex=lambda P, n: 0.6 * S.vnoise(P * 2.2, 4)),
    })
    parts = dict(skin='skin', hair='ash', eyes='eyes', torso='robe', pelvis='robe', legs='robe', shin='robe',
                 boots='leather', arms='robe', farm='robe', hands='skin')

    def gear(r, p, it):
        s = r.s
        H, HR = r.head, r.head_rot
        R = r.rot
        hr = r.b['head_r'] * s
        # 머리: 정수리는 민머리, 뒤로 길게 늘어진 잿빛 머리 + 가슴까지 오는 수염
        it.append(Item(S.ellipsoid(H + HR @ V(0, -2.4 * s, -0.4 * s), V(4.6 * s, 2.4 * s, 3.4 * s), HR), 'ash'))
        it.append(Item(S.capsule(H + HR @ V(0, -3.0 * s, -1.0 * s), H + HR @ V(0, -4.6 * s, -11.0 * s), 3.0 * s, 1.8 * s), 'ash'))
        it += beard(r, 'ash', length=14.0, width=3.8)
        it.append(Item(S.sphere(H + HR @ V(0, hr * 0.92, 2.2 * s), 0.85 * s), 'rune'))   # 이마의 봉인 문양
        # 겉로브(회흑) + 검붉은 안감 테두리 + 해진 망토
        it += Hm.robe(r, p, 'robe', 'crimson')
        it += Hm.cape(r, p, 'robe', length=30, width=7.0, tatter=True, split=True)
        it.append(Item(S.torus(r.neck - r.up * 1.6 * s, R, 4.0 * s, 1.3 * s), 'crimson'))   # 목 둘레 검붉은 깃
        it.append(Item(S.cylinder(r.waist + r.up * 0.8 * s, 5.4 * s, 1.1 * s, R, 0.3), 'crimson'))   # 허리띠
        # 왼팔 결정화: 팔뚝을 따라 솟은 보랏빛 결정 + 손 끝 결정
        el, ha = r.lel, r.lha
        ax = S.nrm(ha - el)
        for k, (u, ln, rad) in enumerate(((0.0, 4.4, 1.3), (0.3, 5.6, 1.5), (0.6, 5.0, 1.4), (0.9, 4.0, 1.2), (1.05, 3.4, 1.1))):
            c = el + (ha - el) * u
            out = S.nrm(np.cross(ax, r.up if k % 2 else r.fwd)) * (1 if k % 2 else -1)
            it.append(Item(S.capsule(c, c + (out * 0.8 + ax * 0.6) * ln * s, rad * s, 0.15 * s), 'shard'))
        it.append(Item(S.capsule(el - (ha - el) * 0.25, ha, 2.5 * s, 2.2 * s), 'shard'))   # 소매 밖으로 드러난 결정 팔
        # 오른 손목: 끊어진 족쇄 + 늘어진 사슬 세 고리
        cuff = r.rha + (r.rel - r.rha) * 0.25
        it.append(Item(S.torus(cuff, S.frame_from(S.nrm(r.rel - r.rha)), 1.9 * s, 0.7 * s), 'iron'))
        for k in range(3):
            c = cuff - r.up * (2.0 + k * 1.6) * s + r.fwd * 0.4 * s * k
            it.append(Item(S.torus(c, R @ (S.rx(90) if k % 2 else S.ry(90)), 0.9 * s, 0.35 * s), 'iron'))
        # 허리에 사슬로 묶은 금서
        bk = r.waist + r.right * 5.6 * s + r.fwd * 1.2 * s - r.up * 3.0 * s
        it.append(Item(S.box(bk, V(1.2 * s, 2.6 * s, 3.2 * s), R, 0.3 * s), 'tome'))
        it.append(Item(S.box(bk, V(1.35 * s, 2.75 * s, 0.4 * s), R, 0.1 * s), 'iron'))
        it.append(Item(S.sphere(bk + r.right * 1.3 * s, 0.6 * s), 'rune'))
        # 지팡이: 끝이 갈고리처럼 휜 나무 + 주위를 떠도는 파편 3개
        h, w = r.rha, r.wdir
        top = h + w * 22 * s
        it.append(Item(S.capsule(h - w * 12 * s, top, 0.9 * s, 1.1 * s), 'gnarl'))
        hook = top + w * 3.0 * s + r.fwd * 3.0 * s
        it.append(Item(S.capsule(top, hook, 1.0 * s, 0.8 * s), 'gnarl'))
        it.append(Item(S.capsule(hook, hook + r.fwd * 1.5 * s - w * 2.5 * s, 0.8 * s, 0.4 * s), 'gnarl'))
        orb = top + r.fwd * 1.6 * s + w * 0.6 * s
        for k in range(3):
            a = math.radians(k * 120 + 20)
            c = orb + (r.right * math.cos(a) + r.fwd * math.sin(a)) * 3.4 * s + w * (k - 1) * 1.2 * s
            it.append(Item(S.capsule(c - w * 1.6 * s, c + w * 1.6 * s, 1.15 * s, 0.15 * s), 'shard'))

    return dict(name='npc_belos', label='벨로스', mats=m, parts=parts, gear=gear, weapon='staff',
                build=dict(scale=1.0, torso=14.0), opts=dict(no_legs=True, chest=(5.8, 3.8, 5.0), jaw=False))


def _npc_elysia():
    """엘리시아 — 엘라시아 숲의 수호자. 요정 직업 뼈대 그대로, 은발 + 은빛·옅은 녹색 잎 갑옷 + 긴 망토."""
    base = Hm._class_elf()
    m = dict(base['mats'])
    m.update({
        'hair': Mat(['#6a7072', '#9aa2a4', '#c4ccce', '#e2e8e8', '#f6fafa']),             # 은발
        'leafarmor': Mat(['#0c1c18', '#18302a', '#26483e', '#386456', '#4e8270'], gloss=0.4),  # 청록 잎
        'leaf2': Mat(['#3a4a40', '#5e7266', '#86988c', '#b0c0b4', '#dae6dc']),           # 은빛 잎
        'inner': Mat(['#0e1a22', '#182a36', '#243c4c', '#325062', '#42667a']),
        'gem': Mat(['#0a3a20', '#146038', '#1e8c50', '#40c078', '#a8f0c8'], gloss=1.0, emit=True),  # 숲의 보석
        'bowwood': Mat(['#2a2a24', '#4a4a3e', '#6e6c5a', '#929078', '#b8b49a'], gloss=0.4),  # 흰 자작나무 활
    })
    d = dict(base)
    d.update(name='npc_elysia', label='엘리시아', mats=m)
    return d



# ───────────────────────── 마을 사람 7명용 작은 도구 ─────────────────────────


def short_hair(r, mat, back=1.0):
    """짧은 머리: 정수리·뒤통수를 덮는 모자 모양."""
    s = r.s
    H, HR = r.head, r.head_rot
    return [Item(S.ellipsoid(H + HR @ V(0, -0.9 * s, 0.9 * s), V(4.6 * s, 4.5 * s * back, 4.3 * s), HR), mat)]


def bun(r, mat):
    """뒤로 틀어 올린 머리."""
    s = r.s
    H, HR = r.head, r.head_rot
    return short_hair(r, mat) + [Item(S.sphere(H + HR @ V(0, -4.4 * s, 2.4 * s), 2.4 * s), mat)]


def pigtails(r, mat):
    """양 갈래 머리(아이)."""
    s = r.s
    H, HR = r.head, r.head_rot
    it = short_hair(r, mat)
    for sx in (-1, 1):
        a0 = H + HR @ V(sx * 4.2 * s, -1.6 * s, 1.0 * s)
        it.append(Item(S.capsule(a0, a0 + HR @ V(sx * 1.6 * s, -1.0 * s, -6.5 * s), 1.5 * s, 1.0 * s), mat))
    return it


def apron_front(r, mat, top_up=1.0, bot_down=9.0, wide=4.6):
    """몸 앞쪽에만 대는 앞치마."""
    s = r.s
    top = r.chest + r.fwd * 4.9 * s + r.up * top_up * s
    bot = r.hip + r.fwd * 5.4 * s - r.up * bot_down * s
    return [Item(S.box((top + bot) / 2, V(wide * s, 0.7 * s, np.linalg.norm(top - bot) / 2), r.rot, 0.5 * s), mat)]


def straw_hat(r, mat, band):
    s = r.s
    H, HR = r.head, r.head_rot
    hr = r.b['head_r'] * s
    return [Item(S.cylinder(H + HR @ V(0, 0, hr * 0.7), hr * 2.3, 0.4 * s, HR, 0.3), mat),
            Item(S.ellipsoid(H + HR @ V(0, 0, hr * 1.0), V(hr * 1.05, hr * 1.05, hr * 0.8), HR), mat),
            Item(S.cylinder(H + HR @ V(0, 0, hr * 0.95), hr * 1.07, 0.6 * s, HR, 0.2), band)]


def basket(r, wicker, fill):
    """오른손에 든 바구니(약초·꽃이 담김)."""
    s = r.s
    c = r.rha - r.up * 3.6 * s
    body = S.sub(S.cylinder(c, 3.0 * s, 2.2 * s, r.rot, 0.6 * s), S.cylinder(c + r.up * 1.0 * s, 2.5 * s, 2.0 * s, r.rot, 0.2))
    it = [Item(body, wicker), Item(S.torus(r.rha - r.up * 0.6 * s, r.rot @ S.rx(90), 2.6 * s, 0.4 * s), wicker)]
    for k in range(4):
        a = math.radians(k * 90 + 30)
        it.append(Item(S.sphere(c + r.up * 1.6 * s + (r.right * math.cos(a) + r.fwd * math.sin(a)) * 1.4 * s, 1.1 * s), fill))
    return it


def mug(r, mat, foam):
    s = r.s
    c = r.rha + r.up * 1.4 * s + r.fwd * 0.6 * s
    return [Item(S.cylinder(c, 1.5 * s, 2.0 * s, r.rot, 0.3 * s), mat),
            Item(S.cylinder(c + r.up * 2.1 * s, 1.55 * s, 0.6 * s, r.rot, 0.4 * s), foam)]


def pole(r, wood, length=36):
    """오른손에 세워 든 긴 자루(창·쇠스랑의 몸통). 끝 위치를 돌려준다."""
    s = r.s
    h, w = r.rha, r.wdir
    top = h + w * (length * 0.62) * s
    return [Item(S.capsule(h - w * (length * 0.38) * s, top, 0.8 * s, 0.8 * s), wood)], top


def _base_mats(**kw):
    m = dict(Hm.M_COMMON)
    m.update({k: v for k, v in kw.items()})
    return m


def _npc_rowen():
    """로웬 — 기사단 초소 경비대장. 푸른 깃털 투구, 푸른 망토, 세워 든 창."""
    m = _base_mats(
        blue=Mat(['#081226', '#0e1e40', '#16305e', '#22447e', '#325a9c']),
        plume=Mat(['#0a1a40', '#14306a', '#2050a0', '#3a78d0', '#7ab0f0']),
        mail=Mat(['#1d2026', '#30343c', '#474c56', '#626874', '#7d8491'], metal=True,
                 tex=lambda P, n: 0.6 * ((np.floor(P[:, 2] * 0.9) + np.floor(P[:, 0] * 0.9)) % 2 - 0.5)))
    parts = dict(skin='skin', hair='leather', eyes='eyes', torso='steel', pelvis='mail', legs='mail', shin='steel',
                 boots='steel_dk', arms='mail', farm='steel', hands='steel_dk')

    def gear(r, p, it):
        s = r.s
        it += Hm.helmet_knight(r, 'steel', 'steel_dk', plume='plume')
        it += Hm.pauldrons(r, 'steel', 3.5, trim='blue')
        it += Hm.cape(r, p, 'blue', length=28, width=6.4)
        it += Hm.skirt(r, 'blue', 5.4, 6.6, 9.0)
        it.append(Item(S.box(r.waist + r.up * 0.4 * s, V(5.4 * s, 4.4 * s, 0.9 * s), r.rot, 0.4), 'leather'))
        sh, top = pole(r, 'wood', 40)
        it += sh
        w = r.wdir
        it.append(Item(S.capsule(top, top + w * 4.5 * s, 1.1 * s, 0.1 * s), 'steel'))     # 창날
        it.append(Item(S.box(top - w * 0.3 * s, V(1.4 * s, 0.6 * s, 0.4 * s), S.frame_from(w, r.right), 0.2), 'gold'))

    return dict(name='npc_rowen', label='로웬', mats=m, parts=parts, gear=gear, weapon='staff',
                build=dict(scale=1.02), opts=dict(limb=1.1, chest=(7.0, 4.5, 5.9), belly=(4.9, 5.7)))


def _npc_maren():
    """마렌 — 약초상. 땋아 내린 갈색 머리, 연두 두건, 녹색 원피스와 흰 앞치마, 약초 바구니."""
    m = _base_mats(
        skin=Mat(['#5e443a', '#93705e', '#c09c86', '#ddc1ab', '#f2dfcd']),
        hairb=Mat(['#1e100a', '#341c10', '#4c2a18', '#663a22', '#80502e']),
        dress=Mat(['#0e1c10', '#18301a', '#244626', '#325e34', '#447a44']),
        linen=Mat(['#5a5448', '#8a8270', '#b4ac98', '#d6d0bc', '#f0ecdc']),
        scarf=Mat(['#2a3a10', '#425a1a', '#5e7e26', '#7ca236', '#a0c84e']),
        wicker=Mat(['#3a2810', '#5a4018', '#7c5a24', '#9c7632', '#ba9444']),
        herb=Mat(['#163a10', '#22561a', '#327a24', '#48a030', '#70c84a']))
    parts = dict(skin='skin', hair='hairb', eyes='eyes', torso='dress', pelvis='dress', legs='dress', shin='dress',
                 boots='leather', arms='dress', farm='linen', hands='skin')

    def gear(r, p, it):
        s = r.s
        it += Hm.long_hair(r, 'hairb', length=14, width=2.6, flow=p.cape * 0.6, side_locks=False)
        it += Hm.hood(r, 'scarf', peak=False)[:1]                                         # 두건(머리만)
        it += Hm.robe(r, p, 'dress', 'scarf')
        it += apron_front(r, 'linen', 0.0, 12.0, 4.2)
        it += basket(r, 'wicker', 'herb')

    return dict(name='npc_maren', label='마렌', mats=m, parts=parts, gear=gear, weapon='staff',
                build=dict(scale=0.95, sh_w=5.6, hip_w=3.2), opts=dict(no_legs=True, chest=(5.4, 3.6, 4.8), belly=(3.9, 4.6)))


def _npc_erin():
    """에린 — 여관 주인. 틀어 올린 붉은 머리, 포도주색 드레스, 흰 앞치마, 손에 든 맥주잔."""
    m = _base_mats(
        skin=Mat(['#6a4a3c', '#9c7462', '#c69c86', '#e2bea8', '#f6dccc']),
        ginger=Mat(['#3a0e04', '#5e1c08', '#86300e', '#ac4818', '#cc6a2a']),
        wine=Mat(['#1e060e', '#360c1a', '#521428', '#6e1e38', '#8a2c4a']),
        linen=Mat(['#5a5448', '#8a8270', '#b4ac98', '#d6d0bc', '#f0ecdc']),
        foam=Mat(['#8a8678', '#b4b0a2', '#d6d2c6', '#ece8de', '#fbf8f0']))
    parts = dict(skin='skin', hair='ginger', eyes='eyes', torso='wine', pelvis='wine', legs='wine', shin='wine',
                 boots='leather', arms='linen', farm='skin', hands='skin')

    def gear(r, p, it):
        it += bun(r, 'ginger')
        it += Hm.robe(r, p, 'wine', 'linen')
        it += apron_front(r, 'linen', -1.0, 12.0, 4.8)
        it += mug(r, 'wood', 'foam')

    return dict(name='npc_erin', label='에린', mats=m, parts=parts, gear=gear, weapon='staff',
                build=dict(scale=0.97, sh_w=6.0, hip_w=3.4), opts=dict(no_legs=True, chest=(6.2, 4.4, 5.0), belly=(5.0, 5.8)))


def _npc_thomas():
    """토마스 — 농부. 밀짚모자, 흙빛 작업복, 멜빵, 세워 든 쇠스랑."""
    m = _base_mats(
        skin=Mat(['#4e3022', '#7c5038', '#a6724e', '#c69068', '#dcac84']),
        straw=Mat(['#5a4414', '#8a6a24', '#b8923a', '#d8b65a', '#f0d888']),
        tunic=Mat(['#2a1e12', '#42301e', '#5c442c', '#76583a', '#8e6e4a']),
        pants=Mat(['#141a22', '#202a36', '#2e3c4c', '#3e5062', '#50667a']),
        band=Mat(['#3a0a08', '#5a1410', '#7c2018', '#9a2e22', '#b84030']))
    parts = dict(skin='skin', hair='leather', eyes='eyes', torso='tunic', pelvis='pants', legs='pants', shin='pants',
                 boots='leather', arms='tunic', farm='skin', hands='skin')

    def gear(r, p, it):
        s = r.s
        it += straw_hat(r, 'straw', 'band')
        for sx in (-1, 1):                                                                  # 멜빵
            it.append(Item(S.capsule(r.chest + r.up * 4.0 * s + r.right * sx * 2.6 * s + r.fwd * 3.6 * s,
                                     r.waist + r.right * sx * 2.6 * s + r.fwd * 4.6 * s, 0.6 * s), 'pants'))
        sh, top = pole(r, 'wood', 38)
        it += sh
        w = r.wdir
        M = S.frame_from(w, r.right)
        it.append(Item(S.box(top, V(3.0 * s, 0.5 * s, 0.5 * s), M, 0.2), 'iron'))          # 쇠스랑 가로대
        for k in (-1, 0, 1):
            b0 = top + M[:, 0] * k * 2.6 * s
            it.append(Item(S.capsule(b0, b0 + w * 5.5 * s, 0.45 * s, 0.15 * s), 'iron'))

    return dict(name='npc_thomas', label='토마스', mats=m, parts=parts, gear=gear, weapon='staff',
                build=dict(scale=0.98), opts=dict(limb=1.05, chest=(6.6, 4.4, 5.6), belly=(5.4, 6.2)))


def _npc_garen():
    """가렌 — 무기점 주인. 우람한 체격, 붉은 두건, 짧은 갈색 수염, 가죽 조끼, 어깨에 멘 넓은 검."""
    m = _base_mats(
        skin=Mat(['#4e3022', '#7c5038', '#a6724e', '#c69068', '#dcac84']),
        brown=Mat(['#1a0e08', '#2e1a0e', '#462816', '#5e3820', '#784a2c']),
        red=Mat(['#2c0607', '#4a0c0e', '#6c1416', '#8f1f1f', '#b0302a']),
        shirt=Mat(['#3a3428', '#5a5240', '#7a705a', '#9a8e74', '#b8ac90']))
    parts = dict(skin='skin', hair='brown', eyes='eyes', torso='shirt', pelvis='leather', legs='brown', shin='leather',
                 boots='leather', arms='skin', farm='skin', hands='leather')

    def gear(r, p, it):
        s = r.s
        H, HR = r.head, r.head_rot
        it.append(Item(S.ellipsoid(H + HR @ V(0, -0.6 * s, 1.2 * s), V(4.7 * s, 4.6 * s, 3.8 * s), HR), 'red'))    # 두건
        it.append(Item(S.capsule(H + HR @ V(0, -4.2 * s, 1.0 * s), H + HR @ V(1.0 * s, -6.5 * s, -2.5 * s), 1.0 * s, 0.5 * s), 'red'))
        it.append(Item(S.ellipsoid(H + HR @ V(0, 2.4 * s, -2.6 * s), V(3.8 * s, 2.6 * s, 2.4 * s), HR), 'brown'))   # 짧은 수염
        it.append(Item(S.ellipsoid(r.chest + r.rot @ V(0, 0.6 * s, 0.6 * s), V(7.4 * s, 5.0 * s, 6.0 * s), r.rot), 'leather'))  # 가죽 조끼
        it.append(Item(S.box(r.waist + r.up * 0.4 * s, V(6.0 * s, 4.8 * s, 1.0 * s), r.rot, 0.4), 'brown'))
        it += Hm.broadsword(r, 19.0, 2.4, guard='iron', grip='leather', blade='steel', pommel='iron')

    return dict(name='npc_garen', label='가렌', mats=m, parts=parts, gear=gear, weapon='blade',
                build=dict(scale=1.08, sh_w=7.2), opts=dict(limb=1.25, chest=(7.8, 5.2, 6.2), belly=(6.0, 6.6)))


def _npc_lia():
    """리아 — 노엘의 여동생. 아이 체형(큰 머리·짧은 팔다리), 양 갈래 머리, 분홍 원피스, 꽃 바구니."""
    m = _base_mats(
        skin=Mat(['#6a4a3c', '#9c7462', '#c69c86', '#e2bea8', '#f6dccc']),
        hairb=Mat(['#2a160a', '#442410', '#60361a', '#7c4a24', '#985e30']),
        pink=Mat(['#3a0e1e', '#5e1a32', '#86284a', '#ac3c64', '#d05a84']),
        linen=Mat(['#5a5448', '#8a8270', '#b4ac98', '#d6d0bc', '#f0ecdc']),
        wicker=Mat(['#3a2810', '#5a4018', '#7c5a24', '#9c7632', '#ba9444']),
        flower=Mat(['#5a2a06', '#a04a0a', '#e08a18', '#f8c040', '#fff0a0'], emit=False))
    parts = dict(skin='skin', hair='hairb', eyes='eyes', torso='pink', pelvis='pink', legs='pink', shin='pink',
                 boots='leather', arms='pink', farm='skin', hands='skin')

    def gear(r, p, it):
        it += pigtails(r, 'hairb')
        it += Hm.robe(r, p, 'pink', 'linen')
        it += basket(r, 'wicker', 'flower')

    return dict(name='npc_lia', label='리아', mats=m, parts=parts, gear=gear, weapon='staff',
                build=dict(scale=0.78, head_r=5.2, sh_w=5.0, hip_w=3.0, torso=13.0),
                opts=dict(no_legs=True, chest=(5.0, 3.4, 4.4), belly=(3.8, 4.4)))


def _npc_noel():
    """노엘 — 사라진 정찰병, 리아의 오빠. 올리브 두건 망토, 가죽 경갑, 손에 든 짧은 활."""
    m = _base_mats(
        skin=Mat(['#6a4a3c', '#9c7462', '#c69c86', '#e2bea8', '#f6dccc']),
        hairb=Mat(['#2a160a', '#442410', '#60361a', '#7c4a24', '#985e30']),
        olive=Mat(['#141a0c', '#222c14', '#323f1e', '#44542a', '#586c38'],
                  tex=lambda P, n: 0.35 * S.vnoise(P * 0.9, 6)),
        fletch=Mat(['#3a2a1a', '#5a4430', '#7a6048', '#9a7c60', '#b89a7c']))
    parts = dict(skin='skin', hair='hairb', eyes='eyes', torso='leather_lt', pelvis='leather', legs='olive', shin='leather',
                 boots='leather', arms='olive', farm='leather_lt', hands='leather')

    def gear(r, p, it):
        it += short_hair(r, 'hairb')
        it += Hm.hood(r, 'olive', peak=True)
        it += Hm.cape(r, p, 'olive', length=24, width=5.6, tatter=True)
        it += Hm.quiver(r, 'leather', 'fletch')
        it += Hm.bow(r, 'wood', 'string', draw=p.draw)

    return dict(name='npc_noel', label='노엘', mats=m, parts=parts, gear=gear, weapon='bow',
                build=dict(scale=0.96, sh_w=6.0), opts=dict(limb=0.95, chest=(6.0, 4.0, 5.2), belly=(4.4, 5.0)))


NPCS = [_npc_drogan(), _npc_arden(), _npc_seria(), _npc_belos(), _npc_elysia(),
        _npc_rowen(), _npc_maren(), _npc_erin(), _npc_thomas(), _npc_garen(), _npc_lia(), _npc_noel()]
