"""Terraform dry-run + blast-radius analysis."""
import asyncio
import json
import tempfile
from pathlib import Path


def blast_radius_from_plan(plan_json: dict) -> dict:
    counts = {"create": 0, "update": 0, "delete": 0, "replace": 0}
    for rc in plan_json.get("resource_changes", []):
        acts = rc["change"]["actions"]
        if acts == ["no-op"] or acts == ["read"]:
            continue
        if "delete" in acts and "create" in acts:
            counts["replace"] += 1
        elif "delete" in acts:
            counts["delete"] += 1
        elif "create" in acts:
            counts["create"] += 1
        elif "update" in acts:
            counts["update"] += 1
    # destructive changes weigh more than additive ones
    score = counts["create"] + counts["update"] + 3 * counts["delete"] + 3 * counts["replace"]
    return {**counts, "score": score}


def estimate_from_hcl(hcl: str) -> dict:
    n = hcl.count('resource "')
    return {"create": n, "update": 0, "delete": 0, "replace": 0, "score": n, "estimated": True}


async def _run(*cmd, cwd):
    p = await asyncio.create_subprocess_exec(*cmd, cwd=cwd, stdout=asyncio.subprocess.PIPE,
                                             stderr=asyncio.subprocess.STDOUT)
    out, _ = await p.communicate()
    return p.returncode, out.decode()


async def dry_run(hcl: str) -> tuple[dict, str]:
    """Returns (blast_radius, log). Never applies. Falls back to static estimate if terraform is absent."""
    with tempfile.TemporaryDirectory() as d:
        Path(d, "main.tf").write_text(hcl)
        try:
            rc, log = await _run("terraform", "init", "-backend=false", "-input=false", "-no-color", cwd=d)
            if rc:
                return estimate_from_hcl(hcl), log
            rc, log2 = await _run("terraform", "plan", "-input=false", "-lock=false", "-out=tfplan", "-no-color", cwd=d)
            if rc:
                return estimate_from_hcl(hcl), log + log2
            _, js = await _run("terraform", "show", "-json", "tfplan", cwd=d)
            return blast_radius_from_plan(json.loads(js)), log + log2
        except FileNotFoundError:
            return estimate_from_hcl(hcl), "terraform binary not found; static estimate only"
