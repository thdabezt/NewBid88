from app.domain.entities import User, Wallet
from app.domain.errors import InvalidCredentials
from app.domain.ports import Clock, PasswordHasher, TokenService, UnitOfWorkFactory


class AuthService:
    def __init__(self, uow: UnitOfWorkFactory, hasher: PasswordHasher, tokens: TokenService, clock: Clock) -> None:
        self._uow = uow
        self._hasher = hasher
        self._tokens = tokens
        self._clock = clock
        # Checked against when the username is unknown, so both login failures cost one bcrypt verify.
        self._dummy_hash = hasher.hash("not-a-real-password")

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

    def login(self, username: str, password: str) -> tuple[str, int]:
        """Return an access token and its lifetime in seconds."""
        with self._uow() as uow:
            user = uow.users.get_by_username(username.lower())
        password_ok = self._hasher.verify(password, user.password_hash if user else self._dummy_hash)
        if user is None or not password_ok:
            raise InvalidCredentials()
        return self._tokens.issue(user.id, user.username)
