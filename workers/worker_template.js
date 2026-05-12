// GEM INTELLIGENCE — Cloudflare Worker v2 (KV-Backend)
// Daten kommen aus KV Namespace GEM_KV, nicht mehr hardcodiert
// Deploy: Cloudflare Dashboard → Worker → Code ersetzen + KV Binding setzen

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': 'https://gladiii92.github.io',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Content-Type': 'application/json',
};

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS_HEADERS });
    }

    // KV lesen — gecacht für 60s (kein KV-Read bei jedem Request)
    let gemData;
    try {
      const raw = await env.GEM_KV.get('gems', { cacheTtl: 60 });
      if (!raw) {
        return new Response(JSON.stringify({ error: 'KV leer — generate_worker.py ausführen' }),
          { status: 503, headers: CORS_HEADERS });
      }
      gemData = JSON.parse(raw);
    } catch (e) {
      return new Response(JSON.stringify({ error: 'KV Fehler: ' + e.message }),
        { status: 500, headers: CORS_HEADERS });
    }

    const url = new URL(request.url);

    if (url.pathname === '/gems') {
      return new Response(JSON.stringify(gemData), { headers: CORS_HEADERS });
    }

    const match = url.pathname.match(/^\/gems\/(\d+)$/);
    if (match) {
      const gem = gemData.find(g => g.id === parseInt(match[1]));
      if (!gem) return new Response('Not found', { status: 404, headers: CORS_HEADERS });
      return new Response(JSON.stringify(gem), { headers: CORS_HEADERS });
    }

    return new Response('GEM INTELLIGENCE API v2', { headers: CORS_HEADERS });
  }
};