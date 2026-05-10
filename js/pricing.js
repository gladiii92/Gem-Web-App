// PRICING ENGINE
// Datenformat: range[quality] = { retail_min, retail_max, wholesale_min, wholesale_max, _wholesale_source }
// _wholesale_source: 'auto_1_5' | 'crawler' | 'manual'
// Crawler schreibt später wholesale_min/max + _wholesale_source = 'crawler' — pricing.js ändert sich NICHT

const GRADE_KEYS = ['I1', 'SI2', 'SI1', 'VS', 'VVS'];

function findPriceRange(gem, carat) {
  return gem.price_ranges.find(r => carat >= r.carat_min && carat <= r.carat_max) || null;
}

function rangeHasPrices(range) {
  return GRADE_KEYS.some(g => range[g] !== undefined);
}

/**
 * @param {Object} gem
 * @param {'I1'|'SI2'|'SI1'|'VS'|'VVS'} quality
 * @param {number} carat
 * @param {'retail'|'wholesale'} mode
 * @returns {{ minPerCarat, maxPerCarat, minTotal, maxTotal, wholesaleSource }|{ error: string }}
 */
export function calculatePrice(gem, quality, carat, mode = 'retail') {
  if (!gem || !quality || !carat || carat <= 0) {
    return { error: 'Bitte alle Felder korrekt ausfüllen.' };
  }

  const range = findPriceRange(gem, carat);
  if (!range) return { error: 'Keine Preisspanne für dieses Karat gefunden.' };

  if (!rangeHasPrices(range)) {
    return { error: `⚠️ Kein Ankauf empfohlen für ${gem.name} über ${range.carat_min} ct.` };
  }

  const gradeData = range[quality];
  if (!gradeData) return { error: 'Keine Preisdaten für diese Qualitätsstufe.' };

  const minKey = mode === 'wholesale' ? 'wholesale_min' : 'retail_min';
  const maxKey = mode === 'wholesale' ? 'wholesale_max' : 'retail_max';

  return {
    minPerCarat:    gradeData[minKey],
    maxPerCarat:    gradeData[maxKey],
    minTotal:       Math.round(gradeData[minKey] * carat),
    maxTotal:       Math.round(gradeData[maxKey] * carat),
    wholesaleSource: gradeData._wholesale_source ?? null, // 'auto_1_5' | 'crawler' | 'manual'
  };
}

export function getAvailableGrades(gem) {
  const firstRange = gem.price_ranges.find(r => rangeHasPrices(r));
  if (!firstRange) return ['VVS'];
  return GRADE_KEYS.filter(g => firstRange[g] !== undefined);
}