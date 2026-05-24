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

  // Bootstrap on DOMContentLoaded so we don't race the markup
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      initCopyButtons();
      initScrollReveal();
      initVideoFallback();
    });
  } else {
    initCopyButtons();
    initScrollReveal();
    initVideoFallback();
  }
})();
