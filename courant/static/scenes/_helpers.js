// Shared helpers for scenes. Import as :
//   import { Particles, gradient } from './_helpers.js';

export function gradient(ctx, w, h, stops) {
  const g = ctx.createLinearGradient(0, 0, 0, h);
  for (const [pos, color] of stops) g.addColorStop(pos, color);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);
}

export class Particles {
  constructor(count, spawnFn) {
    this.spawn = spawnFn;
    this.items = Array.from({ length: count }, () => spawnFn());
  }

  update(updateFn, respawnPredicate) {
    for (const p of this.items) {
      updateFn(p);
      if (respawnPredicate(p)) Object.assign(p, this.spawn());
    }
  }

  draw(drawFn, ctx) {
    for (const p of this.items) drawFn(ctx, p);
  }
}
