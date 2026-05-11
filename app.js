let gems = [];

// ── Hilfsfunktionen ───────────────────────────────────────────────────────────
const formatUSD = (v) => '$' + Math.round(v).toLocaleString('en-US');

function totalStonesAnalyzed() {
  let total = 0;
  gems.forEach(g => {
    total += g.retail_sample_count  || 0;
    total += g.wholesale_sample_count || 0;
  });
  return total;
}

function getCrawlerStats(range) {
  const cs = range._crawler_stats;
  if (!cs || !cs.by_source) return null;
  return cs.by_source;
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const gemSelect     = document.getElementById('gem-select');
  const qualitySelect = document.getElementById('quality-select');

  fetch('data.json')
    .then(r => r.json())
    .then(data => {
      gems = data;

      // Stones-Counter
      const counter = document.getElementById('stones-counter');
      if (counter) {
        counter.textContent = `* ${totalStonesAnalyzed().toLocaleString('en-US')} stones analyzed`;
      }

      // Gem-Selector befüllen
      data.forEach(gem => {
        gemSelect.add(new Option(`${gem.id}. ${gem.name}${gem.special ? ' (Nur VVS)' : ''}`, gem.id));
      });

      gemSelect.dispatchEvent(new Event('change'));

      gemSelect.addEventListener('change', () => {
        const gem = gems.find(g => g.id === parseInt(gemSelect.value, 10));
        qualitySelect.innerHTML = '';
        if (gem && gem.special) {
          qualitySelect.add(new Option('High (VVS)', 'VVS'));
        } else {
          [
            ['I1',  'Low (I1)'],
            ['SI2', 'Mid-Low (SI2)'],
            ['SI1', 'Mid (SI1)'],
            ['VS',  'Mid-High (VS)'],
            ['VVS', 'High (VVS)'],
          ].forEach(([val, label]) => qualitySelect.add(new Option(label, val)));
        }
      });
    })
    .catch(err => console.error('Fehler beim Laden der Daten:', err));
});

// ── Preis berechnen ───────────────────────────────────────────────────────────
function calculatePrice() {
  const gemId   = parseInt(document.getElementById('gem-select').value, 10);
  const quality = document.getElementById('quality-select').value;
  const carat   = parseFloat(document.getElementById('carat').value);
  const mode    = document.querySelector('.tab-btn.active')?.dataset.mode || 'retail';
  const resultBox = document.getElementById('result');

  if (isNaN(gemId) || !quality || isNaN(carat) || carat <= 0) {
    resultBox.innerHTML = '<p>Bitte Stein, Qualität und Karat korrekt auswählen.</p>';
    return;
  }

  const gem = gems.find(g => g.id === gemId);
  if (!gem) { resultBox.innerHTML = '<p>Edelstein nicht gefunden.</p>'; return; }

  const range = gem.price_ranges.find(r => carat >= r.carat_min && carat <= r.carat_max);
  if (!range) { resultBox.innerHTML = '<p>Keine Preisspanne für dieses Karat.</p>'; return; }

  const GRADES   = ['I1', 'SI2', 'SI1', 'VS', 'VVS'];
  const bySource = getCrawlerStats(range);

  // ── Manuelle Ranges (alle Clarity-Grades) ────────────────────────────────
  let manualRows = '';
  GRADES.forEach(grade => {
    const gradeData = range[grade];
    if (!gradeData) return;

    const isSelected = grade === quality;
    const highlight  = isSelected ? ' style="font-weight:bold;background:#f0f8ff;"' : '';

    if (mode === 'retail') {
      const min = gradeData.retail_min;
      const max = gradeData.retail_max;
      if (!min || !max) return;
      manualRows += `<tr${highlight}>
        <td>${grade}</td>
        <td>${formatUSD(min * carat)}</td>
        <td>${formatUSD(max * carat)}</td>
      </tr>`;
    } else {
      // Großhandel: echte Crawler-Daten falls vorhanden, sonst Fallback 1/5
      const ws = bySource?.gemrock?.wholesale;
      if (ws) {
        manualRows += `<tr${highlight}>
          <td>${grade}</td>
          <td>${formatUSD(ws.min * carat)}</td>
          <td>${formatUSD(ws.max * carat)}</td>
        </tr>`;
      } else {
        const min = gradeData.wholesale_min || (gradeData.retail_min / 5);
        const max = gradeData.wholesale_max || (gradeData.retail_max / 5);
        manualRows += `<tr${highlight}>
          <td>${grade}</td>
          <td>${formatUSD(min * carat)}</td>
          <td>${formatUSD(max * carat)}</td>
        </tr>`;
      }
    }
  });

  // ── Crawler-Marktdaten Block ──────────────────────────────────────────────
  let marketBlock = '';
  if (bySource) {
    const totalN = Object.values(bySource)
      .flatMap(s => [s.retail?.n_raw || 0, s.wholesale?.n_raw || 0])
      .reduce((a, b) => a + b, 0);

    let sourceRows = '';

    const wl = bySource?.gemrock?.wholesale || bySource?.gemrock?.retail;
    const ll = bySource?.['1stdibs']?.retail;

    if (wl) {
      sourceRows += `<tr>
        <td>Wholesale-Layer</td>
        <td>${formatUSD(wl.min)}</td>
        <td>${formatUSD(wl.max)}</td>
        <td>${formatUSD(wl.median)}</td>
      </tr>`;
    }
    if (ll) {
      sourceRows += `<tr>
        <td>Luxury-Layer</td>
        <td>${formatUSD(ll.min)}</td>
        <td>${formatUSD(ll.max)}</td>
        <td>${formatUSD(ll.median)}</td>
      </tr>`;
    }

    if (sourceRows) {
      marketBlock = `
        <h4 style="margin-top:1.2em;margin-bottom:0.4em;">
          Marktdaten
          <small style="font-weight:normal;color:#888;">(${totalN.toLocaleString('en-US')} Steine analysiert)</small>
        </h4>
        <table>
          <thead><tr><th>Markt</th><th>Min</th><th>Max</th><th>Ø Median</th></tr></thead>
          <tbody>${sourceRows}</tbody>
        </table>`;
    }
  }

  // ── Output zusammenbauen ──────────────────────────────────────────────────
  const modeLabel = mode === 'retail' ? 'Retail' : 'Großhandel';

  resultBox.innerHTML = `
    <p><strong>${gem.name}</strong> · ${carat} ct · ${quality} · ${modeLabel}</p>
    <table>
      <thead><tr><th>Clarity</th><th>Min</th><th>Max</th></tr></thead>
      <tbody>${manualRows || '<tr><td colspan="3">Keine Daten verfügbar</td></tr>'}</tbody>
    </table>
    ${marketBlock}
  `;
}