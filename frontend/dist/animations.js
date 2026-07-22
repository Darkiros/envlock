// Animations canvas 2D. createAnimation(key, canvas, opts) -> { stop() }.
// Resize géré par ResizeObserver (re-seed propre, pas de glitch).

function _run(canvas, opts, impl) {
  const ctx = canvas.getContext("2d", { alpha: false });
  let W = 0, H = 0, DPR = 1, running = true, raf = 0, frame = 0;
  const st = { seeded: false };

  function resize() {
    DPR = Math.min(2, window.devicePixelRatio || 1);
    W = canvas.clientWidth; H = canvas.clientHeight;
    canvas.width = Math.max(1, Math.round(W * DPR));
    canvas.height = Math.max(1, Math.round(H * DPR));
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    st.seeded = false;
    frame = 0;
  }
  const ro = new ResizeObserver(resize);
  ro.observe(canvas);
  resize();

  function loop() {
    if (!running) return;
    if (!st.seeded && W > 1 && H > 1) { impl.seed(W, H, opts, st); st.seeded = true; }
    if (st.seeded) { impl.frame(ctx, W, H, opts, st, frame); frame++; }
    raf = requestAnimationFrame(loop);
  }
  raf = requestAnimationFrame(loop);

  return {
    stop() {
      running = false;
      cancelAnimationFrame(raf);
      ro.disconnect();
    },
  };
}

const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);

// ----------------------------------------------------------------- ORBE
const _sphere = {
  seed(W, H, o, st) {
    let n = Math.round(o.count || 800);
    if (Math.min(W, H) < 240) n = Math.max(300, n >> 1);
    st.pts = [];
    const ga = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < n; i++) {
      const y = 1 - (i / Math.max(1, n - 1)) * 2;
      const r = Math.sqrt(Math.max(0, 1 - y * y));
      const th = ga * i;
      st.pts.push({ x: Math.cos(th) * r, y, z: Math.sin(th) * r, ph: Math.random() * 6.283 });
    }
  },
  frame(ctx, W, H, o, st, f) {
    ctx.globalCompositeOperation = "source-over";
    ctx.fillStyle = o.background || "#05070d";
    ctx.fillRect(0, 0, W, H);
    const cx = W / 2, cy = H / 2, R = Math.min(W, H) * 0.34;
    const t = f / 30;
    const yaw = t * (o.rot_speed || 0.35), pitch = 0.4 + 0.08 * Math.sin(t * 0.3);
    const cyw = Math.cos(yaw), syw = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
    const pulse = 1 + (o.pulse || 0.15) * Math.max(0, Math.sin(t * 1.3)) * (0.6 + 0.4 * Math.sin(t * 0.5));
    const ws = o.wave_speed || 1.0, amp = o.amp || 0.2, hue = o.hue || 193, dot = o.dot_size || 1.7;
    ctx.globalCompositeOperation = "lighter";
    for (const p of st.pts) {
      const n = 0.6 * Math.sin(4 * p.y + t * ws) + 0.4 * Math.cos(5 * p.x - t * ws * 0.8) + 0.5 * Math.sin(6 * p.z + t * ws * 1.3);
      const rr = 1 + amp * n * pulse;
      let x = p.x * rr, y = p.y * rr, z = p.z * rr;
      let rx = x * cyw + z * syw, rz = -x * syw + z * cyw;
      let ry = y * cp - rz * sp; rz = y * sp + rz * cp;
      const depth = clamp((rz + 1.4) / 2.8, 0, 1);
      const persp = 1 / (1 - 0.3 * rz);
      const sx = cx + rx * R * persp, sy = cy - ry * R * persp;
      const tw = 0.75 + 0.25 * Math.sin(t * 3 + p.ph);
      ctx.fillStyle = `hsla(${hue},100%,${52 + depth * 38}%,${(0.12 + 0.88 * depth) * tw})`;
      ctx.beginPath(); ctx.arc(sx, sy, 0.6 + dot * depth, 0, 6.283); ctx.fill();
    }
  },
};

// ------------------------------------------------------------ PARTICULES
const _particles = {
  seed(W, H, o, st) {
    const area = Math.max(0.15, (W * H) / (1920 * 1080));
    const n = Math.max(12, Math.round(90 * Math.min(1, area)));
    st.pts = [];
    for (let i = 0; i < n; i++)
      st.pts.push({ x: Math.random() * W, y: Math.random() * H, vx: (Math.random() - 0.5) * 1.2, vy: (Math.random() - 0.5) * 1.2 });
  },
  frame(ctx, W, H, o, st) {
    ctx.globalCompositeOperation = "source-over";
    ctx.fillStyle = "#0a0e17"; ctx.fillRect(0, 0, W, H);
    for (const p of st.pts) {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0 || p.x > W) p.vx *= -1;
      if (p.y < 0 || p.y > H) p.vy *= -1;
    }
    const link = 140 * Math.max(0.45, Math.min(1, Math.max(W, H) / 1400));
    for (let i = 0; i < st.pts.length; i++) {
      const a = st.pts[i];
      for (let j = i + 1; j < st.pts.length; j++) {
        const b = st.pts[j], d = Math.hypot(a.x - b.x, a.y - b.y);
        if (d < link) {
          ctx.strokeStyle = `rgba(79,157,255,${0.6 * (1 - d / link)})`;
          ctx.lineWidth = 1;
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        }
      }
    }
    ctx.fillStyle = "rgba(120,180,255,0.9)";
    for (const p of st.pts) { ctx.beginPath(); ctx.arc(p.x, p.y, 2, 0, 6.283); ctx.fill(); }
  },
};

// ---------------------------------------------------------------- MATRIX
const _CHARS = "0123456789ABCDEFｦｧｨｩｪｫｬｭｮｯｱｲｳｴｵｶｷｸｹｺ$#%&@*+=";
const _matrix = {
  seed(W, H, o, st) {
    st.size = Math.min(W, H) < 200 ? 10 : 18;
    st.cw = Math.round(st.size * 0.7); st.ch = st.size + 3;
    const cols = Math.max(1, Math.floor(W / st.cw));
    st.drops = []; st.speed = [];
    for (let i = 0; i < cols; i++) { st.drops.push((Math.random() * -40) | 0); st.speed.push(Math.random() < 0.25 ? 2 : 1); }
  },
  frame(ctx, W, H, o, st, f) {
    if (f < 3) { ctx.fillStyle = "#000"; ctx.fillRect(0, 0, W, H); }
    ctx.globalCompositeOperation = "source-over";
    ctx.fillStyle = "rgba(0,0,0,0.24)"; ctx.fillRect(0, 0, W, H);
    ctx.font = st.size + "px monospace";
    const rows = Math.max(1, Math.floor(H / st.ch)), trail = 12;
    for (let i = 0; i < st.drops.length; i++) {
      st.drops[i] += st.speed[i];
      if (st.drops[i] > rows + 4 + Math.random() * 26) { st.drops[i] = (Math.random() * -20) | 0; }
      const x = i * st.cw, head = st.drops[i];
      for (let t = 0; t < trail; t++) {
        const row = head - t; if (row < 0) continue;
        const y = row * st.ch + st.ch; if (y > H + st.ch) continue;
        const ch = _CHARS[(Math.random() * _CHARS.length) | 0];
        ctx.fillStyle = t === 0 ? "rgb(220,255,220)" : `rgba(0,255,102,${0.9 * (1 - t / trail)})`;
        ctx.fillText(ch, x, y);
      }
    }
  },
};

// -------------------------------------------------------------- DÉGRADÉ
const _gradient = {
  seed(W, H, o, st) {
    const cols = ["#5b2be0", "#2b6be0", "#e02b8a"];
    st.blobs = cols.map((c, i) => ({ c, phase: i * 2.1, sx: 0.3 + 0.12 * i, sy: 0.22 + 0.15 * i }));
  },
  frame(ctx, W, H, o, st, f) {
    ctx.globalCompositeOperation = "source-over";
    ctx.fillStyle = "#07070d"; ctx.fillRect(0, 0, W, H);
    const t = f / 60, R = Math.max(W, H) * 0.55;
    ctx.globalCompositeOperation = "lighter";
    for (const b of st.blobs) {
      const cx = (0.5 + 0.32 * Math.sin(t * b.sx + b.phase)) * W;
      const cy = (0.5 + 0.32 * Math.cos(t * b.sy + b.phase)) * H;
      const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, R);
      g.addColorStop(0, b.c + "aa"); g.addColorStop(1, b.c + "00");
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    }
  },
};

const _IMPL = { sphere: _sphere, particles: _particles, matrix: _matrix, gradient: _gradient };

function createAnimation(key, canvas, opts) {
  return _run(canvas, opts || {}, _IMPL[key] || _sphere);
}
