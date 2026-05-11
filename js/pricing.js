// PRICING ENGINE v2
// Datenformat: range[quality] = { retail_min, retail_max, wholesale_min, wholesale_max, _wholesale_source }
// _wholesale_source: 'auto_1_5' | 'crawler' | 'manual'

import { calcCombinedFactor } from './modifiers.js';

const GRADE_KEYS = ['I1', 'SI2', 'SI1', 'VS', 'VVS'];

function findPriceRange(gem, carat) {
  return gem.price_ranges.find(r => carat >= r.carat_min && carat <= r.carat_max) || null;
}

function rangeHasPrices(range) {
  return GRADE_KEYS.some(g => range[g] !== undefined);
}

/**
 * @param {object} gem
 * @param {string} quality  — Clarity-Grade (z.B. 'VVS')
 * @param {number} carat
 * @param {string} mode     — 'retail' | 'wholesale'
 * @param {string[]} activeModifiers — Array aktiver Modifier-IDs
 * @returns {{ allGrades, crawlerStats, wholesaleSource } | { error: string }}
 */
export function calculatePrice(gem, quality, carat, mode = 'retail', activeModifiers = []) {
  if (!gem || !quality || !carat || carat <= 0)
    return { error: 'Bitte alle Felder korrekt ausfüllen.' };

  const range = findPriceRange(gem, carat);
  if (!range) return { error: 'Keine Preisspanne für dieses Karat gefunden.' };

  if (!rangeHasPrices(range))
    return { error: `⚠️ Kein Ankauf empfohlen für ${gem.name} über ${range.carat_min} ct.` };

  const modFactor = calcCombinedFactor(activeModifiers);

  // ── Alle Clarity-Grades berechnen ────────────────────────────────────────
  const allGrades = GRADE_KEYS
    .filter(g => range[g] !== undefined)
    .map(g => {
      const gradeData = range[g];
      const minKey = mode === 'wholesale' ? 'wholesale_min' : 'retail_min';
      const maxKey = mode === 'wholesale' ? 'wholesale_max' : 'retail_max';
      const rawMin = gradeData[minKey] ?? null;
      const rawMax = gradeData[maxKey] ?? null;
      return {
        grade:          g,
        minPerCarat:    rawMin != null ? Math.round(rawMin * modFactor) : null,
        maxPerCarat:    rawMax != null ? Math.round(rawMax * modFactor) : null,
        minTotal:       rawMin != null ? Math.round(rawMin * carat * modFactor) : null,
        maxTotal:       rawMax != null ? Math.round(rawMax * carat * modFactor) : null,
        wholesaleSource: gradeData._wholesale_source ?? null,
      };
    });

  // ── Crawler-Stats aus _crawler_stats.by_source ───────────────────────────
  const crawlerStats = range._crawler_stats?.by_source ?? null;

  // Ausgewählte Grade für Rückwärtskompatibilität
  const selected = allGrades.find(g => g.grade === quality) || allGrades.at(-1);

  return {
    ...selected,
    allGrades,
    crawlerStats,
    modFactor,
  };
}

export function getAvailableGrades(gem) {
  const firstRange = gem.price_ranges.find(r => rangeHasPrices(r));
  if (!firstRange) return ['VVS'];
  return GRADE_KEYS.filter(g => firstRange[g] !== undefined);
}
