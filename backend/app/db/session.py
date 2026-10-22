from sqlalchemy import create_engine, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import Base, User

s = get_settings()
engine = create_async_engine(s.database_url, pool_size=10, max_overflow=20, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
sync_engine = create_engine(s.sync_database_url, pool_pre_ping=True)
SyncSession = sessionmaker(sync_engine, expire_on_commit=False)


async def get_session():
    async with SessionLocal() as session:
        yield session


HARDENING = [
    "SELECT create_hypertable('telemetry_metrics','time',if_not_exists=>TRUE,chunk_time_interval=>INTERVAL '1 day')",
    "ALTER TABLE telemetry_metrics SET (timescaledb.compress, timescaledb.compress_segmentby='resource_id,metric')",
    "SELECT add_compression_policy('telemetry_metrics', INTERVAL '7 days', if_not_exists=>TRUE)",
    "SELECT add_retention_policy('telemetry_metrics', INTERVAL '90 days', if_not_exists=>TRUE)",
    """CREATE OR REPLACE FUNCTION audit_immutable() RETURNS trigger AS $$
       BEGIN RAISE EXCEPTION 'audit_logs is append-only'; END; $$ LANGUAGE plpgsql""",
    "DROP TRIGGER IF EXISTS audit_no_mutation ON audit_logs",
    """CREATE TRIGGER audit_no_mutation BEFORE UPDATE OR DELETE ON audit_logs
       FOR EACH ROW EXECUTE FUNCTION audit_immutable()""",
]


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
        await conn.run_sync(Base.metadata.create_all)
        for stmt in HARDENING:
            await conn.execute(text(stmt))
    async with SessionLocal() as session:
        if not (await session.execute(select(User).where(User.email == s.admin_email))).scalar():
            session.add(User(email=s.admin_email, password_hash=hash_password(s.admin_password), role="admin"))
            await session.commit()


def init_db_sync() -> None:
    """Sync variant for scripts: tables plus hypertable and audit trigger."""
    from sqlalchemy import text
    with sync_engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
        Base.metadata.create_all(conn)
        for stmt in HARDENING:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass
