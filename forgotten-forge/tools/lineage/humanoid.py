"""사람형 리그(7등신) + 클래스 장비 + 동작.

관절은 물체 공간(정면 +y, 오른쪽 +x, 위 +z)에서 계산한다. 키 약 53 단위 → 화면 약 46px.
"""
import math

import numpy as np

import sdf as S
from sdf import V, Item, Mat, ramp_from

D2R = math.pi / 180.0


def sagittal(a_deg, side_deg=0.0, side=1):
    """a: 아래(0°)에서 앞(90°)으로 젖힌 각, side: 바깥쪽으로 벌린 각."""
    a = a_deg * D2R
    c = side_deg * D2R
    return V(side * math.sin(c), math.sin(a) * math.cos(c), -math.cos(a) * math.cos(c))


class Pose(dict):
    DEFAULT = dict(
        bob=0.0, lean=0.0, twist=0.0, roll=0.0,
        lhip=0.0, rhip=0.0, lknee=4.0, rknee=4.0, lhip_side=0.0, rhip_side=0.0,
        lsh=8.0, rsh=8.0, lab=10.0, rab=10.0, lel=18.0, rel=18.0,
        wpn=70.0, wpn_side=0.0, wpn_roll=0.0, shd=0.0,
        head=0.0, head_yaw=0.0, cape=0.0, crouch=0.0, glow=0.0, draw=0.0, mouth=0.0, plant=0.0,
    )

    def __init__(self, **kw):
        super().__init__(self.DEFAULT)
        self.update(kw)

    def __getattr__(self, k):
        return self[k]


class Rig:
    """관절 위치 계산."""

    def __init__(self, p, build=None):
        b = dict(scale=1.0, hip_w=3.4, sh_w=6.5, thigh=12.0, shin=11.0, uarm=10.0, farm=9.0,
                 torso=15.0, head_r=4.4, neck=4.5)
        if build:
            b.update(build)
        self.b = b
        s = b['scale']
        self.s = s
        hipz = (b['thigh'] + b['shin'] + 3.0) * s
        hipC = V(0, 0, hipz)
        rot_l = S.rx(-p.lean)   # 앞으로 숙임: +y 방향으로 상체 이동
        rot_t = S.rz(-p.twist)
        rot_r = S.ry(p.roll)
        self.rot = rot_t @ rot_l @ rot_r

        def leg(side, a, k, ab):
            hp = hipC + V(side * b['hip_w'] * s, 0, 0)
            kn = hp + sagittal(a, ab, side) * b['thigh'] * s
            an = kn + sagittal(a - k, ab, side) * b['shin'] * s
            return hp, kn, an
        lk, rk = p.lknee, p.rknee
        if p.plant:
            # 두 발 모두 땅을 딛도록: 더 길게 뻗은 다리의 무릎을 굽혀 높이를 맞춘다
            def drop(a, k, ab, side):
                return leg(side, a, k, ab)[2][2]
            zl, zr = drop(p.lhip, lk, p.lhip_side, -1), drop(p.rhip, rk, p.rhip_side, 1)
            if abs(zl - zr) > 0.2:
                if zl < zr:   # 왼다리가 더 아래로 뻗음 → 왼 무릎을 더 굽힘
                    a_, ab_, sd, k0, target = p.lhip, p.lhip_side, -1, lk, zr
                else:
                    a_, ab_, sd, k0, target = p.rhip, p.rhip_side, 1, rk, zl
                lo, hi = k0, k0 + 120
                for _ in range(24):
                    mid = (lo + hi) / 2
                    if drop(a_, mid, ab_, sd) < target:
                        lo = mid
                    else:
                        hi = mid
                if sd < 0:
                    lk = (lo + hi) / 2
                else:
                    rk = (lo + hi) / 2
        self.lhp, self.lkn, self.lan = leg(-1, p.lhip, lk, p.lhip_side)
        self.rhp, self.rkn, self.ran = leg(1, p.rhip, rk, p.rhip_side)
        # 접지: 낮은 발목이 z=3s
        minz = min(self.lan[2], self.ran[2]) - 3.0 * s
        off = V(0, 0, -minz + p.bob - p.crouch)
        for nm in ('lhp', 'lkn', 'lan', 'rhp', 'rkn', 'ran'):
            setattr(self, nm, getattr(self, nm) + off)
        self.hip = hipC + off
        # 무릎을 굽혀 앉을 때 발은 그대로 두기 위한 보정은 crouch 파라미터가 담당
        self.waist = self.hip + V(0, 0, 4.0 * s)
        R = self.rot
        T = b['torso'] * s

        def up(v):
            return self.waist + R @ (np.asarray(v) * s)
        self.chest = up(V(0, 0, 8.5))
        self.lsh = up(V(-b['sh_w'], 0, T - 2.0))
        self.rsh = up(V(b['sh_w'], 0, T - 2.0))
        self.neck = up(V(0, 0, T))
        hr = S.rx(-p.head) @ S.rz(-p.head_yaw)
        self.head_rot = R @ hr
        self.head = up(V(0, 0, T + b['neck'] + 0.2))

        def arm(side, shp, a, ab, el):
            e = shp + R @ sagittal(a, ab, side) * b['uarm'] * s
            h = e + R @ sagittal(a + el, ab * 0.5, side) * b['farm'] * s
            return e, h
        self.lel, self.lha = arm(-1, self.lsh, p.lsh, p.lab, p.lel)
        self.rel, self.rha = arm(1, self.rsh, p.rsh, p.rab, p.rel)
        self.wdir = R @ S.nrm(sagittal(p.wpn, p.wpn_side, 1))
        self.fwd = R @ V(0, 1, 0)
        self.up = R @ V(0, 0, 1)
        self.right = R @ V(1, 0, 0)


# ───────────────────────── 몸 조립 ─────────────────────────


def body_items(r, p, m, opts=None):
    """m: 부위→재질 이름. opts: 체형(굵기 등)."""
    o = dict(limb=1.0, chest=(6.6, 4.2, 5.6), belly=(4.6, 5.4), pelvis=(5.2, 3.7, 4.1), head_r=None,
             no_legs=False, eyes=True, hair=True, ears=False, jaw=True)
    if opts:
        o.update(opts)
    s = r.s
    L = o['limb'] * s
    hr = (o['head_r'] or r.b['head_r']) * s
    it = []
    A = it.append
    R = r.rot
    if not o['no_legs']:
        for hp, kn, an in ((r.lhp, r.lkn, r.lan), (r.rhp, r.rkn, r.ran)):
            A(Item(S.capsule(hp, kn, 2.9 * L, 2.2 * L), m['legs']))
            A(Item(S.capsule(kn, an, 2.2 * L, 1.7 * L), m.get('shin', m['legs'])))
            sh = S.nrm(an - kn)
            pitch = math.degrees(math.atan2(sh[1], -sh[2])) * 0.35
            fr = S.rx(-pitch)
            A(Item(S.box(an + fr @ V(0, 1.6 * s, -1.4 * s), V(1.7 * L, 3.1 * s, 1.4 * s), fr, 0.9 * s), m['boots']))
    A(Item(S.ellipsoid(r.hip + V(0, 0, 1.2 * s), V(*[q * s for q in o['pelvis']]), R), m['pelvis']))
    A(Item(S.capsule(r.waist, r.chest, o['belly'][0] * s, o['belly'][1] * s), m['torso']))
    A(Item(S.ellipsoid(r.chest + R @ V(0, 0, 1.0 * s), V(*[q * s for q in o['chest']]), R), m['torso']))
    A(Item(S.capsule(r.neck - r.up * 2 * s, r.neck + r.up * 1.5 * s, 1.7 * s), m['skin']))
    for sh, el, ha in ((r.lsh, r.lel, r.lha), (r.rsh, r.rel, r.rha)):
        A(Item(S.capsule(sh, el, 2.1 * L, 1.8 * L), m['arms']))
        A(Item(S.capsule(el, ha, 1.8 * L, 1.4 * L), m.get('farm', m['arms'])))
        A(Item(S.sphere(ha, 1.75 * L), m['hands']))
    H = r.head
    HR = r.head_rot
    A(Item(S.ellipsoid(H, V(hr * 0.92, hr, hr * 1.02), HR), m['skin']))
    if o['jaw']:
        A(Item(S.ellipsoid(H + HR @ V(0, 1.2 * s, -2.2 * s), V(hr * 0.68, hr * 0.62, hr * 0.5), HR), m['skin']))
    if o['hair'] and m.get('hair'):
        A(Item(S.ellipsoid(H + HR @ V(0, -0.9 * s, 0.9 * s), V(hr * 0.98, hr * 0.98, hr * 1.02), HR), m['hair']))
    if o['eyes'] and m.get('eyes'):
        for sx in (-1, 1):
            A(Item(S.sphere(H + HR @ V(sx * 1.55 * s, hr * 0.86, 0.1 * s), 0.72 * s), m['eyes']))
    if o['ears']:
        for sx in (-1, 1):
            base = H + HR @ V(sx * hr * 0.85, -0.3 * s, 0.4 * s)
            tip = H + HR @ V(sx * hr * 1.9, -1.6 * s, 2.6 * s)
            A(Item(S.capsule(base, tip, 1.0 * s, 0.2 * s), m['skin']))
    return it


# ───────────────────────── 장비 조각 ─────────────────────────


def sword(r, mats, length=21, width=1.45, guard='gold', grip='leather', blade='steel', pommel=None, tag='blade', fuller=True):
    s = r.s
    h = r.rha
    w = r.wdir
    base = h + w * 2.4 * s
    tip = base + w * length * s
    M = S.frame_from(w, r.right)
    it = []
    blade_f = S.box((base + tip) / 2, V(width * s, 0.5 * s, length * s / 2), M, 0.2)
    tipcut = S.halfspace(-(M[:, 0] * 0.0) + w, np.dot(w, tip) - 0.0)
    it.append(Item(S.inter(blade_f, S.capsule(base - w * 2, tip, width * s * 1.25, 0.1)), blade, tag))
    it.append(Item(S.box(h + w * 2.1 * s, V(3.6 * s, 0.9 * s, 0.7 * s), M, 0.35), guard))
    it.append(Item(S.capsule(h - w * 2.4 * s, h + w * 1.8 * s, 0.85 * s), grip))
    it.append(Item(S.sphere(h - w * 3.0 * s, 1.15 * s), pommel or guard))
    return it


def broadsword(r, length=17.5, width=2.1, guard='steel_dk', grip='leather', blade='steel', pommel='gold', tag='blade'):
    """넓은 외날 기사검: 두꺼운 칼날, 등쪽은 곧고 칼끝은 날 쪽에서 비스듬히 잘림, 아래로 휜 큰 코등이."""
    s = r.s
    h = r.rha
    w = r.wdir
    M = S.frame_from(w, r.right)       # 로컬 z = 칼날 방향
    ex = M[:, 0]                        # 칼날 폭 방향(날 ↔ 등)
    base = h + w * 2.6 * s
    tip = base + w * length * s
    body = S.box((base + tip) / 2, V(width * s, 0.5 * s, length * s / 2), M, 0.15)
    # 칼끝: 날 쪽(+ex)에서 등 쪽 끝으로 비스듬히 자름
    n_cut = S.nrm(w * 1.0 + ex * 0.55)
    body = S.inter(body, S.halfspace(n_cut, np.dot(n_cut, tip - ex * width * s * 0.9)))
    it = [Item(body, blade, tag),
          # 홈(풀러): 칼날 가운데 어두운 줄
          Item(S.box(base + w * length * s * 0.38 - ex * 0.35 * s, V(0.42 * s, 0.56 * s, length * s * 0.32), M, 0.1), 'steel_dk', tag)]
    # 코등이: 가운데 블록 + 아래(손 쪽)로 휘는 양 날개
    gc = h + w * 2.2 * s
    it.append(Item(S.box(gc, V(1.6 * s, 1.0 * s, 1.0 * s), M, 0.3), guard))
    for sg in (-1, 1):
        a = gc + ex * sg * 1.2 * s
        b = gc + ex * sg * 4.6 * s - w * 1.4 * s
        it.append(Item(S.capsule(a, b, 0.75 * s, 0.5 * s), guard))
        it.append(Item(S.sphere(b, 0.75 * s), guard))
    it.append(Item(S.capsule(h - w * 2.2 * s, h + w * 1.6 * s, 0.9 * s), grip))
    it.append(Item(S.ellipsoid(h - w * 2.9 * s, V(1.3 * s, 1.0 * s, 1.0 * s), M), pommel))
    return it


def greatsword(r, mats, length=34, width=2.2, guard='g_dark', grip='leather', blade='steel', tag='blade'):
    s = r.s
    h = r.rha
    w = r.wdir
    base = h + w * 3.0 * s
    tip = base + w * length * s
    M = S.frame_from(w, r.right)
    it = [Item(S.inter(S.box((base + tip) / 2, V(width * s, 0.6 * s, length * s / 2), M, 0.25),
                       S.capsule(base - w * 3, tip, width * s * 1.3, 0.2)), blade, tag),
          Item(S.box(h + w * 2.6 * s, V(5.5 * s, 1.2 * s, 1.0 * s), M, 0.4), guard),
          Item(S.capsule(h - w * 4.2 * s, h + w * 2.0 * s, 1.1 * s), grip),
          Item(S.sphere(h - w * 4.8 * s, 1.6 * s), guard)]
    return it


def axe(r, length=17, head='iron', haft='wood', tag='blade'):
    s = r.s
    h = r.rha
    w = r.wdir
    top = h + w * length * s
    M = S.frame_from(w, r.right)
    side = S.nrm(np.cross(w, r.right))
    it = [Item(S.capsule(h - w * 3 * s, top, 1.0 * s, 0.9 * s), haft)]
    bc = top - w * 2.5 * s + side * 3.2 * s
    Mb = S.frame_from(side, w)
    it.append(Item(S.inter(S.ellipsoid(bc, V(4.8 * s, 0.75 * s, 4.4 * s) if False else V(0.75 * s, 4.6 * s, 4.2 * s), np.stack([r.right, w, side], 1) if False else S.frame_from(r.right, w)),
                           S.halfspace(-side, -np.dot(side, top) + 0.5)), head, tag))
    it.append(Item(S.box(top - w * 2.5 * s, V(1.4 * s, 1.4 * s, 2.6 * s), M, 0.3), head))
    return it


def shield_kite(r, mat_face, mat_rim, mat_boss, s_size=1.0, emblem=None):
    s = r.s * s_size
    fwd = r.fwd
    out = S.nrm(fwd * 0.8 - r.right * 0.55)
    c = r.lha + out * 2.6 * s + r.up * 1.0 * s
    M = S.frame_from(out, r.up)
    face = S.ellipsoid(c, V(5.6 * s, 7.6 * s, 1.2 * s), M)
    taper = S.halfspace(M @ V(0.0, -1, 0) * 1.0 + M @ V(0.8, 0, 0) * 0, 0)
    cut1 = S.halfspace(M @ S.nrm(V(0.75, -0.66, 0)), np.dot(M @ S.nrm(V(0.75, -0.66, 0)), c) + 3.4 * s)
    cut2 = S.halfspace(M @ S.nrm(V(-0.75, -0.66, 0)), np.dot(M @ S.nrm(V(-0.75, -0.66, 0)), c) + 3.4 * s)
    shape = S.inter(face, cut1, cut2)
    it = [Item(S.shell(shape, 0.0) if False else shape, mat_face),
          Item(S.sub(S.inter(S.ellipsoid(c - out * 0.3, V(6.0 * s, 8.0 * s, 1.15 * s), M),
                             S.halfspace(M @ S.nrm(V(0.75, -0.66, 0)), np.dot(M @ S.nrm(V(0.75, -0.66, 0)), c) + 3.9 * s),
                             S.halfspace(M @ S.nrm(V(-0.75, -0.66, 0)), np.dot(M @ S.nrm(V(-0.75, -0.66, 0)), c) + 3.9 * s)),
                     S.halfspace(-out, -np.dot(out, c) + 0.2)), mat_rim),
          Item(S.sphere(c + out * 1.0 * s + M @ V(0, 1.8 * s, 0), 1.5 * s), mat_boss)]
    if emblem:
        it.append(Item(S.box(c + out * 1.05 * s, V(0.7 * s, 4.2 * s, 0.4 * s), M, 0.2), emblem))
        it.append(Item(S.box(c + out * 1.05 * s + M @ V(0, 1.8 * s, 0), V(3.0 * s, 0.7 * s, 0.4 * s), M, 0.2), emblem))
    return it


def round_shield(r, face, rim, boss, size=5.6):
    s = r.s
    out = S.nrm(r.fwd * 0.8 - r.right * 0.55)
    c = r.lha + out * 2.4 * s
    M = S.frame_from(out, r.up)
    return [Item(S.cylinder(c, size * s, 0.7 * s, M, 0.3), face),
            Item(S.sub(S.cylinder(c, size * s + 0.6, 0.85 * s, M, 0.3), S.cylinder(c, size * s - 0.8, 2 * s, M)), rim),
            Item(S.sphere(c + out * 0.9 * s, 1.5 * s), boss)]


def cape(r, p, mat, length=30, width=7.0, sway=0.0, tatter=False, split=False):
    """어깨에서 늘어진 망토(뒤로 휘는 정도 = p.cape)."""
    s = r.s
    back = -r.fwd
    top = (r.lsh + r.rsh) / 2 + back * 2.4 * s + r.up * 0.5 * s
    segs = 4
    it = []
    prev = top
    ang = 6 + p.cape
    for k in range(segs):
        a = math.radians(ang * (1 + k * 0.55))
        dn = S.nrm(V(0, 0, -1) * math.cos(a) + back * math.sin(a))
        nxt = prev + dn * (length * s / segs)
        c = (prev + nxt) / 2
        M = np.stack([r.right, S.nrm(np.cross(dn, r.right)), dn], 1)
        wd = (width + k * 1.4) * s
        f = S.box(c, V(wd, 0.55 * s, length * s / segs / 2 + 0.6), M, 0.4)
        if tatter and k == segs - 1:
            f = S.sub(f, S.displace(S.halfspace(dn, np.dot(dn, nxt) - 2.5 * s), 2.5, 0.45, seed=7))
        if split and k == segs - 1:   # 끝을 두 갈래로 가름
            f = S.sub(f, S.box(nxt, V(0.9 * s, 2.0 * s, length * s / segs * 0.55), M))
        it.append(Item(f, mat))
        prev = nxt
    return it


def helmet_knight(r, steel, dark, plume=None):
    s = r.s
    H, HR = r.head, r.head_rot
    hr = r.b['head_r'] * s
    it = [Item(S.ellipsoid(H + HR @ V(0, 0, 0.3 * s), V(hr * 1.08, hr * 1.16, hr * 1.12), HR), steel),
          Item(S.box(H + HR @ V(0, hr * 1.02, 0.4 * s), V(hr * 0.75, 0.6 * s, 0.45 * s), HR, 0.2), dark),
          Item(S.box(H + HR @ V(0, hr * 0.98, -1.1 * s), V(0.35 * s, 0.6 * s, 1.6 * s), HR, 0.1), dark),
          Item(S.box(H + HR @ V(0, 0, hr * 0.9), V(0.6 * s, hr * 1.1, 0.9 * s), HR, 0.4), steel)]
    if plume:
        it.append(Item(S.capsule(H + HR @ V(0, 1.0 * s, hr * 1.1), H + HR @ V(0, -hr * 1.6, hr * 0.5), 1.4 * s, 0.9 * s), plume))
    return it


def pauldrons(r, mat, size=3.3, trim=None):
    s = r.s
    it = []
    for sh, sx in ((r.lsh, -1), (r.rsh, 1)):
        c = sh + r.up * 0.8 * s + r.right * sx * 0.8 * s
        it.append(Item(S.ellipsoid(c, V(size * s, size * 1.05 * s, size * 0.8 * s), r.rot), mat))
        if trim:
            it.append(Item(S.ellipsoid(c - r.up * 1.4 * s, V(size * 1.06 * s, size * 1.1 * s, 0.6 * s), r.rot), trim))
    return it


def skirt(r, mat, top_r=5.6, bot_r=7.2, length=9.0, split=True):
    s = r.s
    a = r.hip + V(0, 0, 2.5 * s)
    b = r.hip - V(0, 0, length * s - 2.5 * s)
    f = S.capsule(a, b, top_r * s, bot_r * s)
    f = S.inter(f, S.halfspace(V(0, 0, -1), -(b[2] + 0.5)))
    f = S.shell(f, 0.8 * s)
    f = S.inter(f, S.halfspace(V(0, 0, 1), a[2]))
    if split:
        f = S.sub(f, S.box(r.hip + V(0, 7 * s, -length * s), V(0.9 * s, 6 * s, length * s * 0.85)))
    return [Item(f, mat)]


def robe(r, p, mat, trim, length=None):
    """허리에서 발까지 덮는 로브(다리 걸음에 따라 앞뒤로 흔들림)."""
    s = r.s
    a = r.waist + V(0, 0, 1.0 * s)
    sw = (r.lan[1] + r.ran[1]) * 0.5
    spread = abs(r.lan[1] - r.ran[1])
    b = V(r.hip[0], r.hip[1] * 0.5 + sw * 0.6, 0.6 * s)
    f = S.capsule(a, b, 5.0 * s, (8.0 + spread * 0.12) * s)
    f = S.inter(f, S.halfspace(V(0, 0, -1), -0.4 * s))
    it = [Item(f, mat)]
    it.append(Item(S.inter(S.shell(S.capsule(a, b, 5.0 * s, (8.0 + spread * 0.12) * s), 0.6 * s),
                           S.halfspace(V(0, 0, 1), 2.6 * s), S.halfspace(V(0, 0, -1), -0.4 * s)), trim))
    return it


def bow(r, wood, string, tag='bow', draw=0.0):
    """왼손에 든 활. 활 면은 몸 앞 수직면, draw: 0..1 당김."""
    s = r.s
    c = r.lha
    fwd = r.fwd
    up = r.up
    it = []
    n = 7
    pts = []
    bend = 3.0 + draw * 2.5
    for k in range(n + 1):
        t = k / n * 2 - 1
        pts.append(c + up * t * 11 * s + fwd * (1 - t * t) * bend * s)
    for k in range(n):
        rr = (1.1 if abs(k - n / 2) < 1.5 else 0.8) * s
        it.append(Item(S.capsule(pts[k], pts[k + 1], rr), wood, tag))
    hand = c - fwd * (2 + draw * 9) * s if draw > 0 else None
    top, bot = pts[0], pts[-1]
    if hand is not None:
        it.append(Item(S.capsule(top, hand, 0.3 * s), string))
        it.append(Item(S.capsule(hand, bot, 0.3 * s), string))
        it.append(Item(S.capsule(hand, c + fwd * 3 * s, 0.4 * s), wood))
    else:
        it.append(Item(S.capsule(top, bot, 0.3 * s), string))
    return it


def quiver(r, leather, fletch):
    s = r.s
    back = -r.fwd
    a = r.waist + back * 4.5 * s + r.right * 2 * s
    b = r.neck + back * 4.5 * s - r.right * 3 * s + r.up * 2 * s
    it = [Item(S.capsule(a, b, 1.9 * s, 2.1 * s), leather)]
    d = S.nrm(b - a)
    for k, ox in enumerate((-0.9, 0.6, 0.1)):
        it.append(Item(S.capsule(b + r.right * ox * s, b + d * 3.0 * s + r.right * ox * s, 0.55 * s), fletch))
    return it


def staff(r, wood, orb, cage, length=30, tag='staff'):
    s = r.s
    h = r.rha
    w = r.wdir
    top = h + w * (length * 0.62) * s
    bot = h - w * (length * 0.38) * s
    it = [Item(S.capsule(bot, top, 0.95 * s, 1.15 * s), wood)]
    oc = top + w * 2.4 * s
    it.append(Item(S.sphere(oc, 2.0 * s), orb, tag))
    M = S.frame_from(w, r.right)
    for k in range(3):
        a = k * 120
        Mk = M @ S.rz(a)
        it.append(Item(S.capsule(top, oc + Mk @ V(2.3 * s, 0, 1.5 * s), 0.45 * s), cage))
    return it


def hood(r, mat, peak=True):
    s = r.s
    H, HR = r.head, r.head_rot
    hr = r.b['head_r'] * s
    outer = S.ellipsoid(H + HR @ V(0, -0.6 * s, 0.6 * s), V(hr * 1.2, hr * 1.25, hr * 1.25), HR)
    face = S.ellipsoid(H + HR @ V(0, hr * 1.25, -0.4 * s), V(hr * 0.75, hr * 0.8, hr * 0.9), HR)
    f = S.sub(outer, face)
    it = [Item(f, mat)]
    if peak:
        it.append(Item(S.capsule(H + HR @ V(0, -1.0 * s, hr * 0.9), H + HR @ V(0, -hr * 1.4, hr * 1.4), 2.0 * s, 0.4 * s), mat))
    # 어깨까지 내려오는 두건 자락
    it.append(Item(S.capsule(r.neck - r.up * 1.5 * s, r.neck + r.up * 1.5 * s, 5.4 * s, 3.8 * s), mat))
    return it


def wizard_hat(r, mat, band):
    s = r.s
    H, HR = r.head, r.head_rot
    hr = r.b['head_r'] * s
    brim = S.cylinder(H + HR @ V(0, 0, hr * 0.75), hr * 1.9, 0.45 * s, HR, 0.3)
    crown = S.capsule(H + HR @ V(0, 0, hr * 0.7), H + HR @ V(0, -hr * 0.9, hr * 3.0), hr * 1.0, 0.3)
    return [Item(brim, mat), Item(crown, mat),
            Item(S.cylinder(H + HR @ V(0, -0.05, hr * 1.05), hr * 1.02, 0.7 * s, HR, 0.2), band)]


def crown(r, gold, gem):
    s = r.s
    H, HR = r.head, r.head_rot
    hr = r.b['head_r'] * s
    c = H + HR @ V(0, -0.2 * s, hr * 0.78)
    M = HR
    it = [Item(S.sub(S.cylinder(c, hr * 0.98, 0.9 * s, M, 0.2), S.cylinder(c, hr * 0.82, 2 * s, M)), gold)]
    for k in range(5):
        a = math.radians(k * 72 + 90)
        p0 = c + M @ V(math.cos(a) * hr * 0.92, math.sin(a) * hr * 0.92, 0.6 * s)
        it.append(Item(S.capsule(p0, p0 + M @ V(0, 0, 2.3 * s), 0.7 * s, 0.25 * s), gold))
    it.append(Item(S.sphere(c + M @ V(0, hr * 0.96, 0.1 * s), 0.85 * s), gem))
    return it


# ───────────────────────── 클래스 정의 ─────────────────────────

M_COMMON = {
    'skin': Mat(['#5a3a2e', '#8a5c45', '#b07f62', '#cfa080', '#e6c3a1']),
    'eyes': Mat(['#120c0a', '#1c1310', '#241914', '#2c1f18', '#33241c']),
    'steel': Mat(['#20232a', '#3a3f4a', '#5d6470', '#8a919c', '#b9bec6'], metal=True, hi='#eef2f6'),
    'steel_dk': Mat(['#15171c', '#23262d', '#353a44', '#4c525e', '#666d79'], metal=True, hi='#9aa3b0'),
    'iron': Mat(['#1b1c1f', '#2e3034', '#46494f', '#63676e', '#83878e'], metal=True, hi='#b5b8bd'),
    'gold': Mat(['#4a2e0c', '#7c5316', '#b07d22', '#d9a83a', '#f2d36b'], metal=True, hi='#fff2b8'),
    'g_dark': Mat(['#2a1a0a', '#4a3010', '#6e4b1a', '#946a28', '#b88d3d'], metal=True, hi='#e3c27a'),
    'leather': Mat(['#20140d', '#3a2416', '#55361f', '#70492b', '#8a5e3a']),
    'leather_lt': Mat(['#3a2617', '#5a3d25', '#7a5634', '#9a7045', '#b58a58']),
    'wood': Mat(['#21150c', '#3a2614', '#56391e', '#73502b', '#8f683b']),
    'cloth_dk': Mat(['#121214', '#1d1d22', '#2a2a31', '#383843', '#474756']),
    'string': Mat(['#9b9384', '#b5ad9d', '#cfc7b6', '#e0d9c8', '#efe9da']),
}


def _class_knight():
    m = dict(M_COMMON)
    m.update({
        'redcloth': Mat(['#2c0607', '#4a0c0e', '#6c1416', '#8f1f1f', '#b0302a']),
        'mail': Mat(['#1d2026', '#30343c', '#474c56', '#626874', '#7d8491'], metal=True,
                    tex=lambda P, n: 0.6 * ((np.floor(P[:, 2] * 0.9) + np.floor(P[:, 0] * 0.9)) % 2 - 0.5)),
        'hair': Mat(['#0e0a08', '#18120e', '#241b15', '#30241c', '#3d2e24']),
    })
    parts = dict(skin='skin', hair='hair', eyes='eyes', torso='steel', pelvis='mail', legs='mail', shin='steel',
                 boots='steel_dk', arms='mail', farm='steel', hands='steel_dk')

    def gear(r, p, it):
        s = r.s
        H, HR = r.head, r.head_rot
        # 흐트러진 앞머리·옆머리 (투구 없음)
        for ox, oz, ln in ((-2.6, 3.2, 2.6), (-0.6, 3.8, 3.0), (1.6, 3.4, 2.4), (3.0, 2.4, 2.0)):
            a0 = H + HR @ V(ox * s, 2.2 * s, oz * s)
            it.append(Item(S.capsule(a0, a0 + HR @ V(ox * 0.25 * s, 1.6 * s, -ln * s), 1.0 * s, 0.4 * s), 'hair'))
        it.append(Item(S.ellipsoid(H + HR @ V(0, -1.4 * s, -1.2 * s), V(4.2 * s, 3.4 * s, 3.6 * s), HR), 'hair'))
        it += pauldrons(r, 'steel', 3.9, trim='gold')
        it += cape(r, p, 'redcloth', length=30, width=6.5, split=True)
        # 목에 두른 붉은 스카프 + 뒤로 날리는 자락
        it.append(Item(S.torus(r.neck - r.up * 1.2 * s, r.rot, 3.4 * s, 1.5 * s), 'redcloth'))
        back = -r.fwd
        t0 = r.neck - r.up * 1.0 * s + back * 3.0 * s + r.right * 1.5 * s
        flow = math.radians(20 + p.cape * 1.6)
        t1 = t0 + (back * math.sin(flow) - r.up * math.cos(flow)) * 7 * s + r.right * 1.5 * s
        it.append(Item(S.capsule(t0, t1, 1.3 * s, 0.7 * s), 'redcloth'))
        it += skirt(r, 'mail', 5.4, 6.6, 9.0)
        # 금 테두리 흉갑 장식
        it.append(Item(S.box(r.chest + r.fwd * 4.3 * s + r.up * 0.6 * s, V(4.6 * s, 0.35 * s, 0.45 * s), r.rot, 0.1), 'gold'))
        it.append(Item(S.box(r.chest + r.fwd * 4.5 * s - r.up * 1.4 * s, V(0.45 * s, 0.35 * s, 2.0 * s), r.rot, 0.1), 'gold'))
        it.append(Item(S.box(r.waist + r.up * 0.4 * s, V(5.4 * s, 4.4 * s, 0.9 * s), r.rot, 0.4), 'leather'))
        it.append(Item(S.box(r.waist + r.up * 0.4 * s + r.fwd * 4.3 * s, V(1.2 * s, 0.4 * s, 1.0 * s), r.rot, 0.2), 'gold'))
        it += broadsword(r, 18.0, 2.0, guard='gold', grip='leather', blade='steel', pommel='gold')
    return dict(name='knight', label='기사', mats=m, parts=parts, gear=gear, weapon='blade', build=None,
                opts=dict(hair=True, eyes=True, limb=1.12, chest=(7.2, 4.6, 6.0), belly=(5.0, 5.8)))


def _class_elf():
    m = dict(M_COMMON)
    m.update({
        'skin': Mat(['#5b4236', '#8c6a58', '#b89480', '#d8b9a3', '#efd9c6']),
        'cloak': Mat(['#0d1a10', '#16291a', '#213b25', '#2e5032', '#3d6740']),
        'tunic': Mat(['#1e2a12', '#2f421c', '#435c28', '#587636', '#6f9145']),
        'hair': Mat(['#4a3812', '#73561c', '#9c7a2a', '#c29e3e', '#e0c25e']),
        'fletch': Mat(['#4a1010', '#6e1a18', '#922622', '#b33a30', '#cc5544']),
        'bowwood': Mat(['#2a180c', '#432812', '#5f3b1c', '#7c5128', '#9a6936'], gloss=0.4),
    })
    parts = dict(skin='skin', hair='hair', eyes='eyes', torso='tunic', pelvis='leather', legs='leather_lt', shin='leather',
                 boots='leather', arms='tunic', farm='leather', hands='leather')

    def gear(r, p, it):
        it += hood(r, 'cloak', peak=True) if p.get('hooded', False) else []
        # 긴 머리 꽁지
        H, HR, s = r.head, r.head_rot, r.s
        it.append(Item(S.capsule(H + HR @ V(0, -3.5 * s, 0.5 * s), r.neck - r.fwd * 3.6 * s - r.up * 6 * s, 2.2 * s, 1.4 * s), 'hair'))
        it += cape(r, p, 'cloak', length=24, width=6.0)
        it.append(Item(S.box(r.waist + r.up * 0.5 * s, V(5.3 * s, 4.2 * s, 0.9 * s), r.rot, 0.5), 'leather'))
        it += quiver(r, 'leather', 'fletch')
        it += bow(r, 'bowwood', 'string', draw=p.draw)
    return dict(name='elf', label='요정', mats=m, parts=parts, gear=gear, weapon='bow',
                build=dict(scale=0.97, sh_w=6.0), opts=dict(ears=True, limb=0.9, chest=(6.0, 3.9, 5.2), belly=(4.2, 4.9)))


def _class_mage():
    m = dict(M_COMMON)
    m.update({
        'robe': Mat(['#160b1e', '#251334', '#371d4c', '#4b2965', '#61367f']),
        'trim': Mat(['#4a2e0c', '#7c5316', '#b07d22', '#d9a83a', '#f2d36b'], metal=True, hi='#fff2b8'),
        'orb': Mat(['#2a6fbf', '#4f9be0', '#7cc3f5', '#b5e4ff', '#e8f8ff'], emit=True),
        'hair': Mat(['#6a6a6e', '#8e8e94', '#b0b0b6', '#ceced4', '#e6e6ea']),
        'beard': Mat(['#6a6a6e', '#8e8e94', '#b0b0b6', '#ceced4', '#e6e6ea']),
    })
    parts = dict(skin='skin', hair='hair', eyes='eyes', torso='robe', pelvis='robe', legs='robe', shin='robe',
                 boots='leather', arms='robe', farm='robe', hands='skin')

    def gear(r, p, it):
        s = r.s
        it += robe(r, p, 'robe', 'trim')
        it += wizard_hat(r, 'robe', 'trim')
        H, HR = r.head, r.head_rot
        it.append(Item(S.capsule(H + HR @ V(0, 3.4 * s, -2.0 * s), H + HR @ V(0, 2.4 * s, -8.0 * s), 2.4 * s, 0.6 * s), 'beard'))
        # 넓은 소매
        for el, ha in ((r.lel, r.lha), (r.rel, r.rha)):
            it.append(Item(S.capsule(el, ha + (ha - el) * -0.15, 2.2 * s, 3.0 * s), 'robe'))
        it.append(Item(S.cylinder(r.waist + r.up * 0.8 * s, 5.3 * s, 0.8 * s, r.rot, 0.3), 'trim'))
        it += staff(r, 'wood', 'orb', 'gold', 32)
    return dict(name='mage', label='마법사', mats=m, parts=parts, gear=gear, weapon='staff', build=None,
                opts=dict(no_legs=True, chest=(6.2, 4.0, 5.4)))


def _class_lord():
    m = dict(M_COMMON)
    m.update({
        'cape': Mat(['#2c0607', '#4a0c0e', '#6c1416', '#8f1f1f', '#b0302a']),
        'royal': Mat(['#1e1f26', '#30323c', '#4a4d5a', '#686c7a', '#8b8f9c'], metal=True, hi='#e6e9ef'),
        'hair': Mat(['#120c09', '#1e1510', '#2c1f17', '#3a291e', '#493427']),
        'gem': Mat(['#5a0a14', '#8e1222', '#c41e34', '#e84a5a', '#ff8e96'], gloss=1.0),
        'fur': Mat(['#3c3630', '#5e554b', '#81766a', '#a3978a', '#c2b6a8'],
                   tex=lambda P, n: 0.5 * S.vnoise(P * 1.3, 3)),
    })
    parts = dict(skin='skin', hair='hair', eyes='eyes', torso='royal', pelvis='leather', legs='cloth_dk', shin='royal',
                 boots='leather', arms='cloth_dk', farm='royal', hands='leather')

    def gear(r, p, it):
        s = r.s
        it += crown(r, 'gold', 'gem')
        it += pauldrons(r, 'gold', 3.1, trim='royal')
        it += cape(r, p, 'cape', length=33, width=7.0)
        # 모피 깃
        it.append(Item(S.torus(r.neck - r.up * 1.5 * s - r.fwd * 0.5 * s, r.rot, 4.6 * s, 2.1 * s), 'fur'))
        it += skirt(r, 'cape', 5.8, 7.2, 9.5)
        it.append(Item(S.box(r.chest + r.fwd * 4.1 * r.s - r.up * 0.5 * r.s, V(2.3 * r.s, 0.5 * r.s, 2.3 * r.s), r.rot @ S.ry(45), 0.3), 'gold'))
        it += broadsword(r, 18.5, 1.9, guard='gold', grip='cape', blade='steel', pommel='gem')
    return dict(name='lord', label='군주', mats=m, parts=parts, gear=gear, weapon='blade', build=dict(scale=1.02),
                opts=dict(chest=(6.9, 4.3, 5.8)))


CLASSES = [_class_knight(), _class_elf(), _class_mage(), _class_lord()]


# ───────────────────────── 동작 ─────────────────────────
# 프레임 수: 대기 6 · 걷기 8 · 공격 8 · 피격 3 · 사망 6. 공격의 타격 프레임은 HIT_FRAME.

ANIMS = [('idle', 6), ('walk', 8), ('attack', 8), ('hurt', 3), ('death', 6)]
HIT_FRAME = 4


def ease(u):
    return u * u * (3 - 2 * u)


def keyed(keys, f, n):
    """keys: 프레임 번호와 맞춘 dict 목록(길이 n이면 그대로), 다르면 부드럽게 보간."""
    if len(keys) == n:
        return dict(keys[f])
    u = f / max(1, n - 1) * (len(keys) - 1)
    i = min(int(u), len(keys) - 2)
    w = ease(u - i)
    a, b = keys[i], keys[i + 1]
    out = {}
    for k in set(a) | set(b):
        va, vb = a.get(k, b.get(k)), b.get(k, a.get(k))
        out[k] = va + (vb - va) * w
    return out


def _bend(p):
    """'sink'(무게 실어 주저앉기)를 무릎·고관절 굽힘으로 바꾼다(발은 땅에 붙은 채 몸이 내려감)."""
    s = p.pop('sink', 0.0)
    if s:
        p['lknee'] = p.get('lknee', 4.0) + s * 11
        p['rknee'] = p.get('rknee', 4.0) + s * 11
        p['lhip'] = p.get('lhip', 0.0) + s * 5
        p['rhip'] = p.get('rhip', 0.0) + s * 5
        p['lean'] = p.get('lean', 0.0) + s * 2
    return p


# 공격 키프레임 (8프레임: 준비 → 예비동작 2 → 휘두름 → 타격 → 멈춤(히트스톱) → 여운 → 복귀)
ATK_SWORD = [
    dict(rsh=26, rel=58, wpn=150, wpn_side=-8, lean=4, twist=6, sink=0.3, lhip=0, rhip=0),
    dict(rsh=115, rel=65, wpn=185, wpn_side=-14, lean=-5, twist=-16, sink=0.8, lhip=-4, rhip=6),
    dict(rsh=158, rel=42, wpn=212, wpn_side=-10, lean=-10, twist=-28, sink=1.1, lhip=-6, rhip=8),
    dict(rsh=118, rel=14, wpn=140, wpn_side=8, lean=4, twist=0, sink=0.6, lhip=14, rhip=-12),
    dict(rsh=66, rel=6, wpn=98, wpn_side=22, lean=14, twist=24, sink=1.6, lhip=22, rhip=-18),
    dict(rsh=60, rel=6, wpn=94, wpn_side=24, lean=15, twist=26, sink=1.7, lhip=22, rhip=-18),
    dict(rsh=34, rel=18, wpn=78, wpn_side=20, lean=11, twist=20, sink=1.3, lhip=18, rhip=-14),
    dict(rsh=26, rel=54, wpn=140, wpn_side=-6, lean=5, twist=8, sink=0.4, lhip=4, rhip=-3),
]
ATK_GREAT = [
    dict(rsh=34, rel=62, wpn=145, wpn_side=-30, lean=5, twist=8, sink=0.4),
    dict(rsh=120, rel=60, wpn=190, wpn_side=-24, lean=-6, twist=-22, sink=1.0, lhip=-6, rhip=8),
    dict(rsh=165, rel=40, wpn=218, wpn_side=-14, lean=-12, twist=-34, sink=1.4, lhip=-8, rhip=10),
    dict(rsh=125, rel=18, wpn=150, wpn_side=6, lean=6, twist=-4, sink=0.8, lhip=16, rhip=-14),
    dict(rsh=60, rel=8, wpn=92, wpn_side=26, lean=18, twist=26, sink=2.0, lhip=26, rhip=-20),
    dict(rsh=55, rel=8, wpn=88, wpn_side=28, lean=19, twist=28, sink=2.1, lhip=26, rhip=-20),
    dict(rsh=32, rel=20, wpn=78, wpn_side=22, lean=14, twist=22, sink=1.6, lhip=20, rhip=-16),
    dict(rsh=34, rel=60, wpn=140, wpn_side=-28, lean=6, twist=10, sink=0.5, lhip=4, rhip=-3),
]
ATK_BOW = [
    dict(lsh=45, lel=10, rsh=14, rel=30, twist=0, lean=2, draw=0.0, sink=0.3),
    dict(lsh=80, lel=4, rsh=60, rel=70, twist=8, lean=3, draw=0.0, sink=0.5, lhip=8, rhip=-8),
    dict(lsh=88, lel=2, rsh=86, rel=60, twist=12, lean=4, draw=0.15, sink=0.7, lhip=10, rhip=-10),
    dict(lsh=88, lel=2, rsh=86, rel=100, twist=18, lean=4, draw=0.55, sink=0.8, lhip=10, rhip=-10),
    dict(lsh=88, lel=2, rsh=84, rel=135, twist=24, lean=4, draw=1.0, sink=0.9, lhip=10, rhip=-10),
    dict(lsh=88, lel=2, rsh=84, rel=138, twist=25, lean=4, draw=1.0, sink=0.9, lhip=10, rhip=-10),
    dict(lsh=92, lel=0, rsh=70, rel=160, rab=40, twist=20, lean=-2, draw=0.0, sink=0.7, lhip=10, rhip=-10),
    dict(lsh=60, lel=8, rsh=30, rel=60, twist=6, lean=2, draw=0.0, sink=0.4, lhip=4, rhip=-4),
]
ATK_STAFF = [
    dict(rsh=30, rel=45, wpn=170, wpn_side=-6, lsh=12, lel=25, lean=0, glow=0.0, sink=0.2),
    dict(rsh=80, rel=90, wpn=180, wpn_side=-4, lsh=30, lel=40, lean=-4, glow=0.2, sink=0.5),
    dict(rsh=140, rel=55, wpn=198, wpn_side=0, lsh=60, lel=30, lean=-9, glow=0.5, sink=0.9, lhip=-4, rhip=6),
    dict(rsh=158, rel=30, wpn=206, wpn_side=0, lsh=80, lel=20, lean=-12, glow=0.8, sink=1.1, lhip=-6, rhip=8),
    dict(rsh=85, rel=8, wpn=125, wpn_side=0, lsh=90, lel=6, lean=10, glow=1.0, sink=1.5, lhip=16, rhip=-14),
    dict(rsh=80, rel=8, wpn=120, wpn_side=0, lsh=92, lel=6, lean=11, glow=1.0, sink=1.6, lhip=16, rhip=-14),
    dict(rsh=55, rel=24, wpn=140, wpn_side=-2, lsh=60, lel=20, lean=6, glow=0.5, sink=1.0, lhip=10, rhip=-8),
    dict(rsh=34, rel=42, wpn=165, wpn_side=-6, lsh=20, lel=25, lean=2, glow=0.1, sink=0.4),
]


# 전투 대기 기준 자세(모든 동작의 출발점): 발을 앞뒤·좌우로 넓게, 무릎 굽혀 낮게, 몸은 비스듬히
STANCE = {
    'sword': dict(lhip=14, rhip=-12, lhip_side=11, rhip_side=11, lknee=28, rknee=18, twist=14, head_yaw=-12, lean=6,
                  rsh=26, rab=16, rel=58, wpn=158, wpn_side=-8, lsh=30, lab=12, lel=52),
    'great': dict(lhip=16, rhip=-14, lhip_side=12, rhip_side=12, lknee=30, rknee=18, twist=18, head_yaw=-14, lean=8,
                  rsh=34, rab=20, rel=64, wpn=145, wpn_side=-32, lsh=44, lab=24, lel=74),
    'bow': dict(lhip=12, rhip=-10, lhip_side=11, rhip_side=11, lknee=24, rknee=14, twist=22, head_yaw=-18, lean=5,
                lsh=34, lab=14, lel=18, rsh=16, rab=14, rel=40, wpn=40),
    'staff': dict(lhip=10, rhip=-8, lhip_side=9, rhip_side=9, lknee=22, rknee=12, twist=8, head_yaw=-6, lean=5,
                  rsh=24, rab=16, rel=48, wpn=172, wpn_side=-6, lsh=22, lab=18, lel=50),
}
# 기사·군주: 참고 시트처럼 무게 실은 직립 — 발은 어깨너비, 무릎 살짝, 검은 몸 옆에서 아래로 비스듬히
STANCE['blade'] = dict(lhip=8, rhip=-6, lhip_side=8, rhip_side=8, lknee=16, rknee=12, twist=8, head_yaw=-6, lean=3,
                       rsh=12, rab=20, rel=24, wpn=38, wpn_side=14, lsh=6, lab=18, lel=22)
STANCE['axe'] = STANCE['sword']

# 가로 베기 (팔을 끝까지 뻗음): 준비 → 검을 오른쪽 뒤로 당김 → 몸을 비틀며 앞으로 내디딤 → 왼쪽까지 베어 넘김
ATK_BLADE = [
    dict(rsh=14, rab=22, rel=26, wpn=45, wpn_side=14, lean=4, twist=8, lsh=8, lab=18, lel=24, lhip=0, rhip=0, sink=0.2),
    dict(rsh=60, rab=55, rel=40, wpn=95, wpn_side=55, lean=2, twist=26, lsh=30, lab=10, lel=50, lhip=-2, rhip=2, sink=0.7),
    dict(rsh=78, rab=70, rel=30, wpn=100, wpn_side=80, lean=0, twist=38, lsh=45, lab=8, lel=55, lhip=-4, rhip=4, sink=1.0),
    dict(rsh=86, rab=30, rel=8, wpn=95, wpn_side=20, lean=12, twist=6, lsh=20, lab=30, lel=30, lhip=20, rhip=-18, sink=1.4),
    dict(rsh=88, rab=6, rel=2, wpn=92, wpn_side=-55, lean=18, twist=-26, lsh=-10, lab=40, lel=20, lhip=30, rhip=-26, sink=1.9),
    dict(rsh=88, rab=4, rel=2, wpn=91, wpn_side=-62, lean=19, twist=-28, lsh=-12, lab=42, lel=20, lhip=30, rhip=-26, sink=2.0),
    dict(rsh=70, rab=6, rel=10, wpn=80, wpn_side=-85, lean=15, twist=-32, lsh=-6, lab=36, lel=24, lhip=26, rhip=-22, sink=1.6),
    dict(rsh=24, rab=18, rel=24, wpn=50, wpn_side=0, lean=6, twist=0, lsh=4, lab=20, lel=24, lhip=8, rhip=-6, sink=0.6),
]
LEG_KEYS = ('lhip', 'rhip', 'lhip_side', 'rhip_side', 'lknee', 'rknee')


def pose_for(kind, anim, f, n):
    """kind: 'sword' | 'axe' | 'great' | 'bow' | 'staff'"""
    t = f / n
    ph = 2 * math.pi * t
    st = dict(STANCE.get(kind, STANCE['sword']))
    legs = {k: st[k] for k in LEG_KEYS}
    base = {k: v for k, v in st.items() if k not in LEG_KEYS}

    if anim == 'idle':
        # 낮게 버틴 채 숨쉬기: 들숨에 상체가 오르고 무릎이 펴짐, 날숨에 가라앉음
        b = math.sin(ph)
        c = math.sin(ph - 0.9)
        p = dict(base)
        p.update(legs)
        p.update(plant=1, bob=-0.5 + 0.5 * b, lean=base['lean'] + 0.8 * b, roll=0.5 * c,
                 cape=2 + 1.4 * c, head=-1.0 * c)
        p['lknee'] = legs['lknee'] + 3 * (1 - b)
        p['rsh'] = base['rsh'] + 2 * c
        p['lsh'] = base['lsh'] + 1.5 * c
        p['wpn'] = base.get('wpn', 70) + 2 * c
        return Pose(**p)

    if anim == 'walk' and kind == 'blade':
        # 참고 시트의 이동: 상체를 깊이 숙이고, 검은 뒤로 낮게 끌며, 망토는 크게 휘날림
        sw = math.sin(ph)
        cw = math.cos(ph)
        lift_l = max(0.0, cw) ** 1.3
        lift_r = max(0.0, -cw) ** 1.3
        contact = 1 - abs(cw)
        p = dict(lhip=6 + 34 * sw, rhip=6 - 34 * sw,
                 lknee=26 + 50 * lift_l + 10 * contact, rknee=26 + 50 * lift_r + 10 * contact,
                 lhip_side=6, rhip_side=6, lean=20, twist=-8 * sw + 6, roll=2.5 * cw, head=-12 + 2 * contact,
                 rsh=-38 - 8 * sw, rab=22, rel=12, wpn=-30, wpn_side=18,
                 lsh=30 - 26 * sw, lab=16, lel=40, cape=15 + 5 * abs(cw), bob=0.4 * abs(math.sin(ph)))
        return Pose(**p)

    if anim == 'walk':
        # 무기를 겨눈 채 낮은 자세로 걷기: 보폭은 넓고, 디딜 때 무릎으로 충격 흡수
        sw = math.sin(ph)
        cw = math.cos(ph)
        lift_l = max(0.0, cw) ** 1.3
        lift_r = max(0.0, -cw) ** 1.3
        contact = 1 - abs(cw)
        p = dict(base)
        p.update(lhip=4 + 28 * sw, rhip=-4 - 28 * sw,
                 lknee=16 + 42 * lift_l + 8 * contact, rknee=16 + 42 * lift_r + 8 * contact,
                 lhip_side=5, rhip_side=5,
                 lean=base['lean'] + 1, twist=base['twist'] * 0.5 - 7 * sw, roll=2.2 * cw, head=1.5 * contact,
                 head_yaw=base.get('head_yaw', 0) * 0.5, cape=9 + 5 * abs(cw))
        if kind == 'staff':
            p['lsh'] = base['lsh'] - 22 * sw
        elif kind != 'bow':
            p['lsh'] = base['lsh'] - 8 * sw
        p['rsh'] = base['rsh'] + 10 * sw
        p['bob'] = 0.3 * abs(math.sin(ph))
        return Pose(**p)

    if anim == 'attack':
        keys = {'bow': ATK_BOW, 'staff': ATK_STAFF, 'great': ATK_GREAT, 'blade': ATK_BLADE}.get(kind, ATK_SWORD)
        k = keyed(keys, f, n)
        p = dict(base)
        p.update(rab=16, lab=20, shd=1, plant=1)
        if kind in ('sword', 'axe'):
            p.update(lsh=34, lel=54, lab=14)
        p.update(k)
        # 발은 대기 자세처럼 넓게 벌린 채 휘두름(키프레임의 다리 값은 그 위에 더함)
        p['lhip'] = legs['lhip'] * 0.6 + k.get('lhip', 0)
        p['rhip'] = legs['rhip'] * 0.6 + k.get('rhip', 0)
        p['lhip_side'] = legs['lhip_side']
        p['rhip_side'] = legs['rhip_side']
        p['lknee'] = legs['lknee']
        p['rknee'] = legs['rknee']
        p['twist'] = k.get('twist', 0) + legs['lhip'] * 0.3
        p['cape'] = min(16, 6 + 6 * abs(k.get('twist', 0)) / 25 + (6 if f in (3, 4) else 0))
        return Pose(**_bend(p))

    if anim == 'hurt':
        k = [1.0, 0.75, 0.3][f] if n == 3 else (1.0 - f / max(1, n - 1) * 0.7)
        p = dict(base)
        p.update(legs)
        p.update(plant=1, lean=base['lean'] - 22 * k, head=-16 * k, twist=base['twist'] + 8 * k,
                 lsh=base['lsh'] + 18 * k, rsh=base['rsh'] - 12 * k,
                 rab=28 * k + 14, lab=24 * k + 16, cape=16 * k, sink=0.6 * k)
        return Pose(**_bend(p))

    if anim == 'death' and kind == 'blade':
        u = f / max(1, n - 1)
        kneel = min(1.0, u * 2.2)          # 앞 절반: 오른 무릎을 꿇음
        fall = max(0.0, (u - 0.35) / 0.65)  # 뒤 절반: 앞으로 엎어짐
        p = dict(base)
        p.update(lhip=8 + 62 * kneel, lknee=16 + 80 * kneel, rhip=-6 + 4 * kneel, rknee=12 + 100 * kneel,
                 lhip_side=8, rhip_side=8, lean=3 + 28 * kneel + 20 * fall, head=10 * kneel + 10 * fall,
                 rsh=12 + 30 * kneel - 20 * fall, rel=24 + 30 * kneel, wpn=38 - 20 * kneel, wpn_side=14,
                 lsh=6 + 40 * kneel + 40 * fall, lab=18, lel=22 + 30 * kneel, cape=6 + 14 * fall)
        return Pose(**p)

    if anim == 'death':
        u = f / max(1, n - 1)
        k = min(1.0, u * 1.25)
        p = dict(base)
        p.update(lean=base['lean'] * (1 - k) - 6 - 12 * k, head=-22 * k,
                 lhip=legs['lhip'] * (1 - k) + 24 * k, rhip=legs['rhip'] * (1 - k) + 14 * k,
                 lhip_side=legs['lhip_side'], rhip_side=legs['rhip_side'],
                 lknee=legs['lknee'] + 30 * k, rknee=legs['rknee'] + 25 * k,
                 lsh=base['lsh'] + 40 * k, rsh=base['rsh'] + 50 * k, lab=14 + 36 * k, rab=14 + 40 * k,
                 lel=20, rel=20, wpn=base.get('wpn', 70) + 40 * k, cape=20 + 10 * k)
        return Pose(**p)
    raise ValueError(anim)


DEATH_ANG = [6, 16, 38, 68, 92, 87]     # 무릎 꺾임 → 가속하며 넘어짐 → 바닥에 튕겼다 가라앉음
DEATH_DROP = [0, 0.3, 0.8, 1.6, 2.6, 2.4]


DEATH_FWD_ANG = [0, 0, 0, 22, 62, 86]
DEATH_FWD_DROP = [0, 0, 0, 0.6, 1.6, 2.6]


def death_xform_forward(f, n=6):
    """무릎 꿇은 뒤 앞으로 엎어지는 강체 변환(무릎 앞쪽 축)."""
    u = f / max(1, n - 1) * (len(DEATH_FWD_ANG) - 1)
    i = min(int(u), len(DEATH_FWD_ANG) - 2)
    w = u - i
    ang = DEATH_FWD_ANG[i] + (DEATH_FWD_ANG[i + 1] - DEATH_FWD_ANG[i]) * w
    drop = DEATH_FWD_DROP[i] + (DEATH_FWD_DROP[i + 1] - DEATH_FWD_DROP[i]) * w
    M = S.rx(-ang)                    # 머리가 +y(앞)로 넘어감
    pivot = V(0, 6.0, 0)
    t = pivot - M @ pivot + V(0, 0, -drop)
    return M, t


def death_xform(f, n=6):
    """뒤로 쓰러지는 강체 변환(발 뒤쪽 축)."""
    if n == len(DEATH_ANG):
        ang, drop = DEATH_ANG[f], DEATH_DROP[f]
    else:
        u = f / max(1, n - 1) * (len(DEATH_ANG) - 1)
        i = min(int(u), len(DEATH_ANG) - 2)
        w = u - i
        ang = DEATH_ANG[i] + (DEATH_ANG[i + 1] - DEATH_ANG[i]) * w
        drop = DEATH_DROP[i] + (DEATH_DROP[i + 1] - DEATH_DROP[i]) * w
    M = S.rx(ang)
    pivot = V(0, -3.5, 0)
    t = pivot - M @ pivot + V(0, 0, -drop)
    return M, t
