from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import chain_hash
from app.db.models import AuditLogs

GENESIS = "0" * 64


async def audit(session: AsyncSession, actor: str, action: str, target: str = "", detail: dict | None = None) -> None:
    last = (await session.execute(select(AuditLogs.hash).order_by(AuditLogs.id.desc()).limit(1))).scalar()
    prev = last or GENESIS
    payload = {"actor": actor, "action": action, "target": target, "detail": detail or {}}
    session.add(AuditLogs(prev_hash=prev, hash=chain_hash(prev, payload), **payload))
    await session.commit()
