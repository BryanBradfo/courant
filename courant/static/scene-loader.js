// scene-loader.js — manages the video background.
//
// Reads /api/scenes to know the registry, then loads the URL for the
// currently selected scene (server-rendered in body.dataset.scene).

const video = document.getElementById('scene-video');
let scenes = {};

async function loadRegistry() {
  try {
    const resp = await fetch('/api/scenes');
    scenes = await resp.json();
  } catch (e) {
    console.warn('Failed to load scene registry', e);
  }
}

async function loadScene(slug) {
  if (!video) return;
  const scene = scenes[slug];
  if (!scene || !scene.url) {
    console.warn(`Scene "${slug}" has no usable URL — showing fallback`);
    video.style.opacity = '0';
    document.body.classList.remove('scene-dark', 'scene-light');
    document.body.classList.add('scene-dark');
    return;
  }

  // Crossfade : fade out, swap src, wait for canplay, fade in
  video.style.opacity = '0';
  await new Promise(r => setTimeout(r, 400));

  video.src = scene.url;
  document.body.classList.remove('scene-dark', 'scene-light');
  document.body.classList.add(scene.theme === 'light' ? 'scene-light' : 'scene-dark');

  // Wait for the first frame to be ready, then fade in
  video.addEventListener('canplay', () => {
    video.style.opacity = '1';
  }, { once: true });

  video.addEventListener('error', () => {
    console.warn(`Failed to load video for scene "${slug}"`);
    video.style.opacity = '0';  // Show gradient fallback
  }, { once: true });

  // Try to start playback
  try {
    await video.play();
  } catch (e) {
    console.warn('Video autoplay failed', e);
  }
}

(async () => {
  await loadRegistry();
  const initial = document.body.dataset.scene || 'night-train';
  await loadScene(initial);
})();

// Pause video when tab is hidden (battery friendliness)
document.addEventListener('visibilitychange', () => {
  if (!video) return;
  if (document.hidden) {
    video.pause();
  } else {
    video.play().catch(() => {});
  }
});

// Expose for scene selector
window.courantLoadScene = loadScene;
