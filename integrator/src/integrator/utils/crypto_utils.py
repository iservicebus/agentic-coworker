import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
import binascii # For robust hex decoding

# SECRET_KEY should be a 64-character hex string (representing 32 bytes for AES-256)
# Ensure this environment variable is set in your Python application's environment.
SECRET_KEY_HEX = os.environ.get("SECRET_KEY")
SECRET_KEY_BYTES = None

if SECRET_KEY_HEX:
    if len(SECRET_KEY_HEX) != 64:
        raise ValueError("SECRET_KEY environment variable must be a 64-character hex string.")
    try:
        SECRET_KEY_BYTES = bytes.fromhex(SECRET_KEY_HEX)
    except ValueError:
        raise ValueError("SECRET_KEY environment variable is not a valid hex string.")
else:
    # This is a critical security configuration.
    # For production, you must ensure this is properly set and managed.
    print("CRITICAL WARNING: SECRET_KEY environment variable is not set. Encryption/decryption will fail or use insecure defaults if any are set later.")
    # To prevent runtime errors during setup if the key isn't immediately available,
    # but this should be handled robustly in a real application.
    # For example, by preventing the application from starting.


def encrypt(text: str) -> dict:
    """
    Encrypts text using AES-256-GCM, compatible with the provided TypeScript.
    Returns a dict with 'encryptedData' (hex string of ciphertext + tag)
    and 'iv' (hex string).
    """
    if SECRET_KEY_BYTES is None:
        raise EnvironmentError("Encryption cannot proceed: SECRET_KEY is not configured properly.")

    iv = os.urandom(12)  # AES-GCM standard IV size is 12 bytes (96 bits)
    aesgcm = AESGCM(SECRET_KEY_BYTES)
    text_bytes = text.encode('utf-8')

    encrypted_bytes_with_tag = aesgcm.encrypt(iv, text_bytes, None) # No associated data (AAD)

    return {
        "encryptedData": encrypted_bytes_with_tag.hex(),
        "iv": iv.hex(),
    }

def decrypt(encrypted_hex: str, iv_hex: str) -> str:
    """
    Decrypts hex-encoded data using AES-256-GCM, compatible with the provided TypeScript.
    'encrypted_hex' is the ciphertext + tag, hex encoded.
    'iv_hex' is the IV, hex encoded.
    Returns the original plaintext string.
    """
    if SECRET_KEY_BYTES is None:
        raise EnvironmentError("Decryption cannot proceed: SECRET_KEY is not configured properly.")

    try:
        iv = bytes.fromhex(iv_hex)
        encrypted_bytes_with_tag = bytes.fromhex(encrypted_hex)
    except binascii.Error as e: # More specific error for hex decoding
        raise ValueError(f"Invalid hex string for IV or encrypted data: {e}")


    aesgcm = AESGCM(SECRET_KEY_BYTES)

    try:
        decrypted_bytes = aesgcm.decrypt(iv, encrypted_bytes_with_tag, None) # No AAD
        return decrypted_bytes.decode('utf-8')
    except InvalidTag:
        raise ValueError("Decryption failed: Invalid authentication tag. Data may be tampered or key/IV incorrect.")
    except Exception as e:
        raise ValueError(f"Decryption failed due to an unexpected error: {e}")
