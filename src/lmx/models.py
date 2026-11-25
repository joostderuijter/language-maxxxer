"""Tables. Knowledge is per user (multi-user ready, ADR-2); content will be shared between users.

Knowledge is an append-only event log (knowledge_events) plus the state derived from it (word_knowledge), see ADR-4.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class KnowledgeEvent(Base):
    """Something that tells us about the user's knowledge of a word. Never updated or deleted."""

    __tablename__ = 'knowledge_events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    language: Mapped[str] = mapped_column(String(8))
    lemma: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(32))  # see knowledge.events.EventKind
    source: Mapped[str] = mapped_column(String(64))  # 'import:csv', 'anki', 'reader', 'quiz', ...
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    __table_args__ = (Index('ix_events_user_lang_lemma', 'user_id', 'language', 'lemma'),)


class WordKnowledge(Base):
    """Current state of one word for one user, derived from its events (rebuildable at any time)."""

    __tablename__ = 'word_knowledge'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    language: Mapped[str] = mapped_column(String(8))
    lemma: Mapped[str] = mapped_column(String(200))
    state: Mapped[str] = mapped_column(String(16))  # see knowledge.events.WordState
    confidence: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    __table_args__ = (UniqueConstraint('user_id', 'language', 'lemma', name='uq_knowledge_user_lang_lemma'),)
