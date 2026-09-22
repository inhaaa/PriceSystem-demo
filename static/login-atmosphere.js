/** Fullscreen decoration only: never reads credentials or captures input. */
export function createTapTracker({ maxDistance = 8, maxDuration = 600 } = {}) {
  let start = null;
  const valid = event => event.isPrimary && event.button === 0;
  const move = event => {
    if (start && start.id === event.pointerId &&
        Math.hypot(event.clientX - start.x, event.clientY - start.y) > maxDistance) {
      start.moved = true;
    }
  };
  return {
    begin(event, excluded = false) {
      start = !excluded && valid(event) ? {
        id: event.pointerId, x: event.clientX, y: event.clientY,
        time: event.timeStamp, moved: false,
      } : null;
    },
    move,
    cancel() { start = null; },
    finish(event, excluded = false) {
      if (!start || start.id !== event.pointerId) return false;
      move(event);
      const elapsed = event.timeStamp - start.time;
      const accepted = !excluded && valid(event) && !start.moved &&
        elapsed >= 0 && elapsed <= maxDuration;
      start = null;
      return accepted;
    },
  };
}

export function isLoginInput(target) {
  // Includes labels, input padding and the password reveal button, not the form.
  return Boolean(target?.closest?.(
    '[data-testid="stTextInput"], input, textarea, select, [contenteditable="true"], [role="textbox"]'
  ));
}

export function sceneScrollProgress(scrollTop, viewportHeight, compact = false, reduced = false) {
  if (compact || reduced || !Number.isFinite(scrollTop) ||
      !Number.isFinite(viewportHeight) || viewportHeight <= 0) return 0;
  return Math.max(0, Math.min(1, scrollTop / viewportHeight));
}

const RINGS = [
  { size: "9rem", dur: 620, delay: 0, peak: 0.95, hole: "58%", rim: "76%", edge: 0.38 },
  { size: "15rem", dur: 880, delay: 120, peak: 0.7, hole: "66%", rim: "81%", edge: 0.26 },
  { size: "23rem", dur: 1150, delay: 260, peak: 0.4, hole: "72%", rim: "85%", edge: 0.16 },
];

/** Mount on the login viewport. Returns an idempotent rerun/unmount disposer. */
export function mountLoginAtmosphere({ root, panel, layer }) {
  const doc = root.ownerDocument;
  const win = doc.defaultView;
  const motion = win.matchMedia("(prefers-reduced-motion: reduce)");
  const tracker = createTapTracker();
  const bursts = new Set();
  const listeners = [];
  let disposed = false;
  let frame = 0;
  let width = win.innerWidth || 1;
  let height = win.innerHeight || 1;
  let targetX = width / 2;
  let targetY = height / 2;
  let x = targetX;
  let y = targetY;
  const scroller = panel.closest('[data-testid="stMain"]') || root;
  let targetScroll = 0;
  let currentScroll = 0;
  const updateScroll = () => {
    targetScroll = sceneScrollProgress(scroller.scrollTop, height, width <= 768, motion.matches);
  };
  const enabled = () => !disposed && !motion.matches && !doc.hidden;
  const listen = (target, name, handler) => {
    const options = { passive: true, capture: true };
    target.addEventListener(name, handler, options);
    listeners.push(() => target.removeEventListener(name, handler, options));
  };
  const paint = () => {
    layer.style.setProperty("--login-glow-x", x.toFixed(1) + "px");
    layer.style.setProperty("--login-glow-y", y.toFixed(1) + "px");
    const nx = Math.max(-0.5, Math.min(0.5, x / width - 0.5));
    const ny = Math.max(-0.5, Math.min(0.5, y / height - 0.5));
    layer.style.setProperty("--atmo-x", (nx * -28).toFixed(2) + "px");
    layer.style.setProperty("--atmo-y", (ny * -20).toFixed(2) + "px");
    layer.style.setProperty("--light-x", (50 + nx * 12).toFixed(2) + "%");
    layer.style.setProperty("--light-y", (28 + ny * 10).toFixed(2) + "%");
    layer.style.setProperty("--scene-scroll", currentScroll.toFixed(4));
    win.__psLoginScene = { scroll: currentScroll };
    const tiltX = nx * 18;
    const tiltY = ny * -12;
    panel.style.setProperty("--login-tilt-x", tiltX.toFixed(2) + "deg");
    panel.style.setProperty("--login-tilt-y", tiltY.toFixed(2) + "deg");
    win.__psLoginPointer = { tiltX, tiltY };
  };
  const tick = () => {
    frame = 0;
    if (!enabled()) return;
    const dx = targetX - x;
    const dy = targetY - y;
    x += dx * 0.085;
    y += dy * 0.085;
    currentScroll += (targetScroll - currentScroll) * 0.075;
    paint();
    if (Math.abs(dx) > 0.4 || Math.abs(dy) > 0.4 ||
        Math.abs(targetScroll - currentScroll) > 0.001) frame = win.requestAnimationFrame(tick);
  };
  const kick = () => {
    if (!frame && enabled()) frame = win.requestAnimationFrame(tick);
  };
  const clearBursts = () => { for (const burst of [...bursts]) burst.remove(); };
  const reset = () => {
    tracker.cancel();
    targetX = width / 2;
    targetY = height / 2;
    layer.dataset.glow = "off";
    panel.dataset.glow = "off";
    kick();
  };
  const aim = event => {
    targetX = event.clientX;
    targetY = event.clientY;
    layer.dataset.glow = "on";
    panel.dataset.glow = panel.contains(event.target) ? "on" : "off";
    kick();
  };
  const splash = event => {
    // Bounded transient nodes/timers, even with rapid tapping.
    if (bursts.size >= 6) bursts.values().next().value.remove();
    const group = doc.createElement("div");
    group.className = "login-atmosphere__burst";
    group.setAttribute("aria-hidden", "true");
    group.style.setProperty("--ripple-x", event.clientX.toFixed(1) + "px");
    group.style.setProperty("--ripple-y", event.clientY.toFixed(1) + "px");
    for (const spec of RINGS) {
      const ring = doc.createElement("span");
      ring.className = "login-panel__ripple";
      for (const [key, value] of Object.entries(spec)) {
        ring.style.setProperty("--ripple-" + key,
          (key === "dur" || key === "delay") ? value + "ms" : String(value));
      }
      group.appendChild(ring);
    }
    for (let i = 0; i < 7; i += 1) {
      const angle = (i / 7) * Math.PI * 2 + Math.random() * 0.5;
      const reach = 34 + Math.random() * 40;
      const drop = doc.createElement("span");
      drop.className = "login-panel__drop";
      drop.style.setProperty("--drop-dx", (Math.cos(angle) * reach).toFixed(1) + "px");
      drop.style.setProperty("--drop-dy", (Math.sin(angle) * reach * 0.72).toFixed(1) + "px");
      drop.style.setProperty("--drop-lift", (10 + Math.random() * 12).toFixed(1) + "px");
      drop.style.setProperty("--drop-dur", (620 + Math.round(Math.random() * 260)) + "ms");
      drop.style.setProperty("--drop-delay", Math.round(Math.random() * 90) + "ms");
      group.appendChild(drop);
    }
    const burst = { remove() {
      win.clearTimeout(burst.timer);
      group.remove();
      bursts.delete(burst);
    } };
    burst.timer = win.setTimeout(() => burst.remove(), 1850);
    bursts.add(burst);
    layer.appendChild(group);
  };
  const onDown = event => {
    if (!enabled()) return;
    const excluded = isLoginInput(event.target);
    tracker.begin(event, excluded);
    if (excluded) reset();
    else if (event.isPrimary && event.button === 0) aim(event);
  };
  const onMove = event => {
    tracker.move(event);
    if (!enabled() || !event.isPrimary) return;
    if (isLoginInput(event.target)) reset();
    else aim(event);
  };
  const onUp = event => {
    if (enabled() && tracker.finish(event, isLoginInput(event.target))) splash(event);
    if (event.pointerType !== "mouse") reset();
  };
  const onResize = () => {
    width = win.innerWidth || 1;
    height = win.innerHeight || 1;
    updateScroll();
    reset();
  };
  const onScroll = () => {
    tracker.cancel();
    updateScroll();
    kick();
  };
  const revealObserver = typeof win.IntersectionObserver === "function"
    ? new win.IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.dataset.revealed = "true";
        revealObserver.unobserve(entry.target);
      }
    }, { threshold: 0.08 }) : null;
  const reveals = new Set();
  const watchReveals = () => {
    for (const element of root.querySelectorAll(
      ".login-masthead, .login-panel, .login-brand, .login-access-footer"
    )) {
      if (reveals.has(element)) continue;
      reveals.add(element);
      element.classList.add("login-reveal");
      element.dataset.revealed = String(!revealObserver || motion.matches);
      if (revealObserver && !motion.matches) revealObserver.observe(element);
    }
  };
  const onVisibility = () => {
    updateScroll();
    reset();
    layer.dataset.paused = String(!enabled());
    if (!enabled()) {
      win.cancelAnimationFrame(frame);
      frame = 0;
      clearBursts();
      x = targetX;
      y = targetY;
      currentScroll = targetScroll;
      paint();
    }
    if (motion.matches) {
      if (revealObserver) revealObserver.disconnect();
      for (const element of reveals) element.dataset.revealed = "true";
    }
  };
  // Passive listeners preserve text selection, native focus, submission and scroll.
  listen(root, "pointerdown", onDown);
  listen(root, "pointermove", onMove);
  listen(root, "pointerup", onUp);
  listen(root, "pointercancel", reset);
  listen(root, "pointerleave", event => { if (event.target === root) reset(); });
  listen(root, "scroll", onScroll);
  listen(win, "blur", reset);
  listen(win, "resize", onResize);
  listen(doc, "visibilitychange", onVisibility);
  listen(motion, "change", onVisibility);
  const observer = new win.MutationObserver(() => {
    if (!root.isConnected || !panel.isConnected || !layer.isConnected) dispose();
    else watchReveals();
  });
  const dispose = () => {
    if (disposed) return;
    disposed = true;
    tracker.cancel();
    win.cancelAnimationFrame(frame);
    observer.disconnect();
    if (revealObserver) revealObserver.disconnect();
    for (const element of reveals) {
      element.classList.remove("login-reveal");
      delete element.dataset.revealed;
    }
    reveals.clear();
    for (const remove of listeners) remove();
    clearBursts();
    layer.dataset.glow = "off";
    layer.dataset.paused = "true";
    delete panel.dataset.glow;
    win.__psLoginPointer = { tiltX: 0, tiltY: 0 };
    win.__psLoginScene = { scroll: 0 };
    panel.style.removeProperty("--login-tilt-x");
    panel.style.removeProperty("--login-tilt-y");
  };
  observer.observe(doc.body, { childList: true, subtree: true });
  updateScroll();
  watchReveals();
  paint();
  onVisibility();
  return dispose;
}
