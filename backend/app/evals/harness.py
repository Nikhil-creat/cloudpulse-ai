"""Offline RAG evaluation: recall@k on a golden set using the hashing embedder (no services needed)."""
from app.knowledge.seed import DOCS
from app.llm.cache import HashingEmbedder

GOLDEN = [
    ("bucket is publicly readable fix", "S3 public access"),
    ("instances with low cpu for weeks", "Idle compute rightsizing"),
    ("ssh open to the whole internet", "Security group exposure"),
    ("aws key leaked on github", "Credential leak response"),
    ("pods running as root", "Kubernetes pod hardening"),
    ("sudden jump in monthly bill", "Cost spike triage"),
    ("wildcard iam permissions", "IAM least privilege"),
    ("database reachable from internet", "Database exposure"),
]


def evaluate(k: int = 3) -> dict:
    emb = HashingEmbedder()
    vecs = [(d["title"], emb.embed(d["title"] + " " + d["text"])) for d in DOCS]
    hits = 0
    for q, want in GOLDEN:
        qv = emb.embed(q)
        top = [t for t, _ in sorted(vecs, key=lambda x: float(qv @ x[1]), reverse=True)[:k]]
        hits += want in top
    return {"recall_at_k": hits / len(GOLDEN), "k": k, "n": len(GOLDEN)}


if __name__ == "__main__":
    print(evaluate())
