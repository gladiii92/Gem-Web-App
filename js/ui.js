import { loadGems, getGemById } from './data.js';
import { calculatePrice, getAvailableGrades } from './pricing.js';
import { saveToHistory, clearHistory, renderHistory } from './history.js';

let currentMode = 'retail';

window.setMode = function(mode) {
  currentMode = mode;
  document.getElementById('btn-retail').classList.toggle('active', mode === 'retail');
  document.getElementById('btn-wholesale').classList.toggle('active', mode === 'wholesale');
};

const GRADE_LABELS = {
  'I1':  'Low (I1)',
  'SI2': 'Mid-Low (SI2)',
  'SI1': 'Mid (SI1)',
  'VS':  'Mid-High (VS)',
  'VVS': 'High (VVS)',
};

const fmt = (n) => n != null ? '$' + Math.round(n).toLocaleString('de-DE') : '–';

// ── Stones Counter ────────────────────────────────────────────────────────────
function renderStonesCounter(gems) {
  const el = document.getElementById('stones-counter');
  if (!el) return;
  const total = gems.reduce((sum, g) => {
    return sum + (g.retail_sample_count || 0) + (g.wholesale_sample_count || 0);
  }, 0);
  el.textContent = `* ${total.toLocaleString('de-DE')} stones analyzed`;
}

// ── Marktdaten-Block ──────────────────────────────────────────────────────────
function renderMarketBlock(crawlerStats) {
  if (!crawlerStats) return '';

  const gemrock = crawlerStats.gemrock;
  const stdibs  = crawlerStats['1stdibs'];
  const wl      = gemrock?.wholesale || gemrock?.retail;
  const ll      = stdibs?.retail;

  if (!wl && !ll) return '';

  const totalN = [
    gemrock?.retail?.n_raw    || 0,
    gemrock?.wholesale?.n_raw || 0,
    stdibs?.retail?.n_raw     || 0,
  ].reduce((a, b) => a + b, 0);

  let rows = '';
  if (wl) {
    rows += `<tr>
      <td style="color:var(--text-secondary);font-size:0.78rem;letter-spacing:0.08em;text-transform:uppercase;padding:10px 0;border-bottom:1px solid rgba(42,47,69,0.6);">Wholesale-Layer</td>
      <td style="text-align:right;padding:10px 0;border-bottom:1px solid rgba(42,47,69,0.6);">${fmt(wl.min)}</td>
      <td style="text-align:right;padding:10px 0;border-bottom:1px solid rgba(42,47,69,0.6);">${fmt(wl.max)}</td>
      <td style="text-align:right;padding:10px 0;border-bottom:1px solid rgba(42,47,69,0.6);color:var(--gold);">${fmt(wl.median)}</td>
    </tr>`;
  }
  if (ll) {
    rows += `<tr>
      <td style="color:var(--text-secondary);font-size:0.78rem;letter-spacing:0.08em;text-transform:uppercase;padding:10px 0;">Luxury-Layer</td>
      <td style="text-align:right;padding:10px 0;">${fmt(ll.min)}</td>
      <td style="text-align:right;padding:10px 0;">${fmt(ll.max)}</td>
      <td style="text-align:right;padding:10px 0;color:var(--gold);">${fmt(ll.median)}</td>
    </tr>`;
  }

  return `
    <div style="margin-top:20px;padding-top:16px;border-top:1px solid var(--border-color);">
      <p style="font-size:0.72rem;font-weight:600;letter-spacing:0.15em;text-transform:uppercase;color:var(--text-muted);margin-bottom:12px;">
        Marktdaten
        <span style="font-weight:400;margin-left:6px;">(${totalN.toLocaleString('de-DE')} Steine analysiert)</span>
      </p>
      <table style="width:100%;border-collapse:collapse;">
        <thead>
          <tr>
            <th style="text-align:left;font-size:0.72rem;letter-spacing:0.1em;text-transform:uppercase;color:var(--text-muted);padding-bottom:8px;">Markt</th>
            <th style="text-align:right;font-size:0.72rem;letter-spacing:0.1em;text-transform:uppercase;color:var(--text-muted);padding-bottom:8px;">Min</th>
            <th style="text-align:right;font-size:0.72rem;letter-spacing:0.1em;text-transform:uppercase;color:var(--text-muted);padding-bottom:8px;">Max</th>
            <th style="text-align:right;font-size:0.72rem;letter-spacing:0.1em;text-transform:uppercase;color:var(--text-muted);padding-bottom:8px;">Ø Median</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  const gemSelect     = document.getElementById('gem-select');
  const qualitySelect = document.getElementById('quality-select');
  const caratInput    = document.getElementById('carat');
  const resultBox     = document.getElementById('result');

  let gems;
  try {
    gems = await loadGems();
  } catch {
    resultBox.innerHTML = '<div class="error">Daten konnten nicht geladen werden.</div>';
    return;
  }

  renderStonesCounter(gems);
  gems.forEach(gem => gemSelect.add(new Option(`${gem.id}. ${gem.name}`, gem.id)));
  updateQualityOptions();
  renderHistory('history');

  gemSelect.addEventListener('change', updateQualityOptions);
  document.getElementById('calc-btn').addEventListener('click', doCalculate);
  document.getElementById('clear-history')?.addEventListener('click', () => {
    clearHistory();
    renderHistory('history');
  });

  function updateQualityOptions() {
    const gem = getGemById(parseInt(gemSelect.value, 10));
    if (!gem) return;
    qualitySelect.innerHTML = '';
    getAvailableGrades(gem).forEach(g =>
      qualitySelect.add(new Option(GRADE_LABELS[g], g))
    );
  }

  function doCalculate() {
    const gem     = getGemById(parseInt(gemSelect.value, 10));
    const quality = qualitySelect.value;
    const carat   = parseFloat(caratInput.value);
    const mode    = currentMode;

    const result = calculatePrice(gem, quality, carat, mode);

    if (result.error) {
      resultBox.innerHTML = `<div class="error">${result.error}</div>`;
      return;
    }

    const modeTag   = mode === 'wholesale' ? 'wholesale' : 'retail';
    const modeBadge = `<span class="badge badge-${modeTag}">${mode === 'wholesale' ? 'Großhandel' : 'Retail'}</span>`;

    // ── Clarity-Tabelle ───────────────────────────────────────────────────────
    const gradeRows = result.allGrades.map(g => {
      const isSelected = g.grade === quality;
      const rowStyle   = isSelected
        ? 'background:rgba(201,168,76,0.08);'
        : '';
      const priceStyle = isSelected
        ? 'color:var(--gold);font-weight:700;'
        : 'color:var(--text-primary);';
      const hasData = g.minTotal != null && g.maxTotal != null;

      return `<tr style="${rowStyle}">
        <td style="color:var(--text-secondary);font-size:0.78rem;letter-spacing:0.08em;text-transform:uppercase;padding:10px 0;border-bottom:1px solid rgba(42,47,69,0.6);width:40%;">
          ${GRADE_LABELS[g.grade] || g.grade}
        </td>
        <td style="text-align:right;padding:10px 0;border-bottom:1px solid rgba(42,47,69,0.6);${priceStyle}">
          ${hasData ? fmt(g.minTotal) : '–'}
        </td>
        <td style="text-align:right;padding:10px 0;border-bottom:1px solid rgba(42,47,69,0.6);${priceStyle}">
          ${hasData ? fmt(g.maxTotal) : '–'}
        </td>
      </tr>`;
    }).join('');

    // ── Wholesale-Warnung ─────────────────────────────────────────────────────
    const sourceWarn = (mode === 'wholesale' && result.wholesaleSource === 'auto_1_5')
      ? '<div class="source-warn">⚠️ Großhandelspreise geschätzt (1/5 Retail) — noch keine Crawler-Daten.</div>'
      : '';

    // ── Notes ─────────────────────────────────────────────────────────────────
    const notes = gem.notes
      ? `<div class="general-note">ℹ️ ${gem.notes}</div>`
      : '';

    resultBox.innerHTML = `
      <div class="result-card">
        <div class="result-header">
          <span class="result-gem-name">${gem.name}</span>
          ${modeBadge}
        </div>
        ${sourceWarn}
        <table style="width:100%;border-collapse:collapse;">
          <thead>
            <tr>
              <th style="text-align:left;font-size:0.72rem;letter-spacing:0.1em;text-transform:uppercase;color:var(--text-muted);padding-bottom:10px;">Clarity</th>
              <th style="text-align:right;font-size:0.72rem;letter-spacing:0.1em;text-transform:uppercase;color:var(--text-muted);padding-bottom:10px;">Min</th>
              <th style="text-align:right;font-size:0.72rem;letter-spacing:0.1em;text-transform:uppercase;color:var(--text-muted);padding-bottom:10px;">Max</th>
            </tr>
          </thead>
          <tbody>${gradeRows}</tbody>
        </table>
        ${renderMarketBlock(result.crawlerStats)}
        ${notes}
        <div style="margin-top:14px;font-size:0.75rem;color:var(--text-muted);">
          ${carat.toFixed(2)} ct
        </div>
      </div>
    `;

    if (result.minTotal != null) {
      saveToHistory({
        gemName:    gem.name,
        quality,
        carat,
        mode,
        totalPrice: result.maxTotal,  // history zeigt Max-Preis als Referenzwert
      });
      renderHistory('history');
    }
  }
});