import re

from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.errors import error_response
from app.domain.errors import AuthenticationError, InvalidToken
from app.domain.ports import TokenService

PUBLIC_ROUTES = [
    ("POST", re.compile(r"/auth/(register|login)")),
    ("GET", re.compile(r"/auctions(/[^/]+)?")),
    ("GET", re.compile(r"/health")),
    ("GET", re.compile(r"/(docs|docs/oauth2-redirect|redoc|openapi\.json)")),
    ("GET", re.compile(r"/auctions/[^/]+/bids")),
]

def is_public(method: str, path: str) -> bool:
    return any(method == public_method and pattern.fullmatch(path) for public_method, pattern in PUBLIC_ROUTES)


def bearer_token(scope: Scope) -> str:
    for name, value in scope["headers"]:
        if name == b"authorization":
            scheme, _, token = value.decode("latin-1").partition(" ")
            if scheme.lower() == "bearer" and token:
                return token
    raise InvalidToken("Missing bearer token")


class JWTAuthMiddleware:
    def __init__(self, app: ASGIApp, tokens: TokenService) -> None:
        self.app = app
        self.tokens = tokens

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or is_public(scope["method"], scope["path"]):
            await self.app(scope, receive, send)
            return

        try:
            user_id = self.tokens.verify(bearer_token(scope))
        except AuthenticationError as exc:
            response = error_response(401, exc.code, exc.message)
            response.headers["WWW-Authenticate"] = "Bearer"
            await response(scope, receive, send)
            return

        scope.setdefault("state", {})["user_id"] = user_id
        await self.app(scope, receive, send)
