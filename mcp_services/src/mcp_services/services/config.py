"""Configuration management for MCP provider."""

import json
import os
from typing import Dict, Any, Optional, Callable, TypeVar
from dataclasses import dataclass

from mcp_services.utils.env import load_env
from mcp_services.utils.logger import get_logger

# Load environment variables at module import
load_env()

logger = get_logger(__name__)

T = TypeVar('T')

@dataclass
class Config:
    """Configuration class with validation and type safety."""
    
    # Server configuration
    port: int = 6666
    transport: str = "sse"
    
    # Authorization configuration
    authorization_enabled: bool = True
    authorization_host: str = "http://localhost:3000"
    iam_url: str = "http://localhost:8888"
    realm: str = "default"
    
    # Service URLs
    integrator_url: str = "http://localhost:6060"
    proxy_url: str = "http://localhost"
    
    # Graphiti configuration
    graphiti_uri: str = "bolt://localhost:7687"
    graphiti_user: str = "neo4j"
    graphiti_password: str = "password"
    
    # Azure configuration
    azure_endpoint: Optional[str] = None
    azure_api_key: Optional[str] = None
    azure_api_version: Optional[str] = None
    azure_llm_deployment: Optional[str] = None
    azure_embedding_deployment: Optional[str] = None
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()
    
    def _validate(self):
        """Validate configuration values."""
        if self.transport not in ["stdio", "sse"]:
            logger.warning(f"Invalid transport '{self.transport}'. Defaulting to 'sse'.")
            self.transport = "sse"
        
        if self.port < 1 or self.port > 65535:
            logger.warning(f"Invalid port {self.port}. Using default 6666.")
            self.port = 6666
    
    @property
    def resource_url(self) -> str:
        """Get the resource URL for SSE endpoint."""
        return f"http://127.0.0.1:{self.port}/sse"
    
    @property
    def oidc_issuer(self) -> str:
        """Get the OIDC issuer URL."""
        return os.getenv("OIDC_ISSUER", f"{self.iam_url}/realms/{self.realm}")
    
    def has_azure_config(self) -> bool:
        """Check if all required Azure configuration is present."""
        return all([
            self.azure_endpoint,
            self.azure_api_key,
            self.azure_api_version,
            self.azure_llm_deployment,
            self.azure_embedding_deployment
        ])


class ConfigLoader:
    """Handles loading configuration from environment variables."""
    
    def load(self) -> Config:
        """Load configuration from environment variables."""
        # Environment variables are already loaded via load_env() at module import
        
        # Create config with values from environment
        config_data = {}
        
        # Define configuration mappings
        config_mappings = {
            'port': (6666, int),
            'transport': ("sse", str),
            'authorization_enabled': (True, self._bool_converter),
            'authorization_host': ("http://localhost:3000", str),
            'integrator_url': ("http://localhost:6060", str),
            'proxy_url': ("http://localhost", str),
            'graphiti_uri': ("bolt://localhost:7687", str),
            'graphiti_user': ("neo4j", str),
            'graphiti_password': ("password", str),
            'azure_endpoint': (None, str),
            'azure_api_key': (None, str),
            'azure_api_version': (None, str),
            'azure_llm_deployment': (None, str),
            'azure_embedding_deployment': (None, str),
            'iam_url': ("http://localhost:8888", str),
            'realm': ("default", str),
        }
        
        for key, (default, converter) in config_mappings.items():
            config_data[key] = self._get_config_value(
                key, default, converter
            )
        
        return Config(**config_data)
    
    def _get_config_value(
        self, 
        key: str, 
        default: T, 
        type_converter: Callable[[Any], T]
    ) -> T:
        """Get configuration value with precedence: env > default."""
        value = os.getenv(key.upper(), default)
        
        if value is None:
            return default
        
        try:
            return type_converter(value)
        except (ValueError, TypeError):
            logger.warning(
                f"Invalid type for {key}. Using default value {default}."
            )
            return default
    
    @staticmethod
    def _bool_converter(value: Any) -> bool:
        """Convert various representations to boolean."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)


# Global config instance
_config: Optional[Config] = None

def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        loader = ConfigLoader()
        _config = loader.load()
    return _config

def reload_config() -> Config:
    """Reload the global configuration."""
    global _config
    loader = ConfigLoader()
    _config = loader.load()
    return _config
