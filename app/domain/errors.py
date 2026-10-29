from typing import Any


class DomainError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


class ValidationError(DomainError):
    """Input failed a business-level validation rule (422)."""


class AuthenticationError(DomainError):
    pass


class ForbiddenError(DomainError):
    pass


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class UsernameTaken(ConflictError):
    def __init__(self, username: str) -> None:
        super().__init__("USERNAME_TAKEN", f"Username {username} is already taken")


class InvalidCredentials(AuthenticationError):
    def __init__(self) -> None:
        super().__init__("INVALID_CREDENTIALS", "Wrong username or password")


class InvalidToken(AuthenticationError):
    def __init__(self, message: str = "Invalid or expired token") -> None:
        super().__init__("UNAUTHORIZED", message)


class UserNotFound(NotFoundError):
    def __init__(self, user_id: int) -> None:
        super().__init__("USER_NOT_FOUND", f"User {user_id} does not exist")
