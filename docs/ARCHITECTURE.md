# CloudPulse AI — Architecture

```mermaid
flowchart LR
  subgraph Clouds
    AWS[AWS CloudWatch/Boto3]
    GCP[GCP Monitoring]
    K8S[Kubernetes Metrics API]
  end
  subgraph Workers[Celery Workers]
    COL[Collectors]
    CNNW[CNN Heatmap Worker]
    APPLY[Terraform Apply Worker]
  end
  subgraph Core[FastAPI Gateway]
    API[REST + SSE + WebSocket]
    MCP[MCP JSON-RPC /mcp]
    SW[LangGraph Swarm]
    GW[Multi-LLM Router]
  end
  AWS & GCP & K8S --> COL --> TS[(TimescaleDB)]
  TS --> CNNW --> CNN[PyTorch CNN] --> PG[(PostgreSQL alerts/plans)]
  API --> SW --> GW
  GW -->|fast tools/chat| GROQ[Groq gpt-oss-120b]
  GW -->|reasoning/multimodal| GEM[Gemini]
  GW <--> RED[(Redis semantic cache + broker)]
  SW --> QD[(Qdrant: CIS, runbooks, tfstate)]
  SW --> TF[Terraform dry-run / blast radius]
  API --> PG
  API -- approve (HITL) --> RED --> APPLY --> Clouds
  MCP --> SW
  UI[Next.js UI] <--> API
  FW[LLM firewall: injection + redaction] --> API
  API --> CRAG[Corrective RAG grader]
  SW --> CRIT[Policy critic]
  API --> PROM[Prometheus/Grafana]
  API --> OTEL[OTel Collector] --> JAE[Jaeger]
  NGX[nginx edge: rate limits, headers] --> API
```

## Trust boundaries
- Credentials: Fernet-encrypted at column level; key from env/KMS, never logged.
- AuthN/Z: OAuth2 password flow → JWT; roles viewer < operator < admin.
- Remediation: every plan is dry-run first; blast radius above `BLAST_RADIUS_MAX` needs admin approval.
- Audit: append-only hash chain (`prev_hash`/`hash`) + DB trigger blocks UPDATE/DELETE.
- MCP exposes read + propose tools only. It cannot approve or apply.
