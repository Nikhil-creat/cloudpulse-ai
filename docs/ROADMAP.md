# 6-Month Roadmap
| Month | Objective | Exit criteria |
|---|---|---|
| 1 Foundations | Monorepo, auth/RBAC, Fernet vault, Timescale schema, AWS collector | Metrics land in hypertable; audit chain verified |
| 2 Telemetry at scale | GCP + K8s collectors, WebSocket stream, dashboards, retention + compression policies | 10k series/min sustained, p95 query < 300 ms |
| 3 LLM gateway + RAG | Groq/Gemini router, semantic cache, Qdrant ingest (CIS, runbooks, tfstate) | Cache hit rate > 30%, failover test green |
| 4 CNN anomaly engine | Heatmap pipeline, real-data labelling, training/eval loop, alerting | F1 > 0.9 on held-out incidents |
| 5 Agent swarm + HITL | FinOps/Security/Planner agents, Terraform sandbox, approval UI, MCP server | 100% of applies gated by approval; dry-run coverage 100% |
| 6 Hardening + GA | OTel dashboards, load/chaos tests, SBOM + image scanning, Helm chart, docs | Pen-test findings closed; GA tag |
