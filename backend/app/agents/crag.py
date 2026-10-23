"""Corrective RAG: retrieve -> grade -> (rewrite query & retry) -> return docs with a confidence verdict."""
import re

from app.agents import rag

_gw = None


def set_gateway(gw) -> None:
    global _gw
    _gw = gw


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", s.lower()))


def grade(query: str, hits: list[dict]) -> list[dict]:
    q = _tokens(query)
    out = []
    for h in hits:
        overlap = len(q & _tokens(h.get("title", "") + " " + h.get("text", ""))) / max(1, len(q))
        out.append({**h, "relevance": round(0.6 * float(h.get("score", 0)) + 0.4 * overlap, 3)})
    return sorted(out, key=lambda d: d["relevance"], reverse=True)


async def crag_search(query: str, k: int = 4, min_relevance: float = 0.2, search_fn=None, gw=None) -> dict:
    search_fn, gw = search_fn or rag.search, gw or _gw
    good = [d for d in grade(query, await search_fn(query, k * 2)) if d["relevance"] >= min_relevance]
    if len(good) >= 2:
        return {"verdict": "correct", "query": query, "docs": good[:k]}
    if gw:
        try:
            rewritten = (await gw.complete([{"role": "user", "content":
                "Rewrite this as a precise cloud-security/FinOps search query (max 12 words), no punctuation:\n" + query}],
                task="chat")).text.strip().split("\n")[0]
            seen = {d["title"] for d in good}
            more = [d for d in grade(rewritten, await search_fn(rewritten, k * 2))
                    if d["relevance"] >= min_relevance and d["title"] not in seen]
            good = sorted(good + more, key=lambda d: d["relevance"], reverse=True)
            if good:
                return {"verdict": "corrected", "query": rewritten, "docs": good[:k]}
        except Exception:
            pass
    return {"verdict": "insufficient", "query": query, "docs": good[:k],
            "note": "Low retrieval confidence; answer from general knowledge and say so."}
