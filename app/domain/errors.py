class DomainError(Exception):
    """A business rule was broken by the input (400)."""

    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


class ValidationError(DomainError):
    """Input failed a business-level validation rule (422)."""


class AuthenticationError(DomainError):
    """Unknown identity: wrong username or password (401)."""


class ForbiddenError(DomainError):
    """Logged in, but not allowed to touch this object (403)."""


class NotFoundError(DomainError):
    """The object does not exist (404)."""


class ConflictError(DomainError):
    """The object is in the wrong state for this action (409)."""


class UsernameTaken(ConflictError):
    """BR-01: the username is already registered."""

    def __init__(self, username: str) -> None:
        super().__init__("USERNAME_TAKEN", f"Username {username} is already taken")


class InvalidCredentials(AuthenticationError):
    """Wrong username or wrong password. One message for both, so nobody can probe which accounts exist."""

    def __init__(self) -> None:
        super().__init__("INVALID_CREDENTIALS", "Wrong username or password")


class InvalidToken(AuthenticationError):
    """Bearer token missing, malformed, signed with another key or expired."""

    def __init__(self, message: str = "Invalid or expired token") -> None:
        super().__init__("UNAUTHORIZED", message)


class UserNotFound(NotFoundError):
    def __init__(self, user_id: int) -> None:
        super().__init__("USER_NOT_FOUND", f"User {user_id} does not exist")
