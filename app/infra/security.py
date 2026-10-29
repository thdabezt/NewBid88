from datetime import timedelta

import bcrypt
import jwt

from app.domain.errors import InvalidToken
from app.domain.ports import Clock


class BcryptHasher:
    def __init__(self, rounds: int) -> None:
        self._rounds = rounds

    def hash(self, plain: str) -> str:
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(self._rounds)).decode()

    def verify(self, plain: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(plain.encode(), hashed.encode())
        except ValueError:
            return False


class JwtTokenService:
    ALGORITHM = "HS256"

    def __init__(self, secret: str, expire_minutes: int, clock: Clock) -> None:
        self._secret = secret
        self._lifetime = timedelta(minutes=expire_minutes)
        self._clock = clock

    def issue(self, user_id: int, username: str) -> tuple[str, int]:
        now = self._clock.now()
        claims = {"sub": str(user_id), "username": username, "iat": now, "exp": now + self._lifetime}
        token = jwt.encode(claims, self._secret, algorithm=self.ALGORITHM)
        return token, int(self._lifetime.total_seconds())

    def verify(self, token: str) -> int:
        try:
            claims = jwt.decode(token, self._secret, algorithms=[self.ALGORITHM], options={"require": ["sub", "exp"]})
            return int(claims["sub"])
        except (jwt.PyJWTError, ValueError):
            raise InvalidToken() from None
