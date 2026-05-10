const IS_LOCAL = location.hostname === '127.0.0.1' || location.hostname === 'localhost';
const API_URL  = IS_LOCAL
  ? './data.json'
  : 'https://gem-api.dave921.workers.dev/gems';

let _gemsCache = null;

export async function loadGems() {
  if (_gemsCache) return _gemsCache;
  const response = await fetch(API_URL);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  _gemsCache = await response.json();
  return _gemsCache;
}

export function getGemById(id) {
  return _gemsCache?.find(g => g.id === id);
}