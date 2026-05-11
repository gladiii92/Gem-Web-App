// vision.js v3 — Multi-Bild Upload (bis zu 3), color_stability Anzeige

const VISION_API_URL = "http://localhost:5000";
const CONFIDENCE_THRESHOLD = 0.85;

const STONE_TYPE_MAP = [
  { keywords: ["paraiba"],                          gemHint: "Paraiba"       },
  { keywords: ["alexandrite", "alexandrit"],        gemHint: "Alexandrit"    },
  { keywords: ["ruby", "rubin"],                    gemHint: "Rubin"         },
  { keywords: ["cornflower blue sapphire"],         gemHint: "Saphir (Blau"  },
  { keywords: ["blue sapphire", "blauer saphir"],   gemHint: "Saphir (Blau"  },
  { keywords: ["yellow sapphire", "gelber saphir"], gemHint: "Gelb"          },
  { keywords: ["padparadscha"],                     gemHint: "Padparadscha"  },
  { keywords: ["white sapphire", "weißer saphir"],  gemHint: "Weiß"          },
  { keywords: ["sapphire", "saphir"],               gemHint: "Saphir"        },
  { keywords: ["emerald", "smaragd"],               gemHint: "Smaragd"       },
  { keywords: ["tanzanite", "tansanit"],            gemHint: "Tanzanit"      },
  { keywords: ["spinel", "spinell"],                gemHint: "Spinell"       },
  { keywords: ["rubellite"],                        gemHint: "Rubellite"     },
  { keywords: ["indicolite"],                       gemHint: "Indicolite"    },
  { keywords: ["chrome tourmaline"],                gemHint: "Chrome"        },
  { keywords: ["watermelon"],                       gemHint: "Watermelon"    },
  { keywords: ["tourmaline", "turmalin"],           gemHint: "Tourmalin"     },
  { keywords: ["rhodolite"],                        gemHint: "Rhodolite"     },
  { keywords: ["malaya"],                           gemHint: "Malaya"        },
  { keywords: ["color-change garnet"],              gemHint: "Color-Change"  },
  { keywords: ["tsavorite", "tsavorit"],            gemHint: "Tsavorit"      },
  { keywords: ["demantoid"],                        gemHint: "Demantoid"     },
  { keywords: ["morganite", "morganit"],            gemHint: "Morganite"     },
  { keywords: ["topaz", "topas"],                   gemHint: "Topaz"         },
];

const CLARITY_MAP = { "I1": "I1", "SI2": "SI2", "SI1": "SI1", "VS": "VS", "VVS": "VVS" };

// ── Health-Check ────────────────────────────────────────────────────────────
async function checkVisionHealth() {
  const statusEl = document.getElementById("vision-status");
  if (!statusEl) return;
  try {
    const resp = await fetch(`${VISION_API_URL}/health`, { signal: AbortSignal.timeout(4000) });
    const data = await resp.json();
    if (data.status === "ok" && data.model_available) {
      statusEl.innerHTML = `<span class="vision-status-ok">✓ Vision bereit (${data.model})</span>`;
    } else if (data.status === "ok" && !data.model_available) {
      statusEl.innerHTML = `<span class="vision-status-warn">⚠️ Ollama läuft, Modell nicht geladen</span>`;
    }
  } catch {
    statusEl.innerHTML = `<span class="vision-status-off">○ Vision offline — <code>python vision/vision_api.py</code> starten</span>`;
  }
}

// ── Stone-Type → Dropdown ───────────────────────────────────────────────────
function matchStoneToDropdown(stoneType) {
  if (!stoneType) return null;
  const lower = stoneType.toLowerCase();
  for (const entry of STONE_TYPE_MAP) {
    if (entry.keywords.some(k => lower.includes(k))) return entry.gemHint;
  }
  return null;
}

function selectGemInDropdown(gemHint) {
  if (!gemHint) return false;
  const select = document.getElementById("gem-select");
  if (!select) return false;
  const hint = gemHint.toLowerCase();
  for (const opt of select.options) {
    if (opt.text.toLowerCase().includes(hint)) {
      select.value = opt.value;
      select.dispatchEvent(new Event("change"));
      return true;
    }
  }
  return false;
}

function applyCandidate(candidate) {
  const caratInput = document.getElementById("carat-input");
  const gemHint    = matchStoneToDropdown(candidate.stone_type);
  const gemMatched = selectGemInDropdown(gemHint);

  const clarityVal = CLARITY_MAP[candidate.clarity_estimate];
  if (clarityVal) {
    const qs = document.getElementById("quality-select");
    if (qs) { qs.value = clarityVal; qs.dispatchEvent(new Event("change")); }
  }

  const currentCarat = parseFloat(caratInput?.value);
  if ((!currentCarat || currentCarat <= 0) && candidate.carat_approx) {
    if (caratInput) {
      caratInput.value = candidate.carat_approx;
      caratInput.dispatchEvent(new Event("input"));
    }
  }
  return gemMatched;
}

// ── Analyse ─────────────────────────────────────────────────────────────────
async function analyzeImage() {
  const fileInput  = document.getElementById("vision-upload");
  const file2      = document.getElementById("vision-upload-2");
  const file3      = document.getElementById("vision-upload-3");
  const caratInput = document.getElementById("carat-input");
  const resultBox  = document.getElementById("vision-result");
  const btn        = document.getElementById("vision-analyze-btn");

  if (!fileInput?.files?.[0]) {
    resultBox.innerHTML = `<div class="vision-error">Bitte mindestens ein Bild auswählen.</div>`;
    return;
  }

  const nImages = [fileInput, file2, file3].filter(el => el?.files?.[0]).length;
  btn.disabled = true;
  btn.textContent = "Analysiere…";
  resultBox.innerHTML = `<div class="vision-loading">
    <div class="vision-spinner"></div>
    <span>qwen2.5vl analysiert ${nImages} Bild${nImages > 1 ? "er" : ""}…</span>
  </div>`;

  const formData = new FormData();
  formData.append("image",  fileInput.files[0]);
  if (file2?.files?.[0]) formData.append("image2", file2.files[0]);
  if (file3?.files?.[0]) formData.append("image3", file3.files[0]);

  const userCarat = parseFloat(caratInput?.value);
  if (userCarat > 0) formData.append("carat", userCarat);

  try {
    const resp = await fetch(`${VISION_API_URL}/analyze`, { method: "POST", body: formData });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.error || `HTTP ${resp.status}`);
    }
    const data = await resp.json();
    renderVisionResult(data);
  } catch (err) {
    resultBox.innerHTML = `<div class="vision-error">Fehler: ${err.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Stein analysieren";
  }
}

// ── Ergebnis rendern ────────────────────────────────────────────────────────
function renderVisionResult(data) {
  const resultBox  = document.getElementById("vision-result");
  const candidates = data.candidates || [];
  if (candidates.length === 0) {
    resultBox.innerHTML = `<div class="vision-error">Keine Kandidaten zurückgegeben.</div>`;
    return;
  }

  const overallConf  = data.overall_confidence || 0;
  const topCandidate = candidates[0];
  const imgHash      = data.image_hash || "";
  const gemMatched   = applyCandidate(topCandidate);

  // Color stability Badge
  const stabilityMap = {
    "stable":       { label: "Farbe stabil",        cls: "conf-high" },
    "slight_shift": { label: "Leichter Farbwechsel", cls: "conf-mid"  },
    "strong_shift": { label: "Starker Farbwechsel",  cls: "conf-low"  },
  };
  const stability = data.color_stability ? stabilityMap[data.color_stability] : null;
  const stabilityHtml = stability
    ? `<span class="vision-confidence ${stability.cls}" style="margin-left:8px">🎨 ${stability.label}</span>`
    : "";

  const imagesNote = data.images_analyzed > 1
    ? `<div class="vision-quality-note">📷 ${data.images_analyzed} Bilder analysiert</div>`
    : "";

  const imageQualityNote = data.image_quality && !["good","excellent"].includes(data.image_quality)
    ? `<div class="vision-quality-note">📷 Bildqualität: ${data.image_quality} — bessere Aufnahme erhöht Genauigkeit</div>`
    : "";

  const candidateCards = candidates.map((c, i) => {
    const prob      = Math.round((c.probability || 0) * 100);
    const confClass = prob >= 70 ? "conf-high" : prob >= 40 ? "conf-mid" : "conf-low";
    const isTop     = i === 0;
    const caratNote = c.carat_estimated
      ? `<span class="vision-estimate-tag">Schätzung</span>`
      : c.carat_approx ? `<span class="vision-known-tag">Bekannt</span>` : "";

    return `
      <div class="vision-candidate-card${isTop ? " top-candidate" : ""}" data-idx="${i}">
        <div class="vision-candidate-header">
          <span class="vision-candidate-name">
            ${["🥇","🥈","🥉"][i] || ""} ${c.stone_type}
          </span>
          <span class="vision-confidence ${confClass}">${prob}%</span>
        </div>
        <div class="vision-result-grid">
          <div class="vision-field">
            <span class="vision-field-label">Farbe</span>
            <span class="vision-field-value">${c.color || "–"}</span>
          </div>
          <div class="vision-field">
            <span class="vision-field-label">Clarity</span>
            <span class="vision-field-value">${c.clarity_estimate || "–"}</span>
          </div>
          <div class="vision-field">
            <span class="vision-field-label">Karat</span>
            <span class="vision-field-value">${c.carat_approx ? c.carat_approx + " ct " : "– "}${caratNote}</span>
          </div>
          <div class="vision-field">
            <span class="vision-field-label">Herkunft</span>
            <span class="vision-field-value">${c.origin_probability || "–"}</span>
          </div>
        </div>
        ${c.reasoning ? `<div class="vision-reasoning">💡 ${c.reasoning}</div>` : ""}
        ${isTop
          ? `<div class="vision-autofill-note">
              ${gemMatched ? "✓ Automatisch im Calculator ausgewählt" : "⚠️ Bitte Stein manuell wählen"}
            </div>
            <div class="vision-feedback-row" style="margin-top:8px;display:flex;align-items:center;gap:8px;">
              <span style="font-size:0.82em;color:#888">Falsch erkannt?</span>
              <input id="feedback-correct-input" type="text" placeholder="Richtiger Stein…"
                      style="font-size:0.82em;padding:3px 7px;border:1px solid #ccc;border-radius:4px;width:160px"/>
              <button onclick="submitFeedback('${c.stone_type}', document.getElementById('feedback-correct-input').value, '${imgHash}')"
                      style="font-size:0.82em;padding:3px 10px;border:none;background:#e8f0fe;border-radius:4px;cursor:pointer">
                Melden
              </button>
            </div>`
          : `<button class="btn-apply-candidate" onclick="window.applyVisionCandidate(${i})">
              Diesen Stein verwenden →
            </button>`
        }
      </div>`;
  }).join("");

  resultBox.innerHTML = `
    <div class="vision-result-card">
      ${imagesNote}
      ${imageQualityNote}
      <div style="display:flex;align-items:center;flex-wrap:wrap;gap:6px;margin-bottom:10px">
        ${overallConf < CONFIDENCE_THRESHOLD
          ? `<div class="vision-uncertainty-note" style="margin:0;flex:1">⚠️ Gesamtkonfidenz ${Math.round(overallConf*100)}% — bitte Kandidaten prüfen</div>`
          : ""}
        ${stabilityHtml}
      </div>
      ${candidateCards}
      ${data.notes ? `<div class="vision-notes">💬 ${data.notes}</div>` : ""}
    </div>`;
}

// ── Kandidat manuell anwenden ───────────────────────────────────────────────
window.applyVisionCandidate = function(idx) {
  const cards = document.querySelectorAll(".vision-candidate-card");
  if (!cards[idx]) return;

  cards.forEach(c => c.classList.remove("top-candidate"));
  cards[idx].classList.add("top-candidate");

  const nameEl    = cards[idx].querySelector(".vision-candidate-name");
  const stoneName = nameEl?.textContent.replace(/^[🥇🥈🥉]\s*/, "").trim();
  const fields    = cards[idx].querySelectorAll(".vision-field-value");

  const clarityText = fields[1]?.textContent.trim();
  const clarityVal  = CLARITY_MAP[clarityText];
  if (clarityVal) {
    const qs = document.getElementById("quality-select");
    if (qs) { qs.value = clarityVal; qs.dispatchEvent(new Event("change")); }
  }

  const gemHint = matchStoneToDropdown(stoneName);
  const matched = selectGemInDropdown(gemHint);

  const btnEl = cards[idx].querySelector(".btn-apply-candidate");
  if (btnEl) {
    btnEl.textContent = matched ? "✓ Ausgewählt" : "⚠️ Bitte manuell wählen";
    btnEl.disabled = true;
  }
};
window.submitFeedback = submitFeedback;

// ── Multi-Bild Preview ───────────────────────────────────────────────────────
function setupImagePreviews() {
  const configs = [
    { input: "vision-upload",   preview: "vision-preview",   idx: 0 },
    { input: "vision-upload-2", preview: "vision-preview-2", idx: 1 },
    { input: "vision-upload-3", preview: "vision-preview-3", idx: 2 },
  ];

  configs.forEach(({ input, preview, idx }) => {
    const inp  = document.getElementById(input);
    const prev = document.getElementById(preview);
    if (!inp || !prev) return;

    inp.addEventListener("change", () => {
      const file = inp.files?.[0];
      // Altes Thumbnail entfernen
      const oldThumb = document.getElementById(`thumb-${idx}`);
      if (oldThumb) oldThumb.remove();

      if (!file) { prev.src = ""; prev.hidden = true; return; }

      const reader = new FileReader();
      reader.onload = (e) => {
        prev.src = e.target.result;

        // Thumbnail in Vorschau-Zeile einfügen
        const row   = document.getElementById("vision-previews-row");
        const thumb = document.createElement("img");
        thumb.id        = `thumb-${idx}`;
        thumb.src       = e.target.result;
        thumb.className = "vision-preview-thumb";
        thumb.title     = `Bild ${idx + 1}: ${file.name}`;
        row?.appendChild(thumb);
      };
      reader.readAsDataURL(file);
    });
  });
}

// ── Feedback ─────────────────────────────────────────────────────────────────
async function submitFeedback(predicted, correct, imageHash) {
  if (!correct?.trim()) return;
  try {
    const resp = await fetch(`${VISION_API_URL}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ predicted, correct: correct.trim(), image_hash: imageHash }),
    });
    const data = await resp.json();
    if (data.status === "saved") {
      // Button-Feedback direkt im DOM
      const btn = document.querySelector(".vision-feedback-row button");
      if (btn) { btn.textContent = "✓ Gespeichert"; btn.disabled = true; }
    }
  } catch (e) {
    console.warn("[vision] Feedback fehlgeschlagen:", e);
  }
}

// ── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  checkVisionHealth();
  setupImagePreviews();
  document.getElementById("vision-analyze-btn")?.addEventListener("click", analyzeImage);
});
