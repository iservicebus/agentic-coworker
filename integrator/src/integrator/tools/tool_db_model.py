from sqlalchemy import Column, BigInteger, String, Text, JSON, DateTime, ForeignKey, Integer
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.schema import UniqueConstraint, ForeignKeyConstraint
from sqlalchemy.sql import func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

# Import Base from iam_db_model to ensure we use the same declarative base
from integrator.iam.iam_db_model import Base, Agent, Tenant

VECTOR_DIM=1536


class Application(Base):
    __tablename__ = "applications"

    app_name = Column(Text, primary_key=True, nullable=False)
    tenant_name = Column(Text, ForeignKey(Tenant.name, ondelete="CASCADE"), primary_key=True, nullable=False)
    app_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship(Tenant)



class AppKey(Base):
    __tablename__ = "app_keys"

    app_name = Column(Text, primary_key=True, nullable=False)
    agent_id = Column(Text, primary_key=True, nullable=False)
    tenant_name = Column(Text, primary_key=True, nullable=False)
    secrets = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        ForeignKeyConstraint(
            ['app_name', 'tenant_name'],
            ['applications.app_name', 'applications.tenant_name'],
            ondelete='CASCADE'
        ),
        ForeignKeyConstraint(
            ['agent_id', 'tenant_name'],
            ['agents.agent_id', 'agents.tenant_name'],
            ondelete='CASCADE'
        ),
    )

    def __repr__(self):
        return f"<AppKey(app_name='{self.app_name}', agent_id='{self.agent_id}', tenant_name='{self.tenant_name}')>"


class StagingService(Base):
    __tablename__ = "staging_services"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String(255), nullable=False)
    tenant = Column(String(255), ForeignKey(Tenant.name, ondelete="CASCADE"), nullable=False)
    service_data = Column(JSONB, nullable=False) # The entire service object

    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_by = Column(String(255), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant_rel = relationship(Tenant)

    def __repr__(self):
        return f"<StagingService(id={self.id}, name='{self.name}', tenant='{self.tenant}')>"


class McpTool(Base):
    __tablename__ = "mcp_tools"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    embedding: Mapped[list] = mapped_column(Vector(VECTOR_DIM))
    document: Mapped[dict] = mapped_column(JSON)
    canonical_data: Mapped[dict] = mapped_column(JSON)
    tenant: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text)
    tool_type: Mapped[str] = mapped_column(String(255), default='general')
    created_by: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[str] = mapped_column(String)
    updated_by: Mapped[str] = mapped_column(String(255))
    updated_at: Mapped[str] = mapped_column(String)

    __table_args__ = (UniqueConstraint('name', 'tenant', name='uq_mcp_tool_name_tenant'),)


class Skill(Base):
    __tablename__ = "skills"
    name = Column(String(255), primary_key=True, nullable=False)
    tenant_name = Column(Text, ForeignKey(Tenant.name, ondelete="CASCADE"), primary_key=True, nullable=False)
    label = Column(String, nullable=False)
    description = Column(Text)
    operational_entities = Column(JSONB, default=list)
    operational_procedures = Column(JSONB, default=list)
    operational_intent = Column(Text, default="")
    preconditions = Column(JSONB, default=list)
    postconditions = Column(JSONB, default=list)
    proficiency = Column(String(50), default="")
    emb = Column(Vector(VECTOR_DIM))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    tenant = relationship(Tenant)


class CapabilitySkill(Base):
    __tablename__ = "capability_skill"
    # Note: the actual FK constraints to capabilities(name, tenant_name) and skills(name, tenant_name)
    # are managed at the database level by SQL migrations/scripts. We keep these as plain String
    # columns here to avoid cross-metadata dependency issues between domain and
    # tool models while still enforcing referential integrity in the DB.
    capability_name = Column(String(255), nullable=False, primary_key=True)
    skill_name = Column(String(255), nullable=False, primary_key=True)
    tenant_name = Column(Text, ForeignKey(Tenant.name, ondelete="CASCADE"), primary_key=True, nullable=False)


class ToolSkill(Base):
    __tablename__ = "tool_skills"
    tool_id = Column(UUID(as_uuid=True), ForeignKey('mcp_tools.id'), nullable=False, primary_key=True)
    skill_name = Column(String(255), nullable=False, primary_key=True)
    tenant_name = Column(Text, ForeignKey(Tenant.name, ondelete="CASCADE"), primary_key=True, nullable=False)
    step_index = Column(Integer, nullable=True)
    step_intent = Column(Text, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ['skill_name', 'tenant_name'],
            ['skills.name', 'skills.tenant_name'],
            ondelete='CASCADE'
        ),
    )

    # Add relationship to McpTool
    tool = relationship("McpTool")


class CapabilityTool(Base):
    __tablename__ = "capability_tool"
    # Note: the actual FK constraint to capabilities(name, tenant_name) is managed at the
    # database level by SQL migrations/scripts. We keep this as a plain String
    # column here to avoid cross-metadata dependency issues between domain and
    # tool models while still enforcing referential integrity in the DB.
    capability_name = Column(String(255), nullable=False, primary_key=True)
    tool_id = Column(UUID(as_uuid=True), ForeignKey('mcp_tools.id'), nullable=False, primary_key=True)
    tenant_name = Column(Text, ForeignKey(Tenant.name, ondelete="CASCADE"), primary_key=True, nullable=False)

    # Relationship back to tool (capability relationship handled in domain models)
    tool = relationship("McpTool")


class ToolRel(Base):
    """Relationship between MCP tools (tool flows).

    Each row represents a directed edge from ``source_tool_id`` to
    ``target_tool_id`` with an associated composite intent and optional
    field-mapping metadata.
    """
    __tablename__ = "tool_rels"

    source_tool_id = Column(UUID(as_uuid=True), ForeignKey("mcp_tools.id"), primary_key=True, nullable=False)
    target_tool_id = Column(UUID(as_uuid=True), ForeignKey("mcp_tools.id"), primary_key=True, nullable=False)
    composite_intent = Column(Text, nullable=True)
    field_mapping = Column(JSONB, nullable=True)

    # Relationships back to tools
    source_tool = relationship("McpTool", foreign_keys=[source_tool_id])
    target_tool = relationship("McpTool", foreign_keys=[target_tool_id])


class ApplicationMcpTool(Base):
    """Relationship between Application and MCP Tool.

    Each row represents an association between an application and an MCP tool
    within a specific tenant, allowing applications to be linked to the tools
    they use or provide.
    """
    __tablename__ = "application_mcp_tool"

    app_name = Column(Text, primary_key=True, nullable=False)
    tenant_name = Column(Text, primary_key=True, nullable=False)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("mcp_tools.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        ForeignKeyConstraint(
            ['app_name', 'tenant_name'],
            ['applications.app_name', 'applications.tenant_name'],
            ondelete='CASCADE'
        ),
    )

    # Relationships
    application = relationship("Application")
    tool = relationship("McpTool")

    def __repr__(self):
        return f"<ApplicationMcpTool(app_name='{self.app_name}', tenant_name='{self.tenant_name}', tool_id={self.tool_id})>"
