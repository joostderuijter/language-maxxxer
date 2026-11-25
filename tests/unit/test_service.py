from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from lmx.knowledge import service
from lmx.knowledge.events import EventKind, WordState
from lmx.models import KnowledgeEvent, User, WordKnowledge

E = EventKind


def test_record_creates_event_and_state(session: Session, uid: int) -> None:
    snap = service.record(session, uid, 'ko', ' 먹다 ', E.MARKED_KNOWN, 'test')
    assert snap.state == WordState.KNOWN
    assert service.state_of(session, uid, 'ko', '먹다').state == WordState.KNOWN
    ev = session.scalars(select(KnowledgeEvent)).all()
    assert [(e.lemma, e.kind, e.source) for e in ev] == [('먹다', 'marked_known', 'test')]


def test_record_updates_existing_row(session: Session, uid: int) -> None:
    service.record(session, uid, 'ko', '먹다', E.MARKED_KNOWN, 'test')
    service.record(session, uid, 'ko', '먹다', E.LAPSED, 'anki')
    rows = session.scalars(select(WordKnowledge)).all()
    assert len(rows) == 1 and rows[0].state == 'learning'


def test_empty_lemma_rejected(session: Session, uid: int) -> None:
    with pytest.raises(ValueError):
        service.record(session, uid, 'ko', '  ', E.SEEN, 'test')


def test_unknown_word_state(session: Session, uid: int) -> None:
    s = service.state_of(session, uid, 'ko', '없는말')
    assert (s.state, s.confidence) == (WordState.UNKNOWN, 0.0)


def test_languages_and_users_are_separate(session: Session, uid: int) -> None:
    other = User(name='other')
    session.add(other)
    session.flush()
    service.record(session, uid, 'ko', '사과', E.MARKED_KNOWN, 'test')
    assert service.state_of(session, uid, 'ja', '사과').state == WordState.UNKNOWN
    assert service.state_of(session, other.id, 'ko', '사과').state == WordState.UNKNOWN
    assert service.counts(session, other.id, 'ko')['known'] == 0


def test_counts_has_every_state(session: Session, uid: int) -> None:
    service.record_many(
        session, uid, 'ko', [('a', E.MARKED_KNOWN), ('b', E.MARKED_KNOWN), ('c', E.SEEN), ('d', E.IGNORED)], 'test'
    )
    assert service.counts(session, uid, 'ko') == {'unknown': 0, 'seen': 1, 'learning': 0, 'known': 2, 'ignored': 1}


def test_rebuild_matches_incremental_and_repairs_state(session: Session, uid: int) -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    for i, (lemma, kind) in enumerate(
        [('a', E.SEEN), ('a', E.CARD_ADDED), ('b', E.MARKED_KNOWN), ('a', E.MATURE), ('b', E.LAPSED)]
    ):
        service.record(session, uid, 'ko', lemma, kind, 'test', at=t0 + timedelta(minutes=i))
    before = {r.lemma: (r.state, r.confidence) for r in session.scalars(select(WordKnowledge))}
    for r in session.scalars(select(WordKnowledge)):  # corrupt the derived state
        r.state, r.confidence = 'unknown', 0.0
    session.add(WordKnowledge(user_id=uid, language='ko', lemma='c', state='known', confidence=1.0))
    session.flush()
    assert service.rebuild(session, uid, 'ko') == 2
    after = {r.lemma: (r.state, r.confidence) for r in session.scalars(select(WordKnowledge))}
    assert after == before == {'a': ('known', 0.95), 'b': ('learning', 0.4)}  # 'c' had no events: removed


def test_rebuild_recreates_missing_rows(session: Session, uid: int) -> None:
    service.record(session, uid, 'ko', 'a', E.MARKED_KNOWN, 'test')
    for r in session.scalars(select(WordKnowledge)):
        session.delete(r)
    session.flush()
    assert service.rebuild(session, uid, 'ko') == 1
    assert service.state_of(session, uid, 'ko', 'a').state == WordState.KNOWN
