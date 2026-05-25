// audio-player.js — Spotify-style mini-player wired to /api/audio.

(function () {
  'use strict';

  const player = document.getElementById('audio-player');
  if (!player) return;
  const audio = document.getElementById('audio-element');
  const toggle = document.getElementById('audio-toggle');
  const titleEl = document.getElementById('audio-track-title');
  const artistEl = document.getElementById('audio-track-artist');
  const prevBtn = document.getElementById('audio-prev');
  const nextBtn = document.getElementById('audio-next');

  const LS_SLUG = 'courant_audio_slug';
  const LS_VOLUME = 'courant_audio_volume';

  let tracks = {};
  let order = [];
  let currentSlug = null;

  function safeGet(key) {
    try { return window.localStorage.getItem(key); } catch (e) { return null; }
  }
  function safeSet(key, value) {
    try { window.localStorage.setItem(key, value); } catch (e) { /* private mode */ }
  }

  function showStopped() {
    toggle.classList.remove('is-playing');
    toggle.setAttribute('aria-label', 'Play ambient audio');
  }
  function showPlaying() {
    toggle.classList.add('is-playing');
    toggle.setAttribute('aria-label', 'Pause ambient audio');
  }

  function setMeta(slug) {
    if (slug && tracks[slug]) {
      titleEl.textContent = tracks[slug].name;
      artistEl.textContent = tracks[slug].author || 'Courant ambient';
    } else {
      titleEl.textContent = 'Lofi';
      artistEl.textContent = 'Courant ambient';
    }
  }

  function loadTrack(slug, autoPlay) {
    if (!slug || !tracks[slug]) {
      audio.pause();
      audio.removeAttribute('src');
      currentSlug = null;
      setMeta(null);
      showStopped();
      safeSet(LS_SLUG, '');
      return;
    }
    audio.src = tracks[slug].url;
    currentSlug = slug;
    setMeta(slug);
    safeSet(LS_SLUG, slug);
    if (!autoPlay) { showStopped(); return; }
    const p = audio.play();
    if (p && typeof p.then === 'function') {
      p.then(showPlaying).catch((err) => {
        console.warn('Audio play failed (file missing? run "courant install-audio")', err);
        showStopped();
      });
    }
  }

  function cycleTrack(direction) {
    if (order.length === 0) return;
    const baseIdx = currentSlug ? order.indexOf(currentSlug) : -1;
    const nextIdx = (baseIdx + direction + order.length) % order.length;
    loadTrack(order[nextIdx], true);
  }

  toggle.addEventListener('click', () => {
    if (!audio.src) {
      if (order.length > 0) loadTrack(order[0], true);
      return;
    }
    if (audio.paused) {
      const p = audio.play();
      if (p && typeof p.then === 'function') p.then(showPlaying).catch(showStopped);
    } else {
      audio.pause();
      showStopped();
    }
  });

  prevBtn.addEventListener('click', () => cycleTrack(-1));
  nextBtn.addEventListener('click', () => cycleTrack(1));

  audio.addEventListener('play', showPlaying);
  audio.addEventListener('pause', () => { if (!audio.ended) showStopped(); });
  audio.addEventListener('ended', showStopped);

  async function bootstrap() {
    try {
      const resp = await fetch('/api/audio');
      tracks = await resp.json();
      order = Object.keys(tracks);
    } catch (e) {
      console.warn('Failed to load audio registry', e);
      return;
    }

    const savedVolume = safeGet(LS_VOLUME);
    audio.volume = savedVolume !== null ? Number(savedVolume) / 100 : 0.5;

    const savedSlug = safeGet(LS_SLUG);
    if (savedSlug && tracks[savedSlug]) {
      loadTrack(savedSlug, false);
    } else {
      setMeta(null);
    }
  }

  bootstrap();
})();
