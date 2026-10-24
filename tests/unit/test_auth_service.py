import pytest

from app.domain.errors import UsernameTaken
from app.services.auth_service import AuthService
from tests.fakes import FakeHasher, FakeUnitOfWork, FixedClock, InMemoryDb


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
    return AuthService(lambda: FakeUnitOfWork(db), hasher, clock)


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
