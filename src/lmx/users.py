"""Users. Single-user for now: everything runs as the default user (multi-user later, ADR-2)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import User

DEFAULT_USER = 'me'


def default_user_id(session: Session) -> int:
    uid = session.scalar(select(User.id).where(User.name == DEFAULT_USER))
    if uid is None:
        user = User(name=DEFAULT_USER)
        session.add(user)
        session.flush()
        uid = user.id
    return uid
