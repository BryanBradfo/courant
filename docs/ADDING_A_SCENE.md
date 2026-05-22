# Adding a new ambient scene to Courant

Each ambient scene is a single self-contained JavaScript file under
`courant/static/scenes/`. The framework calls a small contract on it,
nothing more. This is meant to be the most contributor-friendly entry
point in the codebase.

## The contract

Your scene file must `export default` an object with two members :

```javascript
export default {
  theme: 'dark',   // or 'light' — controls the glassmorphism panel contrast

  init(canvas, ctx) {
    // canvas : the DOM canvas element, already DPI-scaled
    // ctx    : the 2D rendering context

    // Set up your animation loop with requestAnimationFrame.
    // Return a cleanup function that cancels the loop.

    let raf = requestAnimationFrame(function loop() {
      // ... draw your frame here ...
      raf = requestAnimationFrame(loop);
    });

    return function cleanup() {
      cancelAnimationFrame(raf);
    };
  },
};
```

## Helpers

`courant/static/scenes/_helpers.js` exposes :

- `gradient(ctx, w, h, stops)` — draws a vertical gradient fill across the canvas
- `Particles` — a small particle pool (constructor takes count + spawn fn ; methods `update(updateFn, respawnPredicate)` and `draw(drawFn, ctx)`)

Import them as `import { Particles, gradient } from './_helpers.js';`.

## Performance

- Cap your loop at 30 fps for battery friendliness. The existing scenes use a `lastFrame` timestamp + `FRAME_INTERVAL` pattern — copy it.
- Avoid creating new objects in the inner loop. Use the `Particles` pool.
- The scene loader pauses your loop automatically when the tab is hidden.
- Respect `prefers-reduced-motion` : the global CSS rule already disables animations for those users, but if you do heavy work in `init` you should bail early.

## Registering the scene

Add the slug (the filename without `.js`) to two places :

1. `AVAILABLE_SCENES` in `courant/web.py` — gates the settings dropdown
2. Optionally `docs/superpowers/specs/2026-05-21-courant-design.md` — for the
   design palette reference table

## Style guidance

- Use a tight palette : 2-4 hex codes max. The existing scenes hold to this.
- Avoid pure white. `#f5f5f5` or warm whites (`#fff8d9`) feel cozier.
- Subtle motion beats showy motion. Bubbles drift, rain falls at an angle,
  stars twinkle slowly — none of this jumps or flashes.
- Test on both bright and dim screens. Glassmorphism contrast can be fragile.

## Submitting

Open a PR with :
- Your scene file
- A short description of the vibe you were going for
- A screenshot or short GIF if possible

We welcome variety. Different cultures, different times of day, different
weather, different planets — all good.
