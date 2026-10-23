"""Pure hash-chain helpers for the append-only audit log (no framework imports)."""
import hashlib
import json

GENESIS = "0" * 64


def chain_hash(prev_hash: str, payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256((prev_hash + body).encode()).hexdigest()


def verify_chain(rows: list[dict]) -> dict:
    """rows: ordered dicts with prev_hash, hash, actor, action, target, detail."""
    prev = GENESIS
    for i, r in enumerate(rows):
        payload = {"actor": r["actor"], "action": r["action"], "target": r["target"], "detail": r["detail"]}
        if r["prev_hash"] != prev or r["hash"] != chain_hash(prev, payload):
            return {"valid": False, "checked": i, "broken_at": i}
        prev = r["hash"]
    return {"valid": True, "checked": len(rows), "broken_at": None}
