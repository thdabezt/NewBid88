from datetime import UTC, datetime, timedelta

import pytest

from app.domain.errors import InvalidToken
from app.infra.security import BcryptHasher, JwtTokenService
from tests.fakes import FixedClock

SECRET = "unit-test-secret-at-least-32-bytes"


def tokens_issued(minutes_ago: int = 0, secret: str = SECRET) -> JwtTokenService:
    # PyJWT checks exp against the system clock, so start from the real current time.
    return JwtTokenService(secret, 60, FixedClock(datetime.now(UTC) - timedelta(minutes=minutes_ago)))


def test_bcrypt_hash_verifies_only_the_same_password():
    hasher = BcryptHasher(rounds=4)
    hashed = hasher.hash("matkhau123")

    assert hasher.verify("matkhau123", hashed)
    assert not hasher.verify("matkhau124", hashed)


def test_bcrypt_rejects_password_over_72_bytes_instead_of_raising():
    hasher = BcryptHasher(rounds=4)

    assert not hasher.verify("a" * 73, hasher.hash("matkhau123"))


def test_token_round_trip():
    tokens = tokens_issued()

    token, expires_in = tokens.issue(7, "an_nguyen")

    assert expires_in == 3600
    assert tokens.verify(token) == 7


def test_expired_token_is_rejected():
    token, _ = tokens_issued(minutes_ago=61).issue(7, "an_nguyen")

    with pytest.raises(InvalidToken):
        tokens_issued().verify(token)


def test_token_signed_with_another_secret_is_rejected():
    token, _ = tokens_issued(secret="another-secret-at-least-32-bytes!").issue(7, "an_nguyen")

    with pytest.raises(InvalidToken):
        tokens_issued().verify(token)


def test_garbage_token_is_rejected():
    with pytest.raises(InvalidToken):
        tokens_issued().verify("not-a-jwt")
