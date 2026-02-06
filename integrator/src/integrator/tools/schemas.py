"""
Pydantic schemas for input validation and data serialization.
Provides type safety and validation for all API inputs and outputs.
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import uuid
from uuid import UUID

class ToolRequest(BaseModel):
    tool_dict: Dict[str, Any] = Field(..., description="Tool data as JSON string or dictionary")
    tenant_name: str = Field(..., min_length=1, max_length=255, description="Tenant Name")
    username: str = Field(..., min_length=1, max_length=255, description="User Name")
    staging_id: Optional[UUID] = Field(None, description="tool staging ID")

    @field_validator('tenant_name')
    def validate_ids(cls, v):
        if not v.strip():
            raise ValueError("ID fields cannot be empty or whitespace only")
        return v.strip()


class ToolResponse(BaseModel):
    """Schema for ingestion response data."""
    tool_id: uuid.UUID
    success: bool = True
    message: Optional[str] = ""
