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
