"""실제 악기 녹음 음원(FluidR3 GM 사운드폰트, CC-BY 3.0)으로 배경음악을 렌더링한다.

곡은 아래 SONGS에 마디 단위로 직접 작곡해 둔다(화음 진행 · 선율 · 반주 형태).
반복 재생용으로 두 바퀴를 렌더링한 뒤 둘째 바퀴만 잘라 내므로, 처음과 끝이 잔향까지 자연스럽게 이어진다.

실행: python3 tools/lineage/music_render.py <사운드폰트 폴더> <출력 폴더> [곡 id ...]
  사운드폰트 폴더: https://github.com/gleitz/midi-js-soundfonts (FluidR3_GM/<악기>-mp3.js)
출력: <id>.mp3 (128kbps, 44.1kHz 스테레오)
"""
import base64, json, os, re, subprocess, sys
import numpy as np

SR = 44100
NOTE_NAMES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
def nname(m): return NOTE_NAMES[m % 12] + str(m // 12 - 1)

class Font:
    def __init__(self, folder):
        self.folder, self.cache, self.raw = folder, {}, {}
    def _load(self, inst):
        if inst not in self.raw:
            s = open(os.path.join(self.folder, inst + '.js')).read()
            self.raw[inst] = dict(re.findall(r'"([A-G]b?\d)":\s*"data:audio/mp3;base64,([^"]+)"', s))
        return self.raw[inst]
    def note(self, inst, m):
        k = (inst, m)
        if k not in self.cache:
            b64 = self._load(inst).get(nname(m))
            if b64 is None: raise KeyError(f'{inst} {nname(m)} 없음')
            p = subprocess.run(['ffmpeg', '-v', 'quiet', '-i', 'pipe:0', '-f', 'f32le', '-ac', '1', '-ar', str(SR), 'pipe:1'],
                               input=base64.b64decode(b64), capture_output=True, check=True)
            a = np.frombuffer(p.stdout, dtype=np.float32).copy()
            # 앞쪽 무음 제거(mp3 인코더 지연)
            nz = np.argmax(np.abs(a) > 1e-4); self.cache[k] = a[nz:]
        return self.cache[k]

# ── 악기 설정: (사운드폰트 이름, 팬, 음량, 해제 초, 공격 초, 잔향 보내기) ──
INST = {
    'strings': ('string_ensemble_1', 0.0, 0.55, 0.6, 0.25, 0.45),
    'cello':   ('cello', -0.25, 0.75, 0.25, 0.03, 0.3),
    'bass':    ('contrabass', -0.1, 0.6, 0.3, 0.03, 0.25),
    'horn':    ('french_horn', 0.2, 0.7, 0.3, 0.06, 0.4),
    'flute':   ('flute', 0.25, 0.6, 0.25, 0.04, 0.4),
    'oboe':    ('oboe', 0.2, 0.55, 0.2, 0.03, 0.35),
    'harp':    ('orchestral_harp', -0.35, 0.5, 1.2, 0.0, 0.35),
    'choir':   ('choir_aahs', 0.0, 0.45, 0.8, 0.3, 0.6),
    'timp':    ('timpani', 0.0, 0.8, 1.5, 0.0, 0.35),
    'pizz':    ('pizzicato_strings', 0.3, 0.55, 0.3, 0.0, 0.3),
    'bell':    ('tubular_bells', 0.15, 0.35, 2.5, 0.0, 0.5),
    'lute':    ('acoustic_guitar_nylon', -0.3, 0.6, 0.6, 0.0, 0.3),
}

def reverb_ir(seconds=3.2, decay=3.0):
    rng = np.random.default_rng(7); n = int(SR * seconds); t = np.arange(n) / n
    ir = np.zeros((2, n), np.float32)
    for ch in range(2):
        noise = rng.standard_normal(n).astype(np.float32)
        # 시간이 지날수록 어두워지는 꼬리: 단순 1차 저역 필터 계수를 점점 낮춤
        out = np.empty(n, np.float32); lp = 0.0
        a = 0.55 - 0.45 * t
        for i in range(0, n, 256):
            seg = noise[i:i + 256]; ai = a[i]
            for j in range(len(seg)): lp += ai * (seg[j] - lp); out[i + j] = lp
        ir[ch] = out * (1 - t) ** decay
        ir[ch, :int(SR * 0.02)] = 0
        for tm, g in [(0.021, 0.5), (0.033, -0.35), (0.047, 0.25), (0.061, -0.2)]: ir[ch, int(SR * (tm + ch * 0.004))] += g
    return ir / np.abs(ir).sum(axis=1, keepdims=True).max() * 9

def conv(x, h):
    n = len(x) + len(h) - 1; N = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(h, N), N)[:n]

def render(song, font):
    bpm, beat = song['bpm'], 60 / song['bpm']
    bars = song['bars']; L = sum(b.get('len', 4) for b in bars) * beat
    total = int(SR * (2 * L + 6))
    dry = {k: np.zeros((2, total), np.float32) for k in ['dry', 'wet']}
    rng = np.random.default_rng(song.get('seed', 1))
    def place(inst, m, t, dur, vel):
        name, pan, gain, rel, att, send = INST[inst]
        a = font.note(name, m)
        n = min(len(a), int(SR * (dur + rel)))
        x = a[:n].copy()
        if att > 0: k = min(n, int(SR * att)); x[:k] *= np.linspace(0, 1, k)
        hold = int(SR * dur)
        if hold < n: r = n - hold; x[hold:] *= np.linspace(1, 0, r) ** 2
        x *= gain * vel * rng.uniform(0.92, 1.05)
        i0 = int(SR * (t + rng.uniform(-0.006, 0.006)))
        if i0 < 0: return
        x = x[:max(0, total - i0)]
        l, r_ = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        for ch, g in ((0, l), (1, r_)):
            dry['dry'][ch, i0:i0 + len(x)] += x * g * (1 - send * 0.5)
            dry['wet'][ch, i0:i0 + len(x)] += x * g * send
    for loop in range(2):
        t0 = loop * L + 1.0
        for bi, bar in enumerate(bars):
            bl = bar.get('len', 4)
            for ev in song['play'](bar, bi):
                inst, m, b, d, v = ev
                place(inst, m, t0 + b * beat, d * beat, v)
            t0 += bl * beat
    ir = reverb_ir(song.get('verb', 3.2))
    out = dry['dry'].astype(np.float64)
    for ch in range(2): out[ch] += conv(dry['wet'][ch], ir[ch])[:total]
    s0 = int(SR * (1.0 + L)); s1 = s0 + int(SR * L)
    seg = out[:, s0:s1]
    # 음량: RMS 기준 -18dBFS로 맞추고 부드러운 리미터
    rms = np.sqrt(np.mean(seg ** 2)); seg *= (10 ** (-18 / 20)) / max(rms, 1e-9)
    seg = np.tanh(seg * 1.1) / np.tanh(1.1)
    return seg.astype(np.float32), L

def write_mp3(seg, path):
    p = subprocess.run(['ffmpeg', '-v', 'quiet', '-y', '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-i', 'pipe:0', '-b:a', '128k', path],
                       input=seg.T.copy().tobytes(), check=True)

# ═════════════ 곡 ═════════════
def triad(root, q='m'):   # 근음 MIDI + 화음 종류 → 구성음
    return {'m': [0, 3, 7], 'M': [0, 4, 7], 'sus': [0, 5, 7], '7': [0, 4, 7, 10]}[q] and [root + x for x in {'m': [0, 3, 7], 'M': [0, 4, 7], 'sus': [0, 5, 7], '7': [0, 4, 7, 10]}[q]]

CH = {'Dm': (50, 'm'), 'Bb': (46, 'M'), 'F': (53, 'M'), 'C': (48, 'M'), 'Gm': (55, 'm'), 'A': (45, 'M'), 'Asus': (45, 'sus'), 'E': (52, 'M'), 'Am': (45, 'm')}

FIELD_A = [[(69, 2), (74, 1), (76, 1)], [(77, 1.5), (76, .5), (74, 1), (72, 1)], [(69, 3), (72, 1)], [(67, 2), (64, 1), (67, 1)],
           [(69, 2), (74, 1), (77, 1)], [(79, 1.5), (77, .5), (76, 1), (74, 1)], [(76, 2), (73, 1), (76, 1)], [(74, 4)]]
FIELD_B = [[(62, 1), (67, 1), (70, 2)], [(69, 2), (65, 1), (62, 1)], [(65, 1), (70, 1), (74, 2)], [(72, 2), (69, 2)],
           [(70, 1), (69, 1), (67, 1), (70, 1)], [(69, 3), (65, 1)], [(68, 2), (71, 2)], [(69, 4)]]

def field_bars():
    intro = [('Dm', None), ('Bb', None), ('F', None), ('Asus', None)]
    a = list(zip(['Dm', 'Bb', 'F', 'C', 'Dm', 'Gm', 'A', 'Dm'], FIELD_A))
    b = list(zip(['Gm', 'Dm', 'Bb', 'F', 'Gm', 'Dm', 'E', 'A'], FIELD_B))
    outro = [('Dm', [(74, 2), (72, 2)]), ('Bb', [(70, 4)]), ('Gm', [(67, 2), (70, 2)]), ('Asus', [(69, 2), (73, 2)])]
    bars = []
    for c, m in intro: bars.append({'ch': c, 'mel': m, 'sec': 'intro'})
    for c, m in a: bars.append({'ch': c, 'mel': m, 'sec': 'A'})
    for c, m in b: bars.append({'ch': c, 'mel': m, 'sec': 'B'})
    for c, m in a: bars.append({'ch': c, 'mel': m, 'sec': 'A2'})
    for c, m in outro: bars.append({'ch': c, 'mel': m, 'sec': 'outro'})
    return bars

def field_play(bar, bi):
    r, q = CH[bar['ch']]; tones = triad(r, q); sec = bar['sec']; ev = []
    lvl = {'intro': 0.55, 'A': 0.7, 'B': 0.8, 'A2': 1.0, 'outro': 0.6}[sec]
    # 현악 화음(가운데 음역)
    for n in tones: ev.append(('strings', n + 12 if n + 12 < 66 else n, 0, 4, 0.5 * lvl))
    # 첼로·콘트라베이스 근음
    ev.append(('cello', r - 12 if r >= 48 else r, 0, 2, 0.8 * lvl)); ev.append(('cello', r - 12 + (7 if sec != 'intro' else 0) if r >= 48 else r + 7, 2, 2, 0.6 * lvl))
    if sec in ('B', 'A2'): ev.append(('bass', r - 24 if r >= 48 else r - 12, 0, 4, 0.7 * lvl))
    # 하프 8분 아르페지오
    if sec in ('intro', 'A', 'A2', 'outro'):
        arp = [tones[0], tones[1] + 12, tones[2] + 12, tones[0] + 24, tones[2] + 12, tones[1] + 12, tones[0] + 12, tones[2] + 12]
        for i, n in enumerate(arp): ev.append(('harp', n, i * 0.5, 0.5, (0.75 if i % 4 == 0 else 0.55) * lvl))
    # B: 피치카토 4분 박자
    if sec == 'B':
        for i, n in enumerate([tones[0] + 12, tones[2] + 12, tones[1] + 12, tones[2] + 12]): ev.append(('pizz', n, i, 1, 0.6))
    # 선율
    if bar['mel']:
        inst = {'A': 'flute', 'B': 'horn', 'A2': 'flute', 'outro': 'oboe', 'intro': 'flute'}[sec]
        b = 0
        for n, d in bar['mel']:
            m = n - 12 if inst == 'horn' else n
            ev.append((inst, m, b, d * 0.97, 0.85))
            if sec == 'A2': ev.append(('horn', n - 12, b, d * 0.97, 0.45))
            b += d
    # 합창: A2에서 화음을 높게
    if sec == 'A2':
        for n in tones: ev.append(('choir', n + 12, 0, 4, 0.5))
    # 팀파니: 단락 시작과 B 끝
    if sec == 'A2' and bi % 4 == 0 or sec == 'B' and bar['ch'] == 'A':
        ev.append(('timp', 38 if r % 12 == 2 else 45, 0, 2, 0.8))
        if sec == 'B': [ev.append(('timp', 45, 3 + k * 0.25, 0.25, 0.4 + k * 0.1)) for k in range(4)]
    if sec == 'outro' and bar['ch'] == 'Asus': ev.append(('bell', 69, 0, 4, 0.5))
    return ev

SONGS = {
    'field_orch': {'bpm': 84, 'bars': field_bars(), 'play': field_play, 'seed': 3, 'verb': 3.2},
}

if __name__ == '__main__':
    sf, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
    font = Font(sf)
    for sid in (sys.argv[3:] or SONGS):
        seg, L = render(SONGS[sid], font)
        path = os.path.join(out, sid + '.mp3'); write_mp3(seg, path)
        print(sid, f'{L:.1f}s', f'peak {np.abs(seg).max():.2f}', f'{os.path.getsize(path) / 1e6:.2f}MB', path)
