from sqlalchemy import Column, String, Text, JSON, ForeignKey, UniqueConstraint, ForeignKeyConstraint, PrimaryKeyConstraint
from pgvector.sqlalchemy import Vector
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import text

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid


Base = declarative_base()

VECTOR_DIM=1536



class Domain(Base):
    __tablename__ = "domains"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String, nullable=False)
    tenant_name = Column(Text, ForeignKey("tenants.name", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String, nullable=False)
    description = Column(Text, default="")
    scope = Column(Text, default="")
    domain_entities = Column(JSON, default=list)
    domain_purposes = Column(Text, default="")
    value_metrics = Column(JSON, default=list)
    emb = Column(Vector(VECTOR_DIM))
    created_at = Column(Text)
    
    __table_args__ = (
        UniqueConstraint('name', 'tenant_name', name='uq_domain_name_tenant'),
    )

class Capability(Base):
    __tablename__ = "capabilities"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String, nullable=False)
    tenant_name = Column(Text, ForeignKey("tenants.name", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String, nullable=False)
    description = Column(Text, default="")
    business_context = Column(JSON, default=list)
    business_processes = Column(JSON, default=list)
    outcome = Column(Text, default="")
    business_intent = Column(JSON, default=list)
    emb = Column(Vector(VECTOR_DIM))
    created_at = Column(Text)
    
    __table_args__ = (
        UniqueConstraint('name', 'tenant_name', name='uq_capability_name_tenant'),
    )


class DomainCapability(Base):
    __tablename__ = "domain_capability"
    domain_name = Column(String, nullable=False)
    capability_name = Column(String, nullable=False)
    tenant_name = Column(Text, ForeignKey("tenants.name", ondelete="CASCADE"), nullable=False)
    
    __table_args__ = (
        PrimaryKeyConstraint('domain_name', 'capability_name', 'tenant_name'),
        ForeignKeyConstraint(['domain_name', 'tenant_name'], ['domains.name', 'domains.tenant_name']),
        ForeignKeyConstraint(['capability_name', 'tenant_name'], ['capabilities.name', 'capabilities.tenant_name']),
    )


class CanonicalSkill(Base):
    __tablename__ = "canonical_skills"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String, nullable=False)
    tenant_name = Column(Text, ForeignKey("tenants.name", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String, nullable=False)
    skill_kind = Column(String, default="")
    intent = Column(String, default="")
    entity = Column(JSON, default=list)
    criticality = Column(String, default="")
    description = Column(Text, default="")
    created_at = Column(Text)
    
    __table_args__ = (
        UniqueConstraint('name', 'tenant_name', name='uq_canonical_skill_name_tenant'),
    )


class CapabilityCanonicalSkill(Base):
    __tablename__ = "capability_canonical_skill"
    capability_name = Column(String, nullable=False)
    canonical_skill_name = Column(String, nullable=False)
    tenant_name = Column(Text, ForeignKey("tenants.name", ondelete="CASCADE"), nullable=False)
    
    __table_args__ = (
        PrimaryKeyConstraint('capability_name', 'canonical_skill_name', 'tenant_name'),
        ForeignKeyConstraint(['capability_name', 'tenant_name'], ['capabilities.name', 'capabilities.tenant_name']),
        ForeignKeyConstraint(['canonical_skill_name', 'tenant_name'], ['canonical_skills.name', 'canonical_skills.tenant_name']),
    )


class Workflow(Base):
    __tablename__ = "workflows"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String, nullable=False)
    tenant_name = Column(Text, ForeignKey("tenants.name", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String, nullable=False)
    description = Column(Text, default="")
    value_metrics = Column(JSON, default=list)
    created_at = Column(Text)
    
    __table_args__ = (
        UniqueConstraint('name', 'tenant_name', name='uq_workflow_name_tenant'),
    )


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String, nullable=False)
    tenant_name = Column(Text, ForeignKey("tenants.name", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String, nullable=False)
    step_order = Column(String, nullable=False)
    intent = Column(Text, default="")
    description = Column(Text, default="")
    workflow_name = Column(String, nullable=False)
    created_at = Column(Text)
    
    __table_args__ = (
        UniqueConstraint('name', 'tenant_name', name='uq_workflow_step_name_tenant'),
        ForeignKeyConstraint(['workflow_name', 'tenant_name'], ['workflows.name', 'workflows.tenant_name']),
    )


class WorkflowStepDomain(Base):
    __tablename__ = "workflow_step_domain"
    workflow_step_name = Column(String, nullable=False)
    domain_name = Column(String, nullable=False)
    tenant_name = Column(Text, ForeignKey("tenants.name", ondelete="CASCADE"), nullable=False)
    
    __table_args__ = (
        PrimaryKeyConstraint('workflow_step_name', 'domain_name', 'tenant_name'),
        ForeignKeyConstraint(['workflow_step_name', 'tenant_name'], ['workflow_steps.name', 'workflow_steps.tenant_name']),
        ForeignKeyConstraint(['domain_name', 'tenant_name'], ['domains.name', 'domains.tenant_name']),
    )


class WorkflowStepCapability(Base):
    __tablename__ = "workflow_step_capability"
    workflow_step_name = Column(String, nullable=False)
    capability_name = Column(String, nullable=False)
    tenant_name = Column(Text, ForeignKey("tenants.name", ondelete="CASCADE"), nullable=False)
    
    __table_args__ = (
        PrimaryKeyConstraint('workflow_step_name', 'capability_name', 'tenant_name'),
        ForeignKeyConstraint(['workflow_step_name', 'tenant_name'], ['workflow_steps.name', 'workflow_steps.tenant_name']),
        ForeignKeyConstraint(['capability_name', 'tenant_name'], ['capabilities.name', 'capabilities.tenant_name']),
    )
