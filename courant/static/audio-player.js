// audio-player.js — manages the ambient audio mini-player.

const player = document.getElementById('audio-player');
const audio = document.getElementById('audio-element');
const toggle = document.getElementById('audio-toggle');
const trackName = document.getElementById('audio-track-name');
const select = document.getElementById('audio-select');
const volume = document.getElementById('audio-volume');

let tracks = {};

async function loadTrackList() {
  try {
    const resp = await fetch('/api/audio');
    tracks = await resp.json();
    // Populate select
    for (const [slug, meta] of Object.entries(tracks)) {
      const opt = document.createElement('option');
      opt.value = slug;
      opt.textContent = meta.name;
      select.appendChild(opt);
    }
  } catch (e) {
    console.warn('Failed to load audio registry', e);
  }
}

function setTrack(slug) {
  if (!slug) {
    audio.pause();
    audio.removeAttribute('src');
    trackName.textContent = '—';
    toggle.textContent = '♪';
    return;
  }
  const meta = tracks[slug];
  if (!meta) return;
  audio.src = meta.url;
  trackName.textContent = meta.name;
  audio.play().then(() => {
    toggle.textContent = '⏸';
    localStorage.setItem('courant_audio_slug', slug);
  }).catch((err) => {
    console.warn('Audio play failed (file missing?)', err);
    toggle.textContent = '♪';
  });
}

toggle.addEventListener('click', () => {
  if (!audio.src) return;
  if (audio.paused) {
    audio.play();
    toggle.textContent = '⏸';
  } else {
    audio.pause();
    toggle.textContent = '♪';
  }
});

select.addEventListener('change', (e) => {
  setTrack(e.target.value);
});

volume.addEventListener('input', (e) => {
  audio.volume = e.target.value / 100;
  localStorage.setItem('courant_audio_volume', e.target.value);
});

// Restore last state
(async () => {
  await loadTrackList();
  const savedVolume = localStorage.getItem('courant_audio_volume');
  if (savedVolume) {
    volume.value = savedVolume;
    audio.volume = savedVolume / 100;
  }
  const savedSlug = localStorage.getItem('courant_audio_slug');
  if (savedSlug && tracks[savedSlug]) {
    select.value = savedSlug;
    // Don't autoplay — browsers block autoplay with sound. User must click play.
    audio.src = tracks[savedSlug].url;
    trackName.textContent = tracks[savedSlug].name;
  }
})();
