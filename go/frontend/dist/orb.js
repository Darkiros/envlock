// Orbe de particules « JARVIS » — dessine sur un canvas, renvoie {stop}.
// Algorithme identique à l'aperçu navigateur (portable canvas 2D).
function startOrb(canvas, opts) {
  const ctx = canvas.getContext("2d", { alpha: false });
  const P = Object.assign(
    { count: 800, amp: 0.20, wave_speed: 1.0, rot_speed: 0.35,
      dot_size: 1.7, hue: 193, pulse: 0.15 },
    opts || {}
  );
  let W = 0, H = 0, DPR = 1, pts = [], running = true, raf = 0, t = 0;

  function build(n) {
    pts = [];
    const ga = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < n; i++) {
      const y = 1 - (i / Math.max(1, n - 1)) * 2;
      const r = Math.sqrt(Math.max(0, 1 - y * y));
      const th = ga * i;
      pts.push({ x: Math.cos(th) * r, y: y, z: Math.sin(th) * r, ph: Math.random() * 6.283 });
    }
  }
  function resize() {
    DPR = Math.min(2, window.devicePixelRatio || 1);
    W = canvas.clientWidth; H = canvas.clientHeight;
    canvas.width = Math.max(1, W * DPR); canvas.height = Math.max(1, H * DPR);
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  }
  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);

  function frame() {
    if (!running) return;
    t += 0.016;
    ctx.globalCompositeOperation = "source-over";
    ctx.fillStyle = "#05070d";
    ctx.fillRect(0, 0, W, H);

    const cx = W / 2, cy = H / 2, R = Math.min(W, H) * 0.34;
    const yaw = t * P.rot_speed, pitch = 0.4 + 0.08 * Math.sin(t * 0.3);
    const cyw = Math.cos(yaw), syw = Math.sin(yaw);
    const cp = Math.cos(pitch), sp = Math.sin(pitch);
    const pulse = 1 + P.pulse * Math.max(0, Math.sin(t * 1.3)) * (0.6 + 0.4 * Math.sin(t * 0.5));
    const ws = P.wave_speed;

    ctx.globalCompositeOperation = "lighter";
    for (let i = 0; i < pts.length; i++) {
      const p = pts[i];
      const n = 0.6 * Math.sin(4 * p.y + t * ws)
              + 0.4 * Math.cos(5 * p.x - t * ws * 0.8)
              + 0.5 * Math.sin(6 * p.z + t * ws * 1.3);
      const rr = 1 + P.amp * n * pulse;
      let x = p.x * rr, y = p.y * rr, z = p.z * rr;
      let rx = x * cyw + z * syw, rz = -x * syw + z * cyw;
      let ry = y * cp - rz * sp; rz = y * sp + rz * cp;
      const depth = clamp((rz + 1.4) / 2.8, 0, 1);
      const persp = 1 / (1 - 0.3 * rz);
      const sx = cx + rx * R * persp, sy = cy - ry * R * persp;
      const tw = 0.75 + 0.25 * Math.sin(t * 3 + p.ph);
      const alpha = (0.12 + 0.88 * depth) * tw;
      const s = 0.6 + P.dot_size * depth;
      ctx.fillStyle = `hsla(${P.hue}, 100%, ${52 + depth * 38}%, ${alpha})`;
      ctx.beginPath(); ctx.arc(sx, sy, s, 0, 6.283); ctx.fill();
    }
    raf = requestAnimationFrame(frame);
  }

  window.addEventListener("resize", resize);
  resize();
  build(Math.round(P.count));
  raf = requestAnimationFrame(frame);

  return {
    stop() {
      running = false;
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    },
    resize,
  };
}
