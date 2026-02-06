"""
Migration helper to transition from local utils to shared utils.
This file demonstrates how to import from the shared library while maintaining backward compatibility.
"""

# Import from shared library
try:
    from aintegrator_shared_utils.logging import get_logger, setup_logging
    from aintegrator_shared_utils.env import load_env
    from aintegrator_shared_utils.oauth import validate_token_sync as validate_token, validate_auth_sync as validate_auth
    from aintegrator_shared_utils.host import generate_host_id
    from aintegrator_shared_utils.json_processing import preprocess_keys, transform_json_with_schema
    from aintegrator_shared_utils.crypto import encrypt, decrypt, CryptoUtils
    
    # Flag to indicate shared utils are available
    SHARED_UTILS_AVAILABLE = True
    
except ImportError:
    # Fallback to local utils if shared utils are not available
    from .logger import get_logger, setup_logging
    
    # These functions don't exist in support_services yet, so we'll create stubs
    def load_env():
        """Stub for load_env - implement if needed"""
        pass
    
    def validate_token(request):
        """Stub for validate_token - implement if needed"""
        raise NotImplementedError("OAuth validation not implemented in local utils")
    
    def validate_auth(auth, client_id):
        """Stub for validate_auth - implement if needed"""
        raise NotImplementedError("OAuth validation not implemented in local utils")
    
    def generate_host_id(url):
        """Stub for generate_host_id - implement if needed"""
        raise NotImplementedError("Host ID generation not implemented in local utils")
    
    def preprocess_keys(data):
        """Stub for preprocess_keys - implement if needed"""
        return data
    
    def transform_json_with_schema(input_data, schema, similarity_cutoff=0.8):
        """Stub for transform_json_with_schema - implement if needed"""
        return input_data
    
    def encrypt(text):
        """Stub for encrypt - implement if needed"""
        raise NotImplementedError("Encryption not implemented in local utils")
    
    def decrypt(encrypted_hex, iv_hex):
        """Stub for decrypt - implement if needed"""
        raise NotImplementedError("Decryption not implemented in local utils")
    
    class CryptoUtils:
        """Stub for CryptoUtils - implement if needed"""
        def __init__(self, secret_key_hex=None):
            raise NotImplementedError("CryptoUtils not implemented in local utils")
    
    SHARED_UTILS_AVAILABLE = False
    print("Warning: Using local utils with stubs. Consider installing aintegrator-shared-utils for full functionality.")

# Re-export for backward compatibility
__all__ = [
    'get_logger',
    'setup_logging', 
    'load_env',
    'validate_token',
    'validate_auth',
    'generate_host_id',
    'preprocess_keys',
    'transform_json_with_schema',
    'encrypt',
    'decrypt',
    'CryptoUtils',
    'SHARED_UTILS_AVAILABLE'
]
