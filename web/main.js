// Courant landing page — vanilla JS interactions.
// No dependencies. All behavior is progressive enhancement: the page works
// without this script, it just won't reveal-on-scroll or copy via clicks.

(function () {
  'use strict';

  /**
   * initCopyButtons
   * Wire up every [data-copy] element so clicking copies its `data-copy`
   * value to the clipboard and briefly shows a "Copied!" state.
   */
  function initCopyButtons() {
    const buttons = document.querySelectorAll('[data-copy]');
    buttons.forEach((btn) => {
      btn.addEventListener('click', async () => {
        const text = btn.getAttribute('data-copy') || '';
        const ok = await copyText(text);
        if (ok) {
          btn.classList.add('copied');
          // Clear after 2s so user can copy again
          window.setTimeout(() => btn.classList.remove('copied'), 2000);
        }
      });
    });
  }

  /**
   * copyText
   * Try the modern Clipboard API first, fall back to a hidden textarea
   * + document.execCommand('copy') for older browsers / insecure contexts.
   * Returns true on success.
   */
  async function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch (err) {
        // Fall through to the legacy fallback
      }
    }
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.top = '-1000px';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      const success = document.execCommand('copy');
      document.body.removeChild(ta);
      return success;
    } catch (err) {
      return false;
    }
  }

  /**
   * initScrollReveal
   * Attach an IntersectionObserver to every [data-reveal] element so the
   * `.revealed` class is added when it scrolls into view. Skip entirely
   * if the user has requested reduced motion.
   */
  function initScrollReveal() {
    const prefersReduced =
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) return;

    const targets = document.querySelectorAll('[data-reveal]');
    if (!('IntersectionObserver' in window)) {
      // Old browser — reveal everything up-front
      targets.forEach((el) => el.classList.add('revealed'));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('revealed');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
    );

    targets.forEach((el) => observer.observe(el));
  }

  /**
   * Ambient audio tracks served from the audio-v1 GitHub release.
   * Keep slug list in sync with courant/data/audio.json in the main app.
   */
  const AUDIO_TRACKS = {
    'cozy-night': {
      name: 'Cozy Night',
      author: 'fassounds',
      url: 'https://github.com/BryanBradfo/courant/releases/download/audio-v1/cozy-night.mp3',
    },
    'mellow': {
      name: 'Mellow Lofi',
      author: 'leberch',
      url: 'https://github.com/BryanBradfo/courant/releases/download/audio-v1/mellow.mp3',
    },
    'study': {
      name: 'Study Time',
      author: 'Lofi Music Library',
      url: 'https://github.com/BryanBradfo/courant/releases/download/audio-v1/study.mp3',
    },
    'focus': {
      name: 'Deep Focus',
      author: 'pulsebox',
      url: 'https://github.com/BryanBradfo/courant/releases/download/audio-v1/focus.mp3',
    },
    'daydream': {
      name: 'Daydream',
      author: 'pulsebox',
      url: 'https://github.com/BryanBradfo/courant/releases/download/audio-v1/daydream.mp3',
    },
    'jazzy': {
      name: 'Jazzy Love',
      author: 'sonican',
      url: 'https://github.com/BryanBradfo/courant/releases/download/audio-v1/jazzy.mp3',
    },
  };

  const AUDIO_ORDER = ['cozy-night', 'mellow', 'study', 'focus', 'daydream', 'jazzy'];

  const LS_SLUG = 'courant_landing_audio_slug';
  const LS_VOLUME = 'courant_landing_audio_volume';

  function safeGet(key) {
    try { return window.localStorage.getItem(key); } catch (e) { return null; }
  }
  function safeSet(key, value) {
    try { window.localStorage.setItem(key, value); } catch (e) { /* private mode */ }
  }

  /**
   * initAudioPlayer
   * Wire the Spotify-style mini-player. Streams the selected mp3 from the
   * audio-v1 GitHub release. Prev/next buttons cycle through AUDIO_ORDER.
   * Persists the last track + volume in localStorage. Never autoplays.
   */
  function initAudioPlayer() {
    const player = document.getElementById('audio-player');
    if (!player) return;
    const audio = document.getElementById('audio-element');
    const toggle = document.getElementById('audio-toggle');
    const titleEl = document.getElementById('audio-track-title');
    const artistEl = document.getElementById('audio-track-artist');
    const prevBtn = document.getElementById('audio-prev');
    const nextBtn = document.getElementById('audio-next');

    let currentSlug = null;

    function showStopped() {
      toggle.classList.remove('is-playing');
      toggle.setAttribute('aria-label', 'Play ambient audio');
    }
    function showPlaying() {
      toggle.classList.add('is-playing');
      toggle.setAttribute('aria-label', 'Pause ambient audio');
    }

    function setMeta(slug) {
      if (slug && AUDIO_TRACKS[slug]) {
        titleEl.textContent = AUDIO_TRACKS[slug].name;
        artistEl.textContent = AUDIO_TRACKS[slug].author;
      } else {
        titleEl.textContent = 'Lofi';
        artistEl.textContent = 'Courant ambient';
      }
    }

    function loadTrack(slug, autoPlay) {
      if (!slug || !AUDIO_TRACKS[slug]) {
        audio.pause();
        audio.removeAttribute('src');
        currentSlug = null;
        setMeta(null);
        showStopped();
        safeSet(LS_SLUG, '');
        return;
      }
      audio.src = AUDIO_TRACKS[slug].url;
      currentSlug = slug;
      setMeta(slug);
      safeSet(LS_SLUG, slug);
      if (!autoPlay) { showStopped(); return; }
      const p = audio.play();
      if (p && typeof p.then === 'function') {
        p.then(showPlaying).catch(showStopped);
      }
    }

    function cycleTrack(direction) {
      const len = AUDIO_ORDER.length;
      const baseIdx = currentSlug ? AUDIO_ORDER.indexOf(currentSlug) : -1;
      const nextIdx = (baseIdx + direction + len) % len;
      loadTrack(AUDIO_ORDER[nextIdx], true);
    }

    toggle.addEventListener('click', () => {
      if (!audio.src) {
        loadTrack(AUDIO_ORDER[0], true);
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
    audio.addEventListener('ended', showStopped); // loop is on, just defensive

    // Restore previous state (no autoplay; browsers block it)
    const savedVolume = safeGet(LS_VOLUME);
    audio.volume = savedVolume !== null ? Number(savedVolume) / 100 : 0.5;
    const savedSlug = safeGet(LS_SLUG);
    if (savedSlug && AUDIO_TRACKS[savedSlug]) {
      loadTrack(savedSlug, false);
    } else {
      setMeta(null);
    }
  }

  /**
   * initVideoFallback
   * If the hero <video> errors (e.g., the GitHub release URL is unreachable
   * or the file 404s), tag <body> with .video-failed so the CSS swaps in a
   * static gradient instead of a black box.
   */
  function initVideoFallback() {
    const video = document.getElementById('hero-video');
    if (!video) return;

    const markFailed = () => document.body.classList.add('video-failed');

    // The <source> element fires `error`, not the <video> itself, in most
    // browsers when the resource fails to load. Listen on both for safety.
    const sources = video.querySelectorAll('source');
    sources.forEach((s) => s.addEventListener('error', markFailed, { once: true }));
    video.addEventListener('error', markFailed, { once: true });

    // Backstop: if metadata never loads within a few seconds, give up.
    window.setTimeout(() => {
      if (video.readyState === 0) markFailed();
    }, 6000);
  }

  function bootstrap() {
    initCopyButtons();
    initScrollReveal();
    initVideoFallback();
    initAudioPlayer();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrap);
  } else {
    bootstrap();
  }
})();
