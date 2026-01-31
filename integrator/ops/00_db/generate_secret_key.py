import os
import binascii

def generate_aes_key_hex():
    """Generates a 32-byte (256-bit) random key and returns its hex representation."""
    random_bytes = os.urandom(32)
    hex_key = binascii.hexlify(random_bytes).decode('ascii')
    return hex_key

if __name__ == "__main__":
    secret_key_hex = generate_aes_key_hex()
    print("Generated SECRET_KEY (64-character hex string):")
    print(secret_key_hex)
    print("\nTo use this key:")
    print("1. Copy the 64-character hex string printed above.")
    print("2. Set it as an environment variable named 'SECRET_KEY'. For example:")
    print("   export SECRET_KEY=\"your_generated_key_here\"")
    print("   (Replace 'your_generated_key_here' with the actual key)")
    print("3. Ensure this environment variable is available to your Python application")
    print("   and any scripts that perform encryption/decryption (like db/insert_tables.py).")
