// sse-notifier.js -- live in-page notifications driven by /api/stream.
//
// When the daemon fires a reminder, this script renders a glassmorphism
// toast top-right and plays a short Web Audio chime. Complementary to the
// D-Bus desktop notification, not a replacement.
//
// Built entirely via DOM methods (no innerHTML), so the reminder name and
// message - which come from user-edited reminder rows - cannot be used to
// inject HTML into the page.

(function () {
  'use strict';

  const root = document.getElementById('toast-root');
  if (!root) return;

  const TOAST_TTL_MS = 30_000;
  let audioCtx = null;

  function getAudioContext() {
    if (audioCtx) return audioCtx;
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return null;
    audioCtx = new Ctx();
    return audioCtx;
  }

  function playChime() {
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return;
    }
    const ctx = getAudioContext();
    if (!ctx) return;
    const now = ctx.currentTime;
    const tones = [
      { freq: 660, start: 0, dur: 0.18 },
      { freq: 880, start: 0.16, dur: 0.22 },
    ];
    tones.forEach((t) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = t.freq;
      gain.gain.setValueAtTime(0, now + t.start);
      gain.gain.linearRampToValueAtTime(0.18, now + t.start + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, now + t.start + t.dur);
      osc.connect(gain).connect(ctx.destination);
      osc.start(now + t.start);
      osc.stop(now + t.start + t.dur + 0.05);
    });
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function buildActionForm(reminderId, kind, label) {
    const form = el('form', 'toast-action-form');
    form.setAttribute('hx-post', '/api/events');
    form.setAttribute('hx-swap', 'none');

    const rid = el('input');
    rid.type = 'hidden';
    rid.name = 'reminder_id';
    rid.value = String(reminderId);
    form.appendChild(rid);

    const k = el('input');
    k.type = 'hidden';
    k.name = 'kind';
    k.value = kind;
    form.appendChild(k);

    const btn = el('button', 'toast-action', label);
    btn.type = 'submit';
    form.appendChild(btn);
    return form;
  }

  function renderToast(event) {
    const node = el('div', 'toast');
    node.setAttribute('role', 'status');
    node.setAttribute('aria-live', 'polite');

    const body = el('div', 'toast-body');
    body.appendChild(el('div', 'toast-title', event.name || 'Reminder'));
    body.appendChild(el('div', 'toast-message', event.message || ''));
    node.appendChild(body);

    const actions = el('div', 'toast-actions');
    const ackLabel = (event.tracked && event.unit_label)
      ? '+1 ' + event.unit_label
      : 'Done';
    actions.appendChild(buildActionForm(event.reminder_id, 'ack', ackLabel));
    actions.appendChild(buildActionForm(event.reminder_id, 'snooze', 'Snooze'));
    node.appendChild(actions);

    const close = el('button', 'toast-close', '×');
    close.type = 'button';
    close.setAttribute('aria-label', 'Dismiss');
    node.appendChild(close);

    const dismiss = () => {
      node.classList.add('is-leaving');
      setTimeout(() => node.remove(), 250);
    };

    close.addEventListener('click', dismiss);
    node.querySelectorAll('.toast-action').forEach((btn) => {
      btn.addEventListener('click', () => setTimeout(dismiss, 60));
    });
    setTimeout(dismiss, TOAST_TTL_MS);

    root.appendChild(node);
    if (window.htmx) window.htmx.process(node);
    requestAnimationFrame(() => node.classList.add('is-visible'));
  }

  function connect() {
    const source = new EventSource('/api/stream');
    source.onmessage = (msg) => {
      let event;
      try { event = JSON.parse(msg.data); } catch (e) { return; }
      if (event && event.type === 'reminder_fired') {
        renderToast(event);
        playChime();
      }
    };
    source.onerror = () => {
      // EventSource reconnects automatically per `retry` directive.
    };
  }

  connect();
})();
