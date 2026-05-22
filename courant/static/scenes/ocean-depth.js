// Ocean depth — bubbles rising slowly through a blue gradient with diagonal light rays.

export default {
  theme: 'dark',

  init(canvas, ctx) {
    const W = () => window.innerWidth;
    const H = () => window.innerHeight;

    // Pre-allocate bubbles
    const BUBBLE_COUNT = 80;
    const bubbles = Array.from({ length: BUBBLE_COUNT }, () => spawnBubble(H()));

    let raf = null;
    let lastFrame = 0;
    const TARGET_FPS = 30;
    const FRAME_INTERVAL = 1000 / TARGET_FPS;

    function spawnBubble(maxY) {
      return {
        x: Math.random() * W(),
        y: maxY + Math.random() * 100,
        r: 1 + Math.random() * 4,
        vy: 0.3 + Math.random() * 0.6,
        alpha: 0.15 + Math.random() * 0.25,
        drift: (Math.random() - 0.5) * 0.3,
      };
    }

    function draw() {
      const w = W(), h = H();

      // Background gradient : deep navy → mid blue
      const grad = ctx.createLinearGradient(0, 0, 0, h);
      grad.addColorStop(0, '#0a2540');
      grad.addColorStop(1, '#1e5780');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);

      // Diagonal light rays (subtle)
      ctx.save();
      ctx.globalAlpha = 0.06;
      ctx.fillStyle = '#ffffff';
      for (let i = 0; i < 4; i++) {
        const offset = (i / 4) * w;
        ctx.beginPath();
        ctx.moveTo(offset, 0);
        ctx.lineTo(offset + 200, 0);
        ctx.lineTo(offset + 400 + (i * 50), h);
        ctx.lineTo(offset + 200 + (i * 50), h);
        ctx.closePath();
        ctx.fill();
      }
      ctx.restore();

      // Bubbles
      for (const b of bubbles) {
        ctx.beginPath();
        ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${b.alpha})`;
        ctx.fill();

        b.y -= b.vy;
        b.x += b.drift;
        if (b.y < -10) {
          Object.assign(b, spawnBubble(h));
          b.y = h + 10;
        }
      }
    }

    function loop(now) {
      if (now - lastFrame >= FRAME_INTERVAL) {
        draw();
        lastFrame = now;
      }
      raf = requestAnimationFrame(loop);
    }
    raf = requestAnimationFrame(loop);

    return function cleanup() {
      if (raf) cancelAnimationFrame(raf);
    };
  },
};
