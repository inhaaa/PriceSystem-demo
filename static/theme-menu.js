export default function({ parentElement, data }) {
  const anchor = parentElement.querySelector('.ps-theme-anchor');
  if (!anchor.themeTemplate) {
    anchor.themeTemplate = parentElement.querySelector('.ps-theme-tools');
    anchor.themeTemplate.remove();
  }
  anchor.themeDispose?.();
  const root = anchor.themeTemplate.cloneNode(true);
  const toggle = root.querySelector('.ps-theme-toggle');
  const panel = root.querySelector('.ps-theme-panel');
  const options = root.querySelector('.ps-theme-options');
  const fontOptions = root.querySelector('.ps-font-options');
  const names = data.themes.map(theme => theme.name);
  const normalizeTheme = name => Object.hasOwn(data.themeAliases || {}, name) ? data.themeAliases[name] : name;
  const valid = name => names.includes(name);
  let current = normalizeTheme(document.body.dataset.psColor);
  if (!valid(current)) {
    current = data.defaultTheme;
    try {
      const saved = normalizeTheme(localStorage.getItem(data.storageKey));
      if (valid(saved)) current = saved;
    } catch (_) { /* Browser storage may be disabled; the current page still works. */ }
  }
  document.body.dataset.psColor = current;
  const fontIds = data.fonts.map(font => font.id);
  const validFont = id => fontIds.includes(id);
  let currentFont = document.body.dataset.psFont;
  if (!validFont(currentFont)) {
    currentFont = data.defaultFont;
    try {
      const saved = localStorage.getItem(data.fontStorageKey);
      if (validFont(saved)) currentFont = saved;
    } catch (_) { /* Keep the default when browser storage is disabled. */ }
  }
  document.body.dataset.psFont = currentFont;
  syncNativeGridFont(currentFont, data.fontFaces);

  for (const theme of data.themes) {
    const label = document.createElement('label');
    label.className = 'ps-theme-option';
    const radio = document.createElement('input');
    radio.type = 'radio';
    radio.name = 'ps-theme-color';
    radio.value = theme.name;
    radio.setAttribute('aria-label', theme.name);
    const swatch = document.createElement('span');
    swatch.className = 'ps-theme-swatch';
    swatch.style.setProperty('--swatch-color', theme.color);
    swatch.style.setProperty('--swatch-ink', theme.ink);
    swatch.setAttribute('aria-hidden', 'true');
    label.append(radio, swatch, document.createTextNode(theme.name));
    options.append(label);
  }
  const radios = [...options.querySelectorAll('input')];
  for (const font of data.fonts) {
    const label = document.createElement('label');
    label.className = 'ps-theme-option ps-font-option';
    label.dataset.font = font.id;
    const radio = document.createElement('input');
    radio.type = 'radio';
    radio.name = 'ps-theme-font';
    radio.value = font.id;
    radio.setAttribute('aria-label', font.label);
    const check = document.createElement('span');
    check.className = 'ps-font-check';
    check.setAttribute('aria-hidden', 'true');
    label.append(radio, check, document.createTextNode(font.label));
    fontOptions.append(label);
  }
  const fontRadios = [...fontOptions.querySelectorAll('input')];
  const resetDraft = () => {
    radios.forEach(radio => { radio.checked = radio.value === current; });
    fontRadios.forEach(radio => { radio.checked = radio.value === currentFont; });
  };
  resetDraft();
  const close = (returnFocus = true) => {
    panel.hidden = true;
    toggle.setAttribute('aria-expanded', 'false');
    resetDraft();
    if (returnFocus) toggle.focus();
  };
  const onToggle = () => {
    if (!panel.hidden) return close();
    resetDraft();
    panel.hidden = false;
    toggle.setAttribute('aria-expanded', 'true');
    radios.find(radio => radio.checked).focus();
  };
  const onConfirm = () => {
    current = radios.find(radio => radio.checked).value;
    currentFont = fontRadios.find(radio => radio.checked).value;
    document.body.dataset.psColor = current;
    document.body.dataset.psFont = currentFont;
    syncNativeGridFont(currentFont, data.fontFaces);
    try { localStorage.setItem(data.storageKey, current); } catch (_) { /* Keep the session color when storage is unavailable. */ }
    try { localStorage.setItem(data.fontStorageKey, currentFont); } catch (_) { /* Keep the session font when storage is unavailable. */ }
    close();
  };
  const onOutside = event => { if (!panel.hidden && !root.contains(event.target)) close(false); };
  const onEscape = event => {
    if (event.key === 'Escape' && !panel.hidden) { event.preventDefault(); close(); }
  };
  const onFocusOut = event => {
    if (!panel.hidden && event.relatedTarget && !root.contains(event.relatedTarget)) close(false);
  };
  const onStorage = event => {
    if (event.storageArea !== localStorage) return;
    if (event.key === data.storageKey) {
      const saved = normalizeTheme(event.newValue);
      current = valid(saved) ? saved : data.defaultTheme;
      document.body.dataset.psColor = current;
    } else if (event.key === data.fontStorageKey) {
      currentFont = validFont(event.newValue) ? event.newValue : data.defaultFont;
      document.body.dataset.psFont = currentFont;
      syncNativeGridFont(currentFont, data.fontFaces);
    } else return;
    resetDraft();
  };
  toggle.addEventListener('click', onToggle);
  root.querySelector('.ps-theme-confirm').addEventListener('click', onConfirm);
  root.querySelector('.ps-theme-cancel').addEventListener('click', () => close());
  root.addEventListener('keydown', onEscape);
  root.addEventListener('focusout', onFocusOut);
  document.addEventListener('pointerdown', onOutside);
  window.addEventListener('storage', onStorage);
  // Escape the zero-height Streamlit wrapper while retaining component cleanup.
  document.body.append(root);
  const dispose = () => {
    document.removeEventListener('pointerdown', onOutside);
    window.removeEventListener('storage', onStorage);
    root.remove();
  };
  anchor.themeDispose = dispose;
  return () => {
    if (anchor.themeDispose === dispose) {
      dispose();
      anchor.themeDispose = null;
    }
  };
}

async function syncNativeGridFont(id, fontFaces = {}) {
  // Streamlit canvas grids draw with Source Sans instead of inherited CSS fonts.
  const state = document.body.psNativeGridFont ||= {id: null, face: null, revision: 0};
  if (state.id === id) return;
  state.id = id;
  const revision = ++state.revision;
  let face = null;
  if (fontFaces[id]) {
    try {
      face = await new FontFace('Source Sans', `url("${fontFaces[id]}")`, {weight: '100 900'}).load();
    } catch (_) {
      if (revision === state.revision) state.id = null;
      return;
    }
  }
  if (revision !== state.revision) return;
  if (state.face) document.fonts.delete(state.face);
  if (face) document.fonts.add(face);
  state.face = face;
  // ResizeObserver repaints the existing grids while retaining selection/scroll.
  state.restore?.();
  const grids = [...document.querySelectorAll('[data-testid="stDataFrame"]')];
  const widths = grids.map(grid => grid.style.width);
  const restore = () => grids.forEach((grid, index) => { grid.style.width = widths[index]; });
  state.restore = restore;
  grids.forEach(grid => { grid.style.width = `${Math.max(0, grid.getBoundingClientRect().width - 1)}px`; });
  requestAnimationFrame(() => requestAnimationFrame(() => {
    if (state.restore === restore) {
      restore();
      state.restore = null;
    }
  }));
}
