export default function({parentElement, data, setStateValue}) {
  if (!data.ready) {
    if (parentElement.schedulePreferencesRestoredSent) return;
    parentElement.schedulePreferencesRestoredSent = true;
    let preferences = null;
    try {
      const saved = localStorage.getItem(data.storageKey);
      if (saved !== null) preferences = JSON.parse(saved);
    } catch (_) { /* Browser storage restrictions leave session controls usable. */ }
    setStateValue('restored', {preferences});
    return;
  }
  try {
    const saved = JSON.stringify(data.preferences);
    if (localStorage.getItem(data.storageKey) !== saved) localStorage.setItem(data.storageKey, saved);
  } catch (_) { /* Display preferences do not require browser storage. */ }
}
