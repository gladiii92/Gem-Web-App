// HISTORY MODULE — localStorage only, kein Pricing, kein DOM außer render
// Senior Note: Custom Event als Pub/Sub — ui.js und history.js kennen sich nicht

const STORAGE_KEY = 'gem_calc_history';
const MAX_ENTRIES = 20;

/**
 * @typedef {{ gemName: string, quality: string, carat: number, totalPrice: number, mode: string, timestamp: number }} HistoryEntry
 */

export function saveToHistory(entry) {
  const history = getHistory();
  history.unshift({ ...entry, timestamp: Date.now() });
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history.slice(0, MAX_ENTRIES)));
}

export function getHistory() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch {
    return [];
  }
}

export function clearHistory() {
  localStorage.removeItem(STORAGE_KEY);
}

export function renderHistory(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const history = getHistory();
  if (history.length === 0) {
    container.innerHTML = '<p class="history-empty">Noch keine Berechnungen gespeichert.</p>';
    return;
  }

  const formatDate = (ts) => new Date(ts).toLocaleDateString('de-DE', {
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
  });

  container.innerHTML = history.map(e => `
    <div class="history-entry">
      <span class="history-gem">${e.gemName}</span>
      <span class="history-meta">${e.quality} · ${e.carat.toFixed(2)} ct · <em>${e.mode === 'retail' ? 'Retail' : 'Großhandel'}</em></span>
      <span class="history-price">$${e.totalPrice.toLocaleString('de-DE')}</span>
      <span class="history-date">${formatDate(e.timestamp)}</span>
    </div>
  `).join('');
}