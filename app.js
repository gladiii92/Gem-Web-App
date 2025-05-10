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

            // 2) Change-Listener
            gemSelect.addEventListener('change', () => {
                const gemId = parseInt(gemSelect.value, 10);
                const gem = gems.find(g => g.id === gemId);
                qualitySelect.innerHTML = '';

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

            // 3) Initiale Anzeige
            gemSelect.dispatchEvent(new Event('change'));
        })
        .catch(err => console.error('Fehler beim Laden der Daten:', err));
});

function calculatePrice() {
    const gemId    = parseInt(document.getElementById('gem-select').value, 10);
    const quality  = document.getElementById('quality-select').value;
    const carat    = parseFloat(document.getElementById('carat').value);
    const resultBox= document.getElementById('result');
    const imageBox = document.getElementById('image-box');

    resultBox.innerHTML = '';
    imageBox.innerHTML   = '';

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

    // „min-max“ String splitten
    const [minStr, maxStr] = (range[quality] || range.VVS).split('-');
    const minPerCarat = Number(minStr);
    const maxPerCarat = Number(maxStr);
    const minTotal    = Math.round(minPerCarat * carat);
    const maxTotal    = Math.round(maxPerCarat * carat);

    const qNote = gem.quality_notes?.[quality] || '';

    // Ergebnis anzeigen mit Min–Max
    resultBox.innerHTML = `
        <div class="result-box">
            <h3>${gem.name}</h3>
            ${gem.notes ? `<div class="general-note">ℹ️ ${gem.notes}</div>` : ''}
            ${qNote  ? `<div class="quality-note">💎 ${qNote.replace(/\n/g, '<br>')}</div>` : ''}
            <table>
                <tr><td>Qualität:</td><td>${quality}</td></tr>
                <tr><td>Karat:</td><td>${carat.toFixed(2)} ct</td></tr>
                <tr><td>Preis/ct:</td><td>$${minPerCarat}–$${maxPerCarat}</td></tr>
                <tr class="total-price"><td>Gesamtpreis:</td><td>$${minTotal}–$${maxTotal}</td></tr>
                <tr class="discount-info"><td colspan="2"><strong>Abschläge:</strong> ID 1–9 = 10% | ID 10–24 = 30% | ID 25–27 = 50%</td></tr>
            </table>
        </div>
    `;

    // Bilder anzeigen
    if (gem.images?.[quality]) {
        gem.images[quality].forEach(url => {
            const img = document.createElement('img');
            img.src = url;
            img.alt = `${gem.name} (${quality})`;
            img.classList.add('quality-image');
            img.addEventListener('click', () => {
                const overlay = document.createElement('div');
                overlay.classList.add('image-overlay', 'active');
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
