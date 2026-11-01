/*
 * 리니지풍 합성 사운드 (Web Audio, 외부 파일 없음)
 *
 * 사용법
 *   const A = LineageAudio.create();          // 클릭 같은 사용자 동작 안에서 호출(브라우저 자동재생 정책)
 *   A.play('hit_sword');                      // 효과음 한 번
 *   A.play('orc_hurt', { pan: -0.3, gain: 0.8 });
 *   A.ambience('forest');  A.ambience(null);  // 환경음 반복 재생 / 정지
 *   A.music(true);  A.music(false);           // 배경음악 (어두운 중세 오케스트라풍)
 *   A.setVolume({ master: 0.9, sfx: 1, music: 0.5, amb: 0.6 });
 *
 * 소리 목록: LineageAudio.SOUNDS (분류·이름·설명)
 * 오프라인 렌더: LineageAudio.renderTo(offlineCtx, name, when) — 검증·WAV 추출용
 */
(function (root) {
  'use strict';

  // ───────────────────────── 공용 도구 ─────────────────────────
  const rnd = (a, b) => a + Math.random() * (b - a);
  const noiseCache = new WeakMap();

  function noiseBuffer(ctx, seconds = 2, color = 'white') {
    let byCtx = noiseCache.get(ctx);
    if (!byCtx) { byCtx = {}; noiseCache.set(ctx, byCtx); }
    const key = color + seconds;
    if (byCtx[key]) return byCtx[key];
    const len = Math.floor(ctx.sampleRate * seconds);
    const buf = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = buf.getChannelData(0);
    let b0 = 0, b1 = 0, b2 = 0, last = 0;
    for (let i = 0; i < len; i++) {
      const w = Math.random() * 2 - 1;
      if (color === 'pink') {
        b0 = 0.99765 * b0 + w * 0.099046; b1 = 0.963 * b1 + w * 0.2965164; b2 = 0.57 * b2 + w * 1.0526913;
        d[i] = (b0 + b1 + b2 + w * 0.1848) * 0.18;
      } else if (color === 'brown') {
        last = (last + 0.02 * w) / 1.02; d[i] = last * 3.5;
      } else d[i] = w;
    }
    byCtx[key] = buf;
    return buf;
  }

  function env(param, t, a, peak, d, sustain = 0, r = 0, floor = 0.0001) {
    // 공격 a초 → peak, 감쇠 d초 → sustain, (r>0이면) 해제
    param.cancelScheduledValues(t);
    param.setValueAtTime(floor, t);
    param.linearRampToValueAtTime(peak, t + Math.max(0.001, a));
    param.exponentialRampToValueAtTime(Math.max(floor, sustain || floor), t + a + Math.max(0.005, d));
    if (r > 0) param.exponentialRampToValueAtTime(floor, t + a + d + r);
  }

  function shaper(ctx, amount = 20) {
    const ws = ctx.createWaveShaper();
    const n = 1024, c = new Float32Array(n);
    for (let i = 0; i < n; i++) { const x = (i / (n - 1)) * 2 - 1; c[i] = ((1 + amount) * x) / (1 + amount * Math.abs(x)); }
    ws.curve = c; ws.oversample = '2x';
    return ws;
  }

  function impulse(ctx, seconds = 2.6, decay = 2.4) {
    const len = Math.floor(ctx.sampleRate * seconds);
    const buf = ctx.createBuffer(2, len, ctx.sampleRate);
    for (let ch = 0; ch < 2; ch++) {
      const d = buf.getChannelData(ch);
      for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, decay) * (i < 40 ? i / 40 : 1);
    }
    return buf;
  }

  // 소리 하나를 그리는 데 쓰는 작은 빌더
  function V(ctx, out, t) {
    const nodes = [];
    const api = {
      t, ctx, out,
      gain(v = 1, to = out) { const g = ctx.createGain(); g.gain.value = v; g.connect(to); nodes.push(g); return g; },
      noise(color, to, dur = 1, rate = 1) {
        const s = ctx.createBufferSource(); s.buffer = noiseBuffer(ctx, 2, color || 'white'); s.playbackRate.value = rate;
        s.loop = true; s.connect(to); s.start(t, Math.random()); s.stop(t + dur + 0.05); return s;
      },
      osc(type, f, to, dur = 1, detune = 0) {
        const o = ctx.createOscillator(); o.type = type; o.frequency.setValueAtTime(f, t); o.detune.value = detune;
        o.connect(to); o.start(t); o.stop(t + dur + 0.05); return o;
      },
      filter(type, f, q = 1, to = out) {
        const b = ctx.createBiquadFilter(); b.type = type; b.frequency.setValueAtTime(f, t); b.Q.value = q; b.connect(to); return b;
      },
      pan(p, to = out) {
        if (!ctx.createStereoPanner) return to;
        const s = ctx.createStereoPanner(); s.pan.value = p; s.connect(to); return s;
      },
    };
    return api;
  }

  // ───────────────────────── 효과음 레시피 ─────────────────────────
  // 각 레시피: (v, o) → 지속 시간(초). v는 빌더, o는 옵션(pitch 배율 등)

  function whoosh(v, o, f0, f1, dur, level) {
    const g = v.gain(0);
    const bp = v.filter('bandpass', f0, 1.4, g);
    bp.frequency.exponentialRampToValueAtTime(f1, v.t + dur * 0.7);
    v.noise('pink', bp, dur);
    g.gain.setValueAtTime(0.0001, v.t);
    g.gain.exponentialRampToValueAtTime(level, v.t + dur * 0.45);
    g.gain.exponentialRampToValueAtTime(0.0001, v.t + dur);
    return dur;
  }

  function thud(v, f0, f1, dur, level, t = v.t) {
    const g = v.gain(0);
    const o = v.osc('sine', f0, g, dur);
    o.frequency.setValueAtTime(f0, t); o.frequency.exponentialRampToValueAtTime(f1, t + dur * 0.8);
    env(g.gain, t, 0.002, level, dur);
    return dur;
  }

  function clank(v, base, dur, level, partials = [1, 2.76, 5.4, 8.93, 13.3]) {
    const g = v.gain(1);
    const hp = v.filter('highpass', 300, 0.7, g);
    partials.forEach((p, i) => {
      const pg = v.gain(0, hp);
      v.osc('sine', base * p * rnd(0.99, 1.01), pg, dur);
      env(pg.gain, v.t, 0.001, level / (1 + i * 0.7), dur * (1 - i * 0.12));
    });
    return dur;
  }

  function crack(v, f, q, dur, level, color = 'white', t = v.t) {
    const g = v.gain(0);
    const bp = v.filter('bandpass', f, q, g);
    v.noise(color, bp, dur);
    env(g.gain, t, 0.001, level, dur);
    return dur;
  }

  // 성도(포먼트) 목소리: 톱니파 → 모음 필터 3개 → 거칠기
  const VOWELS = { a: [730, 1090, 2440], o: [570, 840, 2410], u: [300, 870, 2240], e: [530, 1840, 2480], r: [490, 1350, 1690] };
  function voice(v, o) {
    const { f0 = 110, f1 = 80, dur = 0.6, vowel = 'a', vowel2 = null, level = 0.5, rough = 0.4, vib = 6, breath = 0.2, curve = 'fall', t = v.t } = o;
    const ctx = v.ctx;
    const out = v.gain(0);
    const dist = shaper(ctx, 2 + rough * 30); dist.connect(out);
    const sum = ctx.createGain(); sum.connect(dist);
    const fm = VOWELS[vowel], fm2 = VOWELS[vowel2 || vowel];
    // 성대 진동(톱니파) + 떨림 + 거친 진폭 변조(으르렁)
    const osc = ctx.createOscillator(); osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(f0, t);
    if (curve === 'fall') osc.frequency.exponentialRampToValueAtTime(f1, t + dur);
    else if (curve === 'rise') { osc.frequency.exponentialRampToValueAtTime(f0 * 1.3, t + dur * 0.35); osc.frequency.exponentialRampToValueAtTime(f1, t + dur); }
    else osc.frequency.linearRampToValueAtTime(f1, t + dur);
    const lfo = ctx.createOscillator(); lfo.frequency.value = vib;
    const lg = ctx.createGain(); lg.gain.value = f0 * 0.03; lfo.connect(lg); lg.connect(osc.frequency);
    const am = ctx.createGain(); am.gain.value = 1 - rough * 0.3;
    const rl = ctx.createOscillator(); rl.type = 'square'; rl.frequency.value = 28 + rough * 30;
    const rg = ctx.createGain(); rg.gain.value = rough * 0.5; rl.connect(rg); rg.connect(am.gain);
    osc.connect(am);
    // 모음 필터(포먼트 3개) — 모음이 vowel → vowel2로 바뀜
    fm.forEach((f, i) => {
      const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.Q.value = 5 + i * 2;
      bp.frequency.setValueAtTime(f, t); bp.frequency.linearRampToValueAtTime(fm2[i], t + dur);
      const g = ctx.createGain(); g.gain.value = [1.0, 0.55, 0.22][i] * 3;
      am.connect(bp); bp.connect(g); g.connect(sum);
    });
    [osc, lfo, rl].forEach(n => { n.start(t); n.stop(t + dur + 0.1); });
    if (breath > 0) {
      const ng = v.gain(0, sum);
      const bp = v.filter('bandpass', fm[1], 1.5, ng);
      v.noise('pink', bp, dur);
      env(ng.gain, t, dur * 0.1, breath, dur * 0.9);
    }
    out.gain.setValueAtTime(0.0001, t);
    out.gain.linearRampToValueAtTime(level, t + Math.min(0.06, dur * 0.2));
    out.gain.setValueAtTime(level, t + dur * 0.6);
    out.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    return dur;
  }

  function clicks(v, n, spread, f, level, q = 8) {
    for (let i = 0; i < n; i++) crack(v, f * rnd(0.7, 1.4), q, 0.03, level * rnd(0.5, 1), 'white', v.t + rnd(0, spread));
    return spread + 0.05;
  }

  const R = {
    // 전투 ─────────────────────────
    swing_sword: v => whoosh(v, {}, 700, 2600, 0.2, 1.4),
    swing_heavy: v => whoosh(v, {}, 280, 1300, 0.34, 1.8),
    hit_sword: v => { clank(v, 470 * rnd(0.95, 1.05), 0.55, 0.28); crack(v, 3200, 1.2, 0.06, 0.5); thud(v, 140, 60, 0.18, 0.5); return 0.6; },
    hit_blunt: v => { thud(v, 95, 40, 0.3, 0.9); crack(v, 600, 0.8, 0.12, 0.6, 'brown'); crack(v, 1800, 1.5, 0.05, 0.3); return 0.35; },
    hit_flesh: v => { thud(v, 120, 55, 0.16, 0.7); crack(v, 900, 1.1, 0.09, 0.55, 'pink'); return 0.2; },
    bow_release: v => {
      const g = v.gain(0); const lp = v.filter('lowpass', 2400, 2, g); lp.frequency.exponentialRampToValueAtTime(400, v.t + 0.25);
      v.osc('sawtooth', 196, lp, 0.3); env(g.gain, v.t, 0.002, 0.35, 0.28);
      whoosh(v, {}, 1500, 4000, 0.22, 0.12); return 0.35;
    },
    arrow_hit: v => { crack(v, 2500, 2, 0.03, 0.6); const g = v.gain(0); v.osc('triangle', 310, g, 0.15); env(g.gain, v.t, 0.001, 0.4, 0.12); thud(v, 110, 70, 0.1, 0.4); return 0.2; },
    magic_cast: v => {
      const g = v.gain(0); const hp = v.filter('highpass', 400, 0.7, g);
      [523, 659, 784, 1046].forEach((f, i) => { const o = v.osc('sine', f, hp, 0.9, rnd(-8, 8)); o.frequency.exponentialRampToValueAtTime(f * 1.5, v.t + 0.8); });
      const trem = v.ctx.createOscillator(); trem.frequency.value = 11; const tg = v.ctx.createGain(); tg.gain.value = 0.08; trem.connect(tg); tg.connect(g.gain); trem.start(v.t); trem.stop(v.t + 1);
      g.gain.setValueAtTime(0.0001, v.t); g.gain.linearRampToValueAtTime(0.14, v.t + 0.5); g.gain.exponentialRampToValueAtTime(0.0001, v.t + 0.9);
      whoosh(v, {}, 400, 3000, 0.8, 0.12); return 0.95;
    },
    magic_hit: v => {
      const g = v.gain(0); const lp = v.filter('lowpass', 6000, 0.8, g); lp.frequency.exponentialRampToValueAtTime(300, v.t + 0.6);
      v.noise('pink', lp, 0.7); env(g.gain, v.t, 0.003, 0.7, 0.65);
      clank(v, 880, 0.9, 0.12, [1, 1.5, 2.0, 3.0]); thud(v, 80, 35, 0.4, 0.7); return 0.9;
    },
    critical: v => { const h = v.gain(0.5); R.hit_sword(V(v.ctx, h, v.t)); thud(v, 70, 28, 0.5, 0.5); clank(v, 1320, 1.1, 0.06, [1, 2.4, 4.1]); crack(v, 5000, 0.8, 0.12, 0.2); return 1.1; },
    block: v => { clank(v, 300, 0.4, 0.3, [1, 2.3, 3.9, 6.1]); thud(v, 180, 90, 0.12, 0.6); crack(v, 1200, 1, 0.05, 0.4); return 0.45; },
    level_up: v => {
      [392, 523, 659, 784, 1046].forEach((f, i) => { const g = v.gain(0); v.osc('triangle', f, g, 1.6); env(g.gain, v.t + i * 0.09, 0.01, 0.12, 1.2); });
      return 1.7;
    },
    enchant_ok: v => { [659, 988, 1318].forEach((f, i) => { const g = v.gain(0); v.osc('sine', f, g, 1.4); env(g.gain, v.t + i * 0.06, 0.005, 0.15, 1.2); }); clank(v, 1760, 1.2, 0.06, [1, 2.7]); return 1.4; },
    enchant_fail: v => { const g = v.gain(0); const o = v.osc('sawtooth', 220, v.filter('lowpass', 900, 1, g), 0.9); o.frequency.exponentialRampToValueAtTime(70, v.t + 0.85); env(g.gain, v.t, 0.01, 0.25, 0.85); crack(v, 400, 0.6, 0.6, 0.4, 'brown'); return 0.9; },

    // 스킬 ─────────────────────────
    skill_spin: v => {
      // 소용돌이 바람(여러 번 휘감기는 휘두름) + 맑은 칼날 울림
      for (let i = 0; i < 3; i++) { const p = v.gain(1); whoosh(V(v.ctx, p, v.t + i * 0.12), {}, 500 + i * 300, 2600 + i * 400, 0.28, 1.3 - i * 0.25); }
      clank(v, 1180, 0.9, 0.08, [1, 2.01, 3.0]);
      return 0.9;
    },
    skill_slam_charge: v => {
      const g = v.gain(0); const o = v.osc('sawtooth', 110, v.filter('lowpass', 900, 3, g), 0.6);
      o.frequency.exponentialRampToValueAtTime(440, v.t + 0.55); g.gain.setValueAtTime(0.0001, v.t); g.gain.exponentialRampToValueAtTime(0.25, v.t + 0.5); g.gain.exponentialRampToValueAtTime(0.0001, v.t + 0.6);
      const sg = v.gain(0); v.osc('sine', 1760, sg, 0.6); env(sg.gain, v.t + 0.3, 0.2, 0.05, 0.3);
      return 0.6;
    },
    skill_slam: v => {
      thud(v, 60, 24, 1.0, 1.0); crack(v, 260, 0.6, 0.9, 0.9, 'brown'); crack(v, 2400, 1.2, 0.08, 0.5);
      const g = v.gain(0); const lp = v.filter('lowpass', 5000, 0.7, g); lp.frequency.exponentialRampToValueAtTime(400, v.t + 1.0);
      v.noise('pink', lp, 1.1); env(g.gain, v.t, 0.004, 0.6, 1.05);
      clank(v, 1500, 1.4, 0.07, [1, 1.5, 2.25, 3.4]);
      for (let i = 0; i < 6; i++) crack(v, rnd(1500, 3500), 3, 0.05, 0.25, 'white', v.t + 0.15 + i * rnd(0.05, 0.12));
      return 1.4;
    },
    skill_guard: v => {
      // 낮은 웅웅거림 + 반짝이는 화음
      const g = v.gain(0); [220, 330, 440].forEach(f => { v.osc('sine', f, g, 1.6, rnd(-6, 6)); });
      const trem = v.ctx.createOscillator(); trem.frequency.value = 6; const tg = v.ctx.createGain(); tg.gain.value = 0.04; trem.connect(tg); tg.connect(g.gain); trem.start(v.t); trem.stop(v.t + 1.7);
      g.gain.setValueAtTime(0.0001, v.t); g.gain.linearRampToValueAtTime(0.12, v.t + 0.25); g.gain.setValueAtTime(0.12, v.t + 1.0); g.gain.exponentialRampToValueAtTime(0.0001, v.t + 1.6);
      [1318, 1760, 2637].forEach((f, i) => { const sg = v.gain(0); v.osc('triangle', f, sg, 1.0); env(sg.gain, v.t + 0.05 + i * 0.07, 0.005, 0.08, 0.8); });
      return 1.6;
    },
    skill_bless: v => {
      // 합창 화음(장조) + 종소리
      [[57, 'a'], [61, 'a'], [64, 'o'], [69, 'a']].forEach(([n, vw], i) => voice(v, { f0: 440 * Math.pow(2, (n - 69) / 12), f1: 440 * Math.pow(2, (n - 69) / 12), dur: 2.0, vowel: vw, vowel2: 'o', level: 0.12, rough: 0, vib: 5, breath: 0.05, curve: 'flat' }));
      [880, 1320, 1760].forEach((f, i) => { clank(V(v.ctx, v.gain(1), v.t + 0.1 + i * 0.18), f, 1.6, 0.07, [1, 2.76, 5.4]); });
      return 2.1;
    },

    // 몬스터 ─────────────────────────
    orc_attack: v => voice(v, { f0: 120, f1: 85, dur: 0.55, vowel: 'a', vowel2: 'o', level: 0.55, rough: 0.7, curve: 'rise' }),
    orc_hurt: v => voice(v, { f0: 150, f1: 95, dur: 0.28, vowel: 'u', vowel2: 'a', level: 0.5, rough: 0.6 }),
    orc_death: v => voice(v, { f0: 130, f1: 55, dur: 1.2, vowel: 'a', vowel2: 'u', level: 0.5, rough: 0.55, vib: 4 }),
    skeleton_attack: v => { clicks(v, 9, 0.28, 2400, 2.6); return whoosh(v, {}, 900, 2400, 0.22, 0.9); },
    skeleton_hurt: v => { clicks(v, 5, 0.12, 1800, 1.6, 5); return thud(v, 260, 180, 0.08, 0.4); },
    skeleton_death: v => { clicks(v, 26, 0.9, 1500, 2.4, 4); thud(v, 90, 50, 0.25, 0.5, v.t + 0.75); return 1.1; },
    wolf_attack: v => { voice(v, { f0: 160, f1: 120, dur: 0.5, vowel: 'r', level: 0.45, rough: 0.9, breath: 0.4, curve: 'flat' }); crack(v, 3500, 2, 0.05, 0.3, 'white', v.t + 0.35); return 0.55; },
    wolf_hurt: v => voice(v, { f0: 900, f1: 520, dur: 0.3, vowel: 'e', vowel2: 'u', level: 0.35, rough: 0.05, breath: 0.1, vib: 10 }),
    wolf_death: v => voice(v, { f0: 700, f1: 260, dur: 1.1, vowel: 'u', level: 0.3, rough: 0.05, breath: 0.25, vib: 7 }),
    wolf_howl: v => voice(v, { f0: 380, f1: 300, dur: 2.6, vowel: 'u', vowel2: 'o', level: 0.3, rough: 0.0, breath: 0.15, vib: 5, curve: 'rise' }),
    spider_attack: v => { const g = v.gain(0); v.noise('white', v.filter('highpass', 3500, 0.8, g), 0.45); env(g.gain, v.t, 0.05, 0.35, 0.4); clicks(v, 10, 0.4, 4200, 0.35, 12); return 0.5; },
    spider_hurt: v => { const g = v.gain(0); const o = v.osc('sawtooth', 1800, v.filter('bandpass', 2600, 4, g), 0.3); o.frequency.exponentialRampToValueAtTime(2600, v.t + 0.25); env(g.gain, v.t, 0.01, 1.1, 0.28); return 0.3; },
    spider_death: v => { R.spider_hurt(v); clicks(v, 16, 0.8, 3000, 1.6, 10); return 0.9; },
    ooze_attack: v => { const g = v.gain(0); const bp = v.filter('bandpass', 300, 8, g); bp.frequency.exponentialRampToValueAtTime(1400, v.t + 0.12); bp.frequency.exponentialRampToValueAtTime(200, v.t + 0.35); v.noise('brown', bp, 0.4); env(g.gain, v.t, 0.01, 3.5, 0.38); return 0.4; },
    ooze_hurt: v => { for (let i = 0; i < 5; i++) { const t = v.t + i * rnd(0.04, 0.08); const g = v.gain(0); const o = v.osc('sine', rnd(250, 500), g, 0.1); o.frequency.setValueAtTime(rnd(250, 500), t); o.frequency.exponentialRampToValueAtTime(rnd(700, 1100), t + 0.05); env(g.gain, t, 0.003, 0.25, 0.07); } return 0.45; },
    ooze_death: v => { const g = v.gain(0); const bp = v.filter('lowpass', 900, 6, g); bp.frequency.exponentialRampToValueAtTime(120, v.t + 1.2); v.noise('brown', bp, 1.3); env(g.gain, v.t, 0.05, 1.4, 1.2); R.ooze_hurt(v); return 1.3; },
    boss_attack: v => { voice(v, { f0: 70, f1: 50, dur: 1.0, vowel: 'o', vowel2: 'a', level: 0.65, rough: 0.85, vib: 3, curve: 'rise' }); thud(v, 50, 30, 0.8, 0.6); return 1.0; },
    boss_hurt: v => { voice(v, { f0: 95, f1: 60, dur: 0.45, vowel: 'u', vowel2: 'a', level: 0.6, rough: 0.8 }); clank(v, 220, 0.4, 0.15, [1, 2.4, 4.4]); return 0.5; },
    boss_death: v => { voice(v, { f0: 85, f1: 32, dur: 2.6, vowel: 'a', vowel2: 'u', level: 0.6, rough: 0.7, vib: 2.5 }); thud(v, 60, 25, 1.4, 0.8, v.t + 1.8); crack(v, 300, 0.5, 1.2, 0.5, 'brown', v.t + 1.8); return 3.2; },

    // 발소리(지형별) ─────────────────────────
    step_grass: v => crack(v, 2200, 0.9, 0.08, 0.5, 'pink'),
    step_stone: v => { crack(v, 1400, 2.5, 0.05, 0.3); return thud(v, 160, 120, 0.05, 0.2); },
    step_swamp: v => { const g = v.gain(0); const bp = v.filter('bandpass', 500, 6, g); bp.frequency.exponentialRampToValueAtTime(1100, v.t + 0.12); v.noise('brown', bp, 0.16); env(g.gain, v.t, 0.01, 2.2, 0.15); return 0.18; },
  };

  // 스킬 동작별 소리: 프레임 번호 → 소리
  const SKILL_CUES = {
    skill_spin: [[1, 'skill_spin']],
    skill_slam: [[1, 'skill_slam_charge'], [4, 'skill_slam']],
    skill_guard: [[0, 'skill_guard']],
    skill_bless: [[1, 'skill_bless']],
  };

  // 발소리 자동 매핑용: 동작별 사운드
  const ACTOR_SFX = {
    knight: { swing: 'swing_sword', hit: 'hit_sword', skills: SKILL_CUES },
    lord: { swing: 'swing_sword', hit: 'hit_sword', skills: SKILL_CUES },
    elf: { swing: 'bow_release', hit: 'arrow_hit' },
    mage: { swing: 'magic_cast', hit: 'magic_hit' },
    orc: { swing: 'swing_heavy', hit: 'hit_blunt', attack: 'orc_attack', hurt: 'orc_hurt', death: 'orc_death' },
    skeleton: { swing: 'swing_sword', hit: 'hit_sword', attack: 'skeleton_attack', hurt: 'skeleton_hurt', death: 'skeleton_death' },
    wolf: { hit: 'hit_flesh', attack: 'wolf_attack', hurt: 'wolf_hurt', death: 'wolf_death' },
    spider: { hit: 'hit_flesh', attack: 'spider_attack', hurt: 'spider_hurt', death: 'spider_death' },
    ooze: { hit: 'hit_flesh', attack: 'ooze_attack', hurt: 'ooze_hurt', death: 'ooze_death' },
    boss: { swing: 'swing_heavy', hit: 'critical', attack: 'boss_attack', hurt: 'boss_hurt', death: 'boss_death' },
  };

  const SOUNDS = [
    ['전투', 'swing_sword', '칼 휘두름'], ['전투', 'swing_heavy', '무거운 휘두름'], ['전투', 'hit_sword', '칼 적중(쇳소리)'],
    ['전투', 'hit_blunt', '둔기 적중'], ['전투', 'hit_flesh', '물어뜯기·살 타격'], ['전투', 'bow_release', '활 시위'],
    ['전투', 'arrow_hit', '화살 꽂힘'], ['전투', 'magic_cast', '마법 시전'], ['전투', 'magic_hit', '마법 폭발'],
    ['전투', 'critical', '치명타'], ['전투', 'block', '방패 막기'],
    ['스킬', 'skill_spin', '회전 베기'], ['스킬', 'skill_slam_charge', '대지 강타 · 모으기'], ['스킬', 'skill_slam', '대지 강타 · 폭발'],
    ['스킬', 'skill_guard', '수호 결계'], ['스킬', 'skill_bless', '성스러운 축복'],
    ['시스템', 'level_up', '레벨 업'], ['시스템', 'enchant_ok', '강화 성공'], ['시스템', 'enchant_fail', '강화 실패'],
    ['오크 전사', 'orc_attack', '공격 함성'], ['오크 전사', 'orc_hurt', '피격'], ['오크 전사', 'orc_death', '사망'],
    ['해골 병사', 'skeleton_attack', '공격'], ['해골 병사', 'skeleton_hurt', '피격'], ['해골 병사', 'skeleton_death', '무너짐'],
    ['다이어울프', 'wolf_attack', '으르렁'], ['다이어울프', 'wolf_hurt', '깨갱'], ['다이어울프', 'wolf_death', '사망'], ['다이어울프', 'wolf_howl', '울부짖음'],
    ['거대 거미', 'spider_attack', '쉿·딸깍'], ['거대 거미', 'spider_hurt', '비명'], ['거대 거미', 'spider_death', '사망'],
    ['늪 점액', 'ooze_attack', '철퍽'], ['늪 점액', 'ooze_hurt', '거품'], ['늪 점액', 'ooze_death', '녹아내림'],
    ['몰락한 왕', 'boss_attack', '포효'], ['몰락한 왕', 'boss_hurt', '피격'], ['몰락한 왕', 'boss_death', '최후'],
    ['발소리', 'step_grass', '풀밭'], ['발소리', 'step_stone', '돌길'], ['발소리', 'step_swamp', '늪'],
  ];

  // ───────────────────────── 환경음 ─────────────────────────
  const AMBIENCES = {
    forest: '숲 (바람·새)', campfire: '모닥불', swamp: '늪 (물거품·개구리)', dungeon: '던전 (물방울·울림)',
  };

  function startAmbience(ctx, out, kind) {
    const stops = [];
    const timers = [];
    const g = ctx.createGain(); g.gain.value = 0; g.connect(out);
    g.gain.linearRampToValueAtTime(1, ctx.currentTime + 1.5);
    const loopNoise = (color, type, f, q, level) => {
      const s = ctx.createBufferSource(); s.buffer = noiseBuffer(ctx, 2, color); s.loop = true;
      const b = ctx.createBiquadFilter(); b.type = type; b.frequency.value = f; b.Q.value = q;
      const lg = ctx.createGain(); lg.gain.value = level;
      s.connect(b); b.connect(lg); lg.connect(g); s.start();
      stops.push(() => s.stop());
      return { b, lg };
    };
    const every = (ms, fn) => { const id = setInterval(() => fn(ctx.currentTime + 0.05), ms); timers.push(id); };
    const once = (name, t, gain = 0.5, pan = 0) => { const p = ctx.createGain(); p.gain.value = gain; p.connect(g); const pv = V(ctx, panned(ctx, p, pan), t); R[name] ? R[name](pv) : null; };

    if (kind === 'forest') {
      const w = loopNoise('pink', 'lowpass', 500, 0.5, 0.25);
      const lfo = ctx.createOscillator(); lfo.frequency.value = 0.08; const lg = ctx.createGain(); lg.gain.value = 300;
      lfo.connect(lg); lg.connect(w.b.frequency); lfo.start(); stops.push(() => lfo.stop());
      every(1700, t => { if (Math.random() < 0.55) bird(ctx, g, t); });
    } else if (kind === 'campfire') {
      loopNoise('brown', 'lowpass', 300, 0.7, 0.35);
      every(90, t => { if (Math.random() < 0.5) { const v = V(ctx, g, t + Math.random() * 0.08); crack(v, rnd(1500, 5000), rnd(1, 4), rnd(0.01, 0.04), rnd(0.05, 0.3)); } });
    } else if (kind === 'swamp') {
      loopNoise('brown', 'lowpass', 250, 0.6, 0.2);
      every(700, t => { if (Math.random() < 0.6) { const p = ctx.createGain(); p.gain.value = 0.25; p.connect(g); R.ooze_hurt(V(ctx, p, t)); } });
      every(1300, t => { if (Math.random() < 0.5) frog(ctx, g, t); });
    } else if (kind === 'dungeon') {
      const d = ctx.createOscillator(); d.type = 'sawtooth'; d.frequency.value = 41.2;
      const dl = ctx.createBiquadFilter(); dl.type = 'lowpass'; dl.frequency.value = 160;
      const dg = ctx.createGain(); dg.gain.value = 0.07; d.connect(dl); dl.connect(dg); dg.connect(g); d.start(); stops.push(() => d.stop());
      loopNoise('pink', 'bandpass', 380, 0.8, 0.07);
      every(900, t => { if (Math.random() < 0.5) drip(ctx, g, t); });
    }
    return () => {
      g.gain.cancelScheduledValues(ctx.currentTime);
      g.gain.setValueAtTime(g.gain.value, ctx.currentTime);
      g.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.8);
      timers.forEach(clearInterval);
      setTimeout(() => stops.forEach(s => { try { s(); } catch (e) { /* 이미 정지 */ } }), 900);
    };
  }

  function panned(ctx, to, p) { if (!ctx.createStereoPanner) return to; const s = ctx.createStereoPanner(); s.pan.value = p; s.connect(to); return s; }

  function bird(ctx, out, t) {
    const n = 2 + Math.floor(Math.random() * 4), base = rnd(2600, 4200);
    const pan = panned(ctx, out, rnd(-0.8, 0.8));
    for (let i = 0; i < n; i++) {
      const o = ctx.createOscillator(); const g = ctx.createGain(); o.type = 'sine';
      const s = t + i * rnd(0.09, 0.15);
      o.frequency.setValueAtTime(base, s); o.frequency.exponentialRampToValueAtTime(base * rnd(1.2, 1.6), s + 0.05);
      o.frequency.exponentialRampToValueAtTime(base * 0.9, s + 0.09);
      env(g.gain, s, 0.005, 0.05, 0.09);
      o.connect(g); g.connect(pan); o.start(s); o.stop(s + 0.12);
    }
  }
  function frog(ctx, out, t) {
    const pan = panned(ctx, out, rnd(-0.7, 0.7));
    for (let i = 0; i < 3; i++) {
      const s = t + i * 0.14;
      const o = ctx.createOscillator(); o.type = 'square'; o.frequency.value = rnd(150, 190);
      const b = ctx.createBiquadFilter(); b.type = 'bandpass'; b.frequency.value = 700; b.Q.value = 5;
      const g = ctx.createGain(); env(g.gain, s, 0.01, 0.12, 0.09);
      o.connect(b); b.connect(g); g.connect(pan); o.start(s); o.stop(s + 0.12);
    }
  }
  function drip(ctx, out, t) {
    const pan = panned(ctx, out, rnd(-0.6, 0.6));
    const o = ctx.createOscillator(); o.type = 'sine';
    const f = rnd(900, 1600);
    o.frequency.setValueAtTime(f, t); o.frequency.exponentialRampToValueAtTime(f * 2.2, t + 0.06);
    const g = ctx.createGain(); env(g.gain, t, 0.002, 0.18, 0.12);
    o.connect(g); g.connect(pan); o.start(t); o.stop(t + 0.15);
  }

  // ───────────────────────── 배경음악 ─────────────────────────
  // 라 단조 i–VI–iv–V (Am–F–Dm–E), 느린 현악 패드 + 합창 + 첼로 오스티나토 + 팀파니
  const MIDI = n => 440 * Math.pow(2, (n - 69) / 12);
  const CHORDS = [[45, 57, 60, 64], [41, 57, 60, 65], [38, 57, 62, 65], [40, 56, 59, 64]];
  const MELODY = [76, 74, 72, 71, 72, 69, 71, 68];

  function startMusic(ctx, out) {
    const bus = ctx.createGain(); bus.gain.value = 0; bus.connect(out);
    bus.gain.linearRampToValueAtTime(1, ctx.currentTime + 3);
    const bar = 4.0;             // 1마디 4초(60bpm)
    let next = ctx.currentTime + 0.1, idx = 0, alive = true;
    const strings = (t, notes, dur) => {
      const g = ctx.createGain(); g.connect(bus);
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 900; lp.Q.value = 0.6; lp.connect(g);
      g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(0.06, t + 1.2); g.gain.setValueAtTime(0.06, t + dur - 0.8); g.gain.linearRampToValueAtTime(0.0001, t + dur + 0.6);
      notes.forEach(n => [-7, 0, 7].forEach(dt => { const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = MIDI(n); o.detune.value = dt; o.connect(lp); o.start(t); o.stop(t + dur + 0.7); }));
    };
    const choir = (t, n, dur) => {
      const v = V(ctx, bus, t);
      voice(v, { f0: MIDI(n), f1: MIDI(n), dur, vowel: 'a', vowel2: 'o', level: 0.05, rough: 0, vib: 5, breath: 0.05, curve: 'flat' });
    };
    const cello = (t, root) => {
      [0, 0, 7, 0, 12, 7, 3, 7].forEach((st, i) => {
        const s = t + i * (bar / 8);
        const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = MIDI(root + st);
        const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 600;
        const g = ctx.createGain(); env(g.gain, s, 0.04, 0.05, bar / 8 * 0.9);
        o.connect(lp); lp.connect(g); g.connect(bus); o.start(s); o.stop(s + bar / 8 + 0.05);
      });
    };
    const timpani = (t, f, lvl) => {
      const v = V(ctx, bus, t); thud(v, f * 1.3, f, 1.2, lvl); const g = v.gain(0); v.noise('brown', v.filter('lowpass', 300, 1, g), 0.4); env(g.gain, t, 0.002, lvl * 0.4, 0.3);
    };
    function schedule() {
      if (!alive) return;
      while (next < ctx.currentTime + 1.5) {
        const c = CHORDS[idx % 4];
        strings(next, c.slice(1), bar);
        cello(next, c[0]);
        timpani(next, MIDI(c[0] - 12) * 2, 0.35);
        if (idx % 4 === 3) { timpani(next + bar * 0.75, MIDI(c[0] - 12) * 2, 0.22); timpani(next + bar * 0.875, MIDI(c[0] - 12) * 2, 0.26); }
        if (idx % 8 >= 4) choir(next + 0.2, MELODY[idx % 8 * 2 % 8] - 12, bar * 0.9);
        next += bar; idx++;
      }
    }
    schedule();
    const id = setInterval(schedule, 400);
    return () => {
      alive = false; clearInterval(id);
      bus.gain.cancelScheduledValues(ctx.currentTime); bus.gain.setValueAtTime(bus.gain.value, ctx.currentTime);
      bus.gain.linearRampToValueAtTime(0, ctx.currentTime + 1.5);
    };
  }

  // ───────────────────────── 엔진 ─────────────────────────
  function create(opts = {}) {
    const AC = root.AudioContext || root.webkitAudioContext;
    if (!AC) throw new Error('이 브라우저는 Web Audio를 지원하지 않습니다.');
    const ctx = opts.context || new AC();
    const master = ctx.createGain(); master.gain.value = 0.9;
    const comp = ctx.createDynamicsCompressor(); comp.threshold.value = -14; comp.ratio.value = 4;
    master.connect(comp); comp.connect(ctx.destination);
    const verb = ctx.createConvolver(); verb.buffer = impulse(ctx);
    const verbGain = ctx.createGain(); verbGain.gain.value = 0.22; verb.connect(verbGain); verbGain.connect(master);
    const bus = name => { const g = ctx.createGain(); g.connect(master); g.connect(verb); return g; };
    const sfx = bus(), music = bus(), amb = bus();
    music.gain.value = 0.5; amb.gain.value = 0.6;
    let stopAmb = null, stopMusic = null;
    return {
      ctx,
      play(name, o = {}) {
        if (!R[name]) throw new Error('알 수 없는 소리: ' + name);
        if (ctx.state === 'suspended') ctx.resume();
        const g = ctx.createGain(); g.gain.value = o.gain == null ? 1 : o.gain;
        g.connect(panned(ctx, sfx, o.pan || 0));
        return R[name](V(ctx, g, ctx.currentTime + (o.delay || 0) + 0.01));
      },
      ambience(kind) {
        if (stopAmb) { stopAmb(); stopAmb = null; }
        if (kind) { if (ctx.state === 'suspended') ctx.resume(); stopAmb = startAmbience(ctx, amb, kind); }
      },
      music(on) {
        if (stopMusic) { stopMusic(); stopMusic = null; }
        if (on) { if (ctx.state === 'suspended') ctx.resume(); stopMusic = startMusic(ctx, music); }
      },
      setVolume(v) {
        if (v.master != null) master.gain.value = v.master;
        if (v.sfx != null) sfx.gain.value = v.sfx;
        if (v.music != null) music.gain.value = v.music;
        if (v.amb != null) amb.gain.value = v.amb;
      },
      actorSfx(name) { return ACTOR_SFX[name] || {}; },
    };
  }

  function renderTo(ctx, name, when = 0) {
    return R[name](V(ctx, ctx.destination, when));
  }

  root.LineageAudio = { create, renderTo, SOUNDS, AMBIENCES, ACTOR_SFX, names: Object.keys(R) };
})(typeof window !== 'undefined' ? window : globalThis);
