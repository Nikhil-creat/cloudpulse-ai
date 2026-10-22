# Hosting options

| Option | Website | AI proxy (server-held keys) | Full Docker backend | Notes |
|---|---|---|---|---|
| GitHub Pages | Yes | No (visitors paste their own key) | No | Simplest, already working |
| Cloudflare Pages | Yes | Yes (Pages Functions) | No | Best free alternative, no card |
| Vercel | Yes | Yes (Serverless Functions) | No | Set Root Directory to `site` |
| Render (free) | Yes (static) | No | No | Free web services sleep after 15 minutes and free databases expire, so use it for the static site only |
| Your PC or a VM | Yes | Yes | Yes | `docker compose up`; the only way to run Postgres, Redis, Qdrant and Celery together |
