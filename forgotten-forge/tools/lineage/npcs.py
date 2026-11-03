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
    """벨로스 — 추방된 대마법사. 긴 잿빛 수염, 해진 짙은 보라 두건 로브, 뒤틀린 지팡이에 희미한 보랏빛."""
    m = dict(Hm.M_COMMON)
    m.update({
        'skin': Mat(['#4a3a34', '#76605a', '#9e8680', '#bca49c', '#d4bfb6']),
        'ash': Mat(['#3e3e42', '#646468', '#8c8c90', '#b2b2b4', '#d4d4d4']),             # 잿빛 수염
        'violet': Mat(['#100818', '#1c0e2a', '#2a1640', '#3a2056', '#4c2c6c'],
                      tex=lambda P, n: 0.4 * S.vnoise(P * 0.7, 9)),
        'dimtrim': Mat(['#241c10', '#3a2e1a', '#524228', '#6a5838', '#82704a'], metal=True, hi='#b8a478'),  # 빛바랜 금테
        'void': Mat(['#2a0a4a', '#4a167a', '#7030b0', '#a060e0', '#d8b0ff'], emit=True),
        'gnarl': Mat(['#140c08', '#22160e', '#342216', '#48301e', '#5c3e28'],
                     tex=lambda P, n: 0.6 * S.vnoise(P * 2.2, 4)),
    })
    parts = dict(skin='skin', hair='ash', eyes='eyes', torso='violet', pelvis='violet', legs='violet', shin='violet',
                 boots='leather', arms='violet', farm='violet', hands='skin')

    def gear(r, p, it):
        s = r.s
        it += beard(r, 'ash', length=13.0, width=4.0)                                     # 가슴까지 오는 수염
        it += Hm.robe(r, p, 'violet', 'dimtrim')
        it += Hm.hood(r, 'violet', peak=False)
        it += Hm.cape(r, p, 'violet', length=30, width=6.6, tatter=True)
        it += Hm.pauldrons(r, 'violet', 3.0, trim='dimtrim')
        # 목에 건 봉인 사슬 메달
        it.append(Item(S.torus(r.neck - r.up * 2.0 * s + r.fwd * 1.0 * s, r.rot @ S.rx(25), 3.6 * s, 0.4 * s), 'iron'))
        it.append(Item(S.sphere(r.chest + r.fwd * 5.0 * s + r.up * 0.5 * s, 1.0 * s), 'void'))
        it += Hm.staff(r, 'gnarl', 'void', 'gnarl', 34)

    return dict(name='npc_belos', label='벨로스', mats=m, parts=parts, gear=gear, weapon='staff',
                build=dict(scale=1.0), opts=dict(no_legs=True, chest=(6.0, 3.9, 5.2), jaw=False))


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


NPCS = [_npc_drogan(), _npc_arden(), _npc_seria(), _npc_belos(), _npc_elysia()]
