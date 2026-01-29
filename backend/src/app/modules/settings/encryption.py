"""Encryption utilities for secure settings storage."""
import os
from pathlib import Path
from cryptography.fernet import Fernet

# Store encryption key in data directory (outside of repo)
_KEY_FILE = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / ".encryption_key"


def _get_or_create_key() -> bytes:
    """Get existing key or create new one."""
    _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _KEY_FILE.exists():
        return _KEY_FILE.read_bytes()
    key = Fernet.generate_key()
    _KEY_FILE.write_bytes(key)
    return key


_fernet = Fernet(_get_or_create_key())


def encrypt_value(value: str) -> str:
    """Encrypt a string value."""
    return _fernet.encrypt(value.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    """Decrypt an encrypted string value."""
    return _fernet.decrypt(encrypted.encode()).decode()


def mask_value(value: str) -> str:
    """Mask a value, showing only last 4 characters."""
    if len(value) <= 4:
        return "*" * len(value)
    return "*" * (len(value) - 4) + value[-4:]
