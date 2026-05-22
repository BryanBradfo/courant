import { Particles, gradient } from './_helpers.js';

export default {
  theme: 'dark',

  init(canvas, ctx) {
    const W = () => window.innerWidth;
    const H = () => window.innerHeight;

    const leaves = new Particles(40, () => ({
      x: Math.random() * W(),
      y: -10,
      vy: 0.3 + Math.random() * 0.5,
      vx: (Math.random() - 0.5) * 0.4,
      rot: Math.random() * Math.PI * 2,
      vrot: (Math.random() - 0.5) * 0.05,
      size: 5 + Math.random() * 6,
      color: ['#c4945c', '#b8702f', '#9d5e1f', '#e8b569'][Math.floor(Math.random() * 4)],
    }));

    let raf = null;
    let lastFrame = 0;
    const FRAME_INTERVAL = 1000 / 30;

    function draw() {
      const w = W(), h = H();

      // Green forest gradient
      gradient(ctx, w, h, [[0, '#2d3e2f'], [1, '#5a7a5d']]);

      // Vertical god-rays (subtle)
      ctx.save();
      ctx.globalAlpha = 0.05;
      ctx.fillStyle = '#e8d090';
      for (let i = 0; i < 3; i++) {
        const x = (i / 3 + 0.15) * w;
        ctx.beginPath();
        ctx.moveTo(x - 40, 0);
        ctx.lineTo(x + 40, 0);
        ctx.lineTo(x + 100, h);
        ctx.lineTo(x - 100, h);
        ctx.closePath();
        ctx.fill();
      }
      ctx.restore();

      // Leaves
      leaves.draw((ctx, l) => {
        ctx.save();
        ctx.translate(l.x, l.y);
        ctx.rotate(l.rot);
        ctx.fillStyle = l.color;
        ctx.globalAlpha = 0.85;
        ctx.beginPath();
        ctx.ellipse(0, 0, l.size, l.size * 0.6, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }, ctx);

      leaves.update(
        (l) => { l.y += l.vy; l.x += l.vx; l.rot += l.vrot; },
        (l) => l.y > h + 20,
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
