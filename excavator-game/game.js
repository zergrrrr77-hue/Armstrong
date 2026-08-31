(() => {
  const canvas = document.getElementById("game-canvas");
  const ctx = canvas.getContext("2d");
  const starCountEl = document.getElementById("star-count");
  const clearBanner = document.getElementById("clear-banner");
  const btnLeft = document.getElementById("btn-left");
  const btnRight = document.getElementById("btn-right");
  const btnAction = document.getElementById("btn-action");

  let W = 0, H = 0, groundY = 0, dpr = 1;

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth;
    H = window.innerHeight;
    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    groundY = H * (W < H ? 0.55 : 0.72);
    excavator.x = clamp(excavator.x, MARGIN, W - MARGIN);
    for (const obj of objects) obj.x = clamp(obj.x, MARGIN, W - MARGIN);
  }

  const MARGIN = 70;
  const REACH = 115;

  function clamp(v, lo, hi) {
    return Math.max(lo, Math.min(hi, v));
  }
  function rand(a, b) {
    return a + Math.random() * (b - a);
  }
  function pick(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
  }

  // ---------- audio ----------
  let actx = null;
  function ensureAudio() {
    if (!actx) actx = new (window.AudioContext || window.webkitAudioContext)();
    if (actx.state === "suspended") actx.resume();
  }

  function tone(freq, duration, type, gainPeak, startDelay = 0, freqEnd = null) {
    if (!actx) return;
    const t0 = actx.currentTime + startDelay;
    const osc = actx.createOscillator();
    const gain = actx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t0);
    if (freqEnd !== null) osc.frequency.exponentialRampToValueAtTime(Math.max(freqEnd, 1), t0 + duration);
    gain.gain.setValueAtTime(0.0001, t0);
    gain.gain.exponentialRampToValueAtTime(gainPeak, t0 + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + duration);
    osc.connect(gain).connect(actx.destination);
    osc.start(t0);
    osc.stop(t0 + duration + 0.02);
  }

  function noiseBurst(duration, gainPeak, startDelay = 0) {
    if (!actx) return;
    const t0 = actx.currentTime + startDelay;
    const bufferSize = Math.floor(actx.sampleRate * duration);
    const buffer = actx.createBuffer(1, bufferSize, actx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / bufferSize);
    const src = actx.createBufferSource();
    src.buffer = buffer;
    const gain = actx.createGain();
    gain.gain.setValueAtTime(gainPeak, t0);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + duration);
    src.connect(gain).connect(actx.destination);
    src.start(t0);
  }

  const sound = {
    swing() {
      tone(220, 0.12, "sine", 0.05, 0, 180);
    },
    break_() {
      noiseBurst(0.25, 0.35);
      tone(300, 0.2, "square", 0.12, 0, 90);
    },
    push() {
      tone(140, 0.12, "square", 0.15, 0, 100);
      tone(220, 0.08, "square", 0.08, 0.03);
    },
    carLeave() {
      tone(300, 0.1, "sawtooth", 0.12, 0);
      tone(420, 0.16, "sawtooth", 0.12, 0.09);
    },
    dig() {
      tone(90, 0.14, "triangle", 0.18, 0, 60);
      noiseBurst(0.1, 0.1);
    },
    star() {
      tone(660, 0.09, "sine", 0.15, 0);
      tone(880, 0.12, "sine", 0.15, 0.07);
    },
    roundClear() {
      [523, 659, 784, 1047].forEach((f, i) => tone(f, 0.22, "sine", 0.18, i * 0.11));
    },
  };

  // ---------- world state ----------
  const excavator = {
    x: 0,
    dir: 1,
    speed: 260,
    action: { active: false, timer: 0, duration: 0.36, applied: false, target: null },
  };

  let objects = [];
  let particles = [];
  let stars = 0;
  let shake = 0;
  let roundClearing = false;

  const CAR_COLORS = ["#ff5f6d", "#4facfe", "#a06bff", "#ffb86b"];

  function spawnObject(type, x) {
    if (type === "rock") {
      objects.push({ type, x, hp: 1, wobble: rand(0, 10), size: rand(0.85, 1.15) });
    } else if (type === "car") {
      objects.push({
        type,
        x,
        pushCount: 0,
        maxPush: 3,
        color: pick(CAR_COLORS),
        exiting: false,
        exitDir: 0,
      });
    } else if (type === "dirt") {
      objects.push({ type, x, depth: 3, maxDepth: 3 });
    }
  }

  function spawnRound() {
    const count = 3 + Math.floor(Math.random() * 3); // 3~5
    const types = ["rock", "rock", "car", "dirt", "dirt", "car", "rock"];
    const chosen = [];
    let attempts = 0;
    while (chosen.length < count && attempts < 200) {
      attempts++;
      const x = rand(MARGIN + 40, W - MARGIN - 40);
      const tooClose = chosen.some((c) => Math.abs(c - x) < 150) || Math.abs(x - excavator.x) < 160;
      if (!tooClose) chosen.push(x);
    }
    chosen.forEach((x) => spawnObject(pick(types), x));
  }

  function spawnParticles(x, y, color, count, opts = {}) {
    for (let i = 0; i < count; i++) {
      particles.push({
        x,
        y,
        vx: rand(opts.vxMin ?? -140, opts.vxMax ?? 140),
        vy: rand(opts.vyMin ?? -260, opts.vyMax ?? -60),
        life: 0,
        maxLife: rand(0.5, 0.9),
        color,
        size: rand(4, opts.maxSize ?? 9),
        gravity: opts.gravity ?? 620,
        shape: opts.shape ?? "rect",
        rot: rand(0, Math.PI * 2),
        vrot: rand(-6, 6),
      });
    }
  }

  function spawnConfetti() {
    const colors = ["#ff5f6d", "#ffc93c", "#4facfe", "#7ed957", "#a06bff"];
    for (let i = 0; i < 90; i++) {
      particles.push({
        x: rand(0, W),
        y: -20 - rand(0, H * 0.4),
        vx: rand(-60, 60),
        vy: rand(80, 200),
        life: 0,
        maxLife: rand(1.6, 2.4),
        color: pick(colors),
        size: rand(5, 10),
        gravity: 260,
        shape: "confetti",
        rot: rand(0, Math.PI * 2),
        vrot: rand(-8, 8),
      });
    }
  }

  function addStar() {
    stars++;
    starCountEl.textContent = String(stars);
  }

  function removeObject(obj) {
    objects = objects.filter((o) => o !== obj);
    if (objects.length === 0 && !roundClearing) triggerRoundClear();
  }

  function triggerRoundClear() {
    roundClearing = true;
    clearBanner.classList.remove("hidden");
    clearBanner.classList.add("show");
    spawnConfetti();
    sound.roundClear();
    setTimeout(() => {
      clearBanner.classList.remove("show");
      clearBanner.classList.add("hidden");
      spawnRound();
      roundClearing = false;
    }, 1900);
  }

  function findTarget() {
    let best = null;
    let bestDist = Infinity;
    for (const obj of objects) {
      const d = Math.abs(obj.x - excavator.x);
      if (d <= REACH && d < bestDist) {
        best = obj;
        bestDist = d;
      }
    }
    return best;
  }

  function hitObject(obj) {
    const groundLift = 26;
    if (obj.type === "rock") {
      obj.hp -= 1;
      if (obj.hp <= 0) {
        spawnParticles(obj.x, groundY - groundLift, "#9c9c9c", 16, { maxSize: 8 });
        spawnParticles(obj.x, groundY - groundLift, "#6b6b6b", 6, { maxSize: 5 });
        sound.break_();
        shake = 10;
        removeObject(obj);
        addStar();
      }
    } else if (obj.type === "car") {
      const dir = obj.x >= excavator.x ? 1 : -1;
      obj.exitDir = dir;
      obj.pushCount += 1;
      obj.x = clamp(obj.x + dir * 46, MARGIN - 30, W - MARGIN + 30);
      spawnParticles(obj.x - dir * 30, groundY, "#c9a86a", 8, { vyMin: -80, vyMax: -10, gravity: 500, maxSize: 5 });
      sound.push();
      shake = 4;
      const offscreen = obj.x < MARGIN - 20 || obj.x > W - MARGIN + 20;
      if (obj.pushCount >= obj.maxPush || offscreen) {
        sound.carLeave();
        spawnParticles(obj.x, groundY - 20, obj.color, 10, { maxSize: 6 });
        removeObject(obj);
        addStar();
      }
    } else if (obj.type === "dirt") {
      obj.depth -= 1;
      spawnParticles(obj.x, groundY - 10, "#8b5a2b", 12, { maxSize: 7, vyMax: -40 });
      sound.dig();
      shake = 3;
      if (obj.depth <= 0) {
        spawnParticles(obj.x, groundY - 20, "#ffe28a", 14, { maxSize: 6, gravity: 250, shape: "spark" });
        sound.star();
        removeObject(obj);
        addStar();
      }
    }
  }

  function attemptAction() {
    ensureAudio();
    if (excavator.action.active) return;
    const target = findTarget();
    if (target) excavator.dir = target.x >= excavator.x ? 1 : -1;
    excavator.action.active = true;
    excavator.action.timer = 0;
    excavator.action.applied = false;
    excavator.action.target = target;
    if (!target) sound.swing();
  }

  // ---------- input ----------
  const input = { left: false, right: false };
  let actionHold = null;

  function bindHold(el, onDown, onUp) {
    const start = (e) => {
      e.preventDefault();
      el.classList.add("pressed");
      onDown();
    };
    const end = (e) => {
      e.preventDefault();
      el.classList.remove("pressed");
      onUp();
    };
    el.addEventListener("pointerdown", start);
    el.addEventListener("pointerup", end);
    el.addEventListener("pointerleave", end);
    el.addEventListener("pointercancel", end);
  }

  bindHold(
    btnLeft,
    () => (input.left = true),
    () => (input.left = false)
  );
  bindHold(
    btnRight,
    () => (input.right = true),
    () => (input.right = false)
  );
  bindHold(
    btnAction,
    () => {
      attemptAction();
      actionHold = setInterval(attemptAction, 380);
    },
    () => {
      clearInterval(actionHold);
      actionHold = null;
    }
  );

  window.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") input.left = true;
    else if (e.key === "ArrowRight") input.right = true;
    else if ((e.key === " " || e.key === "ArrowUp" || e.key === "Enter") && !e.repeat) attemptAction();
  });
  window.addEventListener("keyup", (e) => {
    if (e.key === "ArrowLeft") input.left = false;
    else if (e.key === "ArrowRight") input.right = false;
  });

  window.addEventListener("resize", resize);

  // ---------- update ----------
  function update(dt) {
    let moving = false;
    if (input.left && !input.right) {
      excavator.x -= excavator.speed * dt;
      excavator.dir = -1;
      moving = true;
    } else if (input.right && !input.left) {
      excavator.x += excavator.speed * dt;
      excavator.dir = 1;
      moving = true;
    }
    excavator.x = clamp(excavator.x, MARGIN, W - MARGIN);
    excavator.moving = moving;

    if (excavator.action.active) {
      excavator.action.timer += dt;
      if (!excavator.action.applied && excavator.action.timer >= excavator.action.duration * 0.5) {
        excavator.action.applied = true;
        if (excavator.action.target && objects.includes(excavator.action.target)) {
          hitObject(excavator.action.target);
        }
      }
      if (excavator.action.timer >= excavator.action.duration) {
        excavator.action.active = false;
        excavator.action.target = null;
      }
    }

    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      p.life += dt;
      if (p.life >= p.maxLife) {
        particles.splice(i, 1);
        continue;
      }
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.vy += p.gravity * dt;
      p.rot += p.vrot * dt;
    }

    if (shake > 0) shake = Math.max(0, shake - dt * 40);
  }

  // ---------- drawing ----------
  function drawBackground(t) {
    const g = ctx.createLinearGradient(0, 0, 0, groundY);
    g.addColorStop(0, "#7ec8ff");
    g.addColorStop(1, "#cfeeff");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, groundY);

    ctx.fillStyle = "rgba(255,255,255,0.9)";
    for (let i = 0; i < 4; i++) {
      const cx = ((t * 12 + i * 260) % (W + 200)) - 100;
      const cy = 60 + i * 38;
      drawCloud(cx, cy, 34 + (i % 2) * 10);
    }

    ctx.fillStyle = "#7bbf6a";
    ctx.beginPath();
    ctx.ellipse(W * 0.2, groundY - 6, 140, 40, 0, Math.PI, 2 * Math.PI);
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(W * 0.75, groundY - 2, 180, 46, 0, Math.PI, 2 * Math.PI);
    ctx.fill();
  }

  function drawCloud(x, y, s) {
    ctx.beginPath();
    ctx.arc(x, y, s * 0.6, 0, Math.PI * 2);
    ctx.arc(x + s * 0.5, y - s * 0.2, s * 0.5, 0, Math.PI * 2);
    ctx.arc(x + s * 0.9, y, s * 0.55, 0, Math.PI * 2);
    ctx.fill();
  }

  function drawGround() {
    ctx.fillStyle = "#8fd15a";
    ctx.fillRect(0, groundY, W, 26);
    ctx.fillStyle = "#c98a4b";
    ctx.fillRect(0, groundY + 26, W, H - groundY - 26);
    ctx.fillStyle = "#b97a3d";
    for (let x = -((performance.now() / 40) % 60); x < W; x += 60) {
      ctx.fillRect(x, groundY + 40, 30, 6);
    }
  }

  function roundRect(x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  function drawExcavator() {
    const x = excavator.x;
    const baseY = groundY;
    const dir = excavator.dir;
    const bob = excavator.moving ? Math.sin(performance.now() / 70) * 3 : 0;

    ctx.save();
    ctx.translate(x, baseY + bob);
    ctx.scale(dir, 1);

    // tracks
    ctx.fillStyle = "#3b3b3b";
    roundRect(-46, -6, 92, 22, 10);
    ctx.fill();
    ctx.fillStyle = "#666";
    for (let i = -34; i <= 34; i += 17) {
      ctx.beginPath();
      ctx.arc(i, 5, 9, 0, Math.PI * 2);
      ctx.fill();
    }

    // body
    ctx.fillStyle = "#ffc93c";
    roundRect(-38, -52, 66, 46, 10);
    ctx.fill();

    // cabin window
    ctx.fillStyle = "#bdeaff";
    roundRect(-30, -44, 30, 26, 6);
    ctx.fill();

    // cute eyes
    ctx.fillStyle = "#fff";
    ctx.beginPath();
    ctx.arc(-20, -32, 6, 0, Math.PI * 2);
    ctx.arc(-8, -32, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#2b2b2b";
    ctx.beginPath();
    ctx.arc(-18, -32, 2.6, 0, Math.PI * 2);
    ctx.arc(-6, -32, 2.6, 0, Math.PI * 2);
    ctx.fill();

    // arm + bucket
    const a = excavator.action;
    let swing = 0;
    if (a.active) {
      const p = Math.min(1, a.timer / a.duration);
      swing = Math.sin(p * Math.PI) * 1;
    }
    const armBaseX = 20,
      armBaseY = -40;
    const armAngle = -0.5 - swing * 1.15;
    const armLen = 40;
    const elbowX = armBaseX + Math.cos(armAngle) * armLen;
    const elbowY = armBaseY + Math.sin(armAngle) * armLen;

    ctx.strokeStyle = "#e08a1e";
    ctx.lineWidth = 12;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(armBaseX, armBaseY);
    ctx.lineTo(elbowX, elbowY);
    ctx.stroke();

    const bucketAngle = armAngle + 1.6 + swing * 0.6;
    const bucketLen = 26;
    const bx = elbowX + Math.cos(bucketAngle) * bucketLen;
    const by = elbowY + Math.sin(bucketAngle) * bucketLen;
    ctx.strokeStyle = "#c96a12";
    ctx.lineWidth = 9;
    ctx.beginPath();
    ctx.moveTo(elbowX, elbowY);
    ctx.lineTo(bx, by);
    ctx.stroke();

    ctx.fillStyle = "#8a8a8a";
    ctx.save();
    ctx.translate(bx, by);
    ctx.rotate(bucketAngle);
    roundRect(-4, -12, 24, 22, 6);
    ctx.fill();
    ctx.restore();

    ctx.restore();
  }

  function drawObject(obj) {
    const inRange = Math.abs(obj.x - excavator.x) <= REACH;
    if (inRange) {
      ctx.fillStyle = "rgba(255,255,255,0.35)";
      ctx.beginPath();
      ctx.ellipse(obj.x, groundY + 6, 46, 12, 0, 0, Math.PI * 2);
      ctx.fill();
    }

    if (obj.type === "rock") {
      const s = obj.size;
      ctx.save();
      ctx.translate(obj.x, groundY - 4);
      ctx.fillStyle = "#a3a3a3";
      ctx.beginPath();
      ctx.moveTo(-30 * s, 0);
      ctx.lineTo(-24 * s, -30 * s);
      ctx.lineTo(0, -42 * s);
      ctx.lineTo(24 * s, -28 * s);
      ctx.lineTo(30 * s, 0);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = "#cfcfcf";
      ctx.beginPath();
      ctx.moveTo(-10 * s, -6 * s);
      ctx.lineTo(0, -34 * s);
      ctx.lineTo(14 * s, -20 * s);
      ctx.closePath();
      ctx.fill();
      ctx.restore();
    } else if (obj.type === "car") {
      ctx.save();
      ctx.translate(obj.x, groundY - 2);
      ctx.fillStyle = obj.color;
      roundRect(-34, -30, 68, 24, 8);
      ctx.fill();
      roundRect(-20, -42, 38, 18, 8);
      ctx.fill();
      ctx.fillStyle = "#cdefff";
      roundRect(-14, -40, 28, 12, 4);
      ctx.fill();
      ctx.fillStyle = "#2b2b2b";
      ctx.beginPath();
      ctx.arc(-20, -4, 9, 0, Math.PI * 2);
      ctx.arc(20, -4, 9, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    } else if (obj.type === "dirt") {
      const p = obj.depth / obj.maxDepth;
      const h = 20 + 34 * p;
      const w = 40 + 30 * p;
      ctx.save();
      ctx.translate(obj.x, groundY);
      ctx.fillStyle = "#7a4a24";
      ctx.beginPath();
      ctx.moveTo(-w, 0);
      ctx.quadraticCurveTo(0, -h * 1.6, w, 0);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = "#94623a";
      ctx.beginPath();
      ctx.arc(-w * 0.3, -h * 0.5, 5, 0, Math.PI * 2);
      ctx.arc(w * 0.25, -h * 0.35, 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }
  }

  function drawParticles() {
    for (const p of particles) {
      const alpha = 1 - p.life / p.maxLife;
      ctx.save();
      ctx.globalAlpha = Math.max(0, alpha);
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rot);
      ctx.fillStyle = p.color;
      if (p.shape === "confetti") {
        ctx.fillRect(-p.size / 2, -p.size / 3, p.size, p.size / 1.6);
      } else if (p.shape === "spark") {
        ctx.beginPath();
        ctx.moveTo(0, -p.size);
        ctx.lineTo(p.size * 0.3, 0);
        ctx.lineTo(0, p.size);
        ctx.lineTo(-p.size * 0.3, 0);
        ctx.closePath();
        ctx.fill();
      } else {
        ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
      }
      ctx.restore();
    }
  }

  function draw(t) {
    ctx.save();
    if (shake > 0) {
      ctx.translate(rand(-shake, shake), rand(-shake, shake));
    }
    drawBackground(t);
    drawGround();

    const sorted = [...objects, { type: "__excavator__", x: excavator.x }].sort((a, b) => a.x - b.x);
    for (const item of sorted) {
      if (item.type === "__excavator__") drawExcavator();
      else drawObject(item);
    }

    drawParticles();
    ctx.restore();
  }

  // ---------- main loop ----------
  let last = performance.now();
  function loop(now) {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    update(dt);
    draw(now / 1000);
    requestAnimationFrame(loop);
  }

  resize();
  excavator.x = W / 2;
  spawnRound();
  requestAnimationFrame(loop);
})();
