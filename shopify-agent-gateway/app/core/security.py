import hashlib
import os
from typing import Optional
from cryptography.fernet import Fernet
from app.core.config import settings


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA-256."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def _get_fernet() -> Optional[Fernet]:
    """Get Fernet instance if ENCRYPTION_KEY is set."""
    if not settings.encryption_key:
        return None
    
    try:
        # If the key is a valid Fernet key, use it directly
        return Fernet(settings.encryption_key.encode())
    except Exception:
        return None


def encrypt_token(token: str) -> str:
    """Encrypt a token using Fernet encryption."""
    fernet = _get_fernet()
    
    if fernet is None:
        # TODO: In production, ensure ENCRYPTION_KEY is always set
        # For now, return plaintext if no encryption key is configured
        return token
    
    return fernet.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a token using Fernet encryption."""
    fernet = _get_fernet()
    
    if fernet is None:
        # TODO: In production, ensure ENCRYPTION_KEY is always set
        # For now, return as-is if no encryption key is configured
        return encrypted_token
    
    try:
        return fernet.decrypt(encrypted_token.encode()).decode()
    except Exception:
        # If decryption fails, return as-is (might be plaintext from dev mode)
        return encrypted_token
