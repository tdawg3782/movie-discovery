"""Tests for Settings encryption service."""
import pytest
from app.modules.settings.encryption import encrypt_value, decrypt_value, mask_value


def test_encrypt_decrypt_roundtrip():
    """Encrypted value should decrypt to original."""
    original = "my-secret-api-key-12345"
    encrypted = encrypt_value(original)
    decrypted = decrypt_value(encrypted)
    assert decrypted == original
    assert encrypted != original


def test_mask_value_shows_last_four():
    """Mask should show only last 4 characters."""
    value = "abcdefghijklmnop"
    masked = mask_value(value)
    assert masked == "************mnop"


def test_mask_short_value():
    """Short values should be fully masked."""
    value = "abc"
    masked = mask_value(value)
    assert masked == "***"
