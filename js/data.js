// DATA LAYER — einzige Stelle die data.json kennt
// Senior Note: Wenn später ein Backend kommt, wird nur diese Datei geändert.
// Der Rest der App merkt nichts. Das ist Dependency Inversion.

const CACHE_KEY = 'gem_data_cache';
const API_URL = './data.json'; // später: 'https://api.yourapp.com/v1/gems'

let _gemsCache = null;

/**
 * Lädt Gem-Daten. Nutzt In-Memory-Cache nach erstem Load.
 * @returns {Promise<Object[]>}
 */
export async function loadGems() {
  if (_gemsCache) return _gemsCache;

  try {
    const response = await fetch(API_URL);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    _gemsCache = await response.json();
    return _gemsCache;
  } catch (err) {
    console.error('[data.js] Fehler beim Laden:', err);
    throw err;
  }
}

/**
 * @param {number} id
 * @returns {Object|undefined}
 */
export function getGemById(id) {
  return _gemsCache?.find(g => g.id === id);
}