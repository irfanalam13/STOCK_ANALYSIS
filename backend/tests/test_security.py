"""Unit tests for password hashing and JWT handling."""
import pytest
from jose import JWTError

from core.security import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("s3cret!")
    assert hashed != "s3cret!"
    assert verify_password("s3cret!", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_carries_role_and_type():
    token = create_access_token("42", "trader")
    payload = decode_token(token, expected_type=TOKEN_TYPE_ACCESS)
    assert payload["sub"] == "42"
    assert payload["role"] == "trader"
    assert payload["type"] == TOKEN_TYPE_ACCESS


def test_refresh_token_cannot_be_used_as_access():
    token = create_refresh_token("42")
    # Decoding as a refresh token works...
    assert decode_token(token, expected_type=TOKEN_TYPE_REFRESH)["sub"] == "42"
    # ...but rejecting it where an access token is expected is enforced.
    with pytest.raises(JWTError):
        decode_token(token, expected_type=TOKEN_TYPE_ACCESS)
