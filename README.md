# CloudPulse AI v2.3

Agentic multi-cloud FinOps, security auto-remediation and AI observability. MCP-native, with corrective RAG, a CNN anomaly detector, an LLM firewall and a human-approved agent swarm.

Live site (after you deploy): https://nikhil-creat.github.io/cloudpulse-ai/

## Deploy live (Vercel, Cloudflare Pages or Render)
See `docs/HOSTING_OPTIONS.md`, `docs/VERCEL_DEPLOY.md` and `docs/CLOUDFLARE_DEPLOY.md`.

### Vercel
See `docs/VERCEL_DEPLOY.md`. Import the repo with Root Directory `site`, add `GROQ_API_KEY` and `GEMINI_API_KEY`, deploy. The assistant then works for every visitor with keys kept server-side.

## What's new in v2.2
Serverless LLM proxy, strict CSP, credentials section, live GitHub activity, command palette (Ctrl K), voice in and out, offline service worker, login lockout, audit-chain verification, AI alert explanations and weekly executive report.

## What's new in v2
- **Agentic AI:** LangGraph swarm with a policy-as-code critic and one self-correction pass; conversation memory in Redis.
- **Corrective RAG:** Qdrant retrieval, relevance grading, query rewrite and retry, seeded runbook knowledge base, offline recall eval.
- **CNN:** PyTorch heatmap classifier plus a training script; the site shows layer-1 feature maps.
- **Security:** LLM firewall (injection and secret redaction), indirect-injection fencing, TOTP MFA, rate limits, nginx edge, hash-chained audit log, STRIDE model.
- **FinOps:** EWMA forecast, robust z-score anomalies, month-end projection.
- **Ops:** Prometheus, Grafana dashboard, OpenTelemetry to Jaeger, Kubernetes manifests, k6 load test, CodeQL, Trivy, gitleaks, Dependabot.
- **Assistant on the site:** works in the browser with your own free Groq or Gemini key.

## Free API keys
1. Groq: https://console.groq.com/keys
2. Gemini: https://aistudio.google.com/apikey

**Platform:** put them in `.env` (`GROQ_API_KEY`, `GEMINI_API_KEY`). `.env` is git-ignored. Never commit keys.
**Website:** paste them into the Assistant panel. They are stored in your browser only.

## Run the platform
```bash
cp .env.example .env     # set FERNET_KEY, JWT_SECRET, passwords, API keys
make up                  # console + API behind nginx on :8080
make seed                # demo data: charts, alerts, a pending plan
make train               # optional: train the CNN -> backend/models/cnn.pt
make migrate             # Alembic baseline migration
make test
```
- Console: http://localhost:8080 · API docs: http://localhost:8080/docs
- Grafana http://localhost:3001 · Prometheus :9090 · Jaeger :16686 (all bound to localhost)
- Seed knowledge base manually: `docker compose exec api python -m app.knowledge.seed`
- RAG eval: `docker compose exec api python -m app.evals.harness`

## MCP
`POST http://localhost:8080/mcp` with `Authorization: Bearer <token>`. Tools: `list_resources`, `metric_summary`, `open_alerts`, `search_runbooks`. Approve and apply are deliberately not exposed.

## Layout
```
backend/app/{api,agents,cnn,collectors,core,db,evals,knowledge,llm,security,workers}   backend/tests
frontend/          Next.js 14 console: Overview, Copilot, Alerts, Plans, Security (MFA)
site/index.html    GitHub Pages site: assistant, CNN inspector, approval-gate demo
deploy/            nginx, prometheus, grafana, otel, k8s
docs/              ARCHITECTURE, SECURITY_MODEL, ROADMAP, DEPLOY_GITHUB_PAGES
loadtest/          k6 script
```

## Honest limits
- The hashing embedder (stemmed words plus character n-grams) scores recall@3 of 0.875 on the bundled eval. Paraphrases with no shared words can miss. Use a neural embedder for production.
- Python logic tests were run offline for the guard, TOTP, policy, forecast, CRAG, gateway and CNN preprocessing. Docker, Next.js and live LLM calls were not run in the build environment.
- Alembic is scaffolded (`make migrate`) but no baseline migration is committed yet; generate it on first deploy.
- LLM prices in `llm/gateway.py` are placeholders.

Built by Nikhil Chary Sriramoju · https://github.com/Nikhil-creat
