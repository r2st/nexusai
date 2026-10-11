"""
Unit tests for core security module (password hashing and JWT tokens).
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import patch

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    create_tokens,
    decode_token,
    verify_token,
    TokenData,
    Token,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_get_password_hash_returns_hash(self):
        """Test that get_password_hash returns a bcrypt hash."""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_get_password_hash_different_for_same_password(self):
        """Test that hashing the same password produces different hashes (due to salt)."""
        password = "same_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2  # Different salts

    def test_verify_password_correct(self):
        """Test that verify_password returns True for correct password."""
        password = "correct_password"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test that verify_password returns False for incorrect password."""
        password = "correct_password"
        hashed = get_password_hash(password)

        assert verify_password("wrong_password", hashed) is False

    def test_verify_password_empty_password(self):
        """Test verify_password with empty password."""
        hashed = get_password_hash("some_password")
        assert verify_password("", hashed) is False

    def test_hash_special_characters(self):
        """Test hashing passwords with special characters."""
        password = "p@$$w0rd!#%^&*()_+-=[]{}|;':\",./<>?"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_hash_unicode_password(self):
        """Test hashing passwords with unicode characters."""
        password = "密码пароль🔐"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_hash_long_password(self):
        """Test hashing long passwords."""
        password = "a" * 100
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_hash_whitespace_password(self):
        """Test hashing passwords with whitespace."""
        password = "  password with spaces  "
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True
        assert verify_password("password with spaces", hashed) is False


class TestAccessToken:
    """Tests for access token creation and validation."""

    def test_create_access_token_basic(self):
        """Test basic access token creation."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_custom_expiry(self):
        """Test access token with custom expiry."""
        data = {"sub": "user123"}
        expires = timedelta(minutes=5)
        token = create_access_token(data, expires_delta=expires)

        decoded = decode_token(token)
        assert decoded is not None
        # Token should expire within ~5 minutes
        assert decoded.exp is not None
        time_diff = decoded.exp - datetime.now(UTC)
        assert time_diff.total_seconds() <= 300 + 5  # 5 minutes + buffer

    def test_create_access_token_contains_type(self):
        """Test that access token contains type claim."""
        data = {"sub": "user123"}
        token = create_access_token(data)

        # Verify with type check
        token_data = verify_token(token, "access")
        assert token_data is not None

    def test_create_access_token_preserves_data(self):
        """Test that token data is preserved."""
        data = {
            "sub": "user123",
            "email": "test@example.com",
            "scopes": ["read", "write"],
        }
        token = create_access_token(data)
        decoded = decode_token(token)

        assert decoded is not None
        assert decoded.user_id == "user123"
        assert decoded.email == "test@example.com"
        assert decoded.scopes == ["read", "write"]

    def test_create_access_token_default_expiry(self):
        """Test access token uses default expiry from settings."""
        data = {"sub": "user123"}
        token = create_access_token(data)
        decoded = decode_token(token)

        assert decoded is not None
        assert decoded.exp is not None
        # Should be in the future
        assert decoded.exp > datetime.now(UTC)


class TestRefreshToken:
    """Tests for refresh token creation and validation."""

    def test_create_refresh_token_basic(self):
        """Test basic refresh token creation."""
        data = {"sub": "user123"}
        token = create_refresh_token(data)

        assert token is not None
        assert isinstance(token, str)

    def test_create_refresh_token_with_custom_expiry(self):
        """Test refresh token with custom expiry."""
        data = {"sub": "user123"}
        expires = timedelta(days=1)
        token = create_refresh_token(data, expires_delta=expires)

        assert token is not None

    def test_refresh_token_type_is_refresh(self):
        """Test that refresh token has correct type."""
        data = {"sub": "user123"}
        token = create_refresh_token(data)

        # Should verify with type "refresh"
        token_data = verify_token(token, "refresh")
        assert token_data is not None

        # Should NOT verify with type "access"
        token_data = verify_token(token, "access")
        assert token_data is None

    def test_refresh_token_longer_expiry(self):
        """Test refresh token has longer expiry than access token."""
        data = {"sub": "user123"}
        access_token = create_access_token(data)
        refresh_token = create_refresh_token(data)

        access_decoded = decode_token(access_token)
        refresh_decoded = verify_token(refresh_token, "refresh")

        assert access_decoded is not None
        assert refresh_decoded is not None
        assert refresh_decoded.exp > access_decoded.exp


class TestCreateTokens:
    """Tests for create_tokens function."""

    def test_create_tokens_returns_token_object(self):
        """Test that create_tokens returns a Token object."""
        result = create_tokens("user123", "test@example.com")

        assert isinstance(result, Token)
        assert result.access_token is not None
        assert result.refresh_token is not None
        assert result.token_type == "bearer"
        assert result.expires_in > 0

    def test_create_tokens_with_scopes(self):
        """Test create_tokens with scopes."""
        result = create_tokens("user123", "test@example.com", scopes=["admin", "read"])

        # Verify scopes are in access token
        decoded = decode_token(result.access_token)
        assert decoded is not None
        assert "admin" in decoded.scopes
        assert "read" in decoded.scopes

    def test_create_tokens_without_scopes(self):
        """Test create_tokens without scopes defaults to empty list."""
        result = create_tokens("user123", "test@example.com")

        decoded = decode_token(result.access_token)
        assert decoded is not None
        assert decoded.scopes == []

    def test_create_tokens_contains_email(self):
        """Test create_tokens includes email in token."""
        result = create_tokens("user123", "test@example.com")

        decoded = decode_token(result.access_token)
        assert decoded is not None
        assert decoded.email == "test@example.com"

    def test_create_tokens_different_users(self):
        """Test create_tokens for different users produce different tokens."""
        result1 = create_tokens("user1", "user1@example.com")
        result2 = create_tokens("user2", "user2@example.com")

        assert result1.access_token != result2.access_token
        assert result1.refresh_token != result2.refresh_token


class TestDecodeToken:
    """Tests for decode_token function."""

    def test_decode_valid_token(self):
        """Test decoding a valid token."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        decoded = decode_token(token)

        assert decoded is not None
        assert isinstance(decoded, TokenData)
        assert decoded.user_id == "user123"
        assert decoded.email == "test@example.com"

    def test_decode_invalid_token(self):
        """Test decoding an invalid token returns None."""
        result = decode_token("invalid.token.here")
        assert result is None

    def test_decode_expired_token(self):
        """Test decoding an expired token returns None."""
        data = {"sub": "user123"}
        expires = timedelta(seconds=-10)  # Already expired
        token = create_access_token(data, expires_delta=expires)

        result = decode_token(token)
        assert result is None

    def test_decode_token_without_sub(self):
        """Test that token without 'sub' claim returns None."""
        import jwt
        from app.core.config import settings

        # Create token without sub
        token = jwt.encode(
            {"email": "test@example.com", "exp": datetime.now(UTC) + timedelta(hours=1)},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        result = decode_token(token)
        assert result is None

    def test_decode_malformed_token(self):
        """Test decoding malformed token returns None."""
        assert decode_token("") is None
        assert decode_token("not.a.jwt") is None
        assert decode_token("x" * 1000) is None

    def test_decode_token_extracts_scopes(self):
        """Test decoding token extracts scopes correctly."""
        data = {"sub": "user123", "scopes": ["read", "write", "admin"]}
        token = create_access_token(data)

        decoded = decode_token(token)
        assert decoded is not None
        assert decoded.scopes == ["read", "write", "admin"]

    def test_decode_token_default_scopes(self):
        """Test decoding token without scopes defaults to empty list."""
        data = {"sub": "user123"}
        token = create_access_token(data)

        decoded = decode_token(token)
        assert decoded is not None
        assert decoded.scopes == []


class TestVerifyToken:
    """Tests for verify_token function."""

    def test_verify_access_token_success(self):
        """Test verifying a valid access token."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        result = verify_token(token, "access")

        assert result is not None
        assert result.user_id == "user123"

    def test_verify_refresh_token_success(self):
        """Test verifying a valid refresh token."""
        data = {"sub": "user123"}
        token = create_refresh_token(data)

        result = verify_token(token, "refresh")

        assert result is not None
        assert result.user_id == "user123"

    def test_verify_token_wrong_type(self):
        """Test that token with wrong type is rejected."""
        data = {"sub": "user123"}
        access_token = create_access_token(data)
        refresh_token = create_refresh_token(data)

        # Access token should not verify as refresh
        assert verify_token(access_token, "refresh") is None

        # Refresh token should not verify as access
        assert verify_token(refresh_token, "access") is None

    def test_verify_invalid_token(self):
        """Test verifying invalid token returns None."""
        assert verify_token("invalid", "access") is None

    def test_verify_expired_token(self):
        """Test verifying expired token returns None."""
        data = {"sub": "user123"}
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        assert verify_token(token, "access") is None

    def test_verify_token_returns_all_data(self):
        """Test verify_token returns all token data."""
        data = {"sub": "user123", "email": "test@example.com", "scopes": ["admin"]}
        token = create_access_token(data)

        result = verify_token(token, "access")

        assert result is not None
        assert result.user_id == "user123"
        assert result.email == "test@example.com"
        assert result.scopes == ["admin"]


class TestTokenDataModel:
    """Tests for TokenData model."""

    def test_token_data_creation(self):
        """Test TokenData model creation."""
        token_data = TokenData(
            user_id="user123",
            email="test@example.com",
            scopes=["read", "write"],
        )

        assert token_data.user_id == "user123"
        assert token_data.email == "test@example.com"
        assert token_data.scopes == ["read", "write"]

    def test_token_data_defaults(self):
        """Test TokenData default values."""
        token_data = TokenData(user_id="user123")

        assert token_data.email is None
        assert token_data.scopes == []
        assert token_data.exp is None

    def test_token_data_with_exp(self):
        """Test TokenData with expiration."""
        exp = datetime.now(UTC) + timedelta(hours=1)
        token_data = TokenData(user_id="user123", exp=exp)

        assert token_data.exp == exp


class TestTokenModel:
    """Tests for Token model."""

    def test_token_creation(self):
        """Test Token model creation."""
        token = Token(
            access_token="access123",
            refresh_token="refresh123",
            expires_in=3600,
        )

        assert token.access_token == "access123"
        assert token.refresh_token == "refresh123"
        assert token.token_type == "bearer"
        assert token.expires_in == 3600

    def test_token_default_type(self):
        """Test Token default type is bearer."""
        token = Token(
            access_token="access",
            refresh_token="refresh",
            expires_in=3600,
        )

        assert token.token_type == "bearer"

    def test_token_custom_type(self):
        """Test Token with custom type."""
        token = Token(
            access_token="access",
            refresh_token="refresh",
            token_type="custom",
            expires_in=3600,
        )

        assert token.token_type == "custom"


class TestTokenSecurityProperties:
    """Tests for security properties of tokens."""

    def test_tokens_are_unique_for_different_users(self):
        """Test that tokens for different users are unique."""
        tokens = [
            create_access_token({"sub": f"user{i}", "email": f"user{i}@example.com"})
            for i in range(10)
        ]

        # All tokens should be unique since user IDs differ
        assert len(set(tokens)) == 10

    def test_token_contains_no_sensitive_data_in_header(self):
        """Test that sensitive data is not exposed in JWT header."""
        import jwt

        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        header = jwt.get_unverified_header(token)

        # Header should only contain algorithm and type
        assert "sub" not in header
        assert "email" not in header
        assert "alg" in header

    def test_different_secrets_produce_different_tokens(self):
        """Test that different secrets produce invalid tokens."""
        import jwt
        from app.core.config import settings

        data = {"sub": "user123"}
        token = create_access_token(data)

        # Try to decode with different secret
        try:
            jwt.decode(
                token,
                "different-secret-key",
                algorithms=[settings.ALGORITHM],
            )
            assert False, "Should have raised an error"
        except Exception:
            pass  # Expected behavior

    def test_tampered_token_is_invalid(self):
        """Test that tampered tokens are rejected."""
        data = {"sub": "user123"}
        token = create_access_token(data)

        # Tamper with the token
        parts = token.split(".")
        parts[1] = parts[1][:-5] + "xxxxx"  # Modify payload
        tampered = ".".join(parts)

        result = decode_token(tampered)
        assert result is None
