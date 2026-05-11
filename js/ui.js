// ui.js v3 — korrekte IDs, gruppiertes Dropdown, Clarity-Befüllung, Modifier-Toggles

import { loadGems, getGemById } from './data.js';
import { calculatePrice, getAvailableGrades } from './pricing.js';
import { saveToHistory, clearHistory, renderHistory } from './history.js';
import { getModifiersForGem, formatFactor } from './modifiers.js';

let currentMode     = 'retail';
let activeModifiers = [];

// ── Mode-Umschaltung ────────────────────────────────────────────────────────
window.setMode = function(mode) {
  currentMode = mode;
  document.getElementById('btn-retail').classList.toggle('active', mode === 'retail');
  document.getElementById('btn-wholesale').classList.toggle('active', mode === 'wholesale');
  triggerRecalc();
};

// ── Dropdown-Gruppen (günstig → teuer, korrekte IDs) ───────────────────────
const GEM_GROUPS = [
  { label: 'Topas',       ids: [1] },
  { label: 'Granat',      ids: [2, 3, 4, 8, 9, 11, 12, 32, 33, 34, 35, 36] },
  { label: 'Spinell',     ids: [14, 16, 20] },
  { label: 'Turmalin',    ids: [28, 29, 30, 31, 26, 27] },
  { label: 'Morganit',    ids: [37] },
  { label: 'Smaragd',     ids: [18] },
  { label: 'Tansanit',    ids: [6, 7] },
  { label: 'Saphir',      ids: [5, 10, 13, 15, 17, 25, 24] },
  { label: 'Rubin',       ids: [19, 21] },
  { label: 'Alexandrit',  ids: [22, 23] },
  { label: 'Paraiba',     ids: [26, 27] },
];

// Paraiba ist in Turmalin UND Paraiba — deduplizieren beim Render
// Lösung: Paraiba-Gruppe überschreibt, Turmalin ohne Paraiba
const GEM_GROUPS_CLEAN = [
  { label: 'Topas',       ids: [1] },
  { label: 'Granat',      ids: [2, 3, 4, 8, 9, 11, 12, 32, 33, 34, 35, 36] },
  { label: 'Spinell',     ids: [14, 16, 20] },
  { label: 'Turmalin',    ids: [28, 29, 30, 31] },
  { label: 'Morganit',    ids: [37] },
  { label: 'Smaragd',     ids: [18] },
  { label: 'Tansanit',    ids: [6, 7] },
  { label: 'Saphir',      ids: [5, 10, 13, 15, 17, 25, 24] },
  { label: 'Rubin',       ids: [19, 21] },
  { label: 'Alexandrit',  ids: [22, 23] },
  { label: 'Paraiba',     ids: [26, 27] },
];

const GRADE_LABELS = {
  'I1':  'Low (I1)',
  'SI2': 'Mid-Low (SI2)',
  'SI1': 'Mid (SI1)',
  'VS':  'Mid-High (VS)',
  'VVS': 'High (VVS)',
};

const fmt = (n) => n != null ? '$' + Math.round(n).toLocaleString('de-DE') : '–';

// ── Stones Counter ──────────────────────────────────────────────────────────
function renderStonesCounter(gems) {
  const el = document.getElementById('stones-counter');
  if (!el) return;
  const total = gems.reduce((sum, g) =>
    sum + (g.retail_sample_count || 0) + (g.wholesale_sample_count || 0), 0);
  el.textContent = `* ${total.toLocaleString('de-DE')} stones in database and analyzed`;
}

// ── Gruppiertes Dropdown befüllen ───────────────────────────────────────────
function buildGemDropdown(gems) {
  const select = document.getElementById('gem-select');
  if (!select) return;
  select.innerHTML = '<option value="">– Stein wählen –</option>';

  const gemMap = {};
  gems.forEach(g => { gemMap[g.id] = g; });

  const usedIds = new Set();

  GEM_GROUPS_CLEAN.forEach(group => {
    const validIds = group.ids.filter(id => gemMap[id] && !usedIds.has(id));
    if (validIds.length === 0) return;

    const optgroup = document.createElement('optgroup');
    optgroup.label = group.label;

    validIds.forEach(id => {
      usedIds.add(id);
      const g = gemMap[id];
      const opt = document.createElement('option');
      opt.value = g.id;
      opt.textContent = g.name;
      optgroup.appendChild(opt);
    });
    select.appendChild(optgroup);
  });

  // Steine die in keiner Gruppe sind → Fallback
  const ungrouped = gems.filter(g => !usedIds.has(g.id));
  if (ungrouped.length > 0) {
    const optgroup = document.createElement('optgroup');
    optgroup.label = 'Weitere';
    ungrouped.forEach(g => {
      const opt = document.createElement('option');
      opt.value = g.id;
      opt.textContent = g.name;
      optgroup.appendChild(opt);
    });
    select.appendChild(optgroup);
  }
}

// ── Clarity-Dropdown befüllen ───────────────────────────────────────────────
function buildClarityDropdown(gem) {
  const select = document.getElementById('quality-select');
  if (!select) return;
  select.innerHTML = '<option value="">– Clarity wählen –</option>';
  const grades = getAvailableGrades(gem);
  grades.forEach(g => {
    const opt = document.createElement('option');
    opt.value = g;
    opt.textContent = GRADE_LABELS[g] || g;
    select.appendChild(opt);
  });
  // Standard: höchste Grade vorauswählen
  if (grades.length > 0) select.value = grades.at(-1);
}

// ── Modifier-Buttons rendern ────────────────────────────────────────────────
function renderModifierButtons(gem) {
  const container = document.getElementById('modifier-buttons');
  if (!container) return;

  const modifiers = getModifiersForGem(gem.id);
  if (modifiers.length === 0) {
    container.innerHTML = '';
    return;
  }

  const typeLabels = { origin: 'Herkunft', color: 'Farbe', treatment: 'Behandlung' };
  const grouped = {};
  modifiers.forEach(m => {
    if (!grouped[m.type]) grouped[m.type] = [];
    grouped[m.type].push(m);
  });

  let html = '<div class="modifier-section">';
  html += '<div class="modifier-warning">⚠️ Preisanpassungen sind Schätzwerte</div>';

  Object.entries(grouped).forEach(([type, mods]) => {
    html += `<div class="modifier-group">
      <span class="modifier-type-label">${typeLabels[type] || type}</span>`;
    mods.forEach(m => {
      const isActive = activeModifiers.includes(m.id);
      const factorLabel = formatFactor(m.factor);
      const factorClass = m.factor >= 1 ? 'mod-positive' : 'mod-negative';
      html += `<button
        class="modifier-btn${isActive ? ' active' : ''}"
        data-mod-id="${m.id}">
        ${m.label}&nbsp;<span class="${factorClass}">${factorLabel}</span>
      </button>`;
    });
    html += `</div>`;
  });
  html += '</div>';
  container.innerHTML = html;

  // Event-Delegation statt onclick im HTML
  container.querySelectorAll('.modifier-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.dataset.modId;
      if (activeModifiers.includes(id)) {
        activeModifiers = activeModifiers.filter(x => x !== id);
        btn.classList.remove('active');
      } else {
        activeModifiers.push(id);
        btn.classList.add('active');
      }
      triggerRecalc();
    });
  });
}

// ── Clarity-Tabelle ─────────────────────────────────────────────────────────
function renderClarityTable(allGrades, selectedGrade) {
  if (!allGrades || allGrades.length === 0) return '';
  const rows = allGrades.map(g => {
    const isSelected = g.grade === selectedGrade;
    return `<tr class="${isSelected ? 'selected-grade' : ''}">
      <td>${GRADE_LABELS[g.grade] || g.grade}</td>
      <td>${fmt(g.minTotal)}</td>
      <td>${fmt(g.maxTotal)}</td>
    </tr>`;
  }).join('');
  return `<table class="clarity-table">
    <thead><tr><th>Clarity</th><th>Min</th><th>Max</th></tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

function renderMarketBlock(crawlerStats, mode, allGrades, selectedGrade) {
  if (!crawlerStats || !allGrades || allGrades.length === 0) return '';

  function buildClarityRows(byClarity, priceType) {
    return allGrades.map(g => {
      const isSelected = g.grade === selectedGrade;
      const gradeStats = byClarity?.[g.grade]?.[priceType];
      return `<tr class="${isSelected ? 'selected-grade' : ''}">
        <td>${GRADE_LABELS[g.grade] || g.grade}</td>
        <td>${gradeStats ? fmt(gradeStats.min)    : '–'}</td>
        <td>${gradeStats ? fmt(gradeStats.max)    : '–'}</td>
        <td>${gradeStats ? fmt(gradeStats.median) : '–'}</td>
      </tr>`;
    }).join('');
  }

  if (mode === 'retail') {
    const src        = crawlerStats['1stdibs'];
    const byClarity  = src?.by_clarity ?? {};
    const fallback   = src?.retail;
    // Mindestens eine Grade muss Daten haben, sonst kein Block
    const hasData = allGrades.some(g => byClarity[g.grade]?.retail);
    if (!hasData && !fallback) return '';

    // Fallback: wenn by_clarity leer → alle Zeilen mit Gesamt-Stats füllen
    const rows = hasData
      ? buildClarityRows(byClarity, 'retail')
      : allGrades.map(g => {
          const isSelected = g.grade === selectedGrade;
          return `<tr class="${isSelected ? 'selected-grade' : ''}">
            <td>${GRADE_LABELS[g.grade] || g.grade}</td>
            <td>${fmt(fallback?.min)}</td>
            <td>${fmt(fallback?.max)}</td>
            <td>${fmt(fallback?.median)}</td>
          </tr>`;
        }).join('');

    return `<table class="market-table">
      <thead><tr>
        <th>Luxury-Layer</th>
        <th>Min</th><th>Max</th><th>Median</th>
      </tr></thead>
      <tbody>
        ${rows}
        <tr><td colspan="4" style="font-size:0.72rem;color:var(--text-muted);padding:5px 10px">
          Endkunden-Markt
        </td></tr>
      </tbody>
    </table>`;
  }

  if (mode === 'wholesale') {
    const src       = crawlerStats['gemrock'];
    const byClarity = src?.by_clarity ?? {};
    const fallback  = src?.wholesale || src?.retail;
    const hasData   = allGrades.some(g => byClarity[g.grade]?.wholesale || byClarity[g.grade]?.retail);
    if (!hasData && !fallback) return '';

    const priceType = src?.by_clarity
      ? (allGrades.some(g => byClarity[g.grade]?.wholesale) ? 'wholesale' : 'retail')
      : null;

    const rows = hasData
      ? buildClarityRows(byClarity, priceType || 'retail')
      : allGrades.map(g => {
          const isSelected = g.grade === selectedGrade;
          return `<tr class="${isSelected ? 'selected-grade' : ''}">
            <td>${GRADE_LABELS[g.grade] || g.grade}</td>
            <td>${fmt(fallback?.min)}</td>
            <td>${fmt(fallback?.max)}</td>
            <td>–</td>
          </tr>`;
        }).join('');

    return `<table class="market-table">
      <thead><tr>
        <th>Wholesale-Layer</th>
        <th>Min</th><th>Max</th><th>Median</th>
      </tr></thead>
      <tbody>
        ${rows}
        <tr><td colspan="4" style="font-size:0.72rem;color:var(--text-muted);padding:5px 10px">
          Händler-Einkauf
        </td></tr>
      </tbody>
    </table>`;
  }
  return '';
}

// ── Ergebnis rendern ────────────────────────────────────────────────────────
function renderResult(gem, result, carat, quality) {
  const resultDiv = document.getElementById('result');
  if (!resultDiv) return;

  if (result.error) {
    resultDiv.innerHTML = `<div class="error">${result.error}</div>`;
    return;
  }

  const { allGrades, crawlerStats, modFactor } = result;

  const totalN = [
    crawlerStats?.gemrock?.retail?.n_raw || 0,
    crawlerStats?.gemrock?.wholesale?.n_raw || 0,
    crawlerStats?.['1stdibs']?.retail?.n_raw || 0,
  ].reduce((a, b) => a + b, 0);

  const modNote = modFactor !== 1.0
    ? `<div class="modifier-active-note">
        Aktive Anpassungen: ×${modFactor.toFixed(2)}
        (${Math.round((modFactor - 1) * 100) >= 0 ? '+' : ''}${Math.round((modFactor - 1) * 100)}%)
      </div>`
    : '';

  const nNote = totalN > 0
    ? `<div class="market-n-note">${totalN} Steine analysiert</div>`
    : '';

  const modeLabel = currentMode === 'retail' ? 'Retail' : 'Grosshandel';
  const modeBadge = currentMode === 'retail'
    ? '<span class="badge badge-retail">Retail</span>'
    : '<span class="badge badge-wholesale">Grosshandel</span>';

  resultDiv.innerHTML = `
    <div class="result-card">
      <div class="result-header">
        <span class="result-gem-name">${gem.name}</span>
        ${modeBadge}
      </div>
      ${modNote}
      ${renderClarityTable(allGrades, quality)}
      ${nNote}
      ${renderMarketBlock(crawlerStats, currentMode, allGrades, quality)}
      ${gem.notes ? `<div class="general-note">ℹ️ ${gem.notes}</div>` : ''}
      <div class="carat-info">${carat.toFixed(2)} ct</div>
    </div>`;
}

// ── Recalc ──────────────────────────────────────────────────────────────────
function triggerRecalc() {
  const gemId   = parseInt(document.getElementById('gem-select')?.value);
  const quality = document.getElementById('quality-select')?.value;
  const carat   = parseFloat(document.getElementById('carat-input')?.value);
  if (!gemId || !quality || !carat || carat <= 0) return;
  const gem = getGemById(gemId);
  if (!gem) return;
  const result = calculatePrice(gem, quality, carat, currentMode, activeModifiers);
  renderResult(gem, result, carat, quality);
}

// ── Gem-Wechsel ─────────────────────────────────────────────────────────────
function onGemChange(gem) {
  activeModifiers = [];
  buildClarityDropdown(gem);
  renderModifierButtons(gem);
  triggerRecalc();
}

// ── Submit ──────────────────────────────────────────────────────────────────
window.calculateAndDisplay = function() {
  const gemId   = parseInt(document.getElementById('gem-select')?.value);
  const quality = document.getElementById('quality-select')?.value;
  const carat   = parseFloat(document.getElementById('carat-input')?.value);

  if (!gemId || !quality || !carat || carat <= 0) {
    document.getElementById('result').innerHTML =
      '<div class="error">Bitte alle Felder ausfüllen.</div>';
    return;
  }

  const gem = getGemById(gemId);
  if (!gem) return;

  const result = calculatePrice(gem, quality, carat, currentMode, activeModifiers);
  renderResult(gem, result, carat, quality);

  saveToHistory({
    gemName:    gem.name,
    quality,
    carat,
    mode:       currentMode,
    totalPrice: result.maxTotal ?? result.minTotal ?? 0,
    timestamp:  new Date().toISOString(),
  });
};

// ── Init ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  const gems = await loadGems();
  buildGemDropdown(gems);
  renderStonesCounter(gems);
  renderHistory();

  document.getElementById('gem-select')?.addEventListener('change', (e) => {
    const gem = getGemById(parseInt(e.target.value));
    if (gem) onGemChange(gem);
  });

  document.getElementById('quality-select')?.addEventListener('change', triggerRecalc);
  document.getElementById('carat-input')?.addEventListener('input', triggerRecalc);

  document.getElementById('clear-history')?.addEventListener('click', () => {
    clearHistory();
    renderHistory();
  });
});
