from sqlalchemy import Column, BigInteger, String, Text, JSON, DateTime, ForeignKey, Integer, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.sql import func, text
from sqlalchemy.orm import relationship

Base = declarative_base()


class McpSession(Base):
    __tablename__ = "mcp_session"

    id = Column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_name = Column(Text, nullable=False)
    agent_id = Column(Text, nullable=False)
    current_context_id = Column(UUID(as_uuid=False), ForeignKey("session_context_history.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationship to latest context row (optional convenience)
    current_context = relationship(
        "SessionContextHistory",
        foreign_keys=[current_context_id],
        lazy="joined",
        post_update=True,
    )

    history = relationship(
        "SessionContextHistory",
        back_populates="session",
        cascade="all, delete-orphan",
        foreign_keys="SessionContextHistory.session_id",
    )

    __table_args__ = (
        UniqueConstraint("agent_id", "tenant_name", name="uq_agent_tenant"),
        Index("idx_mcp_session_tenant", "tenant_name"),
        Index("idx_mcp_session_agent_tenant", "agent_id", "tenant_name"),
    )


class SessionContextHistory(Base):
    __tablename__ = "session_context_history"

    id = Column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    session_id = Column(UUID(as_uuid=False), ForeignKey("mcp_session.id", ondelete="CASCADE"), nullable=False)
    tenant_name = Column(Text, nullable=False)
    seq = Column(BigInteger, nullable=False)  # 1,2,3... per session
    context = Column(JSONB, nullable=True)
    context_hash = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("McpSession", back_populates="history", foreign_keys=[session_id])

    __table_args__ = (
        UniqueConstraint("session_id", "seq", name="uq_session_seq"),
        Index("idx_ctx_hist_session_seq_desc", "session_id", "seq"),
        Index("idx_ctx_hist_session_hash", "session_id", "context_hash"),
        Index("idx_ctx_hist_tenant", "tenant_name"),
    )
