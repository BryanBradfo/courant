import { Particles, gradient } from './_helpers.js';

export default {
  theme: 'dark',

  init(canvas, ctx) {
    const W = () => window.innerWidth;
    const H = () => window.innerHeight;

    const stars = new Particles(200, () => ({
      x: Math.random() * W(),
      y: Math.random() * H() * 0.7,  // stars only in top 70%
      r: 0.5 + Math.random() * 1.5,
      baseAlpha: 0.3 + Math.random() * 0.5,
      twinkleSpeed: 0.001 + Math.random() * 0.003,
      phase: Math.random() * Math.PI * 2,
    }));

    let raf = null;
    let lastFrame = 0;
    let t = 0;
    const FRAME_INTERVAL = 1000 / 30;

    function draw() {
      const w = W(), h = H();
      gradient(ctx, w, h, [[0, '#0c1024'], [1, '#252a4a']]);

      // Moon — top-right
      const moonX = w * 0.85, moonY = h * 0.2;
      const moonGlow = ctx.createRadialGradient(moonX, moonY, 0, moonX, moonY, 90);
      moonGlow.addColorStop(0, 'rgba(255, 248, 217, 0.95)');
      moonGlow.addColorStop(0.3, 'rgba(255, 248, 217, 0.4)');
      moonGlow.addColorStop(1, 'rgba(255, 248, 217, 0)');
      ctx.fillStyle = moonGlow;
      ctx.beginPath();
      ctx.arc(moonX, moonY, 80, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = '#fff8d9';
      ctx.beginPath();
      ctx.arc(moonX, moonY, 35, 0, Math.PI * 2);
      ctx.fill();

      // Twinkling stars
      stars.draw((ctx, s) => {
        const alpha = s.baseAlpha + Math.sin(t * s.twinkleSpeed + s.phase) * 0.3;
        ctx.fillStyle = `rgba(255, 248, 217, ${Math.max(0, alpha)})`;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fill();
      }, ctx);

      t += 16;  // approx 1 frame at 30fps = 33ms ; using 16 gives a slower twinkle
    }

    function loop(now) {
      if (now - lastFrame >= FRAME_INTERVAL) { draw(); lastFrame = now; }
      raf = requestAnimationFrame(loop);
    }
    raf = requestAnimationFrame(loop);

    return () => { if (raf) cancelAnimationFrame(raf); };
  },
};
