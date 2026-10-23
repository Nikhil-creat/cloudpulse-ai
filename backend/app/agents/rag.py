"""Agentic RAG over Qdrant: CIS benchmarks, runbooks, Terraform state."""
import uuid

from app.core.config import get_settings
from app.llm.cache import DIM, HashingEmbedder

COLLECTION = "cloudpulse_knowledge"
_emb = HashingEmbedder()  # replace with Gemini text-embedding for production recall


def client():
    from qdrant_client import AsyncQdrantClient
    return AsyncQdrantClient(url=get_settings().qdrant_url)


async def ensure_collection(c) -> None:
    from qdrant_client.models import Distance, VectorParams
    if not await c.collection_exists(COLLECTION):
        await c.create_collection(COLLECTION, vectors_config=VectorParams(size=DIM, distance=Distance.COSINE))


async def ingest(docs: list[dict]) -> int:
    """docs: [{"source": "cis-aws-1.5", "title": "...", "text": "..."}]"""
    from qdrant_client.models import PointStruct
    c = client()
    await ensure_collection(c)
    pts = [PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_URL, d["source"] + d["title"])),
                       vector=_emb.embed(d["title"] + " " + d["text"]).tolist(), payload=d) for d in docs]
    await c.upsert(COLLECTION, pts)
    return len(pts)


async def search(query: str, k: int = 5, source_prefix: str | None = None) -> list[dict]:
    c = client()
    await ensure_collection(c)
    res = await c.query_points(COLLECTION, query=_emb.embed(query).tolist(), limit=k, with_payload=True)
    hits = [{"score": p.score, **p.payload} for p in res.points]
    return [h for h in hits if not source_prefix or h.get("source", "").startswith(source_prefix)]
