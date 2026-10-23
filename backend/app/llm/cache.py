"""Semantic response cache on Redis. Dependency-free hashing embedder; swap in real embeddings for prod."""
import hashlib
import json
import re

import numpy as np

DIM = 512


def _stem(w: str) -> str:
    for suf in ("ing", "ly", "ed", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


class HashingEmbedder:
    """Signed feature hashing of stemmed uni/bi-grams plus char tri-grams -> L2-normalised vector.
    Deterministic and download-free; swap in a neural embedder for production recall."""

    def _add(self, v, g: str, weight: float) -> None:
        h = int.from_bytes(hashlib.blake2b(g.encode(), digest_size=8).digest(), "big")
        v[h % DIM] += weight if (h >> 63) & 1 else -weight

    def embed(self, text: str) -> np.ndarray:
        words = [_stem(w) for w in re.findall(r"[a-z0-9_]+", text.lower())]
        v = np.zeros(DIM, dtype=np.float32)
        for w in words:
            self._add(v, w, 1.0)
            padded = f"^{w}$"
            for i in range(len(padded) - 2):
                self._add(v, "c:" + padded[i:i + 3], 0.35)
        for a, b in zip(words, words[1:]):
            self._add(v, f"{a}_{b}", 0.7)
        n = np.linalg.norm(v)
        return v / n if n else v


class SemanticCache:
    def __init__(self, redis, embedder=None, threshold=0.92, ttl=3600, max_entries=500):
        self.r, self.emb = redis, embedder or HashingEmbedder()
        self.threshold, self.ttl, self.max = threshold, ttl, max_entries

    def _idx(self, ns: str) -> str:
        return f"sc:{ns}:index"

    async def get(self, ns: str, text: str):
        q = self.emb.embed(text)
        keys = await self.r.lrange(self._idx(ns), 0, self.max - 1)
        if not keys:
            return None
        blobs = await self.r.mget(keys)
        best, best_sim = None, 0.0
        for blob in blobs:
            if not blob:
                continue
            e = json.loads(blob)
            sim = float(np.dot(q, np.asarray(e["v"], dtype=np.float32)))
            if sim > best_sim:
                best, best_sim = e, sim
        return best["resp"] if best and best_sim >= self.threshold else None

    async def put(self, ns: str, text: str, resp: dict) -> None:
        key = f"sc:{ns}:{hashlib.sha256(text.encode()).hexdigest()[:24]}"
        entry = {"v": [round(float(x), 5) for x in self.emb.embed(text)], "resp": resp}
        await self.r.set(key, json.dumps(entry), ex=self.ttl)
        await self.r.lpush(self._idx(ns), key)
        await self.r.ltrim(self._idx(ns), 0, self.max - 1)
