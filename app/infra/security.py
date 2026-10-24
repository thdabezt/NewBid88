import bcrypt


class BcryptHasher:
    def __init__(self, rounds: int) -> None:
        self._rounds = rounds

    def hash(self, plain: str) -> str:
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(self._rounds)).decode()

    def verify(self, plain: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(plain.encode(), hashed.encode())
        except ValueError:
            # bcrypt refuses passwords over 72 bytes; register never stores one, so it cannot match.
            return False
