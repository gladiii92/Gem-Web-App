const gemData = {
    "Spinell": {
        "Farben": {
            "Rot": {
                "SI2": { "1-2": 150, "2-3": 180, "3-5": 220, "note": "SI2 = noch gute Farbe, leicht sichtbare Einschlüsse" },
                "SI1": { "1-2": 200, "2-3": 240, "3-5": 280, "note": "SI1 = kräftiger Ton, minimale Einschlüsse" },
                "VS":  { "1-2": 280, "2-3": 320, "3-5": 380, "note": "VS = sehr gute Klarheit mit schöner Sättigung" },
                "VVS": { "1-2": 350, "2-3": 420, "3-5": 500, "note": "VVS = perfekte Reinheit und Topfarbe" }
            }
        },
        "note": "Alle Preise pro Karat in € für unbehandelte Spinelle mit Designschliff."
    }
};

function populateGemSelect() {
    const gemSelect = document.getElementById('gem-select');
    for (let gem in gemData) {
        const option = document.createElement('option');
        option.value = gem;
        option.textContent = gem;
        gemSelect.appendChild(option);
    }
}

function calculatePrice() {
    const gem = document.getElementById('gem-select').value;
    const quality = document.getElementById('quality-select').value;
    const carat = parseFloat(document.getElementById('carat').value);

    if (!gem || !quality || isNaN(carat)) {
        alert("Bitte wähle alle Felder aus und gib ein gültiges Karatgewicht an.");
        return;
    }

    const color = "Rot"; // aktuell fest programmiert
    const data = gemData[gem]?.Farben?.[color]?.[quality];

    if (!data) {
        document.getElementById("result").innerHTML = "<p>Keine Preisinformation gefunden.</p>";
        return;
    }

    let pricePerCarat;
    if (carat <= 2) pricePerCarat = data["1-2"];
    else if (carat <= 3) pricePerCarat = data["2-3"];
    else pricePerCarat = data["3-5"];

    const totalPrice = pricePerCarat * carat;

    const resultBox = document.getElementById("result");
    resultBox.innerHTML = `
        <div class="quality-note"><strong>Hinweis zur Qualität:</strong><br>${data.note}</div>
        <div class="general-note"><strong>Allgemeiner Hinweis:</strong><br>${gemData[gem].note}</div>
        <table>
            <tr><td>Stein:</td><td>${gem}</td></tr>
            <tr><td>Farbe:</td><td>${color}</td></tr>
            <tr><td>Qualität:</td><td>${quality}</td></tr>
            <tr><td>Karat:</td><td>${carat}</td></tr>
            <tr><td>Preis pro Karat:</td><td>${pricePerCarat} €</td></tr>
            <tr class="total-price"><td>Gesamtpreis:</td><td>${totalPrice.toFixed(2)} €</td></tr>
        </table>
    `;
}

document.addEventListener('DOMContentLoaded', populateGemSelect);
