import os
from cryptography.fernet import Fernet, InvalidToken

def _fernet():
    key = os.getenv("FIELD_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("FIELD_ENCRYPTION_KEY is missing from .env")
    return Fernet(key.encode())

def encrypt_field(value):
    if not value:
        return None
    return _fernet().encrypt(str(value).encode()).decode()

def decrypt_field(value):
    if not value:
        return None
    try:
        return _fernet().decrypt(value.encode()).decode()
    except (InvalidToken, ValueError):
        return None

def mask_identifier(value):
    if not value:
        return None
    return "*" * max(0, len(value) - 4) + value[-4:]
