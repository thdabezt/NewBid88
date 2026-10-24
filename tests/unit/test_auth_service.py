import pytest

from app.domain.errors import InvalidCredentials, UsernameTaken, UserNotFound
from app.services.auth_service import AuthService
from tests.fakes import FakeHasher, FakeTokenService, FakeUnitOfWork, FixedClock, InMemoryDb


@pytest.fixture()
def db():
    return InMemoryDb()


@pytest.fixture()
def hasher():
    return FakeHasher()


@pytest.fixture()
def clock():
    return FixedClock()


@pytest.fixture()
def service(db, hasher, clock):
    return AuthService(lambda: FakeUnitOfWork(db), hasher, FakeTokenService(), clock)


def test_register_stores_lowercase_username_and_hashed_password(service, db, clock):
    user = service.register("An_Nguyen", "matkhau123")

    assert user.username == "an_nguyen"
    assert user.created_at == clock.now()
    assert db.users[user.id].password_hash == "hashed:matkhau123"


def test_register_creates_empty_wallet(service, db):
    user = service.register("an_nguyen", "matkhau123")

    wallet = db.wallets[user.id]
    assert (wallet.balance, wallet.held, wallet.available) == (0, 0, 0)


def test_register_rejects_taken_username_in_any_case(service, db):
    service.register("an_nguyen", "matkhau123")

    with pytest.raises(UsernameTaken):
        service.register("AN_NGUYEN", "khac12345")
    assert len(db.users) == 1
    assert len(db.wallets) == 1


def test_login_returns_token_for_right_password(service):
    user = service.register("an_nguyen", "matkhau123")

    assert service.login("An_Nguyen", "matkhau123") == (f"token-for-{user.id}", 3600)


def test_login_rejects_wrong_password(service):
    service.register("an_nguyen", "matkhau123")

    with pytest.raises(InvalidCredentials):
        service.login("an_nguyen", "wrong-password")


def test_login_unknown_user_still_verifies_a_password(service, hasher):
    with pytest.raises(InvalidCredentials):
        service.login("nobody", "matkhau123")
    assert hasher.verify_calls == 1


def test_get_user(service):
    user = service.register("an_nguyen", "matkhau123")

    assert service.get_user(user.id) == user


def test_get_user_missing(service):
    with pytest.raises(UserNotFound):
        service.get_user(999)
