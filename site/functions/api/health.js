// Cloudflare Pages Function: GET /api/health
export async function onRequestGet({ env }) {
  const providers = [env.GROQ_API_KEY && 'groq', env.GEMINI_API_KEY && 'gemini'].filter(Boolean);
  return new Response(JSON.stringify({ ok: true, version: '2.3.2', llm: providers.length > 0, providers }), {
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
  });
}
