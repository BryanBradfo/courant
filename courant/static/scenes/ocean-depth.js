import { Particles, gradient } from './_helpers.js';

export default {
  theme: 'dark',

  init(canvas, ctx) {
    const W = () => window.innerWidth;
    const H = () => window.innerHeight;

    const bubbles = new Particles(80, () => ({
      x: Math.random() * W(),
      y: H() + Math.random() * 100,
      r: 1 + Math.random() * 4,
      vy: 0.3 + Math.random() * 0.6,
      alpha: 0.15 + Math.random() * 0.25,
      drift: (Math.random() - 0.5) * 0.3,
    }));

    let raf = null;
    let lastFrame = 0;
    const FRAME_INTERVAL = 1000 / 30;

    function draw() {
      const w = W(), h = H();
      gradient(ctx, w, h, [[0, '#0a2540'], [1, '#1e5780']]);

      // Diagonal light rays
      ctx.save();
      ctx.globalAlpha = 0.06;
      ctx.fillStyle = '#ffffff';
      for (let i = 0; i < 4; i++) {
        const x = (i / 4) * w;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x + 200, 0);
        ctx.lineTo(x + 400 + (i * 50), h);
        ctx.lineTo(x + 200 + (i * 50), h);
        ctx.closePath();
        ctx.fill();
      }
      ctx.restore();

      bubbles.update(
        (b) => { b.y -= b.vy; b.x += b.drift; },
        (b) => b.y < -10,
      );
      bubbles.draw((ctx, b) => {
        ctx.beginPath();
        ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${b.alpha})`;
        ctx.fill();
      }, ctx);
    }

    function loop(now) {
      if (now - lastFrame >= FRAME_INTERVAL) { draw(); lastFrame = now; }
      raf = requestAnimationFrame(loop);
    }
    raf = requestAnimationFrame(loop);

    return () => { if (raf) cancelAnimationFrame(raf); };
  },
};
