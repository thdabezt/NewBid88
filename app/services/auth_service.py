from app.domain.entities import User, Wallet
from app.domain.ports import Clock, PasswordHasher, UnitOfWorkFactory


class AuthService:
    def __init__(self, uow: UnitOfWorkFactory, hasher: PasswordHasher, clock: Clock) -> None:
        self._uow = uow
        self._hasher = hasher
        self._clock = clock

    def register(self, username: str, password: str) -> User:
        """BR-01: create the user and an empty wallet in one transaction."""
        # Hash before opening the transaction: bcrypt is slow and should not hold a DB connection.
        password_hash = self._hasher.hash(password)
        now = self._clock.now()
        with self._uow() as uow:
            user = uow.users.add(User(username=username.lower(), password_hash=password_hash, created_at=now))
            uow.wallets.add(Wallet(user_id=user.id, updated_at=now))
            uow.commit()
        return user
