let gems = [];

// Initial setup: load gems and populate selectors
document.addEventListener('DOMContentLoaded', () => {
    const gemSelect = document.getElementById('gem-select');
    const qualitySelect = document.getElementById('quality-select');

    fetch('data.json')
        .then(response => response.json())
        .then(data => {
            gems = data;
            // Populate gem select
            data.forEach(gem => {
                const option = new Option(
                    `${gem.id}. ${gem.name}${gem.special ? ' (Nur VVS)' : ''}`,
                    gem.id
                );
                gemSelect.add(option);
            });

            // Trigger update of quality options
            gemSelect.dispatchEvent(new Event('change'));

            // Update quality options on gem change
            gemSelect.addEventListener('change', () => {
                const gemId = parseInt(gemSelect.value, 10);
                const gem = gems.find(g => g.id === gemId);
                qualitySelect.innerHTML = '';

                if (gem.special) {
                    qualitySelect.add(new Option('High (VVS)', 'VVS'));
                } else {
                    ['I1','SI2','SI1','VS','VVS'].forEach(key => {
                        const label = {
                            'I1': 'Low (I1)',
                            'SI2': 'Mid-Low (SI2)',
                            'SI1': 'Mid (SI1)',
                            'VS': 'Mid-High (VS)',
                            'VVS': 'High (VVS)'
                        }[key];
                        qualitySelect.add(new Option(label, key));
                    });
                }
            });
        })
        .catch(err => console.error('Fehler beim Laden der Daten:', err));
});

// Preis berechnen und Ergebnis anzeigen
function calculatePrice() {
    const gemId = parseInt(document.getElementById('gem-select').value, 10);
    const quality = document.getElementById('quality-select').value;
    const carat = parseFloat(document.getElementById('carat').value);
    const resultBox = document.getElementById('result');

    if (isNaN(gemId) || !quality || isNaN(carat)) {
        resultBox.innerHTML = '<p class="general-note">Bitte Stein, Qualität und Karat korrekt auswählen.</p>';
        return;
    }

    const gem = gems.find(g => g.id === gemId);
    if (!gem) {
        resultBox.innerHTML = '<p class="general-note">Edelstein nicht gefunden.</p>';
        return;
    }

    // Finde passende Preisspanne
    const range = gem.price_ranges.find(r => carat >= r.carat_min && carat <= r.carat_max);
    if (!range) {
        resultBox.innerHTML = '<p class="general-note">Keine Preisspanne für dieses Karat.</p>';
        return;
    }

    const pricePerCarat = range[quality] || range.VVS;
    const totalPrice = pricePerCarat * carat;

    // Formatierung in USD
    const formatUSD = (value) => '$' + value.toFixed(0);

    // Quality Note falls vorhanden
    const qNote = gem.quality_notes && gem.quality_notes[quality] ?
                  gem.quality_notes[quality] : null;

    resultBox.innerHTML = `
        <div class="result-box">
            <h3>${gem.name}</h3>
            ${gem.notes ? `<div class="general-note">ℹ️ ${gem.notes}</div>` : ''}
            ${qNote ? `<div class="quality-note">💎 ${qNote.replace(/\n/g, '<br>')}</div>` : ''}
            <table>
                <tr><td>Qualität:</td><td>${quality}</td></tr>
                <tr><td>Karat:</td><td>${carat.toFixed(2)} ct</td></tr>
                <tr><td>Preis/ct:</td><td>${formatUSD(pricePerCarat)}</td></tr>
                <tr class="total-price"><td>Gesamtpreis:</td><td>${formatUSD(totalPrice)}</td></tr>
            </table>
        </div>
    `;
}
