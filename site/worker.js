// Cloudflare Worker entry (Workers + static assets). Routes /api/* to the AI proxy, everything else to static files.
import { onRequestPost } from './functions/api/llm.js';
import { onRequestGet } from './functions/api/health.js';

const json = (code, body, extra = {}) => new Response(JSON.stringify(body), {
  status: code,
  headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', ...extra },
});

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);
    if (pathname === '/api/health') {
      return request.method === 'GET' || request.method === 'HEAD' ? onRequestGet({ env }) : json(405, { error: 'GET only' }, { Allow: 'GET' });
    }
    if (pathname === '/api/llm') {
      return request.method === 'POST' ? onRequestPost({ request, env }) : json(405, { error: 'POST only' }, { Allow: 'POST' });
    }
    if (pathname.startsWith('/api/')) return json(404, { error: 'Not found' });
    return env.ASSETS.fetch(request);
  },
};
