// scene-loader.js — dynamically loads scene modules and renders them on #scene-canvas.
//
// A scene module exports default object {
//   init(canvas, ctx),  // start animation loop, return cleanup function
//   theme: 'dark' | 'light',
// }
//
// init() should call requestAnimationFrame internally and return a cleanup fn
// that cancels the loop. The loader manages crossfade between scenes.

const canvas = document.getElementById('scene-canvas');
if (canvas) {
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);
}

let currentCleanup = null;

function resizeCanvas() {
  if (!canvas) return;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = window.innerWidth * dpr;
  canvas.height = window.innerHeight * dpr;
  canvas.style.width = `${window.innerWidth}px`;
  canvas.style.height = `${window.innerHeight}px`;
  const ctx = canvas.getContext('2d');
  if (ctx) ctx.scale(dpr, dpr);
}

async function loadScene(name) {
  if (!canvas) return;

  // Tear down previous scene
  if (currentCleanup) {
    try { currentCleanup(); } catch (e) { console.warn('scene cleanup error', e); }
    currentCleanup = null;
  }

  // Crossfade: fade out, swap, fade in
  canvas.style.opacity = '0';
  await new Promise(resolve => setTimeout(resolve, 400));

  // Clear canvas
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  let module;
  try {
    module = await import(`/static/scenes/${name}.js`);
  } catch (e) {
    console.error(`Failed to load scene "${name}"`, e);
    canvas.style.opacity = '1';
    return;
  }

  const scene = module.default;
  document.body.classList.remove('scene-dark', 'scene-light');
  document.body.classList.add(scene.theme === 'light' ? 'scene-light' : 'scene-dark');

  currentCleanup = scene.init(canvas, ctx);
  canvas.style.opacity = '1';
}

// Boot: read scene from body data attribute (server-rendered)
const initialScene = document.body.dataset.scene || 'ocean-depth';
loadScene(initialScene);

// Pause animations when tab is hidden
document.addEventListener('visibilitychange', () => {
  if (document.hidden && currentCleanup) {
    currentCleanup();
    currentCleanup = null;
  } else if (!document.hidden && !currentCleanup) {
    loadScene(document.body.dataset.scene || 'ocean-depth');
  }
});

// Expose for the scene selector
window.courantLoadScene = loadScene;
