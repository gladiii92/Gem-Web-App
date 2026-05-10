import { loadGems, getGemById } from './data.js';
import { calculatePrice, getAvailableGrades } from './pricing.js';
import { saveToHistory, clearHistory, renderHistory } from './history.js';

// Mode-State — wird durch Toggle-Buttons gesetzt
let currentMode = 'retail';

window.setMode = function(mode) {
  currentMode = mode;
  document.getElementById('btn-retail').classList.toggle('active', mode === 'retail');
  document.getElementById('btn-wholesale').classList.toggle('active', mode === 'wholesale');
};

const GRADE_LABELS = {
  'I1': 'Low (I1)', 'SI2': 'Mid-Low (SI2)', 'SI1': 'Mid (SI1)',
  'VS': 'Mid-High (VS)', 'VVS': 'High (VVS)'
};

const fmt = (n) => '$' + n.toLocaleString('de-DE');

document.addEventListener('DOMContentLoaded', async () => {
  const gemSelect     = document.getElementById('gem-select');
  const qualitySelect = document.getElementById('quality-select');
  const caratInput    = document.getElementById('carat');
  const modeSelect    = document.getElementById('mode-select');
  const resultBox     = document.getElementById('result');

  let gems;
  try {
    gems = await loadGems();
  } catch {
    resultBox.innerHTML = '<p class="error">Daten konnten nicht geladen werden.</p>';
    return;
  }

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
    getAvailableGrades(gem).forEach(g => qualitySelect.add(new Option(GRADE_LABELS[g], g)));
  }

  function doCalculate() {
    const gem     = getGemById(parseInt(gemSelect.value, 10));
    const quality = qualitySelect.value;
    const carat   = parseFloat(caratInput.value);
    const mode    = currentMode;

    const result = calculatePrice(gem, quality, carat, mode);

    if (result.error) {
      resultBox.innerHTML = `<p class="error">${result.error}</p>`;
      return;
    }

    const modeTag = mode === 'wholesale'
      ? '<span class="badge badge-wholesale">Großhandel</span>'
      : '<span class="badge badge-retail">Retail</span>';

    // Warnung wenn Großhandelspreise noch automatisch berechnet (nicht gecrawlt)
    const sourceWarn = (mode === 'wholesale' && result.wholesaleSource === 'auto_1_5')
      ? '<div class="source-warn">⚠️ Großhandelspreis = automatisch (1/5 Retail) — noch nicht durch Crawler verifiziert</div>'
      : '';

    const genNote = gem.notes
      ? `<div class="general-note">ℹ️ ${gem.notes}</div>` : '';
    const qNote = gem.quality_notes?.[quality]
      ? `<div class="quality-note">📋 ${gem.quality_notes[quality]}</div>` : '';

    const imgUrl = gem.images?.[quality]?.[0];
    const imgHtml = imgUrl
      ? `<img src="${imgUrl}" alt="${gem.name} ${quality}" class="gem-image" onerror="this.style.display='none'">` : '';

    resultBox.innerHTML = `
      <div class="result-header">${modeTag}</div>
      ${sourceWarn}
      ${imgHtml}
      <table>
        <tr><td>Qualität</td><td><strong>${quality}</strong></td></tr>
        <tr><td>Karat</td><td>${carat.toFixed(2)} ct</td></tr>
        <tr><td>Preis/ct</td><td>${fmt(result.minPerCarat)} – ${fmt(result.maxPerCarat)}</td></tr>
        <tr class="total-price">
          <td>Gesamtpreis</td><td>${fmt(result.minTotal)} – ${fmt(result.maxTotal)}</td>
        </tr>
      </table>
      ${genNote}${qNote}
    `;

    saveToHistory({ gemName: gem.name, quality, carat, totalPrice: result.maxTotal, mode });
    renderHistory('history');
  }
});