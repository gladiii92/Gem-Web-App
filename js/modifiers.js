// modifiers.js — Modifier-Logik für Origins, Farben, Behandlungen
// Faktoren sind aktuell Schätzwerte — werden mit mehr Crawler-Daten verfeinert.
// Format: { id, label, type, factor, appliesTo }
// factor: 1.3 = +30%, 0.7 = -30%
// appliesTo: Array von gem-IDs oder 'all'

export const MODIFIERS = {
  // ── Origins ──────────────────────────────────────────────────────────────
  burma:         { id: 'burma',         label: 'Burma',          type: 'origin',    factor: 1.40, appliesTo: 'all' },
  ceylon:        { id: 'ceylon',        label: 'Ceylon-Origin',  type: 'origin',    factor: 1.20, appliesTo: 'all' },
  kashmir:       { id: 'kashmir',       label: 'Kashmir',        type: 'origin',    factor: 2.50, appliesTo: [1,2,3,4,5,21] },
  colombia:      { id: 'colombia',      label: 'Kolumbien',      type: 'origin',    factor: 1.50, appliesTo: [6] },
  mozambique:    { id: 'mozambique',    label: 'Mosambik',       type: 'origin',    factor: 1.20, appliesTo: 'all' },

  // ── Farben ───────────────────────────────────────────────────────────────
  cornflower:    { id: 'cornflower',    label: 'Cornflower Blue', type: 'color',    factor: 3.00, appliesTo: [1,2,3,4,5] },
  royalblue:     { id: 'royalblue',     label: 'Royal Blue',      type: 'color',    factor: 2.00, appliesTo: [1,2,3,4,5] },
  pigeonblood:   { id: 'pigeonblood',   label: 'Pigeon Blood',    type: 'color',    factor: 4.00, appliesTo: [21] },
  padparadscha:  { id: 'padparadscha',  label: 'Padparadscha',    type: 'color',    factor: 2.50, appliesTo: [10] },

  // ── Behandlungen ─────────────────────────────────────────────────────────
  unheated:      { id: 'unheated',      label: 'Ungeheizt',       type: 'treatment', factor: 1.30, appliesTo: 'all' },
  heated:        { id: 'heated',        label: 'Geheizt',         type: 'treatment', factor: 0.70, appliesTo: 'all' },
  notreatment:   { id: 'notreatment',   label: 'Keine Behandlung',type: 'treatment', factor: 1.25, appliesTo: 'all' },
};

/**
 * Gibt alle Modifier zurück die für eine gem-ID relevant sind.
 * @param {number} gemId
 * @returns {Array}
 */
export function getModifiersForGem(gemId) {
  return Object.values(MODIFIERS).filter(m =>
    m.appliesTo === 'all' || m.appliesTo.includes(gemId)
  );
}

/**
 * Berechnet den kombinierten Faktor aller aktiven Modifier.
 * Additive Logik: Faktoren werden multipliziert.
 * @param {string[]} activeIds — Array von aktiven Modifier-IDs
 * @returns {number} kombinierter Faktor
 */
export function calcCombinedFactor(activeIds) {
  if (!activeIds || activeIds.length === 0) return 1.0;
  return activeIds.reduce((factor, id) => {
    const mod = MODIFIERS[id];
    return mod ? factor * mod.factor : factor;
  }, 1.0);
}

/**
 * Formatiert den Faktor als lesbares Label für den Button.
 * 1.3 → "+30%", 0.7 → "-30%"
 */
export function formatFactor(factor) {
  const pct = Math.round((factor - 1) * 100);
  return pct >= 0 ? `+${pct}%` : `${pct}%`;
}
