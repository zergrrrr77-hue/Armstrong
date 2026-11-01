"""스킬 이펙트 시트 (2D 절차 생성, 가산 혼합용).

각 이펙트는 두 층으로 나뉜다: under(캐릭터 뒤·바닥), over(캐릭터 앞).
캐릭터 발 위치(ax, ay)에 맞춰 그리고, 캐릭터 스킬 동작과 같은 프레임 수로 함께 재생한다.
게임에서는 globalCompositeOperation='lighter'(가산)로 그리면 빛처럼 보인다.
"""
import math

import numpy as np
from PIL import Image

BLUE = ['#0c1650', '#1f3aa8', '#3f6cf0', '#86a8ff', '#d6e4ff', '#ffffff']
GOLD = ['#4a2a04', '#a0600c', '#e09a1e', '#ffd25a', '#fff0b0', '#ffffff']
STONE = ['#202024', '#3a3a44', '#5a5a66', '#80808c', '#a8a8b4', '#d0d0d8']


def _hex(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


class Layer:
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.Y, self.X = np.mgrid[0:H, 0:W].astype(np.float64) + 0.5
        self.I = np.zeros((H, W))

    def add(self, v):
        self.I += v

    def ring(self, cx, cy, rx, ry, width, amp=1.0, a0=None, a1=None, fade=None, half=None):
        """타원 고리. a0~a1: 각도 범위(라디안, 화면 기준), half: 'back'(위쪽 반)|'front'(아래쪽 반)."""
        nx = (self.X - cx) / max(rx, 0.1)
        ny = (self.Y - cy) / max(ry, 0.1)
        r = np.sqrt(nx * nx + ny * ny)
        d = np.abs(r - 1) * ry
        v = np.clip(1 - d / width, 0, 1) * amp
        ang = np.arctan2(ny, nx)
        if a0 is not None:
            span = (a1 - a0) % (2 * math.pi)
            rel = (ang - a0) % (2 * math.pi)
            inside = rel <= span
            v = v * inside
            if fade:   # 0 → 1 로 진해짐(머리 쪽이 a1)
                v = v * np.clip(rel / max(span, 1e-6), 0, 1) ** fade
        if half == 'back':
            v = v * (self.Y < cy)
        elif half == 'front':
            v = v * (self.Y >= cy)
        self.add(v)
        return ang

    def disk(self, cx, cy, rx, ry, amp=1.0, power=1.5):
        nx = (self.X - cx) / max(rx, 0.1)
        ny = (self.Y - cy) / max(ry, 0.1)
        self.add(np.clip(1 - np.sqrt(nx * nx + ny * ny), 0, 1) ** power * amp)

    def dot(self, x, y, r, amp=1.0):
        d = np.sqrt((self.X - x) ** 2 + (self.Y - y) ** 2)
        self.add(np.clip(1 - d / max(r, 0.5), 0, 1) * amp)

    def beam(self, x, y_bot, height, w, amp=1.0, taper=True):
        """아래(y_bot)에서 위로 솟은 빛 기둥(끝이 뾰족)."""
        top = y_bot - height
        t = np.clip((y_bot - self.Y) / max(height, 1), 0, 1)
        inside = (self.Y <= y_bot) & (self.Y >= top)
        ww = w * ((1 - t) if taper else 1) + 0.3
        v = np.clip(1 - np.abs(self.X - x) / ww, 0, 1) * inside * (0.55 + 0.45 * (1 - t))
        self.add(v * amp)

    def line(self, x0, y0, x1, y1, w, amp=1.0):
        px, py = self.X - x0, self.Y - y0
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy + 1e-9
        t = np.clip((px * dx + py * dy) / L2, 0, 1)
        d = np.sqrt((px - t * dx) ** 2 + (py - t * dy) ** 2)
        self.add(np.clip(1 - d / w, 0, 1) * amp)

    def image(self, ramp, levels=5):
        I = np.clip(self.I, 0, 1.6)
        q = np.floor(np.clip(I, 0, 1) * levels) / levels
        cols = np.array([_hex(c) for c in ramp], np.float64)
        idx = np.clip((q * (len(ramp) - 1)).round().astype(int), 0, len(ramp) - 1)
        rgb = cols[idx]
        core = I > 1.15
        rgb[core] = 255
        a = np.clip(q * 1.25, 0, 1)
        out = np.zeros((self.H, self.W, 4), np.uint8)
        out[..., :3] = rgb.astype(np.uint8)
        out[..., 3] = (a * 255).astype(np.uint8)
        return Image.fromarray(out, 'RGBA')


def _rng(seed):
    return np.random.default_rng(seed)


# ── 회전 베기 ──────────────────────────────────────────
def spin(n=8):
    W, H, ax, ay = 176, 112, 88, 78
    cy = ay - 20
    under, over = [], []
    heads = [None, -0.6, 0.6, 2.0, 3.4, 4.8, 6.1, 6.6]
    for f in range(n):
        U, O = Layer(W, H), Layer(W, H)
        h = heads[f] if f < len(heads) else None
        if h is not None:
            amp = 1.0 if f < 7 else 0.45
            span = 3.6 if f < 7 else 2.6
            for L, half in ((U, 'back'), (O, 'front')):
                L.ring(ax, cy, 54, 27, 7.5, amp, h - span, h, fade=1.0, half=half)
                L.ring(ax, cy, 54, 27, 14, amp * 0.35, h - span, h, fade=1.4, half=half)
                L.ring(ax, cy, 44, 22, 2.4, amp * 0.7, h - span * 0.8, h, fade=1.6, half=half)
            hx, hy = ax + math.cos(h) * 54, cy + math.sin(h) * 27
            L = O if hy >= cy else U
            L.dot(hx, hy, 5, 1.3 * amp)
            r = _rng(f)
            for k in range(7):
                a = h - r.uniform(0, span * 0.7)
                rr = r.uniform(48, 62)
                px, py = ax + math.cos(a) * rr, cy + math.sin(a) * rr * 0.5
                (O if py >= cy else U).dot(px, py, r.uniform(0.8, 1.6), 1.0 * amp)
            U.disk(ax, ay, 40, 18, 0.18 * amp)
        under.append(U.image(BLUE))
        over.append(O.image(BLUE))
    return dict(label='회전 베기', fw=W, fh=H, ax=ax, ay=ay, under=under, over=over, anim='skill_spin', color='blue')


# ── 대지 강타 ──────────────────────────────────────────
def slam(n=8):
    W, H, ax, ay = 144, 176, 72, 134
    hit = 4
    under, over = [], []
    r0 = _rng(11)
    pillars = [(r0.uniform(-46, 46), r0.uniform(-20, 20)) for _ in range(9)]
    pillars = [(x, y * 0.5) for x, y in pillars if (x / 50) ** 2 + (y / 22) ** 2 < 1.1]
    shards = [(r0.uniform(-30, 30), r0.uniform(-12, 12), r0.uniform(1.5, 3.5), r0.uniform(0.6, 1.4)) for _ in range(14)]
    for f in range(n):
        U, O, D = Layer(W, H), Layer(W, H), Layer(W, H)
        if 1 <= f < hit:   # 내려치기 전: 검끝에 모이는 빛
            k = f / hit
            O.dot(ax + 4, ay - 62 - f * 2, 3 + 4 * k, 0.6 + 0.6 * k)
            for j in range(5):
                a = j * 1.26 + f
                O.dot(ax + 4 + math.cos(a) * 12 * (1 - k), ay - 62 - f * 2 + math.sin(a) * 12 * (1 - k), 1.2, 0.9)
        if f >= hit:
            t = (f - hit) / max(1, n - 1 - hit)          # 0..1
            fade = 1 - 0.75 * t
            R = 14 + 52 * t
            U.ring(ax, ay, R, R * 0.5, 3.0, 1.0 * fade)
            U.ring(ax, ay, R * 0.7, R * 0.35, 1.5, 0.6 * fade)
            U.disk(ax, ay, 30 + 20 * t, 13 + 9 * t, 0.9 * fade, 1.2)
            for k, (px, py) in enumerate(pillars):
                grow = min(1.0, (f - hit + 1) / 2.0)
                hgt = (70 + (k * 17) % 40) * grow * (1.0 if t < 0.7 else 1.6 - t)
                O.beam(ax + px, ay + py, hgt, 3.2 + (k % 3), 1.0 * fade)
            O.beam(ax, ay + 2, 120 * min(1.0, (f - hit + 1) / 2.0), 6.5, 1.2 * fade)
            for (sx, sy, sp, sz) in shards:   # 튀어오르는 돌 파편
                tt = (f - hit + 0.5) * 0.9
                px = ax + sx * (1 + tt * 0.8)
                py = ay + sy * 0.5 - (sp * 9 * tt - 5 * tt * tt)
                if py < ay + 10:
                    D.dot(px, py, 1.4 * sz, 1.0)
        under.append(U.image(BLUE))
        o = O.image(BLUE)
        d = D.image(STONE, 4)
        o.alpha_composite(d)
        over.append(o)
    return dict(label='대지 강타', fw=W, fh=H, ax=ax, ay=ay, under=under, over=over, anim='skill_slam', color='blue')


# ── 수호 결계 ──────────────────────────────────────────
def guard(n=6):
    W, H, ax, ay = 144, 150, 72, 110
    under, over = [], []
    for f in range(n):
        U, O = Layer(W, H), Layer(W, H)
        grow = 0.55 if f == 0 else 1.0
        rx, ry = 50 * grow, 25 * grow
        rot = f * (2 * math.pi / n) / 3
        # 바닥 마법진: 겹고리 + 별 + 눈금(룬)
        U.ring(ax, ay, rx, ry, 1.8, 1.0)
        U.ring(ax, ay, rx * 0.82, ry * 0.82, 1.2, 0.8)
        U.ring(ax, ay, rx * 0.4, ry * 0.4, 1.0, 0.6)
        pts = [(ax + math.cos(rot + k * 2 * math.pi / 6) * rx * 0.82, ay + math.sin(rot + k * 2 * math.pi / 6) * ry * 0.82) for k in range(6)]
        for k in range(6):
            x0, y0 = pts[k]
            x1, y1 = pts[(k + 2) % 6]
            U.line(x0, y0, x1, y1, 1.0, 0.55)
        for k in range(24):
            a = -rot * 1.5 + k * 2 * math.pi / 24
            x0, y0 = ax + math.cos(a) * rx * 0.86, ay + math.sin(a) * ry * 0.86
            x1, y1 = ax + math.cos(a) * rx * 0.96, ay + math.sin(a) * ry * 0.96
            U.line(x0, y0, x1, y1, 0.9, 0.7 if k % 3 else 1.0)
        U.disk(ax, ay, rx, ry, 0.22)
        # 돔: 반구 윤곽(뒤쪽은 under, 앞쪽은 over) + 옅은 면
        dome_h = 62 * grow
        for L, sgn in ((U, -1), (O, 1)):
            for k in range(5):     # 위도선
                lat = k / 5
                yy = ay - dome_h * math.sin(lat * math.pi / 2)
                rr = math.cos(lat * math.pi / 2)
                L.ring(ax, yy, rx * rr, ry * rr, 1.1, 0.5 if k else 0.0, half='back' if sgn < 0 else 'front')
        # 돔 외곽선(실루엣): 위쪽 반타원
        O.ring(ax, ay, rx, dome_h, 1.6, 0.9, a0=math.pi, a1=2 * math.pi)
        nx = (O.X - ax) / rx
        ny = (O.Y - ay) / dome_h
        inside = (nx * nx + ny * ny < 1) & (O.Y < ay)
        O.add(inside * (0.10 + 0.08 * math.sin(f)))
        r = _rng(40 + f)
        for k in range(8):
            px = ax + r.uniform(-rx * 0.8, rx * 0.8)
            py = ay - ((f * 9 + k * 13) % 60)
            O.dot(px, py, 1.1, 0.9)
        under.append(U.image(BLUE))
        over.append(O.image(BLUE))
    return dict(label='수호 결계', fw=W, fh=H, ax=ax, ay=ay, under=under, over=over, anim='skill_guard', color='blue', loop=True)


# ── 성스러운 축복 ──────────────────────────────────────
def bless(n=8):
    W, H, ax, ay = 136, 200, 68, 164
    under, over = [], []
    r0 = _rng(77)
    beams = [(r0.uniform(-40, 40), r0.uniform(0.4, 1.0), r0.uniform(1.5, 3.2)) for _ in range(11)]
    for f in range(n):
        U, O = Layer(W, H), Layer(W, H)
        k = min(1.0, f / 3.0)
        rx, ry = 46, 23
        rot = f * 0.25
        U.ring(ax, ay, rx * (0.6 + 0.4 * k), ry * (0.6 + 0.4 * k), 1.8, 1.0 * k)
        U.ring(ax, ay, rx * 0.78, ry * 0.78, 1.1, 0.7 * k)
        for j in range(16):
            a = rot + j * 2 * math.pi / 16
            U.dot(ax + math.cos(a) * rx * 0.9, ay + math.sin(a) * ry * 0.9, 1.2, 0.9 * k)
        for j in range(8):
            a = -rot + j * 2 * math.pi / 8
            U.line(ax, ay, ax + math.cos(a) * rx * 0.75, ay + math.sin(a) * ry * 0.75, 0.8, 0.4 * k)
        U.disk(ax, ay, rx, ry, 0.35 * k)
        if f >= 2:   # 하늘에서 내려오는 빛줄기
            for j, (bx, ln, w) in enumerate(beams):
                phase = ((f - 2) * 0.22 + j * 0.13) % 1.0
                inten = math.sin(phase * math.pi) * k
                yb = ay + (j % 3) * 3 - 4
                O.beam(ax + bx, yb, 150 * ln, w, 0.75 * inten, taper=False)
            O.beam(ax, ay, 175, 9 * k, 0.55 * k, taper=False)
            O.beam(ax, ay, 175, 3.5 * k, 0.9 * k, taper=False)
        r = _rng(90 + f)
        for j in range(12):
            O.dot(ax + r.uniform(-44, 44), ay - r.uniform(5, 130), r.uniform(0.8, 1.5), 1.0 * k)
        under.append(U.image(GOLD))
        over.append(O.image(GOLD))
    return dict(label='성스러운 축복', fw=W, fh=H, ax=ax, ay=ay, under=under, over=over, anim='skill_bless', color='gold')


def build_all():
    return {'spin': spin(), 'slam': slam(), 'guard': guard(), 'bless': bless()}
