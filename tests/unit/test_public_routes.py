import pytest

from app.api.middleware import is_public


@pytest.mark.parametrize(
    "method, path",
    [
        ("POST", "/auth/register"),
        ("POST", "/auth/login"),
        ("GET", "/auctions"),
        ("GET", "/auctions/5"),
        ("GET", "/auctions/5/bids"),
        ("GET", "/auctions/abc/bids"),
        ("GET", "/health"),
        ("GET", "/docs"),
        ("GET", "/openapi.json"),
    ],
)
def test_public(method, path):
    assert is_public(method, path)


@pytest.mark.parametrize(
    "method, path",
    [
        ("GET", "/users/me"),
        ("GET", "/users/me/auctions"),
        ("GET", "/users/me/bids"),
        ("POST", "/auctions"),
        ("DELETE", "/auctions/5"),
        ("POST", "/auctions/5/bids"),
        ("GET", "/auctions/5/extra"),
        ("GET", "/wallet"),
        ("GET", "/no-such-path"),
    ],
)
def test_needs_login(method, path):
    assert not is_public(method, path)