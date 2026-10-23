"""Minimal Model Context Protocol server (JSON-RPC 2.0 over HTTP). Read + propose only: no approve/apply."""
import json

from fastapi import APIRouter, Depends, Request

from app.agents.tools import REGISTRY
from app.core.security import Principal, require_role

router = APIRouter()
PROTOCOL = "2025-06-18"
RESOURCES = [
    {"uri": "cloudpulse://resources", "name": "Managed resources", "mimeType": "application/json"},
    {"uri": "cloudpulse://alerts", "name": "Open security alerts", "mimeType": "application/json"},
]


def ok(id_, result):
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def err(id_, code, msg):
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": msg}}


@router.post("/mcp")
async def mcp(request: Request, p: Principal = Depends(require_role("viewer"))):
    body = await request.json()
    id_, method, params = body.get("id"), body.get("method"), body.get("params") or {}
    if method == "initialize":
        return ok(id_, {"protocolVersion": PROTOCOL, "serverInfo": {"name": "cloudpulse-ai", "version": "1.0.0"},
                        "capabilities": {"tools": {}, "resources": {}}})
    if method == "notifications/initialized":
        return {}
    if method == "ping":
        return ok(id_, {})
    if method == "tools/list":
        return ok(id_, {"tools": [{"name": t.name, "description": t.description, "inputSchema": t.schema}
                                  for t in REGISTRY.values() if t.mcp]})
    if method == "tools/call":
        t = REGISTRY.get(params.get("name"))
        if not t or not t.mcp:
            return err(id_, -32602, "Unknown tool")
        try:
            out = await t.fn(**(params.get("arguments") or {}))
            return ok(id_, {"content": [{"type": "text", "text": json.dumps(out, default=str)}], "isError": False})
        except Exception as e:
            return ok(id_, {"content": [{"type": "text", "text": str(e)}], "isError": True})
    if method == "resources/list":
        return ok(id_, {"resources": RESOURCES})
    if method == "resources/read":
        uri = params.get("uri", "")
        fn = {"cloudpulse://resources": "list_resources", "cloudpulse://alerts": "open_alerts"}.get(uri)
        if not fn:
            return err(id_, -32602, "Unknown resource")
        data = await REGISTRY[fn].fn()
        return ok(id_, {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(data, default=str)}]})
    return err(id_, -32601, f"Method not found: {method}")
