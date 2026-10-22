# Changelog
## 2.3.0 — 2026-10-22
- Cloudflare Pages support: Pages Functions port of the AI proxy, `_headers` security headers
- Render static blueprint (`render.yaml`), hosting comparison doc
## 2.2.1 — 2026-10-22
- Vercel project root is now `site/` (api, vercel.json, package.json moved inside) so Vercel no longer detects multiple services
## 2.2.0 — 2026-10-22
- Vercel deployment: serverless LLM proxy (`/api/llm`) with server-held keys, firewall, per-IP and daily limits, and health check
- Strict CSP: all site scripts moved to external files; security headers in `vercel.json`; `security.txt`
- Site: credentials section (22 items), live GitHub activity, command palette (Ctrl K), voice input and read-aloud, offline service worker, skip link, Vercel Analytics hook
- Backend: login lockout, audit-chain verification endpoint, AI alert explanations (corrective RAG), AI weekly executive report
- Console: Explain with AI on alerts, weekly report button
## 2.1.0 — 2026-10-22
- Added demo data seeder (`make seed`) so the console shows live charts, alerts and a pending plan
- Added Alembic migration scaffold (`make migrate`)
- Added SEO and social metadata, sitemap, robots, 404 page, web manifest, OG image
- Added MIT license, contributing guide, issue and PR templates, CODEOWNERS
## 2.0.0
- LLM firewall, TOTP MFA, corrective RAG, policy critic, forecasting, observability stack, Kubernetes manifests, in-browser assistant
## 1.0.0
- Initial platform: collectors, CNN, swarm, gateway, MCP, console, Pages site
