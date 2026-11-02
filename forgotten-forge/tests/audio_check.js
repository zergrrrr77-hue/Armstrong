// 사운드 점검: 모든 효과음 변형(A/B/C)과 배경음악을 오프라인 렌더링해 무음·클리핑·음량 편차를 확인
// 실행: node forgotten-forge/tests/audio_check.js
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch(); const page = await b.newPage();
  const errs = []; page.on('pageerror', e => errs.push(e.message));
  await page.goto('about:blank');
  await page.addScriptTag({ path: path.resolve(__dirname, '../lineage-assets/audio/sfx.js') });
  const res = await page.evaluate(async () => {
    const A = window.LineageAudio, out = { sfx: [], bgm: [] };
    const stat = (buf, skip = 0) => { let pk = 0, ss = 0, n = 0; for (let c = 0; c < buf.numberOfChannels; c++) { const d = buf.getChannelData(c); for (let i = skip; i < d.length; i++) { const x = Math.abs(d[i]); if (x > pk) pk = x; ss += d[i] * d[i]; n++; if (Number.isNaN(d[i])) return { nan: true }; } } return { pk, rms: Math.sqrt(ss / n) }; };
    for (const vs of A.VARIANT_SETS) for (const v of ['A', 'B', 'C']) for (const name of vs.sample) {
      const ctx = new OfflineAudioContext(2, 44100 * 3.5, 44100);
      try { A.renderTo(ctx, name, 0.01, v); const buf = await ctx.startRendering(); out.sfx.push({ set: vs.id, v, name, ...stat(buf) }); }
      catch (e) { out.sfx.push({ set: vs.id, v, name, err: e.message }); }
    }
    for (const t of A.TRACKS) {
      const sec = 24, ctx = new OfflineAudioContext(2, 44100 * sec, 44100);
      // 오프라인 컨텍스트는 setInterval이 진행되지 않으므로 먼저 한 바퀴를 직접 예약
      const ev = A.compose(t), beat = 60 / t.bpm; let cnt = 0;
      const stop = A.renderTrack(ctx, t.id);   // 첫 1.2초분 예약
      // 나머지: 시간 진행을 흉내 내기 위해 suspend/resume로 예약 함수를 반복 호출
      for (let s = 0.5; s < sec; s += 0.5) { ctx.suspend(s).then(() => { stop.tick(); ctx.resume(); }); }
      const buf = await ctx.startRendering(); stop();
      out.bgm.push({ id: t.id, ...stat(buf, 44100 * 4) });
    }
    return out;
  });
  const bad = [];
  for (const r of res.sfx) { if (r.err || r.nan || r.pk < 0.01) bad.push(r); }
  const byset = {};
  for (const r of res.sfx) { const k = r.set + ':' + r.v; byset[k] = byset[k] || []; byset[k].push(r); }
  for (const [k, rs] of Object.entries(byset)) console.log(k.padEnd(22), rs.map(r => r.err ? 'ERR ' + r.err : `${r.pk.toFixed(2)}/${(r.rms * 100).toFixed(1)}`).join('  '));
  for (const r of res.bgm) console.log('BGM', r.id.padEnd(10), `peak ${r.pk && r.pk.toFixed(2)} rms ${r.rms && (r.rms * 100).toFixed(2)}`);
  console.log(errs.length ? errs : 'no page errors', bad.length ? ['문제', bad] : '무음·오류 없음');
  await b.close();
})();
