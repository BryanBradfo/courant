import { Particles, gradient } from './_helpers.js';

export default {
  theme: 'dark',

  init(canvas, ctx) {
    const W = () => window.innerWidth;
    const H = () => window.innerHeight;

    const drops = new Particles(150, () => ({
      x: Math.random() * W(),
      y: -10 - Math.random() * H(),
      length: 8 + Math.random() * 20,
      speed: 6 + Math.random() * 8,
      alpha: 0.2 + Math.random() * 0.3,
      // Each drop has a trailing streak (the ruissellement effect)
      streak: 30 + Math.random() * 50,
    }));

    let raf = null;
    let lastFrame = 0;
    const FRAME_INTERVAL = 1000 / 30;

    function draw() {
      const w = W(), h = H();

      // Dark gray-blue sky
      gradient(ctx, w, h, [[0, '#1a2332'], [1, '#3d556e']]);

      // Warm interior light glow in bottom-right corner
      const glow = ctx.createRadialGradient(w * 0.85, h * 0.9, 0, w * 0.85, h * 0.9, 400);
      glow.addColorStop(0, 'rgba(232, 213, 168, 0.25)');
      glow.addColorStop(1, 'rgba(232, 213, 168, 0)');
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, w, h);

      // Rain streaks
      ctx.lineWidth = 1;
      drops.draw((ctx, d) => {
        ctx.strokeStyle = `rgba(200, 220, 240, ${d.alpha})`;
        ctx.beginPath();
        ctx.moveTo(d.x, d.y);
        ctx.lineTo(d.x - d.length * 0.2, d.y + d.length);
        ctx.stroke();
      }, ctx);

      drops.update(
        (d) => { d.y += d.speed; d.x -= d.speed * 0.2; },
        (d) => d.y > h + 20,
      );
    }

    function loop(now) {
      if (now - lastFrame >= FRAME_INTERVAL) { draw(); lastFrame = now; }
      raf = requestAnimationFrame(loop);
    }
    raf = requestAnimationFrame(loop);

    return () => { if (raf) cancelAnimationFrame(raf); };
  },
};
