"""Tables. Knowledge is per user (multi-user ready, ADR-2); content will be shared between users.

Knowledge is an append-only event log (knowledge_events) plus the state derived from it (word_knowledge), see ADR-4.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
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


# ---------------------------------------------------------------------------- content (shared by all users, ADR-5)


class ContentItem(Base):
    """One episode / video. Its analysis (sentences, words) is the same for every user; coverage is computed live."""

    __tablename__ = 'content_items'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    language: Mapped[str] = mapped_column(String(8))
    source: Mapped[str] = mapped_column(String(16))  # jellyfin | folder
    external_id: Mapped[str] = mapped_column(String(500))  # Jellyfin item id, or the path relative to the folder
    series: Mapped[str] = mapped_column(String(300))
    season: Mapped[int | None] = mapped_column(Integer)
    episode: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(500))
    path: Mapped[str] = mapped_column(String(1000))
    duration_s: Mapped[float | None] = mapped_column(Float)
    subtitle: Mapped[str | None] = mapped_column(
        String(300)
    )  # where the text came from, e.g. 'stream:3', 'file:x.ko.srt'
    status: Mapped[str] = mapped_column(String(16), default='new')  # new | analyzed | no_subtitles | error
    detail: Mapped[str | None] = mapped_column(String(500))
    analyzer: Mapped[str | None] = mapped_column(String(32))  # language pack version that analysed it
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    __table_args__ = (UniqueConstraint('source', 'external_id', name='uq_content_source_external'),)


class ContentSentence(Base):
    __tablename__ = 'content_sentences'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey('content_items.id', ondelete='CASCADE'))
    idx: Mapped[int] = mapped_column(Integer)
    start_ms: Mapped[int] = mapped_column(Integer)
    end_ms: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)

    __table_args__ = (UniqueConstraint('item_id', 'idx', name='uq_sentence_item_idx'),)


class ContentWord(Base):
    """A distinct learnable word in an item (by Token.key: 배신 / 배신하다 are one word)."""

    __tablename__ = 'content_words'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey('content_items.id', ondelete='CASCADE'))
    key: Mapped[str] = mapped_column(String(200))
    count: Mapped[int] = mapped_column(Integer)
    weak: Mapped[bool] = mapped_column(Boolean)  # true only if EVERY occurrence was weak
    first_idx: Mapped[int] = mapped_column(Integer)  # sentence where it first appears

    __table_args__ = (UniqueConstraint('item_id', 'key', name='uq_word_item_key'),)


class ContentWordLemma(Base):
    """Candidate lemmas of a content word: it counts as known if the user knows ANY of them."""

    __tablename__ = 'content_word_lemmas'
    word_id: Mapped[int] = mapped_column(ForeignKey('content_words.id', ondelete='CASCADE'), primary_key=True)
    lemma: Mapped[str] = mapped_column(String(200), primary_key=True)
    ord: Mapped[int] = mapped_column(Integer)  # 0 = most specific candidate (무난하다 before 무난)

    __table_args__ = (Index('ix_word_lemmas_lemma', 'lemma'),)


class ContentOccurrence(Base):
    """Which words occur in which sentence (once per sentence), for live 1T counts."""

    __tablename__ = 'content_occurrences'
    sentence_id: Mapped[int] = mapped_column(ForeignKey('content_sentences.id', ondelete='CASCADE'), primary_key=True)
    word_id: Mapped[int] = mapped_column(ForeignKey('content_words.id', ondelete='CASCADE'), primary_key=True)
