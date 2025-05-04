let gems = [];

document.addEventListener('DOMContentLoaded', () => {
    const gemSelect = document.getElementById('gem-select');
    const qualitySelect = document.getElementById('quality-select');

    fetch('data.json')
        .then(response => response.json())
        .then(data => {
            gems = data;

            // 1) Edelstein-Dropdown befüllen
            data.forEach(gem => {
                gemSelect.add(new Option(`${gem.id}. ${gem.name}`, gem.id));
            });

            // 2) Change-Listener (vor dem ersten dispatch)
            gemSelect.addEventListener('change', () => {
                const gemId = parseInt(gemSelect.value, 10);
                const gem = gems.find(g => g.id === gemId);
                qualitySelect.innerHTML = '';

                // Labels nur einmal definieren
                const labels = {
                    'I1': 'Low (I1)',
                    'SI2': 'Mid-Low (SI2)',
                    'SI1': 'Mid (SI1)',
                    'VS': 'Mid-High (VS)',
                    'VVS': 'High (VVS)'
                };

                ['I1','SI2','SI1','VS','VVS'].forEach(key => {
                    qualitySelect.add(new Option(labels[key], key));
                });
            });

            // 3) Ersten Change auslösen, damit die Qualität sofort angezeigt wird
            gemSelect.dispatchEvent(new Event('change'));
        })
        .catch(err => console.error('Fehler beim Laden der Daten:', err));
});

function calculatePrice() {
    const gemId = parseInt(document.getElementById('gem-select').value, 10);
    const quality = document.getElementById('quality-select').value;
    const carat = parseFloat(document.getElementById('carat').value);
    const resultBox = document.getElementById('result');
    const imageBox = document.getElementById('image-box');

    resultBox.innerHTML = '';
    imageBox.innerHTML = '';

    if (isNaN(gemId) || !quality || isNaN(carat)) {
        resultBox.innerHTML = '<p class="general-note">Bitte Stein, Qualität und Karat korrekt auswählen.</p>';
        return;
    }

    const gem = gems.find(g => g.id === gemId);
    if (!gem) {
        resultBox.innerHTML = '<p class="general-note">Edelstein nicht gefunden.</p>';
        return;
    }

    const range = gem.price_ranges.find(r => carat >= r.carat_min && carat <= r.carat_max);
    if (!range) {
        resultBox.innerHTML = '<p class="general-note">Keine Preisspanne für dieses Karat.</p>';
        return;
    }

    const pricePerCarat = range[quality] || range.VVS;
    const totalPrice = pricePerCarat * carat;
    const qNote = gem.quality_notes && gem.quality_notes[quality] ? gem.quality_notes[quality] : null;

    // Formatierung der Preiszahlen
    const formatUSD = v => '$' + v.toFixed(0);

    // Ergebnis anzeigen
    resultBox.innerHTML = `
        <div class="result-box">
            <h3>${gem.name}</h3>
            ${gem.notes ? `<div class="general-note">ℹ️ ${gem.notes}</div>` : ''}
            ${qNote ? `<div class="quality-note">💎 ${qNote.replace(/\\n/g, '<br>')}</div>` : ''}
            <table>
                <tr><td>Qualität:</td><td>${quality}</td></tr>
                <tr><td>Karat:</td><td>${carat.toFixed(2)} ct</td></tr>
                <tr><td>Preis/ct:</td><td>${formatUSD(pricePerCarat)}</td></tr>
                <tr class="total-price"><td>Gesamtpreis:</td><td>${formatUSD(totalPrice)}</td></tr>
            </table>
        </div>
    `;

    // Bilder anzeigen
    if (gem.images && gem.images[quality]) {
        gem.images[quality].forEach(url => {
            const img = document.createElement('img');
            img.src = url;
            img.alt = `${gem.name} (${quality})`;
            img.classList.add('quality-image');
            img.addEventListener('click', () => {
                const overlay = document.createElement('div');
                overlay.classList.add('image-overlay');
                const largeImg = document.createElement('img');
                largeImg.src = url;
                overlay.appendChild(largeImg);
                document.body.appendChild(overlay);
                overlay.addEventListener('click', () => overlay.remove());
            });
            imageBox.appendChild(img);
        });
    }
}
