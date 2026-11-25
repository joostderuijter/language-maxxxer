"""Shared FastAPI dependencies."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from ..db import Database


def get_session(request: Request) -> Iterator[Session]:
    """One database session per request: committed when the request succeeds, rolled back on an error."""
    db: Database = request.app.state.db
    with db.session() as s:
        yield s


Db = Annotated[Session, Depends(get_session)]
