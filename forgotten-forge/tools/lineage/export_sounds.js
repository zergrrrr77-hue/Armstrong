// 합성 효과음(sfx.js)을 WAV 파일로 굽는다(변형 A·B·C). 실행: node forgotten-forge/tools/lineage/export_sounds.js <출력 폴더>
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path');
const OUT = process.argv[2]; fs.mkdirSync(OUT, { recursive: true });
(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  await p.setContent('<html></html>');
  await p.addScriptTag({ path: path.resolve(__dirname, '../../lineage-assets/audio/sfx.js') });
  const list = await p.evaluate(() => LineageAudio.SOUNDS.map(([cat, name, label]) => ({ cat, name, label, vars: Object.keys((LineageAudio.VARIANT_SETS || {})[name] || {}) })));
  const index = [];
  for (const s of list) {
    const variants = ['A'];
    const grp = await p.evaluate(n => { for (const [g, d] of Object.entries(LineageAudio.GROUPS)) if (d.names.includes(n)) return Object.keys(d).filter(k => /^[A-C]$/.test(k)); return null; }, s.name);
    for (const v of (grp && grp.length ? grp.sort() : variants)) {
      const b64 = await p.evaluate(async ([name, v]) => {
        const sr = 44100, ctx = new OfflineAudioContext(2, sr * 4, sr);
        LineageAudio.renderTo(ctx, name, 0.02, v === 'A' ? undefined : v);
        const buf = await ctx.startRendering();
        const L = buf.getChannelData(0), R = buf.getChannelData(1);
        let end = L.length - 1; while (end > 0 && Math.abs(L[end]) < 1e-4 && Math.abs(R[end]) < 1e-4) end--;
        const n = Math.min(L.length, end + Math.floor(sr * 0.05));
        const dv = new DataView(new ArrayBuffer(44 + n * 4)); const W = (o, s) => [...s].forEach((c, i) => dv.setUint8(o + i, c.charCodeAt(0)));
        W(0, 'RIFF'); dv.setUint32(4, 36 + n * 4, true); W(8, 'WAVE'); W(12, 'fmt '); dv.setUint32(16, 16, true); dv.setUint16(20, 1, true); dv.setUint16(22, 2, true);
        dv.setUint32(24, sr, true); dv.setUint32(28, sr * 4, true); dv.setUint16(32, 4, true); dv.setUint16(34, 16, true); W(36, 'data'); dv.setUint32(40, n * 4, true);
        for (let i = 0; i < n; i++) { dv.setInt16(44 + i * 4, Math.max(-1, Math.min(1, L[i])) * 32767, true); dv.setInt16(46 + i * 4, Math.max(-1, Math.min(1, R[i])) * 32767, true); }
        let s = ''; const u = new Uint8Array(dv.buffer); for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); return btoa(s);
      }, [s.name, v]);
      const file = `${s.name}${v === 'A' ? '' : '_' + v}.wav`;
      fs.writeFileSync(path.join(OUT, file), Buffer.from(b64, 'base64'));
      index.push({ file, category: s.cat, name: s.name, label: s.label, variant: v });
    }
  }
  fs.writeFileSync(path.join(OUT, 'sounds.json'), JSON.stringify({ note: '44.1kHz 16bit 스테레오. variant A=기본, B·C=변형', sounds: index }, null, 1));
  console.log('sounds', index.length); await b.close();
})();
