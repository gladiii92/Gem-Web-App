document.addEventListener('DOMContentLoaded', () => {
    const gemSelect = document.getElementById('gem-select');
    const qualitySelect = document.getElementById('quality-select');

    // Qualitätsbezeichnungen
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
            // Steinauswahl füllen
            gems.forEach(gem => {
                const option = new Option(
                    `${gem.id}. ${gem.name}${gem.special ? ' (Nur VVS)' : ''}`,
                    gem.id
                );
                gemSelect.add(option);
            });

            // Qualitätsauswahl aktualisieren
            gemSelect.addEventListener('change', () => {
                const gem = gems.find(g => g.id === parseInt(gemSelect.value));
                qualitySelect.innerHTML = '';

                if (gem.special) {
                    // Nur VVS für spezielle Steine
                    const option = new Option(qualityLabels['VVS'], 'VVS');
                    qualitySelect.add(option);
                } else {
                    // Alle Qualitäten für normale Steine
                    Object.entries(qualityLabels).forEach(([key, label]) => {
                        const option = new Option(label, key);
                        qualitySelect.add(option);
                    });
                }
            });

            // Initialen Status setzen
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
                    <p>Qualität: ${document.getElementById('quality-select').selectedOptions[0].text}</p>
                    <p>Karat: ${carat} ct</p>
                    <p>Preis/Kt: $${pricePerCarat.toLocaleString()}</p>
                    <p class="total">Gesamtpreis: $${totalPrice.toLocaleString()}</p>
                </div>
            `;
        });
}