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
        head=0.0, head_yaw=0.0, cape=0.0, crouch=0.0, glow=0.0, draw=0.0, mouth=0.0,
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
        self.lhp, self.lkn, self.lan = leg(-1, p.lhip, p.lknee, p.lhip_side)
        self.rhp, self.rkn, self.ran = leg(1, p.rhip, p.rknee, p.rhip_side)
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


def cape(r, p, mat, length=30, width=7.0, sway=0.0, tatter=False):
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
        'tabard': Mat(['#0e1426', '#172243', '#22335f', '#304679', '#3f5a92']),
        'mail': Mat(['#1d2026', '#30343c', '#474c56', '#626874', '#7d8491'], metal=True,
                    tex=lambda P, n: 0.6 * ((np.floor(P[:, 2] * 0.9) + np.floor(P[:, 0] * 0.9)) % 2 - 0.5)),
        'plume': Mat(['#3a0c0c', '#5e1414', '#861d1d', '#aa2a26', '#c94236']),
        'hair': Mat(['#1a120c', '#2a1d14', '#3b2a1d', '#4d3827', '#5f4632']),
    })
    parts = dict(skin='skin', hair='hair', eyes='eyes', torso='steel', pelvis='mail', legs='mail', shin='steel',
                 boots='steel_dk', arms='mail', farm='steel', hands='steel_dk')

    def gear(r, p, it):
        it += helmet_knight(r, 'steel', 'cloth_dk', plume='plume')
        it += pauldrons(r, 'steel', 3.4, trim='steel_dk')
        it += skirt(r, 'tabard', 5.4, 6.4, 9.0)
        # 가슴 위 휘장(사각 천)
        it.append(Item(S.box(r.chest + r.fwd * 3.9 * r.s - r.up * 3.0 * r.s, V(3.4 * r.s, 0.5 * r.s, 6.0 * r.s), r.rot, 0.3), 'tabard'))
        it.append(Item(S.box(r.chest + r.fwd * 4.4 * r.s - r.up * 1.8 * r.s, V(0.5 * r.s, 0.4 * r.s, 2.4 * r.s), r.rot, 0.1), 'gold'))
        it.append(Item(S.box(r.chest + r.fwd * 4.4 * r.s - r.up * 1.2 * r.s, V(1.8 * r.s, 0.4 * r.s, 0.5 * r.s), r.rot, 0.1), 'gold'))
        it += sword(r, m, 21, guard='steel_dk', grip='leather', blade='steel', pommel='gold')
        it += shield_kite(r, 'tabard', 'steel', 'gold', 1.0, emblem='gold')
    return dict(name='knight', label='기사', mats=m, parts=parts, gear=gear, weapon='sword', build=None, opts=dict(hair=False, eyes=False))


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
        it += sword(r, m, 22, guard='gold', grip='cape', blade='steel', pommel='gem')
    return dict(name='lord', label='군주', mats=m, parts=parts, gear=gear, weapon='sword', build=dict(scale=1.02),
                opts=dict(chest=(6.9, 4.3, 5.8)))


CLASSES = [_class_knight(), _class_elf(), _class_mage(), _class_lord()]


# ───────────────────────── 동작 ─────────────────────────

ANIMS = [('idle', 4), ('walk', 6), ('attack', 5), ('hurt', 2), ('death', 4)]


def pose_for(kind, anim, f, n):
    """kind: 'sword' | 'bow' | 'staff' | 'axe' | 'claw'"""
    t = f / n
    ph = 2 * math.pi * t
    if kind == 'bow':
        base = dict(lsh=40, lab=6, lel=10, rsh=12, rab=12, rel=30, wpn=40)
    elif kind == 'staff':
        base = dict(rsh=26, rel=45, rab=14, wpn=170, wpn_side=-6, lsh=10, lel=25)
    elif kind == 'great':
        base = dict(rsh=30, rel=40, rab=18, wpn=125, wpn_side=-22, lsh=26, lel=55, lab=20)
    else:  # sword / axe
        base = dict(rsh=14, rel=34, rab=12, wpn=62, wpn_side=-12, lsh=30, lel=46, lab=16)

    if anim == 'idle':
        b = math.sin(ph)
        return Pose(**base, bob=-0.35 + 0.35 * b, lean=2 + 0.6 * b, cape=1 + b)
    if anim == 'walk':
        sw = math.sin(ph)
        cw = math.cos(ph)
        p = dict(base)
        p.update(lhip=26 * sw, rhip=-26 * sw,
                 lknee=6 + 34 * max(0.0, cw), rknee=6 + 34 * max(0.0, -cw),
                 lean=5, twist=-5 * sw, cape=8 + 3 * abs(cw))
        if kind not in ('bow',):
            p['lsh'] = base['lsh'] + (-16 * sw if kind != 'staff' else -24 * sw)
        p['rsh'] = base['rsh'] + 14 * sw
        p['bob'] = 0.5 * abs(math.sin(ph))
        return Pose(**p)
    if anim == 'attack':
        if kind == 'bow':
            k = [0.0, 0.5, 1.0, 1.0, 0.2][f]
            return Pose(lsh=88, lab=4, lel=2, rsh=88 - 6 * k, rab=10, rel=40 + 100 * k, lean=4, twist=10 + 14 * k,
                        draw=k if f < 4 else 0.0, rhip=-10, lhip=10)
        if kind == 'staff':
            seq = [(60, 120, 165, -6, 0), (140, 60, 200, 0, 0.5), (150, 30, 205, 0, 1.0), (80, 10, 120, 0, 1.0), (45, 30, 150, -4, 0.3)]
            rs, rl, w, ws, g = seq[f]
            return Pose(rsh=rs, rel=rl, rab=14, wpn=w, wpn_side=ws, lsh=40 + 40 * g, lel=20, lab=26,
                        lean=-4 + 10 * g, glow=g, lhip=8 * g, rhip=-8 * g)
        if kind == 'great':
            seq = [(70, 80, 160, -30, -8, -14), (150, 50, 205, -10, -12, -24), (110, 20, 130, 10, 6, 6),
                   (40, 15, 70, 25, 12, 24), (20, 30, 95, 10, 6, 12)]
        else:
            seq = [(60, 70, 150, -20, -6, -10), (150, 40, 200, -10, -10, -22), (105, 15, 120, 10, 6, 6),
                   (35, 10, 60, 22, 10, 22), (20, 35, 95, 0, 4, 8)]
        rs, rl, w, ws, ln, tw = seq[f]
        return Pose(rsh=rs, rel=rl, rab=16, wpn=w, wpn_side=ws, lsh=40, lel=50, lab=20, shd=1,
                    lean=ln, twist=tw, lhip=10 if f >= 2 else 0, rhip=-12 if f >= 2 else 0, lknee=12, rknee=10)
    if anim == 'hurt':
        k = [1.0, 0.55][f]
        p = dict(base)
        p.update(lean=-14 * k, head=-12 * k, lsh=base['lsh'] + 20 * k, rsh=base['rsh'] - 10 * k, rab=24 * k + 10,
                 lknee=14 * k, rknee=10 * k, lhip=-8 * k, rhip=6 * k, cape=14 * k)
        return Pose(**p)
    if anim == 'death':
        p = dict(base)
        k = [0.15, 0.45, 0.8, 1.0][f]
        p.update(lean=-6 - 10 * k, head=-20 * k, lknee=40 * k, rknee=30 * k, lhip=20 * k, rhip=12 * k,
                 lsh=60 * k, rsh=70 * k, lab=40 * k, rab=40 * k, lel=20, rel=20, wpn=110 + 60 * k, cape=20)
        return Pose(**p)
    raise ValueError(anim)


def death_xform(f, height=50.0):
    """뒤로 쓰러지는 강체 변환(발 뒤쪽 축)."""
    ang = [8, 30, 64, 86][f]
    M = S.rx(ang)                     # 머리가 -y(뒤)로 넘어감
    pivot = V(0, -3.5, 0)
    drop = [0, 0.5, 1.5, 2.5][f]
    t = pivot - M @ pivot + V(0, 0, -drop)
    return M, t
