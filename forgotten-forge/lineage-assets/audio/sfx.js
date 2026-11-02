/*
 * 리니지풍 합성 사운드 (Web Audio, 외부 파일 없음)
 *
 * 사용법
 *   const A = LineageAudio.create();          // 클릭 같은 사용자 동작 안에서 호출(브라우저 자동재생 정책)
 *   A.play('hit_sword');                      // 효과음 한 번
 *   A.play('orc_hurt', { pan: -0.3, gain: 0.8 });
 *   A.ambience('forest');  A.ambience(null);  // 환경음 반복 재생 / 정지
 *   A.music(true);  A.music('boss');  A.music(false);  // 배경음악: 장면(field·town·dungeon·boss)별 곡, 교차 페이드
 *   A.setPick({ bgm: { field: 'field_b' }, sfx: { hit_sword: 'B', mon_orc: 'C' } });  // 고른 변형(A/B/C) 적용
 *   A.play('hit_sword', { variant: 'C' });   // 특정 변형 미리 듣기
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
  let CURMOD = null;   // 지금 그리는 소리의 변형(음높이·포먼트·거칠기·추가 레이어)
  const cents = r => 1200 * Math.log2(r || 1);
  function V(ctx, out, t, mod) {
    const nodes = [];
    const M = mod || CURMOD || {}, pc = cents(M.pitch), fc = cents(M.pitch) * (M.ftrack == null ? 1 : M.ftrack);
    const api = {
      t, ctx, out, mod: M,
      gain(v = 1, to = out) { const g = ctx.createGain(); g.gain.value = v; g.connect(to); nodes.push(g); return g; },
      noise(color, to, dur = 1, rate = 1) {
        const s = ctx.createBufferSource(); s.buffer = noiseBuffer(ctx, 2, color || 'white'); s.playbackRate.value = rate;
        s.playbackRate.value = rate * (M.pitch || 1);
        s.loop = true; s.connect(to); s.start(t, Math.random()); s.stop(t + dur + 0.05); return s;
      },
      osc(type, f, to, dur = 1, detune = 0) {
        const o = ctx.createOscillator(); o.type = type; o.frequency.setValueAtTime(f, t); o.detune.value = detune + pc;
        o.connect(to); o.start(t); o.stop(t + dur + 0.05); return o;
      },
      filter(type, f, q = 1, to = out) {
        const b = ctx.createBiquadFilter(); b.type = type; b.frequency.setValueAtTime(f, t); b.Q.value = q; b.detune.value = fc; b.connect(to); return b;
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
    const { f0 = 110, f1 = 80, dur = 0.6, vowel = 'a', vowel2 = null, level = 0.5, vib = 6, breath = 0.2, curve = 'fall', t = v.t } = o;
    const ctx = v.ctx, M = v.mod || {};
    const rough = Math.max(0, Math.min(1, (o.rough == null ? 0.4 : o.rough) + (M.rough || 0)));
    const out = v.gain(0);
    const dist = shaper(ctx, 2 + rough * 30); dist.connect(out);
    const sum = ctx.createGain(); sum.connect(dist);
    const fm = VOWELS[vowel], fm2 = VOWELS[vowel2 || vowel];
    // 성대 진동(톱니파) + 떨림 + 거친 진폭 변조(으르렁)
    const osc = ctx.createOscillator(); osc.type = 'sawtooth'; osc.detune.value = cents(M.pitch);
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
      const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.Q.value = 5 + i * 2; bp.detune.value = cents(M.formant || Math.sqrt(M.pitch || 1));
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

    // 요정 스킬 ─────────────────────────
    elf_charge: v => {   // 바람이 감기며 모이는 소리
      const g = v.gain(0); const bp = v.filter('bandpass', 400, 3, g); bp.frequency.exponentialRampToValueAtTime(2400, v.t + 0.6);
      v.noise('pink', bp, 0.7); g.gain.setValueAtTime(0.0001, v.t); g.gain.exponentialRampToValueAtTime(1.8, v.t + 0.55); g.gain.exponentialRampToValueAtTime(0.0001, v.t + 0.7);
      [1046, 1318].forEach((f, i) => { const sg = v.gain(0); v.osc('sine', f, sg, 0.7); env(sg.gain, v.t + 0.2 + i * 0.1, 0.1, 0.05, 0.4); });
      return 0.7;
    },
    elf_wind_shot: v => {   // 시위 + 길게 뻗는 바람 화살
      R.bow_release(v);
      const g = v.gain(0); const bp = v.filter('bandpass', 3000, 2, g); bp.frequency.exponentialRampToValueAtTime(700, v.t + 0.7);
      v.noise('white', bp, 0.8); env(g.gain, v.t + 0.02, 0.02, 0.5, 0.7);
      return 0.8;
    },
    elf_volley: v => {   // 도약 + 세 발 연속 시위
      whoosh(v, {}, 300, 1400, 0.3, 1.0);
      for (let i = 0; i < 3; i++) { const p = v.gain(0.8); R.bow_release(V(v.ctx, p, v.t + 0.32 + i * 0.07)); }
      return 0.8;
    },
    elf_whirl: v => {   // 잎을 휘감는 회오리
      for (let i = 0; i < 4; i++) { const p = v.gain(1); whoosh(V(v.ctx, p, v.t + i * 0.15), {}, 350 + i * 120, 1800 + i * 200, 0.35, 1.0); }
      for (let i = 0; i < 14; i++) crack(v, rnd(2500, 6000), 4, 0.03, 0.15, 'white', v.t + rnd(0, 0.8));
      return 0.95;
    },
    elf_fairy: v => {   // 요정 날갯짓 반짝임 + 맑은 화음
      [784, 988, 1175, 1568].forEach((f, i) => { const g = v.gain(0); v.osc('triangle', f, g, 1.8); env(g.gain, v.t + i * 0.12, 0.02, 0.2, 1.4); });
      for (let i = 0; i < 18; i++) { const g = v.gain(0); const t = v.t + rnd(0, 1.4); const o = v.osc('sine', rnd(2500, 5000), g, 0.1); o.frequency.setValueAtTime(rnd(2500, 5000), t); env(g.gain, t, 0.002, 0.05, 0.08); }
      return 1.8;
    },

    // 마법사 스킬 ─────────────────────────
    mage_charge: v => {
      const g = v.gain(0); [330, 495].forEach(f => { const o = v.osc('sawtooth', f, v.filter('lowpass', 1200, 4, g), 0.6); o.frequency.exponentialRampToValueAtTime(f * 2, v.t + 0.55); });
      g.gain.setValueAtTime(0.0001, v.t); g.gain.exponentialRampToValueAtTime(0.12, v.t + 0.5); g.gain.exponentialRampToValueAtTime(0.0001, v.t + 0.6);
      return 0.6;
    },
    mage_bolt: v => {   // 휙 날아가는 마력 + 보랏빛 폭발
      const g = v.gain(0); const o = v.osc('square', 1600, v.filter('bandpass', 2000, 3, g), 0.3); o.frequency.exponentialRampToValueAtTime(400, v.t + 0.25); env(g.gain, v.t, 0.005, 0.2, 0.25);
      const p = v.gain(1); R.magic_hit(V(v.ctx, p, v.t + 0.22));
      return 1.1;
    },
    mage_ice: v => {   // 얼음이 솟으며 쩍쩍 갈라짐
      thud(v, 90, 40, 0.4, 0.7);
      for (let i = 0; i < 10; i++) { const t = v.t + 0.05 + i * rnd(0.03, 0.07); clank(V(v.ctx, v.gain(1), t), rnd(1800, 3600), 0.35, 0.06, [1, 2.3, 3.7]); crack(v, rnd(3000, 6000), 2, 0.04, 0.3, 'white', t); }
      const g = v.gain(0); v.noise('white', v.filter('highpass', 5000, 0.7, g), 1.0); env(g.gain, v.t, 0.01, 0.15, 0.9);
      return 1.0;
    },
    mage_meteor_fall: v => {   // 하늘에서 떨어지는 굉음
      const g = v.gain(0); const lp = v.filter('lowpass', 300, 2, g); lp.frequency.exponentialRampToValueAtTime(2500, v.t + 0.8);
      v.noise('brown', lp, 0.9); g.gain.setValueAtTime(0.0001, v.t); g.gain.exponentialRampToValueAtTime(1.6, v.t + 0.8); g.gain.exponentialRampToValueAtTime(0.0001, v.t + 0.9);
      return 0.9;
    },
    mage_meteor_hit: v => { thud(v, 55, 20, 1.2, 0.6); crack(v, 200, 0.5, 1.0, 0.55, 'brown'); R.hit_blunt(v); for (let i = 0; i < 8; i++) crack(v, rnd(800, 2500), 2, 0.06, 0.3, 'pink', v.t + 0.1 + i * rnd(0.05, 0.1)); return 1.3; },
    mage_pillar: v => {   // 솟구치는 마나: 상승음 + 합창
      const g = v.gain(0); [220, 277, 330].forEach(f => { const o = v.osc('sawtooth', f, v.filter('lowpass', 1500, 1, g), 1.8); o.frequency.exponentialRampToValueAtTime(f * 2, v.t + 1.6); });
      g.gain.setValueAtTime(0.0001, v.t); g.gain.linearRampToValueAtTime(0.06, v.t + 0.4); g.gain.exponentialRampToValueAtTime(0.0001, v.t + 1.8);
      voice(v, { f0: 440, f1: 660, dur: 1.6, vowel: 'a', vowel2: 'o', level: 0.12, rough: 0, vib: 5, breath: 0.05, curve: 'flat' });
      return 1.8;
    },

    // 보스 스킬 ─────────────────────────
    boss_darkslash: v => {
      voice(v, { f0: 80, f1: 55, dur: 0.6, vowel: 'a', vowel2: 'o', level: 0.5, rough: 0.9, vib: 3 });
      whoosh(V(v.ctx, v.gain(1), v.t + 0.25), {}, 200, 1600, 0.5, 2.2);
      const g = v.gain(0); const lp = v.filter('lowpass', 1800, 2, g); lp.frequency.exponentialRampToValueAtTime(200, v.t + 1.0);
      v.noise('brown', lp, 1.0); env(g.gain, v.t + 0.3, 0.02, 1.2, 0.8);
      return 1.1;
    },
    boss_hellfire_charge: v => {
      voice(v, { f0: 65, f1: 90, dur: 1.0, vowel: 'o', vowel2: 'a', level: 0.6, rough: 0.9, vib: 2.5, curve: 'rise' });
      const g = v.gain(0); const lp = v.filter('lowpass', 200, 3, g); lp.frequency.exponentialRampToValueAtTime(1200, v.t + 1.0);
      v.noise('brown', lp, 1.1); g.gain.setValueAtTime(0.0001, v.t); g.gain.exponentialRampToValueAtTime(1.0, v.t + 1.0); g.gain.exponentialRampToValueAtTime(0.0001, v.t + 1.1);
      return 1.1;
    },
    boss_hellfire: v => {
      thud(v, 45, 18, 1.4, 0.7); crack(v, 180, 0.5, 1.4, 0.7, 'brown');
      R.campfire_burst(v);
      return 1.6;
    },
    campfire_burst: v => {
      const g = v.gain(0); const bp = v.filter('bandpass', 900, 0.6, g); bp.frequency.exponentialRampToValueAtTime(300, v.t + 1.3);
      v.noise('pink', bp, 1.4); env(g.gain, v.t, 0.02, 1.4, 1.3);
      for (let i = 0; i < 20; i++) crack(v, rnd(1500, 5000), rnd(1, 4), rnd(0.01, 0.04), rnd(0.1, 0.4), 'white', v.t + rnd(0, 1.2));
      return 1.4;
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
    skill_wind: [[1, 'elf_charge'], [5, 'elf_wind_shot']],
    skill_volley: [[1, 'elf_volley']],
    skill_whirl: [[1, 'elf_whirl']],
    skill_fairy: [[1, 'elf_fairy']],
    skill_bolt: [[1, 'mage_charge'], [4, 'mage_bolt']],
    skill_ice: [[1, 'mage_charge'], [3, 'mage_ice']],
    skill_meteor: [[2, 'mage_meteor_fall'], [5, 'mage_meteor_hit']],
    skill_pillar: [[1, 'mage_pillar']],
    skill_darkslash: [[1, 'boss_darkslash']],
    skill_hellfire: [[1, 'boss_hellfire_charge'], [5, 'boss_hellfire']],
  };

  // 발소리 자동 매핑용: 동작별 사운드
  const ACTOR_SFX = {
    knight: { swing: 'swing_sword', hit: 'hit_sword', skills: SKILL_CUES },
    lord: { swing: 'swing_sword', hit: 'hit_sword', skills: SKILL_CUES },
    elf: { swing: 'bow_release', hit: 'arrow_hit', skills: SKILL_CUES },
    mage: { swing: 'magic_cast', hit: 'magic_hit', skills: SKILL_CUES },
    orc: { swing: 'swing_heavy', hit: 'hit_blunt', attack: 'orc_attack', hurt: 'orc_hurt', death: 'orc_death' },
    skeleton: { swing: 'swing_sword', hit: 'hit_sword', attack: 'skeleton_attack', hurt: 'skeleton_hurt', death: 'skeleton_death' },
    wolf: { hit: 'hit_flesh', attack: 'wolf_attack', hurt: 'wolf_hurt', death: 'wolf_death' },
    goblin: { swing: 'swing_sword', hit: 'hit_flesh', attack: 'orc_hurt', hurt: 'orc_hurt', death: 'orc_death' },
    skeleton_archer: { swing: 'bow_release', hit: 'arrow_hit', attack: 'skeleton_attack', hurt: 'skeleton_hurt', death: 'skeleton_death' },
    spider: { hit: 'hit_flesh', attack: 'spider_attack', hurt: 'spider_hurt', death: 'spider_death' },
    ooze: { hit: 'hit_flesh', attack: 'ooze_attack', hurt: 'ooze_hurt', death: 'ooze_death' },
    boss: { swing: 'swing_heavy', hit: 'critical', attack: 'boss_attack', hurt: 'boss_hurt', death: 'boss_death', skills: SKILL_CUES },
  };

  const SOUNDS = [
    ['전투', 'swing_sword', '칼 휘두름'], ['전투', 'swing_heavy', '무거운 휘두름'], ['전투', 'hit_sword', '칼 적중(쇳소리)'],
    ['전투', 'hit_blunt', '둔기 적중'], ['전투', 'hit_flesh', '물어뜯기·살 타격'], ['전투', 'bow_release', '활 시위'],
    ['전투', 'arrow_hit', '화살 꽂힘'], ['전투', 'magic_cast', '마법 시전'], ['전투', 'magic_hit', '마법 폭발'],
    ['전투', 'critical', '치명타'], ['전투', 'block', '방패 막기'],
    ['스킬', 'skill_spin', '회전 베기'], ['스킬', 'skill_slam_charge', '대지 강타 · 모으기'], ['스킬', 'skill_slam', '대지 강타 · 폭발'],
    ['스킬', 'skill_guard', '수호 결계'], ['스킬', 'skill_bless', '성스러운 축복'],
    ['요정 스킬', 'elf_charge', '바람 모으기'], ['요정 스킬', 'elf_wind_shot', '바람 화살'], ['요정 스킬', 'elf_volley', '도약 연사'],
    ['요정 스킬', 'elf_whirl', '잎 회오리'], ['요정 스킬', 'elf_fairy', '요정의 축복'],
    ['마법사 스킬', 'mage_charge', '마력 모으기'], ['마법사 스킬', 'mage_bolt', '마력 화살'], ['마법사 스킬', 'mage_ice', '얼음 결정 폭발'],
    ['마법사 스킬', 'mage_meteor_fall', '운석 · 낙하'], ['마법사 스킬', 'mage_meteor_hit', '운석 · 충돌'], ['마법사 스킬', 'mage_pillar', '마나 기둥'],
    ['몰락한 왕', 'boss_darkslash', '암흑 베기'], ['몰락한 왕', 'boss_hellfire_charge', '지옥불 · 포효'], ['몰락한 왕', 'boss_hellfire', '지옥불 · 폭발'],
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
  // ═════════════════════════ 고품질 합성 2판: 변형(A/B/C) · 악기 · 배경음악 ═════════════════════════
  const MIDI = n => 440 * Math.pow(2, (n - 69) / 12);

  // ── 작은 도구 ──
  const at = (v, dt) => V(v.ctx, v.out, v.t + dt);
  function ping(v, f, dur, lvl, t = v.t, type = 'sine') { const g = v.gain(0); const o = v.osc(type, f, g, dur + (t - v.t)); o.frequency.setValueAtTime(f, t); env(g.gain, t, 0.002, lvl, dur); return dur; }
  function sweep(v, type, f0, f1, dur, lvl, t = v.t, lp = 0) { const g = v.gain(0); const d = lp ? v.filter('lowpass', lp, 1, g) : g; const o = v.osc(type, f0, d, dur + (t - v.t)); o.frequency.setValueAtTime(f0, t); o.frequency.exponentialRampToValueAtTime(f1, t + dur); env(g.gain, t, 0.005, lvl, dur); return dur; }
  function swell(v, color, f0, f1, dur, lvl, t = v.t) { const g = v.gain(0); const bp = v.filter('bandpass', f0, 1, g); bp.frequency.setValueAtTime(f0, t); bp.frequency.exponentialRampToValueAtTime(f1, t + dur); v.noise(color, bp, dur + (t - v.t)); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(lvl, t + dur); g.gain.linearRampToValueAtTime(0, t + dur + 0.02); return dur; }
  function tear(v, f0, f1, dur, lvl, t = v.t, color = 'white') { const g = v.gain(0); const bp = v.filter('bandpass', f0, 2, g); bp.frequency.setValueAtTime(f0, t); bp.frequency.exponentialRampToValueAtTime(f1, t + dur); v.noise(color, bp, dur + (t - v.t)); env(g.gain, t, 0.003, lvl, dur); return dur; }
  function grit(v, f, dur, lvl, amt = 40, t = v.t) { const ctx = v.ctx; const g = v.gain(0); const d = shaper(ctx, amt); d.connect(g); const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = f; bp.Q.value = 1; bp.connect(d); v.noise('brown', bp, dur + (t - v.t)); env(g.gain, t, 0.002, lvl, dur); return dur; }
  function vib(v, param, rate, depth, t, dur) { const l = v.ctx.createOscillator(); l.frequency.value = rate; const g = v.ctx.createGain(); g.gain.value = depth; l.connect(g); g.connect(param); l.start(t); l.stop(t + dur + 0.1); }

  // ── 악기(효과음·음악 공용). 모두 (v, t, f, dur, lvl) ──
  const INST = {
    strings(v, t, f, dur, l) {
      const g = v.gain(0), lp = v.filter('lowpass', Math.min(f * 4, 3200), 0.7, g);
      [-9, 0, 9].forEach(dt => { const o = v.osc('sawtooth', f, lp, dur + 1 + (t - v.t), dt); vib(v, o.frequency, 5.2, f * 0.004, t, dur + 1); });
      g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(l, t + Math.min(0.45, dur * 0.35)); g.gain.setValueAtTime(l, t + dur); g.gain.linearRampToValueAtTime(0.0001, t + dur + 0.8);
    },
    stac(v, t, f, dur, l) {   // 짧게 끊는 현(오스티나토)
      const g = v.gain(0), lp = v.filter('lowpass', Math.min(f * 5, 3500), 0.8, g);
      [-7, 7].forEach(dt => v.osc('sawtooth', f, lp, dur + 0.2 + (t - v.t), dt));
      env(g.gain, t, 0.012, l, Math.max(0.08, dur * 0.9));
    },
    violin(v, t, f, dur, l) {
      const g = v.gain(0), lp = v.filter('lowpass', 3000, 1.2, g), hp = v.filter('highpass', 220, 0.7, lp);
      const o = v.osc('sawtooth', f, hp, dur + 0.5 + (t - v.t)); o.frequency.setValueAtTime(f * 0.985, t); o.frequency.linearRampToValueAtTime(f, t + 0.06);
      vib(v, o.frequency, 5.6, f * 0.007, t + 0.15, dur);
      g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(l, t + 0.09); g.gain.setValueAtTime(l * 0.85, t + dur); g.gain.linearRampToValueAtTime(0.0001, t + dur + 0.35);
    },
    flute(v, t, f, dur, l) {
      const g = v.gain(0); const o = v.osc('sine', f, g, dur + 0.4 + (t - v.t)); vib(v, o.frequency, 5, f * 0.008, t + 0.12, dur);
      const g2 = v.gain(l * 0.12, g); v.osc('triangle', f * 2, g2, dur + 0.4 + (t - v.t));
      const ng = v.gain(0, g), bp = v.filter('bandpass', f * 2, 2, ng); v.noise('pink', bp, dur + 0.4 + (t - v.t)); env(ng.gain, t, 0.03, 0.9, dur * 0.5);
      g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(l, t + 0.06); g.gain.setValueAtTime(l * 0.9, t + dur); g.gain.linearRampToValueAtTime(0.0001, t + dur + 0.2);
    },
    choir(v, t, f, dur, l, vw = 'a') { voice(v, { f0: f, f1: f, dur: dur + 0.4, vowel: vw, vowel2: vw === 'a' ? 'o' : vw, level: l, rough: 0, vib: 5, breath: 0.05, curve: 'flat', t }); },
    choirU(v, t, f, dur, l) { INST.choir(v, t, f, dur, l, 'u'); },
    brass(v, t, f, dur, l) {
      const g = v.gain(0), lp = v.filter('lowpass', f * 1.2, 1.5, g);
      lp.frequency.setValueAtTime(f * 1.2, t); lp.frequency.exponentialRampToValueAtTime(Math.min(f * 7, 4200), t + 0.12); lp.frequency.exponentialRampToValueAtTime(Math.min(f * 3, 2400), t + 0.4 + dur * 0.3);
      [-6, 6].forEach(dt => v.osc('sawtooth', f, lp, dur + 0.4 + (t - v.t), dt));
      g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(l, t + 0.05); g.gain.setValueAtTime(l * 0.8, t + dur); g.gain.linearRampToValueAtTime(0.0001, t + dur + 0.25);
    },
    harp(v, t, f, dur, l) {
      const g = v.gain(0), lp = v.filter('lowpass', Math.min(f * 6, 6000), 0.7, g); const d = Math.min(2.4, 0.8 + dur);
      v.osc('triangle', f, lp, d + (t - v.t)); const g2 = v.gain(0.3, lp); v.osc('sine', f * 2, g2, d + (t - v.t));
      env(g.gain, t, 0.002, l, d);
    },
    lute(v, t, f, dur, l) {
      const g = v.gain(0), lp = v.filter('lowpass', 3600, 2.2, g);
      lp.frequency.setValueAtTime(3600, t); lp.frequency.exponentialRampToValueAtTime(650, t + 0.3);
      v.osc('sawtooth', f, lp, 1 + (t - v.t)); const g2 = v.gain(0.35, lp); v.osc('square', f * 0.5, g2, 1 + (t - v.t), 4);
      env(g.gain, t, 0.002, l, Math.min(0.95, 0.4 + dur));
    },
    pluckbass(v, t, f, dur, l) { const g = v.gain(0); v.osc('triangle', f, g, 1 + (t - v.t)); const g2 = v.gain(0.5, g); v.osc('sine', f / 2, g2, 1 + (t - v.t)); env(g.gain, t, 0.004, l, Math.min(0.9, 0.3 + dur)); },
    cello(v, t, f, dur, l) {
      const g = v.gain(0), lp = v.filter('lowpass', 760, 0.8, g); v.osc('sawtooth', f, lp, dur + 0.3 + (t - v.t)); v.osc('sawtooth', f, lp, dur + 0.3 + (t - v.t), 8);
      g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(l, t + 0.04); g.gain.setValueAtTime(l * 0.7, t + Math.max(0.05, dur * 0.85)); g.gain.linearRampToValueAtTime(0.0001, t + dur + 0.12);
    },
    bell(v, t, f, dur, l) { [1, 2.76, 5.4, 8.93].forEach((p, i) => ping(v, f * p, Math.max(0.3, dur * [1, 0.6, 0.4, 0.25][i]), l * [1, 0.45, 0.22, 0.1][i], t)); },
    organ(v, t, f, dur, l) {
      const g = v.gain(0); [[1, 1], [2, 0.4], [3, 0.18]].forEach(([h, a]) => { const gg = v.gain(a, g); v.osc('sine', f * h, gg, dur + 1.2 + (t - v.t), h * 3); });
      g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(l, t + 0.6); g.gain.setValueAtTime(l, t + dur); g.gain.linearRampToValueAtTime(0.0001, t + dur + 1.0);
    },
    drone(v, t, f, dur, l) {
      const g = v.gain(0), lp = v.filter('lowpass', 380, 1.4, g); v.osc('sawtooth', f, lp, dur + 1.5 + (t - v.t)); v.osc('sawtooth', f * 1.004, lp, dur + 1.5 + (t - v.t)); v.osc('sine', f / 2, g, dur + 1.5 + (t - v.t));
      g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(l, t + 1.2); g.gain.setValueAtTime(l, t + dur); g.gain.linearRampToValueAtTime(0.0001, t + dur + 1.4);
    },
  };
  const DRUM = {
    timpani(v, t, l, f = 73) { thud(v, f * 1.3, f, 1.2, l, t); const g = v.gain(0); v.noise('brown', v.filter('lowpass', 300, 1, g), 0.4 + (t - v.t)); env(g.gain, t, 0.002, l * 0.4, 0.3); },
    frame(v, t, l) { thud(v, 150, 90, 0.18, l, t); crack(v, 900, 0.9, 0.06, l * 0.5, 'pink', t); },
    shaker(v, t, l) { const g = v.gain(0); v.noise('white', v.filter('highpass', 6500, 0.7, g), 0.08 + (t - v.t)); env(g.gain, t, 0.012, l, 0.05); },
    tamb(v, t, l) { DRUM.shaker(v, t, l); ping(v, 5200, 0.12, l * 0.08, t); ping(v, 7300, 0.1, l * 0.06, t); },
    war(v, t, l) { thud(v, 72, 38, 0.55, l, t); const g = v.gain(0); v.noise('brown', v.filter('lowpass', 220, 1, g), 0.35 + (t - v.t)); env(g.gain, t, 0.002, l * 0.6, 0.3); },
    taiko(v, t, l) { thud(v, 95, 44, 0.65, l, t); grit(v, 280, 0.12, l * 0.45, 20, t); },
    snare(v, t, l) { crack(v, 2400, 0.8, 0.14, l, 'white', t); thud(v, 200, 150, 0.06, l * 0.5, t); },
    tom(v, t, l) { thud(v, 130, 80, 0.3, l, t); },
    anvil(v, t, l) { const vv = V(v.ctx, v.out, t); clank(vv, 1250, 0.9, l, [1, 2.76, 5.4, 8.93]); },
    cymbal(v, t, l, dur = 1.6) { const g = v.gain(0); v.noise('white', v.filter('highpass', 5000, 0.7, g), dur + 0.1 + (t - v.t)); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(l, t + dur); g.gain.linearRampToValueAtTime(0, t + dur + 0.08); },
  };

  // ── 효과음 변형 B·C (A는 위의 기본 레시피) ──
  const VAR = {
    swing_sword: {
      B: v => { const h = v.filter('highpass', 1800, 0.7, v.gain(1)); whoosh(V(v.ctx, h, v.t), {}, 1500, 6000, 0.15, 1.6); whoosh(v, {}, 900, 3000, 0.16, 0.7); ping(v, 3150, 0.25, 0.015, v.t + 0.08); return 0.3; },
      C: v => { whoosh(v, {}, 380, 1500, 0.27, 1.9); tear(v, 200, 500, 0.2, 0.4, v.t + 0.02, 'brown'); return 0.3; },
    },
    swing_heavy: {
      B: v => { whoosh(v, {}, 160, 900, 0.42, 2.2); thud(v, 70, 40, 0.4, 0.25, v.t + 0.1); return 0.45; },
      C: v => { whoosh(v, {}, 300, 700, 0.2, 0.8); whoosh(at(v, 0.12), {}, 250, 1400, 0.36, 2.0); tear(v, 120, 300, 0.4, 0.5, v.t + 0.12, 'brown'); return 0.5; },
    },
    hit_sword: {
      B: v => { clank(v, 620 * rnd(0.97, 1.03), 0.9, 0.22, [1, 2.32, 4.25, 6.63, 9.38, 12.1]); crack(v, 5000, 0.9, 0.05, 0.6); crack(v, 2200, 2, 0.03, 0.4); thud(v, 180, 80, 0.12, 0.45); ping(v, 3700, 0.6, 0.02); return 0.9; },
      C: v => { tear(v, 4200, 900, 0.12, 0.9); thud(v, 130, 55, 0.2, 0.7); crack(v, 700, 1.2, 0.12, 0.5, 'pink'); clank(v, 880, 0.35, 0.08, [1, 2.7, 5.1]); return 0.4; },
    },
    hit_blunt: {
      B: v => { thud(v, 75, 28, 0.45, 1.0); grit(v, 400, 0.18, 0.5); crack(v, 2500, 1, 0.04, 0.25); return 0.45; },
      C: v => { [0, 0.012].forEach((dt, i) => { const g = v.gain(0); const bp = v.filter('bandpass', 330 * (1 + i * 0.4), 14, g); v.noise('white', bp, 0.25); env(g.gain, v.t + dt, 0.001, 3.2, 0.18); }); thud(v, 140, 70, 0.14, 0.6); return 0.3; },
    },
    hit_flesh: {
      B: v => { thud(v, 100, 45, 0.2, 0.8); const g = v.gain(0); const bp = v.filter('bandpass', 700, 3, g); bp.frequency.exponentialRampToValueAtTime(300, v.t + 0.2); v.noise('pink', bp, 0.25); env(g.gain, v.t, 0.004, 1.6, 0.22); return 0.28; },
      C: v => { thud(v, 150, 60, 0.14, 0.7); clicks(v, 4, 0.05, 1600, 1.2, 6); crack(v, 1100, 1.4, 0.07, 0.5, 'pink'); return 0.2; },
    },
    bow_release: {
      B: v => { const g = v.gain(0); const lp = v.filter('lowpass', 3000, 4, g); lp.frequency.exponentialRampToValueAtTime(300, v.t + 0.35); const o = v.osc('sawtooth', 260, lp, 0.4); o.frequency.exponentialRampToValueAtTime(205, v.t + 0.08); v.osc('square', 115, lp, 0.4); env(g.gain, v.t, 0.001, 0.3, 0.36); whoosh(v, {}, 2000, 5000, 0.2, 0.15); crack(v, 3000, 3, 0.02, 0.4); return 0.42; },
      C: v => { crack(v, 2600, 6, 0.015, 0.9); thud(v, 240, 120, 0.07, 0.5); whoosh(v, {}, 1200, 3500, 0.18, 0.25); return 0.25; },
    },
    arrow_hit: {
      B: v => { crack(v, 3000, 2, 0.02, 0.6); const g = v.gain(0); const bp = v.filter('bandpass', 230, 10, g); v.noise('white', bp, 0.25); env(g.gain, v.t, 0.001, 3.0, 0.22); thud(v, 160, 90, 0.1, 0.4); return 0.28; },
      C: v => { ping(v, 2400, 0.25, 0.12); ping(v, 3700, 0.18, 0.06); thud(v, 130, 70, 0.09, 0.45); crack(v, 1500, 2, 0.04, 0.3, 'pink'); return 0.3; },
    },
    magic_cast: {
      B: v => { const g = v.gain(0); const lp = v.filter('lowpass', 300, 6, g); lp.frequency.exponentialRampToValueAtTime(2200, v.t + 0.7); [110, 165, 220.5].forEach(f => { const o = v.osc('sawtooth', f, lp, 0.95, rnd(-10, 10)); o.frequency.exponentialRampToValueAtTime(f * 1.5, v.t + 0.8); }); g.gain.setValueAtTime(0.0001, v.t); g.gain.exponentialRampToValueAtTime(0.12, v.t + 0.6); g.gain.exponentialRampToValueAtTime(0.0001, v.t + 0.95); swell(v, 'pink', 600, 3000, 0.7, 0.25); return 1.0; },
      C: v => { [1046, 1318, 1568, 2093, 2637].forEach((f, i) => { ping(v, f, 0.6, 0.07, v.t + i * 0.07, 'triangle'); ping(v, f * 2.01, 0.3, 0.015, v.t + i * 0.07); }); swell(v, 'white', 3000, 8000, 0.4, 0.06); return 1.0; },
    },
    magic_hit: {
      B: v => { thud(v, 60, 24, 0.7, 0.9); const g = v.gain(0); const lp = v.filter('lowpass', 2500, 0.8, g); lp.frequency.exponentialRampToValueAtTime(150, v.t + 0.9); v.noise('brown', lp, 1.0); env(g.gain, v.t, 0.004, 1.4, 0.9); for (let i = 0; i < 10; i++) ping(v, rnd(2000, 5000), 0.15, 0.03, v.t + 0.05 + rnd(0, 0.6)); return 1.0; },
      C: v => { const g = v.gain(0); const bp = v.filter('bandpass', 1800, 2, g); const o = v.osc('square', 90, bp, 0.5); vib(v, o.frequency, 37, 600, v.t, 0.5); env(g.gain, v.t, 0.002, 0.5, 0.45); for (let i = 0; i < 12; i++) crack(v, rnd(2500, 7000), 3, 0.02, 0.35, 'white', v.t + rnd(0, 0.4)); thud(v, 90, 40, 0.3, 0.5); return 0.6; },
    },
    critical: {
      B: v => { swell(v, 'pink', 400, 4000, 0.14, 0.5); const h = at(v, 0.14); thud(h, 65, 22, 0.7, 1.0); clank(h, 540, 1.0, 0.22, [1, 2.32, 4.25, 6.63, 9.38]); crack(h, 4000, 0.8, 0.08, 0.7); crack(h, 300, 0.6, 0.5, 0.6, 'brown'); return 1.2; },
      C: v => { tear(v, 6000, 1500, 0.1, 0.8); clank(v, 1568, 1.4, 0.12, [1, 2.0, 3.01, 4.2]); ping(v, 3136, 1.0, 0.05); thud(v, 90, 40, 0.3, 0.6); return 1.4; },
    },
    block: {
      B: v => { thud(v, 130, 70, 0.15, 0.9); const g = v.gain(0); const bp = v.filter('bandpass', 420, 6, g); v.noise('white', bp, 0.2); env(g.gain, v.t, 0.001, 1.5, 0.15); crack(v, 1800, 1.5, 0.03, 0.3); return 0.25; },
      C: v => { [880, 1320, 1980].forEach((f, i) => ping(v, f, 0.6, 0.08 / (i + 1))); const g = v.gain(0); const o = v.osc('sine', 440, g, 0.5); vib(v, o.frequency, 18, 60, v.t, 0.5); env(g.gain, v.t, 0.005, 0.08, 0.45); crack(v, 3000, 1, 0.04, 0.3); return 0.6; },
    },
    level_up: {
      B: v => { [[0, 0.15, [55, 59, 62]], [0.18, 0.15, [55, 59, 62]], [0.36, 0.15, [57, 60, 64]], [0.54, 1.1, [59, 62, 67, 71]]].forEach(([dt, d, ns]) => ns.forEach(n => INST.brass(v, v.t + dt, MIDI(n), d, 0.06))); DRUM.timpani(v, v.t, 0.3, 98); DRUM.timpani(v, v.t + 0.54, 0.55, 98); return 1.9; },
      C: v => { [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24, 26].forEach((st, i) => ping(v, MIDI(67 + st), 0.9, 0.05, v.t + i * 0.045, 'triangle')); [67, 71, 74].forEach(n => INST.choir(v, v.t + 0.4, MIDI(n), 1.2, 0.07)); return 2.1; },
    },
    enchant_ok: {
      B: v => { [72, 76, 79, 84].forEach((n, i) => INST.bell(v, v.t + i * 0.08, MIDI(n), 1.6, 0.06)); INST.choir(v, v.t + 0.1, MIDI(72), 1.1, 0.08); swell(v, 'white', 2000, 9000, 0.3, 0.05); return 1.7; },
      C: v => { [64, 68, 71, 76, 80, 83].forEach((n, i) => INST.bell(v, v.t + i * 0.06, MIDI(n), 1.0, 0.05)); for (let i = 0; i < 20; i++) ping(v, rnd(3000, 7000), 0.1, 0.025, v.t + 0.2 + rnd(0, 1.0)); return 1.5; },
    },
    enchant_fail: {
      B: v => { for (let i = 0; i < 18; i++) clank(at(v, rnd(0, 0.25)), rnd(2500, 6000), 0.3, 0.05, [1, 2.3, 3.9]); tear(v, 8000, 2000, 0.4, 0.6); thud(v, 120, 50, 0.2, 0.5); return 0.8; },
      C: v => { sweep(v, 'sawtooth', 300, 50, 1.0, 0.25, v.t, 800); thud(v, 80, 30, 0.5, 0.8); const g = v.gain(0); v.noise('white', v.filter('highpass', 4000, 0.7, g), 1.2); env(g.gain, v.t + 0.1, 0.05, 0.2, 1.0); return 1.2; },
    },
  };

  // 변형별 음량 보정(오프라인 측정으로 기본형과 비슷한 크기로 맞춤)
  const VGAIN = { 'magic_cast:B': 2.2, 'magic_cast:C': 3.5, 'block:C': 2.6, 'enchant_ok:C': 1.8, 'level_up:B': 0.55, 'critical:B': 0.75, 'hit_blunt:B': 0.75, 'magic_hit:B': 0.65, 'enchant_fail:C': 0.6, 'swing_sword:A': 1.4 };
  const gainTo = (ctx, dest, k) => { const g = ctx.createGain(); g.gain.value = k; g.connect(dest); return g; };
  // ── 묶음 변형: 몬스터 목소리·스킬 묶음·발소리는 음높이·포먼트·거칠기 + 추가 레이어로 바꾼다 ──
  const subBoom = (v, d) => { thud(v, 52, 26, Math.min(1.2, 0.5 + d * 0.4), 0.45); const g = v.gain(0); v.noise('brown', v.filter('lowpass', 260, 1, g), d + 0.3); env(g.gain, v.t, 0.01, 0.35, d + 0.2); };
  const shimmer = (v, d) => { for (let i = 0; i < 10; i++) ping(v, rnd(2600, 6400), 0.18, 0.025, v.t + rnd(0, d)); swell(v, 'white', 4000, 9000, Math.min(0.5, d), 0.05); };
  const ghost = (v, d) => voice(v, { f0: 520, f1: 380, dur: Math.max(0.5, d), vowel: 'u', vowel2: 'o', level: 0.06, rough: 0, vib: 7, breath: 0.4, curve: 'flat' });
  const chain = (v) => { for (let i = 0; i < 3; i++) ping(v, rnd(3800, 5600), 0.08, 0.02, v.t + rnd(0, 0.05)); };
  const GROUPS = {
    mon_orc:      { label: '오크·고블린 목소리', names: ['orc_attack', 'orc_hurt', 'orc_death'], B: { name: '거대 오크', pitch: 0.78, formant: 0.82, rough: 0.15, layer: (v, d, n) => n === 'orc_attack' && thud(v, 80, 45, 0.3, 0.35) }, C: { name: '날쌘 고블린', pitch: 1.4, formant: 1.25, rough: -0.15 } },
    mon_skeleton: { label: '해골 소리', names: ['skeleton_attack', 'skeleton_hurt', 'skeleton_death'], B: { name: '무거운 뼈', pitch: 0.72 }, C: { name: '망령 해골', pitch: 1.12, layer: ghost } },
    mon_wolf:     { label: '다이어울프 목소리', names: ['wolf_attack', 'wolf_hurt', 'wolf_death', 'wolf_howl'], B: { name: '늑대 우두머리', pitch: 0.8, formant: 0.85, rough: 0.1 }, C: { name: '굶주린 늑대', pitch: 1.15, layer: (v, d) => crack(v, 1800, 1, d * 0.6, 0.12, 'pink') } },
    mon_spider:   { label: '거대 거미 소리', names: ['spider_attack', 'spider_hurt', 'spider_death'], B: { name: '어미 거미', pitch: 0.68 }, C: { name: '새끼 거미 떼', pitch: 1.35, layer: (v, d) => clicks(v, 10, d, 4500, 0.4, 10) } },
    mon_ooze:     { label: '늪 점액 소리', names: ['ooze_attack', 'ooze_hurt', 'ooze_death'], B: { name: '거대 점액', pitch: 0.68 }, C: { name: '산성 점액', pitch: 1.4, layer: (v, d) => { const g = v.gain(0); v.noise('white', v.filter('highpass', 5000, 0.7, g), d); env(g.gain, v.t, 0.02, 0.1, d); } } },
    mon_boss:     { label: '몰락한 왕 목소리', names: ['boss_attack', 'boss_hurt', 'boss_death'], B: { name: '심연의 군주', pitch: 0.8, formant: 0.85, rough: 0.1, layer: subBoom }, C: { name: '망령왕', pitch: 1.06, layer: (v, d) => [0, 1, 6].forEach(st => voice(v, { f0: 196 * Math.pow(2, st / 12), f1: 185 * Math.pow(2, st / 12), dur: Math.max(0.6, d), vowel: 'o', level: 0.05, rough: 0, vib: 4, breath: 0.2, curve: 'flat' })) } },
    pack_knight:  { label: '기사 스킬 묶음', names: ['skill_spin', 'skill_slam_charge', 'skill_slam', 'skill_guard', 'skill_bless'], B: { name: '묵직한 강철', pitch: 0.88, layer: subBoom }, C: { name: '찬란한 성기사', pitch: 1.1, layer: shimmer } },
    pack_elf:     { label: '요정 스킬 묶음', names: ['elf_charge', 'elf_wind_shot', 'elf_volley', 'elf_whirl', 'elf_fairy'], B: { name: '폭풍 사냥꾼', pitch: 0.88, layer: (v, d) => swell(v, 'pink', 300, 1200, Math.max(0.3, d * 0.8), 0.5) }, C: { name: '숲의 정령', pitch: 1.12, layer: shimmer } },
    pack_mage:    { label: '마법사 스킬 묶음', names: ['mage_charge', 'mage_bolt', 'mage_ice', 'mage_meteor_fall', 'mage_meteor_hit', 'mage_pillar'], B: { name: '심연 마법', pitch: 0.86, layer: subBoom }, C: { name: '별빛 마법', pitch: 1.1, layer: shimmer } },
    pack_boss:    { label: '몰락한 왕 스킬 묶음', names: ['boss_darkslash', 'boss_hellfire_charge', 'boss_hellfire'], B: { name: '지옥의 굉음', pitch: 0.85, layer: subBoom }, C: { name: '저주의 메아리', pitch: 1.05, layer: ghost } },
    steps:        { label: '발소리', names: ['step_grass', 'step_stone', 'step_swamp'], B: { name: '중갑 발소리', pitch: 0.8, layer: chain }, C: { name: '가벼운 발소리', pitch: 1.25 } },
  };
  GROUPS.mon_orc.A = { name: '기본 오크' }; GROUPS.mon_skeleton.A = { name: '기본 해골' }; GROUPS.mon_wolf.A = { name: '기본 늑대' }; GROUPS.mon_spider.A = { name: '기본 거미' }; GROUPS.mon_ooze.A = { name: '기본 점액' }; GROUPS.mon_boss.A = { name: '기본 왕' };
  for (const k of ['pack_knight', 'pack_elf', 'pack_mage', 'pack_boss']) GROUPS[k].A = { name: '기본' };
  GROUPS.steps.A = { name: '기본 발소리' };
  const GROUP_OF = {}; for (const [g, d] of Object.entries(GROUPS)) d.names.forEach(n => { GROUP_OF[n] = g; });
  // 고르기 화면에 쓸 목록: 레시피 변형(개별) + 묶음 변형
  const VARIANT_SETS = [
    ...[['swing_sword', '칼 휘두름', ['기본', '날카로운 칼바람', '묵직한 칼날']], ['swing_heavy', '무거운 휘두름', ['기본', '깊은 바람', '두 번 감기는 휘두름']],
      ['hit_sword', '칼 적중', ['기본 쇳소리', '강철 충돌', '베어내는 타격']], ['hit_blunt', '둔기 적중', ['기본', '뼈가 울리는 타격', '나무 몽둥이']],
      ['hit_flesh', '살 타격·물기', ['기본', '축축한 타격', '깨무는 소리']], ['bow_release', '활 시위', ['기본', '장궁 울림', '석궁 딸깍']],
      ['arrow_hit', '화살 꽂힘', ['기본', '나무에 박힘', '쇳소리 튕김']], ['magic_cast', '마법 시전', ['기본', '어둠의 상승음', '수정 종소리']],
      ['magic_hit', '마법 폭발', ['기본', '깊은 폭발', '번개']], ['critical', '치명타', ['기본', '빨려드는 강타', '맑은 일격']],
      ['block', '막기', ['기본 쇠방패', '나무 방패', '마법 보호막']], ['level_up', '레벨 업', ['기본 화음', '금관 팡파르', '하프·합창']],
      ['enchant_ok', '강화 성공', ['기본', '종·합창', '반짝이는 종']], ['enchant_fail', '강화 실패', ['기본', '유리 깨짐', '꺼지는 마력']]]
      .map(([id, label, names]) => ({ id, label, kind: 'recipe', sample: [id], names })),
    ...Object.entries(GROUPS).map(([id, g]) => ({ id, label: g.label, kind: 'group', sample: g.names, names: ['A', 'B', 'C'].map(k => g[k].name) })),
  ];

  // ═════════════ 배경음악: 곡 설계(조성·진행·악기 역할) → 결정적 작곡 → 반복 재생 ═════════════
  const SCALES = { minor: [0, 2, 3, 5, 7, 8, 10], harmonic: [0, 2, 3, 5, 7, 8, 11], dorian: [0, 2, 3, 5, 7, 9, 10], major: [0, 2, 4, 5, 7, 9, 11], phrygian: [0, 1, 3, 5, 7, 8, 10], lydian: [0, 2, 4, 6, 7, 9, 11] };
  const RHY = {
    slow: [[4], [2, 2], [3, 1], [2, 1, 1], [1, 1, 2]],
    med: [[1, 1, 2], [2, 1, 1], [1, 1, 1, 1], [1.5, 0.5, 2], [3, 1], [1, 0.5, 0.5, 2]],
    fast: [[0.5, 0.5, 1, 1, 1], [1, 0.5, 0.5, 1, 1], [0.5, 0.5, 0.5, 0.5, 2], [1, 1, 2], [0.5, 0.5, 1, 2]],
    six: [[3, 3], [2, 1, 2, 1], [1, 1, 1, 3], [6], [2, 1, 3], [1, 1, 1, 1, 1, 1]],
  };
  const TRACKS = [
    { id: 'field_a', kind: 'field', name: '어둠의 서곡', desc: '라단조 · 현악 · 합창 · 팀파니 (중후한 오케스트라)', key: 57, mode: 'harmonic', bpm: 60, meter: 4, seed: 11, prog: [0, 5, 3, 4, 0, 5, 3, 4], vol: 0.68,
      layers: [{ t: 'pad', inst: 'strings', oct: 0, lvl: 0.045 }, { t: 'bass', inst: 'cello', oct: -1, lvl: 0.07, pat: [[0, 0, 0.5], [0.5, 0, 0.5], [1, 2, 0.5], [1.5, 0, 0.5], [2, 7, 0.5], [2.5, 2, 0.5], [3, 1, 0.5], [3.5, 2, 0.5]] },
        { t: 'mel', inst: 'choir', oct: 1, lvl: 0.07, rhy: 'slow', form: 'ABAB', from: 4 }, { t: 'drum', d: 'timpani', steps: 'x...', sub: 4, lvl: 0.32, fill: 'x.xx' }] },
    { id: 'field_b', kind: 'field', name: '방랑자의 숲길', desc: '도리아 선법 · 류트 · 플루트 · 프레임 드럼 (중세 민요)', key: 50, mode: 'dorian', bpm: 92, meter: 4, seed: 23, prog: [0, 6, 3, 0, 0, 6, 4, 4], vol: 1.0,
      layers: [{ t: 'arp', inst: 'lute', oct: 0, lvl: 0.06, sub: 8, pat: [0, 2, 1, 2, 3, 2, 1, 2] }, { t: 'bass', inst: 'pluckbass', oct: -1, lvl: 0.12, pat: [[0, 0, 1], [2, 2, 1]] }, { t: 'pad', inst: 'organ', oct: 0, lvl: 0.018 },
        { t: 'mel', inst: 'flute', oct: 2, lvl: 0.055, rhy: 'med', form: 'ABAC', from: 2 }, { t: 'drum', d: 'frame', steps: 'x..x..x.', sub: 8, lvl: 0.35 }, { t: 'drum', d: 'shaker', steps: '.x.x.x.x', sub: 8, lvl: 0.12 }] },
    { id: 'field_c', kind: 'field', name: '새벽 들판', desc: '리디아 선법 · 하프 · 현악 · 종 (잔잔하고 밝은 앰비언트)', key: 60, mode: 'lydian', bpm: 66, meter: 4, seed: 37, prog: [0, 1, 0, 1, 5, 1, 4, 0], vol: 1.08,
      layers: [{ t: 'arp', inst: 'harp', oct: 0, lvl: 0.05, sub: 8, pat: [0, 1, 2, 3, 4, 3, 2, 1] }, { t: 'pad', inst: 'strings', oct: 0, lvl: 0.028 }, { t: 'bass', inst: 'organ', oct: -1, lvl: 0.04, pat: [[0, 0, 4]] },
        { t: 'mel', inst: 'bell', oct: 2, lvl: 0.04, rhy: 'slow', form: 'ABAC', from: 2, rest: 0.35 }] },
    { id: 'town_a', kind: 'town', name: '모닥불 광장', desc: '사장조 6/8 · 류트 · 리코더 · 탬버린 (흥겨운 마을 춤곡)', key: 55, mode: 'major', bpm: 200, meter: 6, seed: 41, prog: [0, 3, 4, 0, 0, 3, 4, 4], vol: 1.02,
      layers: [{ t: 'arp', inst: 'lute', oct: 0, lvl: 0.055, sub: 6, pat: [0, 2, 1, 2, 1, 2] }, { t: 'bass', inst: 'pluckbass', oct: -1, lvl: 0.12, pat: [[0, 0, 2], [3, 2, 2]] }, { t: 'pad', inst: 'organ', oct: 0, lvl: 0.014 },
        { t: 'mel', inst: 'flute', oct: 2, lvl: 0.05, rhy: 'six', form: 'ABAB', from: 2 }, { t: 'drum', d: 'frame', steps: 'x..x..', sub: 6, lvl: 0.32 }, { t: 'drum', d: 'tamb', steps: '...x.x', sub: 6, lvl: 0.14 }] },
    { id: 'town_b', kind: 'town', name: '대장간 골목', desc: '라단조 · 하프 · 피치카토 · 모루 소리 (잊혀진 대장간 테마)', key: 50, mode: 'minor', bpm: 84, meter: 4, seed: 53, prog: [0, 3, 6, 2, 0, 3, 4, 4], vol: 1.3,
      layers: [{ t: 'arp', inst: 'harp', oct: 0, lvl: 0.045, sub: 8, pat: [0, 1, 2, 1, 3, 1, 2, 1] }, { t: 'bass', inst: 'pluckbass', oct: -1, lvl: 0.11, pat: [[0, 0, 1], [1.5, 2, 0.5], [2, 1, 1]] }, { t: 'pad', inst: 'organ', oct: 0, lvl: 0.02 },
        { t: 'mel', inst: 'flute', oct: 2, lvl: 0.045, rhy: 'med', form: 'ABAC', from: 4, rest: 0.2 }, { t: 'drum', d: 'anvil', steps: '...x', sub: 4, lvl: 0.035, every: 2 }, { t: 'drum', d: 'frame', steps: 'x.....x.', sub: 8, lvl: 0.25 }] },
    { id: 'dungeon_a', kind: 'dungeon', name: '잊혀진 지하묘지', desc: '프리지아 선법 · 저음 드론 · 낮은 합창 · 먼 북소리 (음산함)', key: 48, mode: 'phrygian', bpm: 50, meter: 4, seed: 61, prog: [0, 0, 1, 1, 0, 0, 6, 1], vol: 0.92,
      layers: [{ t: 'bass', inst: 'drone', oct: -1, lvl: 0.06, pat: [[0, 0, 4]] }, { t: 'pad', inst: 'choirU', oct: 0, lvl: 0.035, tones: [0, 2] },
        { t: 'mel', inst: 'bell', oct: 2, lvl: 0.03, rhy: 'slow', form: 'ABAC', from: 2, rest: 0.55 }, { t: 'drum', d: 'war', steps: 'x...', sub: 4, lvl: 0.28, every: 2 }] },
    { id: 'dungeon_b', kind: 'dungeon', name: '그림자 회랑', desc: '라단조 · 첼로 오스티나토 · 바이올린 · 팀파니 (긴장감)', key: 45, mode: 'harmonic', bpm: 76, meter: 4, seed: 71, prog: [0, 0, 5, 5, 3, 3, 4, 4], vol: 0.92,
      layers: [{ t: 'bass', inst: 'stac', oct: -1, lvl: 0.06, pat: [[0, 0, 0.4], [0.5, 0, 0.4], [1, 7, 0.4], [1.5, 0, 0.4], [2, 0, 0.4], [2.5, 0, 0.4], [3, 7, 0.4], [3.5, 2, 0.4]] }, { t: 'pad', inst: 'strings', oct: 0, lvl: 0.032 },
        { t: 'mel', inst: 'violin', oct: 2, lvl: 0.04, rhy: 'med', form: 'ABAC', from: 4 }, { t: 'drum', d: 'timpani', steps: 'x.....x.', sub: 8, lvl: 0.28 }, { t: 'drum', d: 'tom', steps: '.......x', sub: 8, lvl: 0.2, every: 2 }] },
    { id: 'boss_a', kind: 'boss', name: '몰락한 왕의 분노', desc: '라단조 132bpm · 금관 · 전쟁 북 · 합창 (웅장한 전투)', key: 50, mode: 'harmonic', bpm: 132, meter: 4, seed: 83, prog: [0, 0, 5, 5, 6, 6, 4, 4], vol: 0.75,
      layers: [{ t: 'bass', inst: 'stac', oct: -1, lvl: 0.06, pat: [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5].map(b => [b, 0, 0.25]) }, { t: 'pad', inst: 'choir', oct: 1, lvl: 0.03 }, { t: 'pad', inst: 'strings', oct: 0, lvl: 0.03 },
        { t: 'mel', inst: 'brass', oct: 1, lvl: 0.045, rhy: 'med', form: 'ABAC', from: 2 }, { t: 'drum', d: 'war', steps: 'x.x...x.', sub: 8, lvl: 0.45 }, { t: 'drum', d: 'snare', steps: '..x...x.', sub: 8, lvl: 0.22 }, { t: 'drum', d: 'cymbal', steps: 'x', sub: 1, lvl: 0.06, every: 4, swell: true }] },
    { id: 'boss_b', kind: 'boss', name: '최후의 결전', desc: '프리지아 120bpm · 타이코 · 질주하는 첼로 · 합창 선율 (어둡고 격렬)', key: 52, mode: 'phrygian', bpm: 120, meter: 4, seed: 97, prog: [0, 1, 0, 1, 6, 5, 1, 1], vol: 0.68,
      layers: [{ t: 'bass', inst: 'stac', oct: -1, lvl: 0.065, pat: [0, 0.5, 0.75, 1, 1.5, 1.75, 2, 2.5, 2.75, 3, 3.5, 3.75].map(b => [b, 0, 0.2]) }, { t: 'pad', inst: 'strings', oct: 0, lvl: 0.03 },
        { t: 'stab', inst: 'brass', oct: 0, lvl: 0.04, beats: [0, 2.5] }, { t: 'mel', inst: 'choir', oct: 1, lvl: 0.06, rhy: 'med', form: 'ABAC', from: 2 },
        { t: 'drum', d: 'taiko', steps: 'x..x..x.', sub: 8, lvl: 0.5 }, { t: 'drum', d: 'snare', steps: '....x...', sub: 8, lvl: 0.2 }] },
  ];
  function mulberry(a) { return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  // 한 바퀴(진행 길이)의 음표를 미리 작곡한다: { bar, beat, inst, midi, dur(박), lvl } / 타악기 { bar, beat, d, lvl }
  function compose(S) {
    const rng = mulberry(S.seed), sc = SCALES[S.mode], L = S.prog.length, ev = [];
    const dm = (d, oct) => S.key + 12 * oct + sc[((d % 7) + 7) % 7] + 12 * Math.floor(d / 7);
    const tones = d => [d, d + 2, d + 4, d + 7, d + 9];
    for (const ly of S.layers) {
      if (ly.t === 'pad') for (let b = 0; b < L; b++) (ly.tones || [0, 1, 2]).forEach(i => ev.push({ bar: b, beat: 0, inst: ly.inst, midi: dm(tones(S.prog[b])[i], ly.oct), dur: S.meter, lvl: ly.lvl }));
      if (ly.t === 'stab') for (let b = 0; b < L; b++) ly.beats.forEach(bt => [0, 1, 2].forEach(i => ev.push({ bar: b, beat: bt, inst: ly.inst, midi: dm(tones(S.prog[b])[i], ly.oct), dur: 0.35, lvl: ly.lvl })));
      if (ly.t === 'bass') for (let b = 0; b < L; b++) ly.pat.forEach(([bt, ti, len]) => ev.push({ bar: b, beat: bt, inst: ly.inst, midi: ti === 7 ? dm(S.prog[b], ly.oct + 1) : dm(tones(S.prog[b])[ti] - (ti ? 7 : 0) + (ti ? 7 : 0), ly.oct), dur: len, lvl: ly.lvl }));
      if (ly.t === 'arp') for (let b = 0; b < L; b++) ly.pat.forEach((ti, i) => ev.push({ bar: b, beat: i * S.meter / ly.sub, inst: ly.inst, midi: dm(tones(S.prog[b])[ti], ly.oct), dur: S.meter / ly.sub * 1.5, lvl: ly.lvl * (i % (ly.sub / 2) === 0 ? 1.15 : 0.9) }));
      if (ly.t === 'drum') for (let b = 0; b < L; b++) {
        if (ly.every && b % ly.every !== ly.every - 1 && !ly.swell) continue;
        if (ly.swell) { if (b % ly.every === ly.every - 1) ev.push({ bar: b, beat: 0, d: ly.d, lvl: ly.lvl, swell: S.meter }); continue; }
        const st = (b === L - 1 && ly.fill) ? ly.fill : ly.steps;
        [...st].forEach((c, i) => { if (c === 'x') ev.push({ bar: b, beat: i * S.meter / st.length, d: ly.d, lvl: ly.lvl * (i === 0 ? 1 : 0.8) }); });
      }
      if (ly.t === 'mel') {
        // 2마디 동기(motif) A·B·C를 만들고 형식(ABAC)대로 배치. 반복되는 A는 화음에 맞게 이동
        const motifs = {}, rhyset = RHY[ly.rhy];
        let deg = S.prog[0] + 7;
        const make = (startBar) => {
          const notes = [];
          for (let k = 0; k < 2; k++) {
            const bar = startBar + k, cd = S.prog[bar % L], ct = tones(cd).map(x => x + 7);
            const r = rhyset[Math.floor(rng() * rhyset.length)]; let beat = 0;
            r.forEach((len, i) => {
              if (i === 0) deg = ct.reduce((a, c) => Math.abs(c - deg) < Math.abs(a - deg) ? c : a, ct[0]);
              else { const step = [-2, -1, -1, 1, 1, 2][Math.floor(rng() * 6)]; deg += step; if (deg > 13) deg -= 2; if (deg < 4) deg += 2; }
              const last = k === 1 && i === r.length - 1; if (last) deg = ct[0] + (deg > ct[0] + 3 ? 7 : 0);
              if (!(ly.rest && i > 0 && rng() < ly.rest)) notes.push({ k, beat, deg, len });
              beat += len;
            });
          }
          return { notes, root: S.prog[startBar % L] };
        };
        const form = ly.form.repeat(Math.ceil(L / (ly.form.length * 2)));
        for (let s = 0; s * 2 < L; s++) {
          const letter = form[s], startBar = s * 2;
          if (!motifs[letter]) motifs[letter] = make(startBar);
          const m = motifs[letter], shift = S.prog[startBar % L] - m.root;
          m.notes.forEach(n => ev.push({ bar: startBar + n.k, beat: n.beat, inst: ly.inst, midi: dm(n.deg + shift, ly.oct - 1), dur: n.len * 0.95, lvl: ly.lvl, mel: true, from: ly.from || 0 }));
        }
      }
    }
    ev.sort((a, b) => a.bar - b.bar || a.beat - b.beat);
    return ev;
  }
  function startTrack(ctx, out, id) {
    const S = TRACKS.find(t => t.id === id) || TRACKS[0];
    const ev = compose(S), beat = 60 / S.bpm, bar = beat * S.meter, L = S.prog.length, loopLen = bar * L;
    const bus = ctx.createGain(); bus.gain.value = 0; bus.connect(out);
    bus.gain.setValueAtTime(0, ctx.currentTime); bus.gain.linearRampToValueAtTime(S.vol, ctx.currentTime + 2.5);
    let loopStart = ctx.currentTime + 0.15, idx = 0, loop = 0, alive = true;
    function schedule() {
      if (!alive) return;
      const horizon = ctx.currentTime + 1.2;
      while (true) {
        if (idx >= ev.length) { idx = 0; loop++; loopStart += loopLen; }
        const e = ev[idx], t = loopStart + (e.bar * S.meter + e.beat) * beat;
        if (t > horizon) break;
        idx++;
        if (t < ctx.currentTime - 0.05) continue;
        if (e.mel && loop === 0 && e.bar < e.from) continue;   // 첫 바퀴는 선율 없이 시작
        const v = V(ctx, bus, t, {});
        if (e.d) { if (e.swell) DRUM.cymbal(v, t, e.lvl, e.swell * beat); else DRUM[e.d](v, t, e.lvl); }
        else INST[e.inst](v, t, MIDI(e.midi), e.dur * beat, e.lvl * (e.mel ? 1 : 1) * (0.92 + Math.random() * 0.16));
      }
    }
    schedule();
    const h = setInterval(schedule, 250);
    const stop = () => {
      alive = false; clearInterval(h);
      const n = ctx.currentTime; bus.gain.cancelScheduledValues(n); bus.gain.setValueAtTime(bus.gain.value, n); bus.gain.linearRampToValueAtTime(0, n + 1.6);
      setTimeout(() => bus.disconnect(), 2500);
    };
    stop.tick = schedule;   // 오프라인 렌더링에서 직접 예약할 때 사용
    return stop;
  }

  // ── 잔향: 초기 반사 + 고음이 먼저 줄어드는 꼬리(스테레오) ──
  function impulse2(ctx, seconds, decay, damp, pre = 0.012) {
    const sr = ctx.sampleRate, len = Math.floor(sr * seconds), buf = ctx.createBuffer(2, len, sr);
    for (let ch = 0; ch < 2; ch++) {
      const d = buf.getChannelData(ch); let lp = 0;
      for (let i = 0; i < len; i++) {
        const x = i / len, a = 0.15 + 0.8 * (1 - Math.pow(x, 0.5)) * (1 - damp);   // 시간이 지날수록 어두워짐
        lp += a * ((Math.random() * 2 - 1) - lp);
        d[i] = lp * Math.pow(1 - x, decay) * (i < sr * pre ? 0 : 1);
      }
      [0.013, 0.021, 0.029, 0.037, 0.047].forEach((tm, k) => { const j = Math.floor(sr * (tm + ch * 0.003)); if (j < len) d[j] += (k % 2 ? -1 : 1) * 0.5 / (k + 1); });
    }
    return buf;
  }

  // ───────────────────────── 엔진 ─────────────────────────
  const DEFAULT_PICKS = { bgm: { field: 'field_a', town: 'town_a', dungeon: 'dungeon_a', boss: 'boss_a' }, sfx: {} };
  function create(opts = {}) {
    const AC = root.AudioContext || root.webkitAudioContext;
    if (!AC) throw new Error('이 브라우저는 Web Audio를 지원하지 않습니다.');
    const ctx = opts.context || new AC();
    const master = ctx.createGain(); master.gain.value = 0.9;
    const glue = ctx.createDynamicsCompressor(); glue.threshold.value = -18; glue.ratio.value = 3; glue.attack.value = 0.01; glue.release.value = 0.2;
    const lim = ctx.createDynamicsCompressor(); lim.threshold.value = -3; lim.knee.value = 0; lim.ratio.value = 20; lim.attack.value = 0.001; lim.release.value = 0.1;
    master.connect(glue); glue.connect(lim); lim.connect(ctx.destination);
    const room = ctx.createConvolver(); room.buffer = impulse2(ctx, 1.5, 3.2, 0.35);
    const hall = ctx.createConvolver(); hall.buffer = impulse2(ctx, 3.6, 2.6, 0.2, 0.025);
    const roomG = ctx.createGain(); roomG.gain.value = 0.2; room.connect(roomG); roomG.connect(master);
    const hallG = ctx.createGain(); hallG.gain.value = 0.32; hall.connect(hallG); hallG.connect(master);
    const bus = (verb) => { const g = ctx.createGain(); g.connect(master); g.connect(verb); return g; };
    const sfx = bus(room), music = bus(hall), amb = bus(room);
    music.gain.value = 0.5; amb.gain.value = 0.6;
    let stopAmb = null, stopMusic = null, curTrack = null, kind = 'field';
    const picks = JSON.parse(JSON.stringify(DEFAULT_PICKS));
    const wake = () => { if (ctx.state === 'suspended') ctx.resume(); };
    function draw(name, dest, when, variant) {
      const grp = GROUP_OF[name], pick = variant || (grp ? picks.sfx[grp] : picks.sfx[name]) || 'A';
      const v0 = when;
      const vg = VGAIN[name + ':' + pick]; if (vg) dest = gainTo(ctx, dest, vg);
      if (!grp && pick !== 'A' && VAR[name] && VAR[name][pick]) { CURMOD = null; return VAR[name][pick](V(ctx, dest, v0, {})); }
      const mod = grp && pick !== 'A' ? GROUPS[grp][pick] : {};
      CURMOD = mod;
      try {
        const v = V(ctx, dest, v0, mod);
        const d = R[name](v) || 0.5;
        if (mod.layer) mod.layer(v, d, name);
        return d;
      } finally { CURMOD = null; }
    }
    function setTrack(id) {
      if (curTrack === id && stopMusic) return;
      if (stopMusic) { stopMusic(); stopMusic = null; }
      curTrack = id; if (id) { wake(); stopMusic = startTrack(ctx, music, id); }
    }
    return {
      ctx,
      play(name, o = {}) {
        if (!R[name]) throw new Error('알 수 없는 소리: ' + name);
        wake();
        const g = ctx.createGain(); g.gain.value = o.gain == null ? 1 : o.gain;
        g.connect(panned(ctx, sfx, o.pan || 0));
        return draw(name, g, ctx.currentTime + (o.delay || 0) + 0.01, o.variant);
      },
      ambience(k) {
        if (stopAmb) { stopAmb(); stopAmb = null; }
        if (k) { wake(); stopAmb = startAmbience(ctx, amb, k); }
      },
      // music(true) 현재 장면 곡 · music('town'|'field'|'dungeon'|'boss') 장면 전환(교차 페이드) · music(false) 정지
      music(on) {
        if (on === false || on == null) { setTrack(null); return; }
        if (typeof on === 'string') kind = on;
        setTrack(picks.bgm[kind] || DEFAULT_PICKS.bgm[kind]);
      },
      playTrack(id) { setTrack(id); },
      get track() { return curTrack; },
      setPick(p = {}) { Object.assign(picks.bgm, p.bgm || {}); Object.assign(picks.sfx, p.sfx || {}); if (stopMusic && p.bgm && p.bgm[kind] && p.bgm[kind] !== curTrack) setTrack(picks.bgm[kind]); },
      get picks() { return JSON.parse(JSON.stringify(picks)); },
      setVolume(v) {
        if (v.master != null) master.gain.value = v.master;
        if (v.sfx != null) sfx.gain.value = v.sfx;
        if (v.music != null) music.gain.value = v.music;
        if (v.amb != null) amb.gain.value = v.amb;
      },
      actorSfx(name) { return ACTOR_SFX[name] || {}; },
    };
  }

  function renderTo(ctx, name, when = 0, variant) {
    const grp = GROUP_OF[name], mod = grp && variant && variant !== 'A' ? GROUPS[grp][variant] : {};
    const dest = gainTo(ctx, ctx.destination, VGAIN[name + ':' + (variant || 'A')] || 1);
    if (!grp && variant && variant !== 'A' && VAR[name]) return VAR[name][variant](V(ctx, dest, when, {}));
    CURMOD = mod; try { const v = V(ctx, dest, when, mod); const d = R[name](v) || 0.5; if (mod.layer) mod.layer(v, d, name); return d; } finally { CURMOD = null; }
  }
  function renderTrack(ctx, id, out) { return startTrack(ctx, out || ctx.destination, id); }

  root.LineageAudio = { create, renderTo, renderTrack, SOUNDS, AMBIENCES, ACTOR_SFX, TRACKS, VARIANT_SETS, GROUPS, DEFAULT_PICKS, compose, names: Object.keys(R) };
})(typeof window !== 'undefined' ? window : globalThis);
