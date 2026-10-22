from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request


def get_db_ping(request: Request) -> Callable[[], bool]:
    """The database check that main.py put on app.state."""
    return request.app.state.db_ping


DbPing = Annotated[Callable[[], bool], Depends(get_db_ping)]
