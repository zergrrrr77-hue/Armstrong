"""리니지풍 프리렌더 도트 엔진 (SDF 레이마칭 → 팔레트 양자화 → 외곽선).

- 3D 형태를 부호거리함수(SDF)로 조립하고, 쿼터뷰(고각 30°) 직교 카메라로 렌더링한다.
- 1 단위 ≈ 1 픽셀. 바닥 z=0, 위쪽 +z, 캐릭터 정면 +y, 오른쪽 +x.
- 빛은 화면 왼쪽 위 앞쪽에서 온다(모든 방향 스프라이트에서 같은 빛).
- 재질마다 어두움→밝음 색 램프를 두고, 명암을 단계로 끊어 도트 느낌을 낸다.
"""
import math

import numpy as np
from PIL import Image

# ───────────────────────── 벡터 도우미 ─────────────────────────


def V(x, y, z):
    return np.array([x, y, z], dtype=np.float64)


def nrm(v):
    v = np.asarray(v, dtype=np.float64)
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def rx(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=np.float64)


def ry(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float64)


def rz(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=np.float64)


def frame_from(z_axis, hint=(0, 1, 0)):
    """z_axis를 로컬 z로 삼는 직교 기저(열벡터 x,y,z)."""
    z = nrm(z_axis)
    h = np.asarray(hint, dtype=np.float64)
    if abs(np.dot(h, z)) > 0.95:
        h = np.array([1.0, 0, 0]) if abs(z[0]) < 0.9 else np.array([0, 0, 1.0])
    x = nrm(np.cross(h, z))
    y = np.cross(z, x)
    return np.stack([x, y, z], axis=1)


def _len(q):
    return np.sqrt(np.einsum('ij,ij->i', q, q))


# ───────────────────────── 기본 도형 (P: (N,3) → (N,)) ─────────────────────────


def sphere(c, r):
    c = np.asarray(c, float)
    return lambda P: _len(P - c) - r


def ellipsoid(c, r, R=None):
    """R: 열벡터가 로컬 축인 3×3 회전(없으면 축 정렬)."""
    c = np.asarray(c, float)
    r = np.asarray(r, float)
    Rm = np.eye(3) if R is None else np.asarray(R, float)

    def f(P):
        q = (P - c) @ Rm
        k0 = _len(q / r)
        k1 = _len(q / (r * r))
        return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)
    return f


def capsule(a, b, ra, rb=None):
    """반지름이 a→b로 변하는 둥근 원뿔(iq sdRoundCone)."""
    rb = ra if rb is None else rb
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    ba = b - a
    l2 = float(np.dot(ba, ba))
    if l2 < 1e-9:
        return sphere(a, max(ra, rb))
    rr = ra - rb
    a2 = l2 - rr * rr
    il2 = 1.0 / l2

    def f(P):
        pa = P - a
        y = pa @ ba
        z = y - l2
        w = pa * l2 - np.outer(y, ba)
        x2 = np.einsum('ij,ij->i', w, w)
        y2 = y * y * l2
        z2 = z * z * l2
        k = np.sign(rr) * rr * rr * x2
        d_cyl = (np.sqrt(np.maximum(x2 * a2 * il2, 0)) + y * rr) * il2 - ra
        d_b = np.sqrt(x2 + z2) * il2 - rb
        d_a = np.sqrt(x2 + y2) * il2 - ra
        out = np.where(np.sign(y) * a2 * y2 < k, d_a, d_cyl)
        out = np.where(np.sign(z) * a2 * z2 > k, d_b, out)
        return out
    return f


def box(c, half, R=None, rnd=0.0):
    c = np.asarray(c, float)
    half = np.asarray(half, float)
    Rm = np.eye(3) if R is None else np.asarray(R, float)

    def f(P):
        q = np.abs((P - c) @ Rm) - half + rnd
        return _len(np.maximum(q, 0)) + np.minimum(q.max(axis=1), 0) - rnd
    return f


def cylinder(c, r, h, R=None, rnd=0.0):
    """로컬 z축 원기둥, 반높이 h."""
    c = np.asarray(c, float)
    Rm = np.eye(3) if R is None else np.asarray(R, float)

    def f(P):
        q = (P - c) @ Rm
        dx = np.sqrt(q[:, 0] ** 2 + q[:, 1] ** 2) - r + rnd
        dy = np.abs(q[:, 2]) - h + rnd
        return np.minimum(np.maximum(dx, dy), 0) + np.sqrt(np.maximum(dx, 0) ** 2 + np.maximum(dy, 0) ** 2) - rnd
    return f


def torus(c, R_, rmaj, rmin):
    """로컬 xy 평면 위 고리(R_의 z열이 고리 축)."""
    c = np.asarray(c, float)
    Rm = np.asarray(R_, float)

    def f(P):
        q = (P - c) @ Rm
        qx = np.sqrt(q[:, 0] ** 2 + q[:, 1] ** 2) - rmaj
        return np.sqrt(qx * qx + q[:, 2] ** 2) - rmin
    return f


def cone(base, tip, rbase):
    return capsule(base, tip, rbase, 0.15)


def plane_z(z0=0.0):
    return lambda P: P[:, 2] - z0


def halfspace(n, d):
    """n·p - d <= 0 쪽이 안."""
    n = nrm(n)
    return lambda P: P @ n - d


# ───────────────────────── 조합 ─────────────────────────


def union(*fs):
    def f(P):
        d = fs[0](P)
        for g in fs[1:]:
            d = np.minimum(d, g(P))
        return d
    return f


def sunion(k, *fs):
    def f(P):
        d = fs[0](P)
        for g in fs[1:]:
            d2 = g(P)
            h = np.clip(0.5 + 0.5 * (d2 - d) / k, 0, 1)
            d = d2 * (1 - h) + d * h - k * h * (1 - h)
        return d
    return f


def inter(*fs):
    def f(P):
        d = fs[0](P)
        for g in fs[1:]:
            d = np.maximum(d, g(P))
        return d
    return f


def sub(f, *gs):
    def h(P):
        d = f(P)
        for g in gs:
            d = np.maximum(d, -g(P))
        return d
    return h


def shell(f, t):
    return lambda P: np.abs(f(P)) - t


def displace(f, amp, freq, seed=0, octaves=2):
    def g(P):
        return f(P) + amp * fbm(P * freq, seed, octaves)
    return g


def xform(f, M, t):
    """f를 회전 M(열=로컬축), 이동 t만큼 옮긴 도형."""
    M = np.asarray(M, float)
    t = np.asarray(t, float)
    return lambda P: f((P - t) @ M)


# ───────────────────────── 노이즈 ─────────────────────────


def _hash3(ix, iy, iz, seed):
    h = (ix * 374761393 + iy * 668265263 + iz * 2147483647 + seed * 1442695041) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return (h & 0xFFFF) / 65535.0 * 2.0 - 1.0


def vnoise(P, seed=0):
    p = np.floor(P).astype(np.int64)
    f = P - p
    u = f * f * (3 - 2 * f)
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (u[:, 0] if dx else 1 - u[:, 0]) * (u[:, 1] if dy else 1 - u[:, 1]) * (u[:, 2] if dz else 1 - u[:, 2])
                out = out + w * _hash3(p[:, 0] + dx, p[:, 1] + dy, p[:, 2] + dz, seed)
    return out


def fbm(P, seed=0, octaves=3):
    amp, tot, s = 1.0, 0.0, 0.0
    Q = P
    for o in range(octaves):
        tot = tot + amp * vnoise(Q, seed + o * 17)
        s += amp
        amp *= 0.5
        Q = Q * 2.03
    return tot / s


def hash2(x, y, seed=0):
    """정수 격자 해시 0..1 (스칼라/배열)."""
    x = np.asarray(x, dtype=np.int64)
    y = np.asarray(y, dtype=np.int64)
    return (_hash3(x, y, np.zeros_like(x), seed) + 1) * 0.5


# ───────────────────────── 재질 ─────────────────────────


def hexrgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class Mat:
    """ramp: 어두움→밝음 색 목록.
    metal: 반사광, emit: 스스로 빛남(명암 무시), tex: f(P_local, n) → 램프 오프셋(실수 배열),
    gloss: 반사광 세기(유리·점액 등), hi: 하이라이트 색(없으면 램프 최상단).
    """

    def __init__(self, ramp, metal=False, emit=False, tex=None, gloss=0.0, hi=None, outline=None, contrast=1.0):
        self.ramp = [hexrgb(c) if isinstance(c, str) else c for c in ramp]
        self.metal = metal
        self.emit = emit
        self.tex = tex
        self.gloss = gloss if not metal else max(gloss, 0.9)
        self.hi = hexrgb(hi) if isinstance(hi, str) else hi
        self.outline = hexrgb(outline) if isinstance(outline, str) else outline
        self.contrast = contrast


def ramp_from(base, n=5, dark=0.42, light=1.35, hue_shift=True):
    """기준색 하나로 램프 생성(어두운 쪽은 푸르고 차갑게, 밝은 쪽은 따뜻하게)."""
    r, g, b = hexrgb(base)
    out = []
    for i in range(n):
        t = i / (n - 1)
        k = dark + (light - dark) * t
        rr, gg, bb = r * k, g * k, b * k
        if hue_shift:
            w = (t - 0.5)
            rr += 18 * w
            gg += 6 * w
            bb -= 14 * w
        out.append(tuple(int(max(0, min(255, v))) for v in (rr, gg, bb)))
    return out


# ───────────────────────── 렌더러 ─────────────────────────

ELEV = 30.0  # 카메라 고각(2:1 마름모 타일과 맞춤)
LIGHT_WORLD = nrm(V(-0.62, -0.42, 0.66))
OUTLINE_INK = (18, 13, 11)


class Item:
    __slots__ = ('f', 'mat', 'tag')

    def __init__(self, f, mat, tag=None):
        self.f = f
        self.mat = mat
        self.tag = tag


def _scene_eval(items, P):
    n = len(items)
    D = np.empty((n, P.shape[0]))
    for i, it in enumerate(items):
        D[i] = it.f(P)
    idx = np.argmin(D, axis=0)
    return D[idx, np.arange(P.shape[0])], idx


def _scene_dist(items, P):
    d = items[0].f(P)
    for it in items[1:]:
        d = np.minimum(d, it.f(P))
    return d


def render(items, mats, W, H, ax, ay, yaw=0.0, elev=ELEV, scale=1.0, M_obj=None, t_obj=None,
           outline=True, inner_lines=True, ao=True, shadows=True, levels=None, light=None,
           return_buffers=False, steps=240, ink=None):
    """items: [Item], mats: {이름: Mat}.
    yaw: 물체를 z축으로 돌리는 각도(도). 0이면 정면(+y)이 화면 아래(남)를 향한다.
    M_obj/t_obj: 추가 강체 변환(쓰러짐 등) — 물체 공간 p = M_obj^T (p' - t_obj).
    반환: RGBA PIL 이미지.
    """
    e = math.radians(elev)
    d_w = V(0, math.cos(e), -math.sin(e))      # 카메라가 +y 쪽(화면 위)을 내려다봄
    U_w = V(0, math.sin(e), math.cos(e))
    R_w = V(1, 0, 0)
    # 정면 +y가 화면 아래(카메라 쪽, -y)를 보도록 물체를 180° 돌린 뒤 yaw 적용
    Mrot = rz(180.0 + yaw)
    if M_obj is not None:
        Mrot = Mrot @ np.asarray(M_obj, float)
    tw = np.zeros(3) if t_obj is None else np.asarray(t_obj, float)
    # 월드 → 물체: p_o = Mrot^T (p_w - tw)
    Minv = Mrot.T

    js, is_ = np.mgrid[0:H, 0:W]
    u = (is_.ravel() + 0.5 - ax) / scale
    v = (ay - (js.ravel() + 0.5)) / scale
    Q = np.outer(u, R_w) + np.outer(v, U_w)
    T0 = 260.0
    O_w = Q - d_w * T0
    O = (O_w - tw) @ Minv.T
    D = np.tile(d_w @ Minv.T, (O.shape[0], 1))
    Lw = LIGHT_WORLD if light is None else nrm(light)
    L = Lw @ Minv.T
    Vv = -(d_w @ Minv.T)

    N = O.shape[0]
    t = np.zeros(N)
    hit = np.zeros(N, dtype=bool)
    active = np.arange(N)
    tmax = T0 * 2
    for _ in range(steps):
        if active.size == 0:
            break
        P = O[active] + D[active] * t[active, None]
        dist = _scene_dist(items, P)
        h = dist < 0.12
        hit[active[h]] = True
        t[active] += np.where(h, 0, np.maximum(dist * 0.9, 0.09))
        keep = (~h) & (t[active] < tmax)
        active = active[keep]

    hid = np.nonzero(hit)[0]
    img = np.zeros((N, 4), dtype=np.uint8)
    depth = np.full(N, np.inf)
    matid = np.full(N, -1)
    itemid = np.full(N, -1)
    lvl = np.zeros(N, dtype=np.int64)
    if hid.size:
        P = O[hid] + D[hid] * t[hid, None]
        _, idx = _scene_eval(items, P)
        itemid[hid] = idx
        # 법선 (사면체)
        eps = 0.25
        ks = np.array([[1, -1, -1], [-1, -1, 1], [-1, 1, -1], [1, 1, 1]], float)
        n = np.zeros_like(P)
        for k in ks:
            n += k * _scene_dist(items, P + k * eps)[:, None]
        n /= np.maximum(_len(n), 1e-9)[:, None]
        ndl = n @ L
        diff = np.clip(ndl, 0, 1)
        shade = 0.30 + 0.70 * diff
        if ao:
            occ = np.zeros(hid.size)
            for s, wgt in ((1.2, 0.5), (2.6, 0.3), (4.5, 0.2)):
                dd = _scene_dist(items, P + n * s)
                occ += wgt * np.clip((s - dd) / s, 0, 1)
            shade *= 1.0 - 0.55 * occ
        if shadows:
            sh_t = np.full(hid.size, 1.2)
            lit = np.ones(hid.size)
            Ps = P + n * 0.4
            for _ in range(28):
                dd = _scene_dist(items, Ps + L * sh_t[:, None])
                lit = np.minimum(lit, np.clip(6.0 * dd / sh_t, 0, 1))
                sh_t += np.clip(dd, 0.4, 3.0)
            shade *= 0.55 + 0.45 * lit
        # 가장자리 림라이트 (뒤에서 오는 약한 빛)
        rim = np.clip(1 - np.abs(n @ Vv), 0, 1) ** 3
        refl = 2 * ndl[:, None] * n - L
        spec = np.clip(refl @ Vv, 0, 1)
        names = [it.mat for it in items]
        mi = np.array([list(mats.keys()).index(names[i]) for i in range(len(items))])[idx]
        matid[hid] = mi
        depth[hid] = t[hid]
        mlist = list(mats.values())
        cols = np.zeros((hid.size, 3))
        lv = np.zeros(hid.size, dtype=np.int64)
        for m_i, m in enumerate(mlist):
            sel = mi == m_i
            if not sel.any():
                continue
            nl = len(m.ramp)
            if m.emit:
                s = 0.75 + 0.25 * diff[sel]
            else:
                s = shade[sel]
                s = 0.5 + (s - 0.5) * m.contrast
                s = s + 0.12 * rim[sel]
            if m.tex is not None:
                s = s + m.tex(P[sel], n[sel]) / (nl - 1)
            li = np.clip(np.floor(s * (nl - 1) + 0.5), 0, nl - 1).astype(np.int64)
            ramp = np.array(m.ramp, float)
            c = ramp[li]
            if m.metal or m.gloss > 0:
                pw = 18 if m.metal else 30
                sp = spec[sel] ** pw * (m.gloss if m.gloss else 1.0)
                hi = np.array(m.hi if m.hi else (min(255, m.ramp[-1][0] + 40), min(255, m.ramp[-1][1] + 40), min(255, m.ramp[-1][2] + 40)), float)
                hmask = sp > 0.45
                c[hmask] = hi
                li = np.where(hmask, nl, li)
            cols[sel] = c
            lv[sel] = li
        img[hid, :3] = np.clip(cols, 0, 255).astype(np.uint8)
        img[hid, 3] = 255
        lvl[hid] = lv

    img = img.reshape(H, W, 4)
    depth = depth.reshape(H, W)
    matid = matid.reshape(H, W)
    lvl = lvl.reshape(H, W)
    mlist = list(mats.values())

    if inner_lines:
        # 깊이 단절(앞 부품이 뒤 부품을 가리는 경계)에서 뒤쪽 픽셀을 한 단계 어둡게
        a = img[:, :, 3] > 0
        out = img.copy()
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nd = np.roll(np.roll(depth, dy, 0), dx, 1)
            mask = a & (nd + 3.5 < depth)
            ys, xs = np.nonzero(mask)
            for y, x in zip(ys, xs):
                m = mlist[matid[y, x]]
                if m.emit:
                    continue
                li = max(0, min(len(m.ramp) - 1, lvl[y, x]) - 1)
                out[y, x, :3] = m.ramp[li]
        img = out

    if outline:
        a = img[:, :, 3] > 0
        edge = np.zeros_like(a)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nb = np.roll(np.roll(a, dy, 0), dx, 1)
            edge |= a & ~nb
        ys, xs = np.nonzero(edge)
        inkc = np.array(OUTLINE_INK if ink is None else ink, float)
        for y, x in zip(ys, xs):
            m = mlist[matid[y, x]]
            if m.emit:
                continue
            base = np.array(m.outline if m.outline else m.ramp[0], float)
            img[y, x, :3] = (base * 0.55 + inkc * 0.45).astype(np.uint8)

    im = Image.fromarray(img, 'RGBA')
    if return_buffers:
        return im, depth, matid, itemid.reshape(H, W)
    return im


def glow(im, mask_fn=None, color=(120, 180, 255), radius=3, strength=0.8, mask=None):
    """mask(빛낼 픽셀) 주위에 반투명 광채를 더한다(강화 무기 등). 가장자리 넘김 없이 패딩 후 계산."""
    pad = radius + 1
    a0 = np.array(im).astype(np.float64)
    a = np.pad(a0, ((pad, pad), (pad, pad), (0, 0)))
    if mask is None:
        mask = a0[:, :, 3] > 0
    m = np.pad(mask.astype(np.float64), pad)
    acc = np.zeros_like(m)
    for r in range(1, radius + 1):
        sh = np.zeros_like(m)
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r + 1:
                    sh = np.maximum(sh, np.roll(np.roll(m, dy, 0), dx, 1))
        acc += sh
    acc = np.clip(acc / radius * strength * 0.75, 0, 0.85)
    col = np.array(color, float)
    alpha = a[:, :, 3] / 255.0
    ga = acc * (1 - alpha)
    out = a.copy()
    out_a = alpha + ga
    for k in range(3):
        out[:, :, k] = np.where(out_a > 0, (a[:, :, k] * alpha + col[k] * ga) / np.maximum(out_a, 1e-6), 0)
    tint = m * strength * 0.3
    for k in range(3):
        out[:, :, k] = out[:, :, k] * (1 - tint) + np.minimum(255, col[k] + 60) * tint
    out[:, :, 3] = np.clip(out_a * 255, 0, 255)
    out = out[pad:-pad, pad:-pad]
    return Image.fromarray(out.astype(np.uint8), 'RGBA')
