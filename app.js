document.addEventListener('DOMContentLoaded', () => {
    const gemSelect = document.getElementById('gem-select');
    const qualitySelect = document.getElementById('quality-select');

    const qualityLabels = {
        'I1': 'Low (I1)',
        'SI2': 'Mid-Low (SI2)',
        'SI1': 'Mid (SI1)',
        'VS': 'Mid-High (VS)',
        'VVS': 'High (VVS)'
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
    const gemId = parseInt(document.getElementById('gem-select').value);
    const quality = document.getElementById('quality-select').value;
    const carat = parseFloat(document.getElementById('carat').value);

    fetch('data.json')
        .then(response => response.json())
        .then(gems => {
            const gem = gems.find(g => g.id === gemId);
            const range = gem.price_ranges.find(r =>
                carat >= r.carat_min && carat <= r.carat_max
            );

            const pricePerCarat = gem.special ? range.VVS : range[quality];
            const totalPrice = pricePerCarat * carat;

            document.getElementById('result').innerHTML = `
                <div class="result-box">
                    <h3>${gem.name}</h3>
                    ${gem.notes ? `<div class="gem-notes">ℹ️ ${gem.notes}</div>` : ''}
                    ${gem.quality_notes ? `<div class="gem-notes">💎 ${gem.quality_notes}</div>` : ''}
                    <table>
                        <tr><td>Qualität:</td><td>${document.getElementById('quality-select').selectedOptions[0].text}</td></tr>
                        <tr><td>Karat:</td><td>${carat} ct</td></tr>
                        <tr><td>Preis/Kt:</td><td>$${pricePerCarat.toLocaleString()}</td></tr>
                        <tr class="total-price"><td>Gesamtpreis:</td><td>$${totalPrice.toLocaleString()}</td></tr>
                    </table>
                </div>
            `;
        });
}
