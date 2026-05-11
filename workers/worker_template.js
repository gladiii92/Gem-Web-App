// GEM INTELLIGENCE — Cloudflare Worker (auto-generated, do not edit directly)
// Edit workers/worker_template.js instead, then run generate_worker.py

const GEM_DATA = __GEM_DATA_PLACEHOLDER__;

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': 'https://gladiii92.github.io',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Content-Type': 'application/json',
};

export default {
  async fetch(request) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS_HEADERS });
    }

    const url = new URL(request.url);

    if (url.pathname === '/gems') {
      return new Response(JSON.stringify(GEM_DATA), {
        headers: CORS_HEADERS
      });
    }

    const match = url.pathname.match(/^\/gems\/(\d+)$/);
    if (match) {
      const gem = GEM_DATA.find(g => g.id === parseInt(match[1]));
      if (!gem) return new Response('Not found', { status: 404, headers: CORS_HEADERS });
      return new Response(JSON.stringify(gem), { headers: CORS_HEADERS });
    }

    return new Response('Gem Intelligence API v1', { headers: CORS_HEADERS });
  }
};