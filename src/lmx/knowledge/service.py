"""Recording knowledge events and reading the derived state."""

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import KnowledgeEvent, WordKnowledge, now
from .events import EventKind, Snapshot, WordState, apply, replay


def record(
    session: Session, user_id: int, language: str, lemma: str, kind: EventKind, source: str, at: datetime | None = None
) -> Snapshot:
    """Append an event and update the word's state. -> the new state"""
    lemma = lemma.strip()
    if not lemma:
        raise ValueError('empty lemma')
    at = at or now()
    session.add(KnowledgeEvent(user_id=user_id, language=language, lemma=lemma, kind=kind.value, source=source, at=at))
    row = session.scalar(
        select(WordKnowledge).where(
            WordKnowledge.user_id == user_id, WordKnowledge.language == language, WordKnowledge.lemma == lemma
        )
    )
    current = Snapshot(WordState(row.state), row.confidence) if row else None
    new = apply(current, kind)
    if row is None:
        session.add(
            WordKnowledge(
                user_id=user_id,
                language=language,
                lemma=lemma,
                state=new.state.value,
                confidence=new.confidence,
                updated_at=at,
            )
        )
    else:
        row.state, row.confidence, row.updated_at = new.state.value, new.confidence, at
    session.flush()
    return new


def record_many(
    session: Session, user_id: int, language: str, items: Iterable[tuple[str, EventKind]], source: str
) -> int:
    n = 0
    for lemma, kind in items:
        record(session, user_id, language, lemma, kind, source)
        n += 1
    return n


def rebuild(session: Session, user_id: int, language: str) -> int:
    """Recompute every word's state from its events (after a reducer change). -> number of words"""
    events = session.execute(
        select(KnowledgeEvent.lemma, KnowledgeEvent.kind)
        .where(KnowledgeEvent.user_id == user_id, KnowledgeEvent.language == language)
        .order_by(KnowledgeEvent.at, KnowledgeEvent.id)
    ).all()
    by_lemma: dict[str, list[EventKind]] = {}
    for lemma, kind in events:
        by_lemma.setdefault(lemma, []).append(EventKind(kind))
    rows = {
        r.lemma: r
        for r in session.scalars(
            select(WordKnowledge).where(WordKnowledge.user_id == user_id, WordKnowledge.language == language)
        )
    }
    for lemma, row in rows.items():
        if lemma not in by_lemma:  # derived state without any events: not real
            session.delete(row)
    for lemma, kinds in by_lemma.items():
        snap = replay(kinds)
        row = rows.get(lemma)
        if row is None:
            session.add(
                WordKnowledge(
                    user_id=user_id, language=language, lemma=lemma, state=snap.state.value, confidence=snap.confidence
                )
            )
        else:
            row.state, row.confidence = snap.state.value, snap.confidence
    session.flush()
    return len(by_lemma)


def state_of(session: Session, user_id: int, language: str, lemma: str) -> Snapshot:
    row = session.scalar(
        select(WordKnowledge).where(
            WordKnowledge.user_id == user_id, WordKnowledge.language == language, WordKnowledge.lemma == lemma
        )
    )
    return Snapshot(WordState(row.state), row.confidence) if row else Snapshot(WordState.UNKNOWN, 0.0)


def counts(session: Session, user_id: int, language: str) -> dict[str, int]:
    """Words per state, every state present (0 if none)."""
    rows = session.execute(
        select(WordKnowledge.state, func.count())
        .where(WordKnowledge.user_id == user_id, WordKnowledge.language == language)
        .group_by(WordKnowledge.state)
    ).all()
    out = {s.value: 0 for s in WordState}
    out.update({state: n for state, n in rows})
    return out
