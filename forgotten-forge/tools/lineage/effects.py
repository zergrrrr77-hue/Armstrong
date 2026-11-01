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
    return dict(label='회전 베기', fw=W, fh=H, ax=ax, ay=ay, under=under, over=over, anim='skill_spin', color='blue', actor='knight')


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
    return dict(label='대지 강타', fw=W, fh=H, ax=ax, ay=ay, under=under, over=over, anim='skill_slam', color='blue', actor='knight')


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
    return dict(label='수호 결계', fw=W, fh=H, ax=ax, ay=ay, under=under, over=over, anim='skill_guard', color='blue', loop=True, actor='knight')


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
    return dict(label='성스러운 축복', fw=W, fh=H, ax=ax, ay=ay, under=under, over=over, anim='skill_bless', color='gold', actor='knight')


def build_all():
    return {'spin': spin(), 'slam': slam(), 'guard': guard(), 'bless': bless()}


# ───────────────────────── 요정·마법사 스킬 이펙트 ─────────────────────────
# dirs=True: 방향마다 다른 이펙트(화살·마력 화살·운석) → under/over/solid 가 [방향][프레임] 목록.

from PIL import ImageDraw

GREEN = ['#0c2a06', '#1e5a10', '#3e9a1e', '#7ad040', '#c8f490', '#ffffff']
ICE = ['#06204a', '#0e4a8e', '#2a86d8', '#74c4ff', '#d0f0ff', '#ffffff']
ARCANE = ['#200a40', '#4a1890', '#7a3ae0', '#b47cff', '#e6ccff', '#ffffff']


def screen_dir(d):
    """방향 번호(0=S, 45°씩) → 화면 위 단위 이동(월드 1단위당 (dx, dy))."""
    a = math.radians(180 + 45 * d)
    fx, fy = -math.sin(a), math.cos(a)
    return fx, -fy * 0.5


def _leafp(L, x, y, ang, ln=3.0, amp=1.0):
    L.line(x - math.cos(ang) * ln, y - math.sin(ang) * ln * 0.6, x + math.cos(ang) * ln, y + math.sin(ang) * ln * 0.6, 1.1, amp)


def _merge(*imgs):
    out = imgs[0].copy()
    for im in imgs[1:]:
        out.alpha_composite(im)
    return out


def wind_arrow(n=8):
    W, H, ax, ay = 240, 170, 120, 118
    under, over = [[] for _ in range(8)], [[] for _ in range(8)]
    for d in range(8):
        dx, dy = screen_dir(d)
        ox, oy = ax + dx * 8, ay - 28 + dy * 8
        for f in range(n):
            U, O = Layer(W, H), Layer(W, H)
            if f <= 4:   # 기 모으기: 몸 주위를 도는 잎과 바람 고리
                k = (f + 1) / 5
                r = 30 - 12 * k
                for L, half in ((U, 'back'), (O, 'front')):
                    L.ring(ax, ay - 14, r + 6, (r + 6) * 0.5, 3.4, 1.0 * k, f * 1.3, f * 1.3 + 4.2, fade=1.0, half=half)
                rr = _rng(200 + f)
                for j in range(9):
                    a = f * 0.9 + j * 0.7
                    px, py = ax + math.cos(a) * r, ay - 14 + math.sin(a) * r * 0.5 - j * 2
                    _leafp(O if math.sin(a) > 0 else U, px, py, a + 1.6, 2.6, 0.9 * k)
                O.dot(ox, oy, 2 + 3 * k, 0.8 * k)
            else:        # 발사: 화살 궤적과 감기는 바람
                t = (f - 4) / 3
                Lm = 40 + 70 * t
                hx, hy = ox + dx * Lm * 1.0, oy + dy * Lm * 1.0
                O.line(ox, oy, hx, hy, 3.4, 1.0)
                O.line(ox + dx * Lm * 0.3, oy + dy * Lm * 0.3, hx, hy, 7.0, 0.5)
                O.dot(hx, hy, 7.5, 1.5)
                for j in range(4):    # 바람 고리(궤적을 감쌈)
                    c = 0.25 + j * 0.22
                    O.ring(ox + dx * Lm * c, oy + dy * Lm * c, 6 + j * 1.5, 9 + j * 1.5, 1.4, 0.8 * (1 - t * 0.5))
                rr = _rng(300 + f + d)
                for j in range(8):
                    c = rr.uniform(0.1, 1.0)
                    _leafp(O, ox + dx * Lm * c + rr.uniform(-6, 6), oy + dy * Lm * c + rr.uniform(-6, 6), rr.uniform(0, 6.3), 2.4, 0.8)
                U.disk(ax, ay, 22, 10, 0.3 * (1 - t))
            under[d].append(U.image(GREEN))
            over[d].append(O.image(GREEN))
    return dict(label='바람 화살', fw=W, fh=H, ax=ax, ay=ay, under=under, over=over, anim='skill_wind', color='green',
                dirs=True, actor='elf')


def volley(n=8):
    W, H, ax, ay = 240, 190, 120, 140
    back = [0, 2, 7, 12, 15, 17, 16, 16]
    up = [0, 3, 9, 12, 11, 6, 0, 0]
    under, over = [[] for _ in range(8)], [[] for _ in range(8)]
    for d in range(8):
        dx, dy = screen_dir(d)
        for f in range(n):
            U, O = Layer(W, H), Layer(W, H)
            if 1 <= f <= 2:   # 도약: 발밑 잎 폭발
                k = 1 if f == 1 else 0.6
                U.ring(ax, ay, 22 + 14 * (f - 1), 11 + 7 * (f - 1), 3.0, 1.0 * k)
                rr = _rng(400 + f)
                for j in range(10):
                    a = rr.uniform(0, 6.3)
                    _leafp(O, ax + math.cos(a) * rr.uniform(6, 24), ay - rr.uniform(0, 18), a, 2.4, 0.9 * k)
            cx = ax - dx * back[f]
            cy = ay - dy * back[f] - up[f] * 0.87 - 30
            if 4 <= f <= 6:   # 부채꼴 3발
                t = (f - 4) / 2
                for spread in (-0.32, 0.0, 0.32):
                    ca, sa = math.cos(spread), math.sin(spread)
                    ddx, ddy = dx * ca - dy * 2 * sa, (dx * sa + dy * 2 * ca) * 0.5
                    Lm = 30 + 80 * t
                    hx, hy = cx + ddx * Lm, cy + ddy * Lm + 8 * t
                    O.line(cx, cy, hx, hy, 2.8, 0.9)
                    O.line(cx + ddx * Lm * 0.5, cy + ddy * Lm * 0.5, hx, hy, 5.0, 0.45)
                    O.dot(hx, hy, 6.0, 1.5)
                O.dot(cx, cy, 5 * (1 - t) + 1, 0.9)
            if f == 3:
                O.dot(cx, cy, 6, 0.8)
            under[d].append(U.image(GREEN))
            over[d].append(O.image(GREEN))
    return dict(label='도약 연사', fw=W, fh=H, ax=ax, ay=ay, under=under, over=over, anim='skill_volley', color='green',
                dirs=True, actor='elf')


def whirl(n=8):
    W, H, ax, ay = 176, 150, 88, 112
    under, over = [], []
    for f in range(n):
        U, O = Layer(W, H), Layer(W, H)
        k = 0.0 if f == 0 else (0.5 if f == 7 else 1.0)
        for j in range(5):     # 위로 올라갈수록 넓어지는 회오리 고리
            yy = ay - 6 - j * 13
            rx = 30 + j * 8 + f * 1.5
            h = f * 1.4 + j * 0.9
            for L, half in ((U, 'back'), (O, 'front')):
                L.ring(ax, yy, rx, rx * 0.42, 4.2 - j * 0.4, (1.1 - j * 0.1) * k, h, h + 3.6, fade=1.0, half=half)
        rr = _rng(500 + f)
        for j in range(16):
            a = f * 0.8 + rr.uniform(0, 6.3)
            hgt = rr.uniform(0, 60)
            rad = 26 + hgt * 0.6
            px, py = ax + math.cos(a) * rad, ay - 6 - hgt + math.sin(a) * rad * 0.4
            _leafp(O if math.sin(a) > 0 else U, px, py, a + 1.4, 2.8, 1.0 * k)
        U.disk(ax, ay, 40, 17, 0.25 * k)
        under.append(U.image(GREEN))
        over.append(O.image(GREEN))
    return dict(label='잎 회오리', fw=W, fh=H, ax=ax, ay=ay, under=under, over=over, anim='skill_whirl', color='green', actor='elf')


def fairy(n=8):
    W, H, ax, ay = 160, 180, 80, 140
    under, over = [], []
    for f in range(n):
        U, O = Layer(W, H), Layer(W, H)
        k = min(1.0, f / 2.0)
        b = math.sin(2 * math.pi * f / n)
        rx, ry = 44, 22
        rot = f * 0.3
        U.ring(ax, ay, rx * (0.6 + 0.4 * k), ry * (0.6 + 0.4 * k), 1.8, 1.0 * k)
        U.ring(ax, ay, rx * 0.75, ry * 0.75, 1.0, 0.7 * k)
        for j in range(12):
            a = rot + j * 2 * math.pi / 12
            _leafp(U, ax + math.cos(a) * rx * 0.88, ay + math.sin(a) * ry * 0.88, a + 1.57, 2.4, 0.9 * k)
        U.disk(ax, ay, rx, ry, 0.3 * k)
        if k > 0.3:   # 등 뒤 요정 날개 (위 2장, 아래 2장)
            wy = ay - 40 - 2 * k
            flap = 1.0 + 0.12 * b
            for sx in (-1, 1):
                for (cxo, cyo, wx, wh, tilt, amp) in ((16, -10, 15, 22, 0.5, 0.9), (13, 8, 10, 13, -0.4, 0.7)):
                    cx, cy = ax + sx * cxo * flap, wy + cyo
                    nx = (U.X - cx)
                    ny = (U.Y - cy)
                    ca, sa = math.cos(tilt * sx), math.sin(tilt * sx)
                    rxp = (nx * ca + ny * sa) / (wx * flap)
                    ryp = (-nx * sa + ny * ca) / wh
                    rr = np.sqrt(rxp ** 2 + ryp ** 2)
                    U.add(np.clip(1 - np.abs(rr - 1) * 7, 0, 1) * amp * k)       # 날개 테두리
                    U.add((rr < 1) * 0.22 * k)                                  # 날개 막
                    U.add(np.clip(1 - np.abs(rxp * 0.0 + ryp * 0.9 - rxp * 0.5) * 9, 0, 1) * (rr < 1) * 0.4 * k)  # 날개맥
        rr0 = _rng(600 + f)
        for j in range(14):   # 내려오는 잎과 반짝임
            x = ax + rr0.uniform(-50, 50)
            y = ay - 130 + ((f * 14 + j * 23) % 130)
            _leafp(O, x, y, rr0.uniform(0, 6.3), 2.2, 0.9 * k)
            O.dot(x + 4, y - 6, 0.9, 0.9 * k)
        O.beam(ax, ay, 150, 5 * k, 0.35 * k, taper=False)
        under.append(U.image(GREEN))
        over.append(O.image(GREEN))
    return dict(label='요정의 축복', fw=W, fh=H, ax=ax, ay=ay, under=under, over=over, anim='skill_fairy', color='green', actor='elf')


def magic_bolt(n=8):
    W, H, ax, ay = 240, 170, 120, 118
    under, over = [[] for _ in range(8)], [[] for _ in range(8)]
    for d in range(8):
        dx, dy = screen_dir(d)
        ox, oy = ax + dx * 14, ay - 32 + dy * 14
        for f in range(n):
            U, O, P = Layer(W, H), Layer(W, H), Layer(W, H)
            if 1 <= f <= 3:     # 손끝 마법진
                k = f / 3
                O.ring(ox, oy, 6 + 4 * k, 9 + 6 * k, 1.0, 0.9)
                O.ring(ox, oy, 3 + 2 * k, 5 + 3 * k, 0.8, 0.6)
                O.dot(ox, oy, 2 + 2 * k, 1.2)
            if 4 <= f <= 5:     # 마력 화살 날아감
                t = (f - 4) / 1.0
                Lm = 30 + 60 * t
                hx, hy = ox + dx * Lm, oy + dy * Lm
                O.line(ox + dx * Lm * 0.3, oy + dy * Lm * 0.3, hx, hy, 2.4, 0.9)
                O.line(hx - dx * 8, hy - dy * 8, hx, hy, 4.0, 0.7)
                O.dot(hx, hy, 4, 1.4)
            if f >= 5:          # 끝에서 보랏빛 마력구가 터짐
                t = (f - 5) / 2
                ex, ey = ox + dx * 92, oy + dy * 92
                P.dot(ex, ey, 8 + 6 * t, 1.2 * (1 - 0.4 * t))
                P.ring(ex, ey, 10 + 14 * t, 10 + 14 * t, 1.6, 0.9 * (1 - 0.5 * t))
                for j in range(8):
                    a = j * math.pi / 4 + t
                    P.line(ex, ey, ex + math.cos(a) * (14 + 12 * t), ey + math.sin(a) * (14 + 12 * t), 0.9, 0.7 * (1 - t * 0.6))
            under[d].append(U.image(ICE))
            over[d].append(_merge(O.image(ICE), P.image(ARCANE)))
    return dict(label='마력 화살', fw=W, fh=H, ax=ax, ay=ay, under=under, over=over, anim='skill_bolt', color='blue',
                dirs=True, actor='mage')


def _crystal(L, x, y, h, w, tilt, amp):
    """바닥에서 솟은 얼음 결정(가운데 밝은 모서리)."""
    tx, ty = x + tilt * h, y - h
    for frac, a2 in ((1.0, 0.55), (0.45, 0.9)):
        ww = w * frac
        px, py = L.X - x, L.Y - y
        dx, dy = tx - x, ty - y
        Ln = math.hypot(dx, dy) + 1e-6
        ux, uy = dx / Ln, dy / Ln
        along = px * ux + py * uy
        across = px * -uy + py * ux
        t = np.clip(along / Ln, 0, 1)
        inside = (along >= 0) & (along <= Ln) & (np.abs(across) <= ww * (1 - t))
        L.add(inside * amp * a2 * (0.6 + 0.4 * t))
    L.line(x, y, tx, ty, 0.8, amp * 0.8)


def ice_burst(n=8):
    W, H, ax, ay = 200, 170, 100, 130
    hit = 3
    under, over = [], []
    rr0 = _rng(700)
    crystals = []
    for j in range(16):
        a = j * 2 * math.pi / 16 + rr0.uniform(-0.15, 0.15)
        rad = rr0.uniform(26, 46)
        crystals.append((math.cos(a) * rad * 1.2, math.sin(a) * rad * 0.6, rr0.uniform(34, 64), rr0.uniform(6, 10), math.cos(a) * 0.4))
    for f in range(n):
        U, O = Layer(W, H), Layer(W, H)
        if f < hit:
            k = (f + 1) / hit
            U.ring(ax, ay, 20 * k, 10 * k, 1.2, 0.7)
            O.dot(ax + 6, ay - 60, 2 + 3 * k, 0.9 * k)
        else:
            g = min(1.0, (f - hit + 1) / 2)
            fade = 1.0 if f < n - 1 else 0.55
            U.ring(ax, ay, 50, 25, 1.6, 0.8 * fade)
            U.disk(ax, ay, 52, 26, 0.35 * fade)
            for (cx, cy, h, w, tilt) in sorted(crystals, key=lambda c: c[1]):
                L = O if cy >= 0 else U
                _crystal(L, ax + cx, ay + cy, h * g, w, tilt, 0.9 * fade)
            rr = _rng(720 + f)
            for j in range(10):
                O.dot(ax + rr.uniform(-55, 55), ay - rr.uniform(10, 70), 1.0, 1.0 * fade)
        under.append(U.image(ICE))
        over.append(O.image(ICE))
    return dict(label='얼음 결정 폭발', fw=W, fh=H, ax=ax, ay=ay, under=under, over=over, anim='skill_ice', color='blue', actor='mage')


def _rock(draw, x, y, r, seed):
    rr = _rng(seed)
    pts = []
    for j in range(7):
        a = j * 2 * math.pi / 7 + rr.uniform(-0.2, 0.2)
        rad = r * rr.uniform(0.7, 1.1)
        pts.append((x + math.cos(a) * rad, y + math.sin(a) * rad * 0.85))
    draw.polygon(pts, fill=(34, 26, 44, 255), outline=(10, 8, 14, 255))
    hl = [(px * 0.6 + x * 0.4 - r * 0.15, py * 0.6 + y * 0.4 - r * 0.2) for px, py in pts[3:6]]
    draw.polygon(hl, fill=(70, 54, 96, 255))
    draw.point([(x - r * 0.3, y - r * 0.4)], fill=(150, 110, 210, 255))


def meteor(n=8):
    W, H, ax, ay = 240, 260, 120, 196
    hit = 5
    under, over, solid = [[] for _ in range(8)], [[] for _ in range(8)], [[] for _ in range(8)]
    rocks = [(-10, 0, 16, 0.0), (18, 8, 11, 0.35), (-26, 12, 9, 0.7), (6, -10, 12, 0.2)]
    for d in range(8):
        dx, dy = screen_dir(d)
        tx, ty = ax + dx * 52, ay + dy * 52    # 앞쪽 떨어질 지점
        for f in range(n):
            U, O = Layer(W, H), Layer(W, H)
            Sd = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            dr = ImageDraw.Draw(Sd)
            if f >= 1:
                k = min(1.0, f / 3)
                fade = 1.0 if f < n - 1 else 0.5
                U.ring(tx, ty, 34 * k, 17 * k, 1.6, 1.0 * fade)
                U.ring(tx, ty, 26 * k, 13 * k, 1.0, 0.7 * fade)
                for j in range(6):
                    a = f * 0.4 + j * math.pi / 3
                    U.line(tx + math.cos(a) * 26 * k, ty + math.sin(a) * 13 * k,
                           tx + math.cos(a + 2.1) * 26 * k, ty + math.sin(a + 2.1) * 13 * k, 0.9, 0.5 * fade)
                U.disk(tx, ty, 34 * k, 17 * k, 0.3 * fade)
            if 2 <= f < hit:   # 하늘에서 떨어지는 바위(보랏빛 꼬리)
                for j, (rx, ry, rs, delay) in enumerate(rocks):
                    t = np.clip((f - 2 + 1 - delay) / (hit - 2), 0, 1)
                    px = tx + rx - 30 * (1 - t)
                    py = ty + ry * 0.5 - 170 * (1 - t)
                    O.line(px + 22, py - 60, px, py, rs * 0.6, 0.9)
                    O.dot(px, py, rs + 3, 0.8)
                    _rock(dr, px, py, rs, j)
            if f >= hit:       # 충돌 폭발 + 파편
                t = (f - hit) / max(1, n - 1 - hit)
                O.dot(tx, ty - 6, 26 * (1 - 0.5 * t), 1.3 * (1 - 0.6 * t))
                O.ring(tx, ty, 20 + 40 * t, 10 + 20 * t, 3.0, 1.0 * (1 - t * 0.7))
                for j in range(10):
                    a = j * 2 * math.pi / 10
                    O.beam(tx + math.cos(a) * 18, ty + math.sin(a) * 9, 50 * (1 - t), 2.4, 0.8 * (1 - t))
                rr = _rng(800 + f)
                for j in range(8):
                    a = rr.uniform(0, 6.3)
                    dist = 10 + 40 * t + rr.uniform(0, 10)
                    _rock(dr, tx + math.cos(a) * dist, ty + math.sin(a) * dist * 0.5 - 20 * t * (1 - t) * 4, rr.uniform(3, 6), 900 + j)
                if f == hit:
                    _rock(dr, tx - 4, ty - 4, 16, 0)
            under[d].append(U.image(ARCANE))
            over[d].append(O.image(ARCANE))
            solid[d].append(Sd)
    return dict(label='운석 낙하', fw=W, fh=H, ax=ax, ay=ay, under=under, over=over, solid=solid, anim='skill_meteor',
                color='purple', dirs=True, actor='mage')


def mana_pillar(n=8):
    W, H, ax, ay = 140, 210, 70, 172
    under, over = [], []
    for f in range(n):
        U, O, P = Layer(W, H), Layer(W, H), Layer(W, H)
        k = min(1.0, f / 2.0)
        rx, ry = 44, 22
        rot = f * 0.28
        U.ring(ax, ay, rx * (0.6 + 0.4 * k), ry * (0.6 + 0.4 * k), 1.8, 1.0 * k)
        U.ring(ax, ay, rx * 0.8, ry * 0.8, 1.1, 0.8 * k)
        U.ring(ax, ay, rx * 0.45, ry * 0.45, 0.9, 0.6 * k)
        for j in range(20):
            a = -rot + j * 2 * math.pi / 20
            U.line(ax + math.cos(a) * rx * 0.84, ay + math.sin(a) * ry * 0.84,
                   ax + math.cos(a) * rx * 0.96, ay + math.sin(a) * ry * 0.96, 0.9, (1.0 if j % 4 == 0 else 0.6) * k)
        for j in range(5):
            a = rot + j * 2 * math.pi / 5
            b2 = rot + (j + 2) * 2 * math.pi / 5
            U.line(ax + math.cos(a) * rx * 0.8, ay + math.sin(a) * ry * 0.8, ax + math.cos(b2) * rx * 0.8, ay + math.sin(b2) * ry * 0.8, 0.9, 0.5 * k)
        U.disk(ax, ay, rx, ry, 0.3 * k)
        if f >= 1:
            P.beam(ax, ay, 190, 12 * k, 0.45 * k, taper=False)
            O.beam(ax, ay, 190, 4 * k, 0.9 * k, taper=False)
            for j in range(6):
                a = rot * 2 + j * math.pi / 3
                O.beam(ax + math.cos(a) * 30, ay + math.sin(a) * 15, 60 + 30 * math.sin(f + j), 1.6, 0.6 * k, taper=True)
            # 머리 위 왕관 모양 반짝임
            cy = ay - 70
            for j in range(5):
                a = -math.pi / 2 + (j - 2) * 0.45
                P.line(ax, cy, ax + math.cos(a) * 16, cy + math.sin(a) * 16, 0.9, 0.8 * k)
            P.dot(ax, cy, 4 * k, 1.2 * k)
        rr = _rng(950 + f)
        for j in range(10):
            O.dot(ax + rr.uniform(-36, 36), ay - rr.uniform(5, 160), 1.0, 1.0 * k)
        under.append(U.image(ICE))
        over.append(_merge(P.image(ARCANE), O.image(ICE)))
    return dict(label='마나 기둥', fw=W, fh=H, ax=ax, ay=ay, under=under, over=over, anim='skill_pillar', color='purple', actor='mage')


def build_all2():
    return {'wind': wind_arrow(), 'volley': volley(), 'whirl': whirl(), 'fairy': fairy(),
            'bolt': magic_bolt(), 'ice': ice_burst(), 'meteor': meteor(), 'pillar': mana_pillar()}



# ───────────────────────── 보스 스킬 이펙트 ─────────────────────────
HELL = ['#2a0402', '#6a0c04', '#b8260a', '#f06a1c', '#ffc060', '#ffffff']


def _smoke(draw, x, y, r, a):
    draw.ellipse([x - r, y - r * 0.8, x + r, y + r * 0.8], fill=(14, 6, 10, int(255 * a)))


def dark_slash(n=8):
    """암흑 베기: 앞으로 날아가는 검붉은 초승달 충격파 + 검은 연기(일반 혼합)."""
    W, H, ax, ay = 320, 240, 160, 160
    under, over, solid = [[] for _ in range(8)], [[] for _ in range(8)], [[] for _ in range(8)]
    for d in range(8):
        dx, dy = screen_dir(d)
        face = math.atan2(dy * 2, dx)       # 바닥 평면 기준 각도
        for f in range(n):
            U, O = Layer(W, H), Layer(W, H)
            Sd = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            dr = ImageDraw.Draw(Sd)
            if 1 <= f <= 3:   # 대검에 모이는 불꽃
                k = f / 3
                O.dot(ax - dx * 20, ay - 50 - dy * 20, 4 + 6 * k, 0.9 * k)
                for j in range(6):
                    a = j * 1.05 + f
                    O.dot(ax - dx * 20 + math.cos(a) * 14 * (1 - k), ay - 50 + math.sin(a) * 10 * (1 - k), 1.4, 0.9)
            if f >= 4:
                t = (f - 4) / (n - 5)
                dist = 30 + 110 * t
                cx, cy = ax + dx * dist, ay - 30 + dy * dist
                R = 44 + 10 * t
                fade = 1 - 0.6 * t
                O.ring(cx - dx * R * 0.6, cy - dy * R * 0.6, R, R * 0.5, 7, 1.1 * fade, face - 1.1, face + 1.1, fade=None)
                O.ring(cx - dx * R * 0.6, cy - dy * R * 0.6, R * 0.82, R * 0.41, 3, 0.8 * fade, face - 0.9, face + 0.9)
                for j in range(9):   # 꼬리 쪽 검은 연기
                    a = face + (j - 4) * 0.25
                    px = cx - dx * R * 0.6 + math.cos(a) * R * 0.75 - dx * 10
                    py = cy - dy * R * 0.6 + math.sin(a) * R * 0.375 - dy * 10
                    _smoke(dr, px, py, 6 + (j % 3) * 2, 0.55 * fade)
                if f == 4:
                    U.disk(ax, ay, 50, 22, 0.6)
            under[d].append(U.image(HELL))
            over[d].append(O.image(HELL))
            solid[d].append(Sd)
    return dict(label='암흑 베기', fw=W, fh=H, ax=ax, ay=ay, under=under, over=over, solid=solid, anim='skill_darkslash',
                color='red', dirs=True, actor='boss')


def hellfire(n=8):
    """지옥불 강타: 예고 원 → 땅에 꽂는 순간 용암 균열과 불기둥."""
    W, H, ax, ay = 300, 260, 150, 190
    hit = 5
    under, over = [], []
    r0 = _rng(1300)
    cracks = [(r0.uniform(0, 6.3), r0.uniform(60, 95)) for _ in range(12)]
    pillars = [(r0.uniform(0, 6.3), r0.uniform(30, 85)) for _ in range(12)]
    for f in range(n):
        U, O = Layer(W, H), Layer(W, H)
        if f < hit:   # 예고: 바닥에 붉은 원이 차오름
            k = (f + 1) / hit
            U.ring(ax, ay, 95, 47.5, 1.6, 0.6 + 0.3 * k)
            U.disk(ax, ay, 95 * k, 47.5 * k, 0.35)
            O.dot(ax, ay - 110, 3 + 8 * k, 0.9 * k)
        else:
            t = (f - hit) / max(1, n - 1 - hit)
            fade = 1 - 0.5 * t
            for (a, ln) in cracks:   # 용암 균열
                x1, y1 = ax + math.cos(a) * ln, ay + math.sin(a) * ln * 0.5
                xm, ym = ax + math.cos(a + 0.2) * ln * 0.5, ay + math.sin(a + 0.2) * ln * 0.25
                U.line(ax, ay, xm, ym, 2.2, 1.0 * fade)
                U.line(xm, ym, x1, y1, 1.6, 0.9 * fade)
            U.disk(ax, ay, 60, 30, 0.9 * fade, 1.0)
            U.ring(ax, ay, 40 + 60 * t, 20 + 30 * t, 3.5, 1.0 * fade)
            for j, (a, rad) in enumerate(pillars):   # 불기둥
                grow = min(1.0, (f - hit + 1) / 1.5)
                px, py = ax + math.cos(a) * rad, ay + math.sin(a) * rad * 0.5
                O.beam(px, py, (50 + (j * 13) % 40) * grow * (1.2 - 0.5 * t), 4 + j % 3, 1.0 * fade)
            O.beam(ax, ay, 140 * min(1.0, (f - hit + 1) / 1.5), 10, 1.1 * fade)
            rr = _rng(1400 + f)
            for j in range(20):
                O.dot(ax + rr.uniform(-90, 90), ay - rr.uniform(10, 150), rr.uniform(0.8, 1.8), 1.0 * fade)
        under.append(U.image(HELL))
        over.append(O.image(HELL))
    return dict(label='지옥불 강타', fw=W, fh=H, ax=ax, ay=ay, under=under, over=over, anim='skill_hellfire', color='red', actor='boss')


def build_boss():
    return {'darkslash': dark_slash(), 'hellfire': hellfire()}
