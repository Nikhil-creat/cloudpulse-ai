"""SQLAlchemy 2.0 ORM models (PostgreSQL + TimescaleDB)."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.core import security


class Base(DeclarativeBase):
    pass


class EncryptedText(TypeDecorator):
    """Transparent Fernet column encryption (AES + HMAC)."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else security.encrypt(value)

    def process_result_value(self, value, dialect):
        return None if value is None else security.decrypt(value)


def _pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Provider(str, enum.Enum):
    aws = "aws"
    gcp = "gcp"
    k8s = "k8s"


class PlanStatus(str, enum.Enum):
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"
    applied = "applied"
    failed = "failed"


class Severity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = _pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="viewer")
    totp_secret: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CloudCredentials(Base):
    __tablename__ = "cloud_credentials"
    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(String(120), unique=True)
    provider: Mapped[Provider] = mapped_column(Enum(Provider))
    secret: Mapped[str] = mapped_column(EncryptedText)  # JSON blob, encrypted at rest
    region: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resources: Mapped[list["ManagedResources"]] = relationship(back_populates="credential")


class ManagedResources(Base):
    __tablename__ = "managed_resources"
    id: Mapped[uuid.UUID] = _pk()
    credential_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cloud_credentials.id", ondelete="CASCADE"))
    provider: Mapped[Provider] = mapped_column(Enum(Provider))
    external_id: Mapped[str] = mapped_column(String(255), index=True)
    kind: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    region: Mapped[str | None] = mapped_column(String(64))
    tags: Mapped[dict] = mapped_column(JSONB, default=dict)
    monthly_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    credential: Mapped[CloudCredentials] = relationship(back_populates="resources")
    __table_args__ = (Index("uq_resource_ext", "credential_id", "external_id", unique=True),)


class TelemetryMetrics(Base):
    """Hypertable on `time` (created in db.session.init_db)."""
    __tablename__ = "telemetry_metrics"
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    metric: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(16))
    labels: Mapped[dict] = mapped_column(JSONB, default=dict)


class AIExecutionPlans(Base):
    __tablename__ = "ai_execution_plans"
    id: Mapped[uuid.UUID] = _pk()
    prompt: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(255))
    status: Mapped[PlanStatus] = mapped_column(Enum(PlanStatus), default=PlanStatus.pending_approval, index=True)
    plan: Mapped[dict] = mapped_column(JSONB)
    terraform_hcl: Mapped[str | None] = mapped_column(Text)
    dry_run_output: Mapped[str | None] = mapped_column(Text)
    blast_radius: Mapped[int] = mapped_column(Integer, default=0)
    approved_by: Mapped[str | None] = mapped_column(String(255))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trace_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SecurityAlerts(Base):
    __tablename__ = "security_alerts"
    id: Mapped[uuid.UUID] = _pk()
    resource_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("managed_resources.id", ondelete="SET NULL"))
    severity: Mapped[Severity] = mapped_column(Enum(Severity), index=True)
    source: Mapped[str] = mapped_column(String(32))  # cnn | cis | agent
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(String(16), default="open")
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLogs(Base):
    """Append-only: a DB trigger rejects UPDATE/DELETE; rows form a SHA-256 hash chain."""
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actor: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(64))
    target: Mapped[str] = mapped_column(String(255), default="")
    detail: Mapped[dict] = mapped_column(JSONB, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))


class LLMUsageTracker(Base):
    __tablename__ = "llm_usage"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    provider: Mapped[str] = mapped_column(String(16))
    model: Mapped[str] = mapped_column(String(64))
    task: Mapped[str] = mapped_column(String(32))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    failover: Mapped[bool] = mapped_column(Boolean, default=False)
    user: Mapped[str | None] = mapped_column(String(255))
