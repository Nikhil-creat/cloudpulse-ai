# Security Model (STRIDE summary)
| Threat | Control in this repo |
|---|---|
| Spoofing | OAuth2 password flow + JWT, optional TOTP MFA (RFC 6238), scrypt password hashing |
| Tampering | Hash-chained audit log; DB trigger blocks UPDATE/DELETE; Terraform apply only from an approved, saved plan |
| Repudiation | Every login, plan proposal, approval, apply writes an audit row with actor and hash |
| Information disclosure | Fernet column encryption for cloud credentials; secret/PII redaction on prompts and outputs; `/metrics` not exposed at the proxy |
| Denial of service | Redis rate limits per user, nginx `limit_req`, 1 MB body cap, LLM circuit breakers and timeouts |
| Elevation of privilege | Role ladder viewer < operator < admin; four-eyes approval; admin required for high blast radius or policy violations |
| Prompt injection (direct) | Regex firewall blocks override attempts before any model call |
| Prompt injection (indirect) | Tool and RAG output is scrubbed and fenced as untrusted data |
| Unsafe agent actions | Policy-as-code critic (open SSH/RDP, wildcard IAM, public buckets, encryption off), Terraform dry-run, blast radius score, HITL gate |
| MCP abuse | MCP exposes read and propose tools only; no approve or apply |
| Supply chain | Dependabot, CodeQL, Trivy, gitleaks, pinned base images, non-root containers with dropped capabilities |

Known gaps for production: add Alembic migrations, a KMS-backed key, mTLS between services, and per-tenant isolation.
