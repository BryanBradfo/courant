import { gradient } from './_helpers.js';

export default {
  theme: 'light',

  init(canvas, ctx) {
    const W = () => window.innerWidth;
    const H = () => window.innerHeight;

    let raf = null;
    let lastFrame = 0;
    let t = 0;
    const FRAME_INTERVAL = 1000 / 30;

    function draw() {
      const w = W(), h = H();

      // Vertical gradient : orange → pink → violet
      gradient(ctx, w, h, [
        [0,    '#fdb585'],
        [0.4,  '#e89bb0'],
        [0.7,  '#c66a8e'],
        [1,    '#5c4a7a'],
      ]);

      // Sun — large soft circle near horizon
      const sunY = h * 0.7;
      const sunGrad = ctx.createRadialGradient(w / 2, sunY, 0, w / 2, sunY, 120);
      sunGrad.addColorStop(0, 'rgba(255, 230, 200, 0.9)');
      sunGrad.addColorStop(1, 'rgba(255, 200, 150, 0)');
      ctx.fillStyle = sunGrad;
      ctx.fillRect(0, 0, w, h);

      // Sea : darker band in lower third
      ctx.fillStyle = 'rgba(40, 30, 70, 0.4)';
      ctx.fillRect(0, h * 0.75, w, h * 0.25);

      // Animated waves (sine lines)
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
      ctx.lineWidth = 1.5;
      for (let layer = 0; layer < 4; layer++) {
        ctx.beginPath();
        const baseY = h * 0.78 + layer * 12;
        for (let x = 0; x <= w; x += 6) {
          const y = baseY + Math.sin((x + t * (1 + layer * 0.2)) * 0.015 + layer) * 6;
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }

      t += 1;
    }

    function loop(now) {
      if (now - lastFrame >= FRAME_INTERVAL) { draw(); lastFrame = now; }
      raf = requestAnimationFrame(loop);
    }
    raf = requestAnimationFrame(loop);

    return () => { if (raf) cancelAnimationFrame(raf); };
  },
};
