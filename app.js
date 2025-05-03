document.addEventListener('DOMContentLoaded', () => {
    const gemSelect = document.getElementById('gem-select');
    const qualitySelect = document.getElementById('quality-select');

    const qualityLabels = {
        'I1':     'Low (I1)',
        'SI2':    'Mid-Low (SI2)',
        'SI1':    'Mid (SI1)',
        'VS':     'Mid-High (VS)',
        'VVS':    'High (VVS)'
    };

    fetch('data.json')
        .then(response => response.json())
        .then(gems => {
            const maxId = Math.max(...gems.map(g => g.id));

            for (let id = 1; id <= maxId; id++) {
                const gem = gems.find(g => g.id === id);
                if (gem) {
                    const option = new Option(
                        `${gem.id}. ${gem.name}${gem.special ? ' (Nur VVS)' : ''}`,
                        gem.id
                    );
                    gemSelect.add(option);
                }
            }

            gemSelect.addEventListener('change', () => {
                const gem = gems.find(g => g.id === parseInt(gemSelect.value));
                qualitySelect.innerHTML = '';

                if (gem.special) {
                    const option = new Option(qualityLabels['VVS'], 'VVS');
                    qualitySelect.add(option);
                } else {
                    Object.entries(qualityLabels).forEach(([key, label]) => {
                        const option = new Option(label, key);
                        qualitySelect.add(option);
                    });
                }
            });

            // Initiale Auswahl auslösen
            gemSelect.dispatchEvent(new Event('change'));
        });
});

function calculatePrice() {
  const selectedGem = document.getElementById('gem-select').value;
  const selectedQuality = document.getElementById('quality-select').value;
  const carat = parseFloat(document.getElementById('carat').value);
  const resultBox = document.getElementById('result');

  // Beispielhafter Zugriff auf deine JSON-Daten
  const gemData = gemstoneData.find(gem => gem.gem === selectedGem);
  if (!gemData) return resultBox.innerHTML = 'Kein Edelstein gefunden.';

  const qualityData = gemData.clarity.find(q => q.clarity === selectedQuality);
  if (!qualityData) return resultBox.innerHTML = 'Keine Preisdaten gefunden.';

  // Preisberechnung (vereinfacht)
  let price = 0;
  if (carat >= 5) price = qualityData.price_5_plus;
  else if (carat >= 3) price = qualityData.price_3_5;
  else if (carat >= 2) price = qualityData.price_2_3;
  else price = qualityData.price_1_2;

  const totalPrice = price * carat;

  // Ausgabe inkl. quality_note
  resultBox.innerHTML = `
    <div class="quality-note"><strong>Hinweis zur Qualität:</strong><br>${qualityData.quality_note || '–'}</div>
    <table>
      <tr><td>Stein:</td><td>${selectedGem}</td></tr>
      <tr><td>Qualität:</td><td>${selectedQuality}</td></tr>
      <tr><td>Karat:</td><td>${carat}</td></tr>
      <tr class="total-price"><td>Preis:</td><td>${totalPrice.toFixed(2)} USD</td></tr>
    </table>
  `;
}
