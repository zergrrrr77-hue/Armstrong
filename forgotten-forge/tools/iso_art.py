"""《잊혀진 대장간》 쿼터뷰(오픈필드) 도트 에셋.

- 주인공: 키 32px, 5방향(남·남동·동·북동·북)을 그리고 서쪽 3방향은 게임에서 좌우 반전해 8방향을 만든다.
- 몬스터: 작아진 슬라임·고블린·수호자 (좌우 2방향, 반전으로 처리).
- 무기: 32px 주인공 손에 맞춘 작은 무기 시트.
- 지형: 64×32 마름모 타일(지역별 변형 4종), 쿼터뷰 소품·건물.

make_web_assets.py가 setup()으로 팔레트·셀아웃 함수를 넘겨준 뒤 build_*()를 부른다.
빛은 왼쪽 위에서 온다.
"""
import math

from PIL import Image

import make_assets as MA

Cv = MA.Cv
h = MA.h
W = None  # make_web_assets 모듈 (setup에서 채움)


def setup(mod):
    global W
    W = mod


def sh(hexc, amt):
    v = [max(0, min(255, int(hexc[i:i + 2], 16) + amt)) for i in (1, 3, 5)]
    return '#%02x%02x%02x' % tuple(v)


def C(hexc):
    """임의의 #색을 팔레트 이름으로 등록."""
    return W.H(hexc)


# ───────────────────────── 주인공 (32×40, 발 기준점 16,38) ─────────────────────────
HW, HH, HAX, HAY = 32, 40, 16, 38
HDIRS = ['S', 'SE', 'E', 'NE', 'N']
HPOSES = ['idle0', 'idle1', 'walk0', 'walk1', 'walk2', 'walk3', 'hurt', 'atk']


def hero(gender, d, pose):
    fem = gender == 'f'
    t = HDIRS.index(d)
    c = Cv(HW, HH)
    bob = 1 if pose in ('idle1', 'walk1', 'walk3', 'hurt') else 0
    step = {'walk0': 1, 'walk2': -1}.get(pose, 0)     # +1: 오른다리 앞
    atk = pose == 'atk'
    back = t >= 3
    side = t == 2
    by = bob                                             # 상체 내려앉음
    lean = (1 if atk else 0) * (0 if t in (0, 4) else 1)

    # ── 다리 + 장화
    def leg(x, lift, dark, wdt=3):
        top, bot = 30, 35 - lift
        pc = 'P2' if dark else 'P1'
        c.rect(x, top, wdt, bot - top, pc)
        if not dark:
            c.rect(x + wdt - 1, top, 1, bot - top, 'P2')
        c.rect(x, bot, wdt, 2, 'B1' if not dark else 'B2')
        c.rect(x, bot, wdt, 1, 'B0' if not dark else 'B1')
        c.rect(x - (1 if t in (0, 4) else 0), bot + 2, wdt + (1 if t in (0, 4) else 1), 1, 'B2')

    if side:
        sw = 2 * step
        leg(14 - sw, 0 if step >= 0 else 1, True)
        leg(15 + sw, 0 if step <= 0 else 1, False)
    else:
        lx, rx = (12, 17) if t in (0, 4) else (13, 17)
        ll = 1 if step < 0 else 0
        rl = 1 if step > 0 else 0
        leg(lx, ll, t == 1 or t == 3)
        leg(rx, rl, False)

    # ── 긴 머리 뒤쪽 (여, 앞을 볼 때는 몸 뒤에)
    hx = 16 + (1 if t in (1, 2, 3) else 0) + lean
    hy = 11 + by
    if fem and not back:
        xs = {0: (8, 24), 1: (8, 22), 2: (7, 19)}[t]
        c.poly([(xs[0], hy), (xs[1], hy), (xs[1] - 1, hy + 14), (xs[0] + 2, hy + 15), (xs[0] - 0.5, hy + 10)], 'H2')
        c.rect(xs[0] + 1, hy + 2, 2, 11, 'H1')

    # ── 뒷팔 (옆모습)
    sw_arm = -step
    if side:
        c.rect(13 - sw_arm + lean, 22 + by, 2, 5, 'O2')
        c.rect(13 - sw_arm + lean, 27 + by, 2, 2, 'S2')

    # ── 몸통
    x0, wdt = (11, 10) if not side else (12, 8)
    x0 += lean
    c.rect(x0, 21 + by, wdt, 8, 'O1')
    c.rect(x0, 21 + by, 1, 7, 'O0')
    c.rect(x0 + wdt - 2, 21 + by, 2, 8, 'O2')
    if not back:
        c.rect(x0 + wdt // 2 - (0 if side else 1), 22 + by, 1, 4, 'O2')  # 앞섶
    # 허리띠
    c.rect(x0, 26 + by, wdt, 1, 'BL1')
    if not back:
        bx = x0 + wdt // 2 + (2 if side else (1 if t == 1 else 0)) - 1
        c.rect(bx, 26 + by, 2, 1, 'GD1')
    if fem:
        c.poly([(x0 - 0.5, 27 + by), (x0 + wdt + 0.5, 27 + by), (x0 + wdt + 2.5, 32 + by), (x0 - 2.5, 32 + by)], 'O1')
        c.rect(x0 - 2, 31 + by, wdt + 4, 1, 'O2')
        for k in range(3):
            px_ = x0 + 1 + k * (wdt // 3) + 1
            c.px(px_, 29 + by, 'O2'); c.px(px_ + (1 if k == 2 else 0), 30 + by, 'O2')
        c.rect(x0 + wdt - 1, 28 + by, 2, 3, 'O2')
    else:
        c.rect(x0, 27 + by, wdt, 2, 'O1')
        c.rect(x0, 28 + by, wdt, 1, 'O2')
        c.rect(x0 + wdt - 2, 27 + by, 2, 2, 'O2')

    # ── 목도리 (상징색)
    c.rect(x0 + 1, 19 + by, wdt - 2, 2, 'SC1')
    c.rect(x0 + 1, 20 + by, wdt - 2, 1, 'SC2')
    c.rect(x0 + 2, 19 + by, 3, 1, 'SC0')
    if back:   # 등 뒤로 늘어진 꼬리
        tx = x0 + (wdt // 2) - 1 + (1 if t == 3 else 0)
        c.rect(tx, 21 + by, 2, 5, 'SC1'); c.rect(tx + 1, 21 + by, 1, 5, 'SC2'); c.px(tx, 26 + by, 'SC2')
    elif side:
        c.rect(x0 - 2, 20 + by, 2, 2, 'SC1'); c.rect(x0 - 3, 21 + by, 2, 2, 'SC2')

    # ── 머리
    hair_rx, hair_ry = 8, 7.5
    c.ell(hx, hy, hair_rx, hair_ry, 'H1')
    # 머리 명암 (오른쪽 아래 그늘)
    for y in range(int(hy - 8), int(hy + 9)):
        for x in range(int(hx - 9), int(hx + 10)):
            if c.get(x, y) == 'H1':
                nx, ny = (x + 0.5 - hx) / hair_rx, (y + 0.5 - hy) / hair_ry
                if nx * 0.7 + ny * 0.7 > 0.62:
                    c.px(x, y, 'H2')
    # 얼굴
    face = {0: (0, 6.5, 5.8), 1: (1.6, 6.0, 5.8), 2: (3.6, 4.6, 4.8)}.get(t)
    if face:
        fs, frx, fry = face
        fcx, fcy = hx + fs, hy + (2.2 if t != 2 else 2.8)
        for y in range(int(fcy - fry) - 1, int(fcy + fry) + 2):
            for x in range(int(fcx - frx) - 1, int(fcx + frx) + 2):
                inf = ((x + 0.5 - fcx) / frx) ** 2 + ((y + 0.5 - fcy) / fry) ** 2 <= 1
                inh = ((x + 0.5 - hx) / hair_rx) ** 2 + ((y + 0.5 - hy) / hair_ry) ** 2 <= 1.0
                if inf and (inh or t == 2) and not (t == 2 and x < hx + 1):
                    c.px(x, y, 'S1')
        # 얼굴 그늘 (오른쪽·아래 가장자리)
        for (x, y), col in list(c.p.items()):
            if col == 'S1' and (c.get(x + 1, y) not in ('S1', 'S2') or c.get(x, y + 1) not in ('S1', 'S2')) and x > fcx - 1:
                c.px(x, y, 'S2')
        if t == 2:  # 코 · 턱 돌출
            c.px(hx + 8, hy + 4, 'S1')
    # 귀
    if t == 2:
        c.rect(hx, hy + 2, 2, 3, 'S2'); c.px(hx + 1, hy + 3, 'S1')
    if t == 3:
        c.rect(hx + 5, hy + 2, 2, 3, 'S2'); c.px(hx + 6, hy + 2, 'S1')

    # 앞머리 (얼굴 위를 덮음)
    if not back:
        fs = face[0]
        top = hy - 1
        for x in range(int(hx - 8), int(hx + 9)):
            for y in range(int(hy - 8), int(top) + 1):
                if c.get(x, y) in ('S1', 'S2'):
                    c.px(x, y, 'H1')
        # 삐침 (아래로 늘어진 앞머리 가닥)
        spikes = [(-5, 2), (-2, 1), (1, 2), (4, 1)] if t == 0 else [(-3, 1), (0, 2), (3, 1), (5, 2)] if t == 1 else [(1, 1), (3, 2), (5, 1)]
        for ox, ln in spikes:
            for k in range(ln):
                xx, yy = hx + ox + (fs if t else 0) * 0.3, top + 1 + k
                if c.get(round(xx), yy) in ('S1', 'S2'):
                    c.px(xx, yy, 'H1' if k == 0 else 'H2')
        # 옆머리
        if t == 0:
            c.rect(hx - 8, hy, 2, 5, 'H1'); c.rect(hx + 6, hy, 2, 5, 'H2')
        elif t == 1:
            c.rect(hx - 7, hy, 3, 4, 'H1'); c.rect(hx + 6, hy - 1, 2, 4, 'H2')
    else:
        # 뒷머리 결
        for k, ox in enumerate((-4, -1, 2, 5)):
            c.line(hx + ox, hy - 1, hx + ox - 1, hy + 4, 'H2')
        c.rect(hx - 4, hy + 6, 9, 1, 'H2')

    # 남: 뾰족 머리 · 여: 리본 + 등을 덮는 긴 머리(뒷모습)
    if not fem:
        for ox, oy, k in ((-5, -6, 0), (-1, -8, 1), (3, -7, 2), (6, -4, 3)):
            c.poly([(hx + ox - 2, hy + oy + 3), (hx + ox + 0.5, hy + oy - 1), (hx + ox + 2.5, hy + oy + 3)], 'H1')
    else:
        if back:
            c.poly([(hx - 6.5, hy + 1), (hx + 6.5, hy + 1), (hx + 5.5, hy + 13), (hx, hy + 14.5), (hx - 5.5, hy + 13)], 'H1')
            c.rect(hx + 4, hy + 2, 2, 11, 'H2')
            for ox in (-3, 0, 3):
                c.line(hx + ox, hy + 4, hx + ox, hy + 11, 'H2')
            c.rect(hx - 3, hy + 7, 1, 3, 'H0')
        rbx = hx - 6 if t in (0, 1) else hx - 3 if t == 2 else hx + 3
        rby = hy - 6
        c.poly([(rbx - 3, rby - 2), (rbx, rby), (rbx - 3, rby + 2)], 'RB1')
        c.poly([(rbx + 3, rby - 2), (rbx, rby), (rbx + 3, rby + 2)], 'RB1')
        c.px(rbx, rby, 'RB2'); c.px(rbx - 2, rby - 1, 'RB0')

    # 머리 광택 (왼쪽 위 호)
    for x in range(int(hx - 5), int(hx + 2)):
        y = round(hy - 5.5 + ((x - (hx - 2)) / 4.0) ** 2 * 1.4)
        if c.get(x, y) in ('H1', 'H2'):
            c.px(x, y, 'H0')

    # ── 눈 · 입
    hurt = pose == 'hurt'

    def eye(x, wdt=2):
        if hurt:
            c.px(x, hy + 2, 'lash'); c.px(x + 1, hy + 3, 'lash') if wdt > 1 else None
            c.px(x, hy + 4, 'lash')
            return
        c.rect(x, hy + 1, wdt, 1, 'lash')
        c.rect(x, hy + 2, wdt, 1, 'E2')
        c.rect(x, hy + 3, wdt, 1, 'E1')
        c.rect(x, hy + 4, wdt, 1, 'E0')
        c.px(x + wdt - 1, hy + 2, 'w')
        if fem:
            c.px(x + wdt, hy + 1, 'lash') if t else c.px(x - 1 if x < hx else x + wdt, hy + 1, 'lash')

    if t == 0:
        eye(hx - 5); eye(hx + 3)
        mx = hx - 1
    elif t == 1:
        eye(hx - 2, 1); eye(hx + 3)
        mx = hx + 2
    elif t == 2:
        eye(hx + 4, 2)
        mx = hx + 5
    if t <= 2:
        my = hy + (6 if t < 2 else 5)
        if hurt:
            c.rect(mx, my, 2 if t < 2 else 1, 1, 'mouthD')
        else:
            c.px(mx, my, 'mouth'); c.px(mx + 1, my, 'mouth') if t < 2 else None
        if fem:
            if t == 0:
                c.px(hx - 5, hy + 5, 'blush'); c.px(hx + 4, hy + 5, 'blush')
            else:
                c.px(hx + 4 + (1 if t == 2 else 0), hy + 5, 'blush')

    # ── 앞팔 (손 위치를 메타데이터로)
    swing = -step
    if side:
        hand = (17 + swing * 2 + (3 if atk else 0) + lean, 27 + by - (2 if atk else 0))
        c.rect(15 + lean, 22 + by, 3, 3, 'O1'); c.px(15 + lean, 22 + by, 'O0')
        W.thick_line(c, 16 + lean, 24 + by, hand[0], hand[1] - 1, 'O1', 2)
        c.rect(hand[0] - 1, hand[1] - 1, 2, 2, 'S1'); c.px(hand[0], hand[1], 'S2')
        front = True
    else:
        la = (9 if t in (0, 4) else 10) + (lean if t == 3 else 0)
        ra = 21 + (lean if t in (1, 3) else 0)
        ly = swing if t != 4 else -swing
        # 왼팔 (화면 기준)
        c.rect(la, 21 + by, 2, 6 + ly, 'O1' if t != 3 else 'O2'); c.px(la, 21 + by, 'O0')
        c.rect(la, 27 + by + ly, 2, 2, 'S1' if not back else 'S2')
        # 오른팔
        ra_len = 6 - ly
        if atk and t in (0, 1):
            ra_len = 4
        c.rect(ra, 21 + by, 2, ra_len, 'O2')
        if back:
            c.rect(ra, 27 + by - ly, 2, 2, 'S2')
        else:
            c.rect(ra, 21 + by + ra_len, 2, 2, 'S1')
        if t == 0:
            hand = (la + 1, 28 + by + ly - (2 if atk else 0))   # 오른손 = 화면 왼쪽
            front = True
        elif t == 1:
            hand = (ra + 1, 21 + by + ra_len + 1)
            front = True
        else:
            hand = (ra + 1, 28 + by - ly)
            front = False
    W.selout(c)
    return c, (hand[0] - HAX, hand[1] - HAY), front, bob


def build_hero():
    sheets, meta = {}, {'fw': HW, 'fh': HH, 'ax': HAX, 'ay': HAY, 'dirs': HDIRS, 'poses': HPOSES, 'hand': {}, 'front': {}, 'bob': {}}
    for g in ('m', 'f'):
        im = Image.new('RGBA', (HW * len(HPOSES), HH * len(HDIRS)), (0, 0, 0, 0))
        for di, d in enumerate(HDIRS):
            for pi, p in enumerate(HPOSES):
                fr, hand, front, bob = hero(g, d, p)
                im.paste(fr.image(), (pi * HW, di * HH))
                meta['hand'][d + ':' + p] = list(hand)
                meta['front'][d + ':' + p] = front
                meta['bob'][p] = bob
        sheets[g] = im
    return sheets, meta


# ───────────────────────── 몬스터 (작게) ─────────────────────────
SL_W, SL_H, SL_AX, SL_AY = 24, 18, 12, 17
SLIME_POSES = {'idle0': (8.5, 6.6), 'idle1': (8.9, 6.2), 'blink': (8.5, 6.6, True), 'jump': (7.4, 8.0), 'land': (10.2, 5.0)}


def slime(rx, ry, blink=False):
    c = Cv(SL_W, SL_H)
    cx, by = 12, 17
    cy = by + 0.5 - ry
    G0, G1, G2, G3, G4 = C('#c8f898'), C('#8fe070'), C('#5cbf4c'), C('#3e9836'), C('#2a6e26')
    for y in range(SL_H):
        for x in range(SL_W):
            if y > by - 1:
                continue
            nx, ny = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
            d = nx * nx + ny * ny
            if d > 1:
                continue
            col = G2
            if ny > 0.7 or (d > 0.8 and ny > 0.25):
                col = G4
            elif ny > 0.3 or nx > 0.65:
                col = G3
            elif (nx + 0.35) ** 2 + (ny + 0.4) ** 2 < 0.2:
                col = G1
            c.px(x, y, col)
    sx, sy = round(cx - rx * 0.45), round(cy - ry * 0.55)
    c.rect(sx, sy, 2, 1, 'w'); c.px(sx - 1, sy + 1, G0)
    ex, ey = round(cx + rx * 0.1), round(cy - ry * 0.1)
    for e in (ex - 2, ex + 2):
        if blink:
            c.rect(e, ey + 1, 2, 1, C('#143214'))
        else:
            c.rect(e, ey, 1, 2, C('#143214'))
    if ry > 5:
        c.px(ex, ey + 3, C('#1e4a1a'))
        c.px(ex - 3, ey + 2, C('#f4a0a8')); c.px(ex + 3, ey + 2, C('#f4a0a8'))
    return W.selout_mono(c, '#143214')


GB_W, GB_H, GB_AX, GB_AY = 40, 40, 18, 38
BS_W, BS_H, BS_AX, BS_AY = 96, 88, 44, 85


def build_monsters():
    sheets, meta = {}, {}
    fr = [slime(*v) for v in SLIME_POSES.values()]
    sheets['slime'] = W.pack(fr, SL_W, SL_H)
    meta['slime'] = {'fw': SL_W, 'fh': SL_H, 'ax': SL_AX, 'ay': SL_AY, 'poses': list(SLIME_POSES.keys())}
    sheets['goblin'] = W.pack([W.goblin(p, 1.0, (GB_W, GB_H), (GB_AX, GB_AY)) for p in W.GOBLIN_POSES], GB_W, GB_H)
    meta['goblin'] = {'fw': GB_W, 'fh': GB_H, 'ax': GB_AX, 'ay': GB_AY, 'poses': W.GOBLIN_POSES}
    sheets['boss'] = W.pack([W.boss(p, 0.9, (BS_W, BS_H), (BS_AX, BS_AY)) for p in W.BOSS_POSES], BS_W, BS_H)
    meta['boss'] = {'fw': BS_W, 'fh': BS_H, 'ax': BS_AX, 'ay': BS_AY, 'poses': W.BOSS_POSES}
    return sheets, meta


# ───────────────────────── 손에 든 무기 (작게, 오른쪽을 향함) ─────────────────────────
WC_W, WC_H = 40, 24


def weapon_small(kind, d):
    c = Cv(WC_W, WC_H)
    string = None
    cy = 12
    if kind == 'sword':
        ax, ay = 5, cy
        L = round(d['L'] * 0.62)
        c.px(1, cy, d['pommel']); c.px(1, cy - 1, d['pommel'])
        for x in range(2, 6):
            c.rect(x, cy - 1, 1, 2, d['grip'][(x // 2) % 2])
        c.rect(6, cy - 4, 2, 8, d['guard'][0]); c.rect(7, cy - 3, 1, 6, d['guard'][1])
        if d.get('gem'):
            c.rect(6, cy - 1, 2, 2, d['gem'])
        if d.get('crescent'):
            c.px(5, cy - 5, d['guard'][0]); c.px(5, cy + 4, d['guard'][0])
        x0 = 8
        for i in range(L):
            x = x0 + i
            tip = i >= L - 2
            c.px(x, cy - 1, d['edge'])
            if not tip or i == L - 2:
                c.px(x, cy, d['blade'] if not tip else d['shadow'])
            if not tip:
                c.px(x, cy + 1, d['shadow'])
            if d.get('fuller') and 1 < i < L - 4:
                c.px(x, cy, d['fuller'])
        c.px(x0 + L, cy - 1, d['edge'])
        if d.get('rust'):
            for i in (2, 5, 8):
                c.px(x0 + i, cy, '#a06e3c')
        if d.get('thorns'):
            for i in range(2, L - 2, 3):
                c.px(x0 + i, cy - 2, d['shadow']); c.px(x0 + i + 1, cy + 2, d['shadow'])
        if d.get('flames'):
            for i in range(1, L - 2, 3):
                c.px(x0 + i, cy - 2, d['blade']); c.px(x0 + i + 1, cy + 2, d['shadow'])
        length = x0 + L - ax
    elif kind == 'spear':
        ax, ay = 10, cy
        end = 28
        c.px(1, cy, d['ring'])
        for x in range(2, end):
            c.px(x, cy, d['shaft'] if x % 6 else d['shaftD'])
        c.rect(end, cy - 1, 1, 3, d['ring'])
        hx = end + 1
        for i in range(7):
            hw = [1, 1, 2, 1, 1, 0, 0][i]
            for o in range(-hw, hw + 1):
                c.px(hx + i, cy + o, d['head'] if o <= 0 else d['headD'])
        c.px(hx + 7, cy, d['headL']); c.px(hx + 1, cy - 1, d['headL'])
        if d.get('tassel'):
            c.px(end - 1, cy + 1, d['tassel']); c.px(end - 1, cy + 2, d['tassel']); c.px(end - 2, cy + 3, d['tassel'])
        if d.get('wings'):
            c.px(hx - 1, cy - 2, d['head']); c.px(hx - 2, cy - 3, d['head']); c.px(hx - 1, cy + 2, d['headD']); c.px(hx - 2, cy + 3, d['headD'])
        length = hx + 7 - ax
    elif kind == 'mace':
        ax, ay = 3, cy
        for x in range(1, 11):
            c.rect(x, cy, 1, 2, d['handle'] if x % 3 else sh(d['handle'], -25))
        if d['shape'] == 'club':
            c.ell(14, cy + 0.5, 4.5, 3.5, d['head']); c.ell(13, cy - 0.5, 2.5, 1.5, d['headL'])
            c.ell(15, cy + 2, 3, 1.2, d['headD']); c.px(17, cy - 2, '#d0ccc4'); c.px(14, cy - 3, '#d0ccc4')
            length = 18 - ax
        elif d['shape'] == 'spike':
            c.ell(14, cy + 0.5, 3.5, 3.5, d['head']); c.px(13, cy - 1, d['headL']); c.px(14, cy - 1, d['headL'])
            for (sx, sy) in ((14, cy - 4), (14, cy + 4), (18, cy), (11, cy - 3), (17, cy - 3), (11, cy + 3), (17, cy + 3)):
                c.px(sx, sy, '#e8ecf0')
            length = 18 - ax
        else:
            c.rect(10, cy - 5, 8, 11, d['head']); c.rect(10, cy - 5, 8, 1, d['headL']); c.rect(10, cy + 5, 8, 1, d['headD'])
            c.rect(17, cy - 4, 1, 9, d['headD'])
            c.rect(12, cy - 2, 3, 4, d['rune']); c.px(13, cy - 1, sh(d['rune'], 60))
            length = 18 - ax
    else:  # bow (세로로 선 활, 손잡이 기준)
        ax, ay = 8, cy
        top, bot = 2, 22
        for y in range(top, bot + 1):
            dy = (y - cy) / 10
            x = round(8 - 4 * dy * dy)
            c.px(x, y, d['wood']); c.px(x + 1, y, d['light'] if abs(dy) < 0.6 else d['dark'])
            if d.get('bands') and y % 4 == 0:
                c.px(x, y, d['dark'])
        c.rect(7, cy - 2, 3, 4, d['grip'])
        c.line(4, top + 1, 4, bot - 1, d['string'])
        if d.get('feathers'):
            c.px(5, 3, '#ffffff'); c.px(5, 21, '#ffffff')
        if d.get('stars'):
            for (sx, sy) in ((6, 5), (6, 19), (10, cy)):
                c.px(sx, sy, '#ffffff')
        length = 4
        string = [4 - ax, top + 1 - ay, bot - 1 - ay]
    return c, (ax, ay), length, string


def build_weapons():
    cells, wmeta = [], {}
    for wid, (kind, d) in W.WEAPONS.items():
        cv, (ax, ay), length, string = weapon_small(kind, d)
        cells.append(W.img_outline(cv.image()))
        wmeta[wid] = {'i': len(cells) - 1, 'ax': ax, 'ay': ay, 'len': length, 'kind': kind}
        if string:
            wmeta[wid]['string'] = string
    sheet = Image.new('RGBA', (WC_W * len(cells), WC_H), (0, 0, 0, 0))
    for i, im in enumerate(cells):
        sheet.alpha_composite(im, (i * WC_W, 0))
    ar = Cv(14, 5)
    ar.rect(0, 2, 11, 1, '#c9a070'); ar.poly([(10, 0.5), (14, 2.5), (10, 4.5)], '#d8dce0')
    ar.rect(0, 1, 3, 1, '#f0f0f0'); ar.rect(0, 3, 3, 1, '#f0f0f0'); ar.rect(1, 2, 2, 1, '#d03838')
    return sheet, {'cw': WC_W, 'ch': WC_H, 'items': wmeta}, W.img_outline(ar.image())


# ───────────────────────── 마름모 지면 타일 (64×32) ─────────────────────────
TW, TH = 64, 32
TILE_KINDS = {
    #           밑색        밝게       어둡게      점무늬1     점무늬2
    'grass':   ('#5aa04c', '#74b85a', '#478a3e', '#86c864', '#3e7a36'),
    'meadow':  ('#68aa4e', '#84c060', '#549442', '#f4f0d8', '#f0a0c0'),
    'path':    ('#a07c54', '#b8946a', '#86663f', '#c8a880', '#6e5236'),
    'village': ('#7a8a5a', '#8e9c68', '#66764a', '#9a9284', '#5a6a40'),
    'cobble':  ('#857a6c', '#a09484', '#5e554c', '#b0a494', '#4a423a'),
    'forest':  ('#2f6a3a', '#3e7c46', '#265a30', '#5a4a30', '#1e4a26'),
    'cave':    ('#3e3448', '#4c4058', '#30283a', '#5a4e6c', '#241e2c'),
    'arena':   ('#4a3e56', '#5c4e6a', '#382e42', '#7a5aa0', '#2a2232'),
}
TILE_VARIANTS = 4


def in_diamond(x, y):
    hw = (y + 1) * 2 if y < 16 else (32 - y) * 2
    return 32 - hw <= x < 32 + hw


def tile(kind, v):
    base, light, dark, sp1, sp2 = TILE_KINDS[kind]
    im = Image.new('RGBA', (TW, TH), (0, 0, 0, 0))
    px = im.load()
    rgb = lambda c_: tuple(int(c_[i:i + 2], 16) for i in (1, 3, 5)) + (255,)
    B, L, D, P1, P2 = rgb(base), rgb(light), rgb(dark), rgb(sp1), rgb(sp2)
    s = v * 17 + len(kind) * 101
    for y in range(TH):
        for x in range(TW):
            if not in_diamond(x, y):
                continue
            # 화면 좌표 그대로 쓰는 저주파 + 고주파 노이즈
            n = h(x // 3, y // 2, s) * 0.6 + h(x, y, s + 1) * 0.4
            col = B
            if n > 0.78:
                col = L
            elif n < 0.2:
                col = D
            px[x, y] = col
    # 종류별 무늬
    if kind in ('grass', 'meadow', 'forest', 'village'):
        n_blade = {'grass': 14, 'meadow': 10, 'forest': 9, 'village': 6}[kind]
        for i in range(n_blade):
            x, y = int(h(i, 1, s) * 56) + 4, int(h(i, 2, s) * 24) + 4
            if in_diamond(x, y) and in_diamond(x, y - 2):
                px[x, y] = L if kind != 'forest' else rgb(sh(base, 24))
                px[x, y - 1] = L
                if in_diamond(x + 1, y):
                    px[x + 1, y] = D
        if kind == 'meadow':
            for i in range(4):
                x, y = int(h(i, 3, s) * 48) + 8, int(h(i, 4, s) * 18) + 7
                if in_diamond(x, y):
                    px[x, y] = P1 if i % 2 else P2
        if kind == 'forest':
            for i in range(3):
                x, y = int(h(i, 5, s) * 40) + 12, int(h(i, 6, s) * 14) + 9
                for k in range(3):
                    if in_diamond(x + k, y):
                        px[x + k, y] = P1
        if kind == 'village':
            for i in range(3):
                x, y = int(h(i, 7, s) * 40) + 12, int(h(i, 8, s) * 14) + 9
                for dx in range(3):
                    for dy in range(2):
                        if in_diamond(x + dx, y + dy):
                            px[x + dx, y + dy] = P1 if dy == 0 else rgb(sh(sp1, -30))
    elif kind == 'path':
        for i in range(6):
            x, y = int(h(i, 1, s) * 48) + 8, int(h(i, 2, s) * 20) + 6
            if in_diamond(x, y) and in_diamond(x + 1, y + 1):
                px[x, y] = P1; px[x + 1, y] = P1; px[x, y + 1] = P2; px[x + 1, y + 1] = P2
    elif kind in ('cobble', 'arena'):
        # 마름모 격자를 따라 놓인 돌 (화면에서 비스듬한 줄)
        for y in range(TH):
            for x in range(TW):
                if not in_diamond(x, y):
                    continue
                u, w_ = (x / 2 + y) / 8.0, (y - x / 2 + 32) / 8.0
                fu, fw = u - math.floor(u), w_ - math.floor(w_)
                if fu < 0.12 or fw < 0.12:
                    px[x, y] = P2 if kind == 'cobble' else D
                elif fu > 0.82 and fw > 0.3:
                    px[x, y] = D
                elif fu < 0.3 and fw < 0.5 and kind == 'cobble':
                    px[x, y] = P1
        if kind == 'arena':
            for i in range(2):
                x, y = int(h(i, 9, s) * 40) + 12, int(h(i, 10, s) * 14) + 9
                if in_diamond(x, y):
                    px[x, y] = P1; px[x + 1, y] = P1
    elif kind == 'cave':
        for i in range(5):
            x, y = int(h(i, 1, s) * 48) + 8, int(h(i, 2, s) * 20) + 6
            if in_diamond(x, y) and in_diamond(x + 2, y):
                px[x, y] = P1; px[x + 1, y] = P1; px[x + 2, y] = P2
    return im


def build_tiles():
    kinds = list(TILE_KINDS)
    sheet = Image.new('RGBA', (TW * TILE_VARIANTS, TH * len(kinds)), (0, 0, 0, 0))
    for r, k in enumerate(kinds):
        for v in range(TILE_VARIANTS):
            sheet.alpha_composite(tile(k, v), (v * TW, r * TH))
    return sheet, {'w': TW, 'h': TH, 'kinds': kinds, 'variants': TILE_VARIANTS}


# ───────────────────────── 쿼터뷰 소품 ─────────────────────────
def sprite_img(c):
    return W.img_outline(c.image())


def shaded_blob(c, cx, cy, rx, ry, base, light=26, dark=-34):
    c.ell(cx, cy, rx, ry, C(sh(base, dark)))
    c.ell(cx - rx * 0.1, cy - ry * 0.14, rx * 0.88, ry * 0.8, C(base))
    c.ell(cx - rx * 0.32, cy - ry * 0.36, rx * 0.5, ry * 0.4, C(sh(base, light)))


def tree_oak(v=0):
    c = Cv(56, 72)
    tr, trD = C('#6a4a30'), C('#4a3220')
    c.rect(24, 44, 8, 24, tr); c.rect(29, 44, 3, 24, trD); c.rect(22, 64, 12, 3, tr)
    c.px(21, 66, tr); c.px(34, 66, trD)
    base = ['#3f8a44', '#4a9448', '#3a7e46'][v % 3]
    for i, (dx, dy, r) in enumerate([(-12, 0, 13), (12, 2, 13), (0, -10, 16), (-8, -18, 11), (9, -17, 11), (0, 6, 14)]):
        shaded_blob(c, 28 + dx, 32 + dy, r, r * 0.86, sh(base, -10 if dy > 0 else 0))
    for i in range(18):
        x, y = 10 + h(i, 1, v) * 36, 12 + h(i, 2, v) * 30
        if c.get(round(x), round(y)):
            c.px(x, y, C(sh(base, 40)) if i % 2 else C(sh(base, -40)))
    return c, (28, 66)


def tree_pine(v=0):
    c = Cv(40, 76)
    c.rect(18, 60, 5, 12, C('#4a3220')); c.rect(21, 60, 2, 12, C('#2e1e12'))
    col = ['#1f5a3c', '#24643f', '#1b5036'][v % 3]
    for i in range(5):
        ty = 66 - i * 12
        w_ = 18 - i * 3
        c.poly([(20 - w_, ty), (20, ty - 18), (20 + w_, ty)], C(sh(col, -18)))
        c.poly([(20 - w_ + 2, ty - 2), (20, ty - 18), (20 + w_ - 4, ty - 2)], C(col))
        c.poly([(20 - w_ + 4, ty - 4), (20, ty - 17), (20 - 2, ty - 4)], C(sh(col, 22)))
    return c, (20, 71)


def tree_dead(v=0):
    c = Cv(44, 60)
    col, colD = C('#4a3a40'), C('#2e242a')
    W.stamp_path(c, [(22, 58), (21, 40), (23, 26)], col, 4)
    W.stamp_path(c, [(22, 36), (12, 26), (8, 16)], col, 2.4)
    W.stamp_path(c, [(22, 30), (32, 20), (36, 10)], col, 2.4)
    W.stamp_path(c, [(12, 26), (5, 24)], colD, 1.4)
    W.stamp_path(c, [(32, 20), (38, 21)], colD, 1.4)
    W.stamp_path(c, [(23, 26), (24, 14)], colD, 1.6)
    c.rect(23, 40, 1, 16, colD)
    c.ell(22, 58, 7, 2, colD)
    return c, (22, 58)


def bush(v=0):
    c = Cv(28, 20)
    base = ['#3f8a44', '#4f9a4a', '#2f6a3a'][v % 3]
    shaded_blob(c, 9, 12, 7, 6, base); shaded_blob(c, 19, 12, 7, 6, base); shaded_blob(c, 14, 8, 8, 6.5, base)
    if v == 1:
        for (x, y) in ((8, 8), (17, 6), (20, 12)):
            c.px(x, y, C('#f06a6a'))
    return c, (14, 17)


def rock(v=0):
    if v == 0:
        c = Cv(30, 22)
        shaded_blob(c, 15, 12, 13, 9, '#8a8478')
        c.line(10, 9, 14, 13, C('#5e584e'))
        return c, (15, 19)
    c = Cv(16, 12)
    shaded_blob(c, 8, 6, 6.5, 4.5, '#7e786c')
    return c, (8, 9)


def tuft(v=0):
    c = Cv(12, 8)
    col = ['#5aa04c', '#3e7a36', '#74b85a'][v % 3]
    for i, (x, hgt) in enumerate(((2, 4), (4, 6), (6, 5), (8, 6), (10, 3))):
        c.line(x, 7, x + (1 if i % 2 else -1) * 0.6, 7 - hgt, C(col if i % 2 else sh(col, 24)))
    return c, (6, 7)


def flowers(v=0):
    c = Cv(14, 8)
    for i in range(5):
        x, y = 1 + h(i, 1, v) * 12, 2 + h(i, 2, v) * 5
        c.line(x, y + 1, x, y + 2, C('#3e7a36'))
        c.px(x, y, C(['#ffffff', '#ffe066', '#ff9ec7', '#c8a8ff'][(i + v) % 4]))
    return c, (7, 7)


def fence(v=0):
    """↘ 방향(월드 x축)으로 뻗은 나무 울타리 한 칸."""
    c = Cv(36, 30)
    wd, wdD, wdL = C('#7a5a3a'), C('#4e3622'), C('#a07a50')
    for i, (px_, py) in enumerate(((2, 10), (32, 25))):
        c.rect(px_, py - 8, 3, 14, wd); c.rect(px_ + 2, py - 8, 1, 14, wdD); c.px(px_, py - 9, wdL)
    for off in (0, 5):
        for k in range(32):
            x, y = 3 + k, 6 + off + k * 0.5
            c.px(x, y, wd); c.px(x, y + 1, wdD)
            if k % 9 == 0:
                c.px(x, y, wdL)
    return c, (18, 22)


def iso_box(c, ox, oy, a, b, H, left, right, top=None):
    """ox,oy = 바닥 마름모 위쪽 꼭짓점. a=월드 x 길이(타일), b=월드 y 길이. 왼쪽 면(y 끝)·오른쪽 면(x 끝)을 칠한다."""
    X = (32 * a, 16 * a)
    Y = (-32 * b, 16 * b)
    P0 = (ox, oy)
    PX = (ox + X[0], oy + X[1])
    PY = (ox + Y[0], oy + Y[1])
    PXY = (ox + X[0] + Y[0], oy + X[1] + Y[1])
    c.poly([PY, PXY, (PXY[0], PXY[1] - H), (PY[0], PY[1] - H)], left)
    c.poly([PXY, PX, (PX[0], PX[1] - H), (PXY[0], PXY[1] - H)], right)
    if top:
        c.poly([(P0[0], P0[1] - H), (PX[0], PX[1] - H), (PXY[0], PXY[1] - H), (PY[0], PY[1] - H)], top)
    return P0, PX, PY, PXY


def forge_building():
    """대장간: 3×3 타일 바닥, 돌벽 + 나무 기둥 + 기와 지붕 + 굴뚝 + 화로 불빛 문."""
    a, b, H = 3, 3, 40
    Wd, Hd = 32 * (a + b) + 4, 16 * (a + b) + H + 52
    c = Cv(Wd, Hd)
    ox, oy = 32 * b + 2, H + 50
    stoneL, stoneR = C('#8a7e70'), C('#6a6056')
    P0, PX, PY, PXY = iso_box(c, ox, oy, a, b, H, stoneL, stoneR)
    # 돌 줄눈
    for k in range(1, 5):
        yy = k * H / 5
        c.line(PY[0], PY[1] - yy, PXY[0], PXY[1] - yy, C('#5e554c'))
        c.line(PXY[0], PXY[1] - yy, PX[0], PX[1] - yy, C('#4e463e'))
    # 모서리 나무 기둥
    for P in (PY, PXY, PX):
        c.rect(P[0] - 2, P[1] - H, 4, H, C('#5a3e26')); c.rect(P[0] - 2, P[1] - H, 1, H, C('#7a5a3a'))
    # 문 (왼쪽 면 가운데) — 화로 불빛
    mx, my = (PY[0] + PXY[0]) / 2, (PY[1] + PXY[1]) / 2
    c.poly([(mx - 9, my - 4.5), (mx + 9, my + 4.5), (mx + 9, my + 4.5 - 24), (mx - 9, my - 4.5 - 24)], C('#2a1a12'))
    c.poly([(mx - 6, my - 3), (mx + 6, my + 3), (mx + 6, my + 3 - 12), (mx - 6, my - 3 - 12)], C('#c85a1e'))
    c.poly([(mx - 4, my - 2), (mx + 4, my + 2), (mx + 4, my + 2 - 7), (mx - 4, my - 2 - 7)], C('#ffb040'))
    # 창 (오른쪽 면)
    wx, wy = (PXY[0] + PX[0]) / 2, (PXY[1] + PX[1]) / 2
    c.poly([(wx - 7, wy + 3.5 - 14), (wx + 7, wy - 3.5 - 14), (wx + 7, wy - 3.5 - 24), (wx - 7, wy + 3.5 - 24)], C('#3a2418'))
    c.poly([(wx - 5, wy + 2.5 - 16), (wx + 5, wy - 2.5 - 16), (wx + 5, wy - 2.5 - 22), (wx - 5, wy + 2.5 - 22)], C('#e8a050'))
    # 지붕 (용마루가 월드 x축 방향)
    ov = 6
    T0 = (P0[0], P0[1] - H - ov * 0.5)
    TX = (PX[0] + ov, PX[1] - H)
    TY = (PY[0] - ov, PY[1] - H)
    TXY = (PXY[0], PXY[1] - H + ov * 0.5)
    rise = 30
    R0 = ((T0[0] + TY[0]) / 2, (T0[1] + TY[1]) / 2 - rise)
    R1 = ((TX[0] + TXY[0]) / 2, (TX[1] + TXY[1]) / 2 - rise)
    roof, roofD, roofL = C('#7a3a2e'), C('#5a2820'), C('#a0503c')
    c.poly([TY, TXY, R1, R0], roof)          # 앞쪽(왼쪽 아래) 경사면
    c.poly([TXY, TX, R1], roofD)             # 박공 (오른쪽 끝)
    for k in range(1, 6):
        f = k / 6
        p1 = (TY[0] + (R0[0] - TY[0]) * f, TY[1] + (R0[1] - TY[1]) * f)
        p2 = (TXY[0] + (R1[0] - TXY[0]) * f, TXY[1] + (R1[1] - TXY[1]) * f)
        c.line(p1[0], p1[1], p2[0], p2[1], roofD)
    c.line(R0[0], R0[1], R1[0], R1[1], roofL)
    c.line(TY[0], TY[1], TXY[0], TXY[1], roofD)
    # 굴뚝
    cx_, cy_ = R0[0] + (R1[0] - R0[0]) * 0.3 + 10, R0[1] + (R1[1] - R0[1]) * 0.3 - 2
    c.rect(cx_ - 4, cy_ - 18, 9, 20, C('#6a6056')); c.rect(cx_ - 4, cy_ - 18, 3, 20, C('#8a7e70')); c.rect(cx_ - 5, cy_ - 20, 11, 3, C('#4e463e'))
    # 모루 (문 옆)
    ax_, ay_ = PY[0] + 10, PY[1] + 2
    c.rect(ax_ - 6, ay_ - 7, 12, 3, C('#3a3a44')); c.rect(ax_ - 2, ay_ - 4, 4, 4, C('#2a2a30')); c.rect(ax_ - 6, ay_ - 7, 12, 1, C('#6a6a78'))
    return c, (ox, oy), {'chimney': [round(cx_ - ox), round(cy_ - 20 - oy)], 'door': [round(mx - ox), round(my - 10 - oy)]}


def house_ruin(v=0):
    """무너진 집: 2×3 타일, 한쪽 벽이 부서지고 지붕이 반쯤 내려앉음."""
    a, b, H = 3, 2, 30
    Wd, Hd = 32 * (a + b) + 4, 16 * (a + b) + H + 30
    c = Cv(Wd, Hd)
    ox, oy = 32 * b + 2, H + 28
    wl, wr = (C('#9a8a74'), C('#76685a')) if v == 0 else (C('#8a7a8a'), C('#6a5a6c'))
    P0, PX, PY, PXY = iso_box(c, ox, oy, a, b, H, wl, wr)
    # 부서진 윗선 (오른쪽 면을 계단식으로 깎음)
    for k in range(5):
        f0, f1 = k / 5, (k + 1) / 5
        x0 = PXY[0] + (PX[0] - PXY[0]) * f0
        x1 = PXY[0] + (PX[0] - PXY[0]) * f1
        cut = [0, 6, 14, 10, 20][k] if v == 0 else [4, 0, 8, 16, 12][k]
        for x in range(int(x0), int(x1) + 1):
            ty = PXY[1] + (PX[1] - PXY[1]) * ((x - PXY[0]) / (PX[0] - PXY[0])) - H
            for y in range(int(ty) - 1, int(ty + cut)):
                c.px(x, y, None)
    for k in range(1, 4):
        yy = k * H / 4
        c.line(PY[0], PY[1] - yy, PXY[0], PXY[1] - yy, C(sh('#9a8a74', -30)))
    # 빈 창 · 문
    mx, my = (PY[0] + PXY[0]) / 2, (PY[1] + PXY[1]) / 2
    c.poly([(mx - 7, my - 3.5), (mx + 7, my + 3.5), (mx + 7, my + 3.5 - 18), (mx - 7, my - 3.5 - 18)], C('#2a2024'))
    wx, wy = (PXY[0] + PX[0]) / 2 - 8, (PXY[1] + PX[1]) / 2 + 4
    c.poly([(wx - 5, wy + 2.5 - 12), (wx + 5, wy - 2.5 - 12), (wx + 5, wy - 2.5 - 20), (wx - 5, wy + 2.5 - 20)], C('#2a2024'))
    # 남은 지붕 조각
    roof, roofD = C('#5a4a5a'), C('#3e323e')
    T0, TY = (P0[0], P0[1] - H), (PY[0] - 4, PY[1] - H)
    R0 = ((T0[0] + TY[0]) / 2, (T0[1] + TY[1]) / 2 - 18)
    mid = (PY[0] + (PXY[0] - PY[0]) * 0.45, PY[1] + (PXY[1] - PY[1]) * 0.45 - H)
    c.poly([TY, mid, (mid[0] + (R0[0] - TY[0]), mid[1] + (R0[1] - TY[1])), R0], roof)
    c.line(TY[0], TY[1], mid[0], mid[1], roofD)
    # 잔해
    for i in range(6):
        x, y = PXY[0] + 6 + h(i, 1, v) * 30, PXY[1] - 4 + h(i, 2, v) * 6
        c.rect(x, y, 3, 2, wr)
    return c, (ox, oy)


def cave_wall(v=0):
    """동굴 벽 한 칸: 1×1 타일 위로 솟은 울퉁불퉁한 바위."""
    H = 44 + v * 6
    c = Cv(66, 32 + H + 6)
    ox, oy = 33, H + 6
    left, right, top = C('#4a3e5a'), C('#352c42'), C('#5e5070')
    P0, PX, PY, PXY = iso_box(c, ox, oy, 1, 1, H, left, right, top)
    for i in range(10):
        x, y = 4 + h(i, 1, v) * 56, oy - H + 10 + h(i, 2, v) * (H + 4)
        if c.get(round(x), round(y)) in (left, right):
            c.rect(x, y, 4, 1, C('#2a2234'))
            c.rect(x, y - 1, 3, 1, C('#6a5a80') if c.get(round(x), round(y)) == left else C('#463a56'))
    if v == 1:
        c.poly([(ox + 8, oy - 8), (ox + 11, oy - 20), (ox + 14, oy - 8)], C('#7a6ad8'))
        c.px(ox + 11, oy - 16, C('#c8b8ff'))
    return c, (ox, oy + 16)


def portal_stone():
    """(다음 버전용) 맵 이동 포탈 받침돌."""
    c = Cv(40, 30)
    shaded_blob(c, 20, 20, 17, 8, '#6a6a7a')
    c.ell(20, 18, 12, 5, C('#3a2a6a')); c.ell(20, 18, 9, 3.5, C('#7a5ad8'))
    return c, (20, 24)


def build_props():
    """소품 아틀라스: 이름 → [x, y, w, h, ax, ay]. 기존 3단계 소품(world_art)도 그대로 함께 넣는다."""
    items = []
    for v in range(3):
        items.append(('oak%d' % v,) + tree_oak(v))
        items.append(('pine%d' % v,) + tree_pine(v))
        items.append(('bush%d' % v,) + bush(v))
        items.append(('tuft%d' % v,) + tuft(v))
    items.append(('dead0',) + tree_dead(0)); items.append(('dead1',) + tree_dead(1))
    items.append(('rockB',) + rock(0)); items.append(('rockS',) + rock(1))
    items.append(('flow0',) + flowers(0)); items.append(('flow1',) + flowers(1))
    items.append(('fence',) + fence())
    items.append(('wall0',) + cave_wall(0)); items.append(('wall1',) + cave_wall(1))
    items.append(('portal',) + portal_stone())
    imgs = [(n, sprite_img(cv), anc) for n, cv, anc in items]
    fc, fanc, fextra = forge_building()
    imgs.append(('forge', sprite_img(fc), fanc))
    for v in range(2):
        hc, hanc = house_ruin(v)
        imgs.append(('house%d' % v, sprite_img(hc), hanc))
    # 3단계 소품 재사용 (가로 시트에서 잘라냄)
    import world_art
    wsheets, wmeta = world_art.build_world()
    old = wsheets['props']
    for name, (x, wdt, hgt, ax) in wmeta['props'].items():
        if name in ('pillar', 'flowers', 'rock'):
            continue
        imgs.append(('o_' + name, old.crop((x, 0, x + wdt, hgt)), (ax, hgt - 1)))
    # 가로로 줄줄이 붙이되 너무 길면 줄바꿈
    maxw, x, y, rowh, placed = 1024, 0, 0, 0, []
    for n, im, anc in imgs:
        if x + im.width > maxw:
            x, y, rowh = 0, y + rowh + 1, 0
        placed.append((n, im, anc, x, y))
        x += im.width + 1
        rowh = max(rowh, im.height)
    sheet = Image.new('RGBA', (maxw, y + rowh), (0, 0, 0, 0))
    meta = {}
    for n, im, anc, x, y in placed:
        sheet.alpha_composite(im, (x, y))
        meta[n] = [x, y, im.width, im.height, anc[0], anc[1]]
    meta['_forge'] = fextra
    return sheet, meta
