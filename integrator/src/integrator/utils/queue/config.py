"""
Configuration management for the NATS JetStream Queue Manager.
Centralizes all configuration with validation and type safety.
"""

import os
from enum import Enum
from typing import Optional
from pydantic import field_validator, Field
from pydantic_settings import BaseSettings

# Load environment variables
from integrator.utils.env import load_env
load_env()


class ConsumerMode(Enum):
    """Consumer mode enumeration for queue operations."""
    PULL = "PULL"
    PUSH = "PUSH"

class NATSQueueConfig(BaseSettings):
    """NATS JetStream Queue Manager configuration settings."""
    

    # Connection settings
    url: str = Field(default="nats://localhost:4222", description="NATS server URL")
    connection_timeout: float = Field(default=10.0, description="Connection timeout in seconds")
    
    # Stream settings
    default_stream_name: str = Field(default="TOOL_PROCESSING", description="Default stream name")
    max_msgs: int = Field(default=100000, description="Maximum messages per stream")
    max_age_days: int = Field(default=7, description="Maximum message age in days")

    # subject settings
    default_subject: str = Field(default="tool.ingest", description="Default subject name")


    # Consumer settings
    
    max_retries: int = Field(default=3, description="Maximum retry attempts for failed messages")
    ack_wait: float = Field(default=600.0, description="Acknowledgment wait time in seconds (10 minutes for long-running operations)")
    max_deliver: int = Field(default=3, description="Maximum delivery attempts before moving to DLQ")
    max_ack_pending: int = Field(default=1, description="Maximum acknowledge pending count - should match thread pool size")

    consumer_mode: ConsumerMode = Field(default=ConsumerMode.PULL, description=" Define how to enqueue the messages in nats stream, by either pull or push call back")
    #consumer_mode: ConsumerMode = Field(default=ConsumerMode.PUSH, description=" Define how to enqueue the messages in nats stream, by either pull or push call back")

    pull_batch_size: int = Field(default=1, description="pull batch size")
    pull_timeout: float = Field(default=50.0, description="tool ingestion pull time")
    pull_polling_interval: float = Field(default=1.0, description="tool pull polling interval")


    # Retry settings
    retry_batch_size: int = Field(default=64, description="Batch size for retry operations")
    retry_timeout: float = Field(default=1.0, description="Timeout for retry fetch operations")
    retry_delete_original: bool = Field(default=True, description="Delete original failed messages after retry")
    retry_max_delay: float = Field(default=60.0, description="Maximum retry delay in seconds")
    
    # Background task settings
    subscription_keepalive_interval: float = Field(default=1.0, description="Background subscription keepalive interval")
    
    # Subject naming patterns
    work_subject_suffix: str = Field(default="work", description="Suffix for work subjects")
    dlq_stream_suffix: str = Field(default="DLQ", description="Suffix for DLQ stream names")
    dlq_subject_suffix: str = Field(default="dlq", description="Suffix for DLQ subjects")
    adv_stream_suffix: str = Field(default="ADV", description="Suffix for advisory stream names")
    
    # Consumer naming patterns
    worker_consumer_suffix: str = Field(default="worker", description="Suffix for worker consumer names")
    dlq_consumer_suffix: str = Field(default="dlq_consumer", description="Suffix for DLQ consumer names")
    adv_consumer_suffix: str = Field(default="adv_consumer", description="Suffix for advisory consumer names")
    
    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Logging format"
    )
    
    @field_validator('url')
    def validate_nats_url(cls, v):
        """Validate NATS URL format."""
        if not v.startswith(('nats://', 'tls://', 'ws://', 'wss://')):
            raise ValueError('NATS URL must start with nats://, tls://, ws://, or wss://')
        return v
    
    @field_validator('max_retries', 'max_deliver')
    def validate_positive_int(cls, v):
        """Validate positive integers."""
        if v < 0:
            raise ValueError('Value must be non-negative')
        return v
    
    @field_validator('ack_wait', 'connection_timeout', 'retry_timeout')
    def validate_positive_float(cls, v):
        """Validate positive floats."""
        if v <= 0:
            raise ValueError('Value must be positive')
        return v
    
    @field_validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()
    
    def get_work_subject(self, stream_name: str) -> str:
        """Get work subject name for a stream."""
        return f"{stream_name}.{self.work_subject_suffix}"
    
    def get_dlq_stream_name(self, stream_name: str) -> str:
        """Get DLQ stream name for a stream."""
        return f"{stream_name}_{self.dlq_stream_suffix}"
    
    def get_dlq_subject(self, stream_name: str) -> str:
        """Get DLQ subject name for a stream."""
        return f"{stream_name}.{self.dlq_subject_suffix}"
    
    def get_adv_stream_name(self, stream_name: str) -> str:
        """Get advisory stream name for a stream."""
        return f"{stream_name}_{self.adv_stream_suffix}"
    
    def get_worker_consumer_name(self, stream_name: str) -> str:
        """Get worker consumer name for a stream."""
        return f"{stream_name}_{self.worker_consumer_suffix}"
    
    def get_dlq_consumer_name(self, stream_name: str) -> str:
        """Get DLQ consumer name for a stream."""
        return f"{stream_name}_{self.dlq_consumer_suffix}"
    
    def get_adv_consumer_name(self, stream_name: str) -> str:
        """Get advisory consumer name for a stream."""
        return f"{stream_name}_{self.adv_consumer_suffix}"
    
    def get_max_age_seconds(self) -> float:
        """Get maximum age in seconds."""
        return self.max_age_days * 24 * 3600
    
    class Config:
        env_prefix = "NATS_QUEUE_"
        case_sensitive = False


# Global configuration instance
nats_queue_config = NATSQueueConfig()
