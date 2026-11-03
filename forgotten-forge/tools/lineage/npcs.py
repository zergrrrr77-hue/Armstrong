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


NPCS = [_npc_drogan()]
