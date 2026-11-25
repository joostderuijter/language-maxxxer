"""The stats cache: triggers mark the right items dirty, refresh() recomputes them, nothing is ever lost."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from lmx.content import cache
from lmx.content.store import Line, save_analysis, stats
from lmx.db import Database
from lmx.knowledge import service
from lmx.knowledge.events import EventKind
from lmx.languages.base import Token
from lmx.models import ContentItem, StatsDirty, User, WordKnowledge
from lmx.users import default_user_id

E = EventKind


def tok(key: str) -> Token:
    return Token(key, 0, len(key), (key,), 'noun', key)


def item(s: Session, name: str, words: list[str], language: str = 'ko') -> ContentItem:
    it = ContentItem(language=language, source='t', external_id=name, series='S', title=name, path=name, status='new')
    s.add(it)
    s.flush()
    save_analysis(s, it, [Line(0, 1, ' '.join(words))], [[tok(w) for w in words]], 'v')
    return it


def dirty(s: Session) -> set[tuple[int, int]]:
    return {(u, i) for u, i in s.execute(select(StatsDirty.user_id, StatsDirty.item_id))}


def test_triggers_mark_items_containing_the_word(session: Session, uid: int) -> None:
    a, b, ja = item(session, 'a', ['밥', '물']), item(session, 'b', ['물']), item(session, 'j', ['밥'], language='ja')
    session.execute(delete(StatsDirty))
    service.record(session, uid, 'ko', '밥', E.MARKED_KNOWN, 't')  # insert
    assert dirty(session) == {(uid, a.id)}  # not b (no 밥), not the Japanese item
    session.execute(delete(StatsDirty))
    service.record(session, uid, 'ko', '물', E.SEEN, 't')
    service.record(session, uid, 'ko', '물', E.SEEN, 't')  # state doesn't change: no extra work...
    assert dirty(session) == {(uid, a.id), (uid, b.id)}
    session.execute(delete(StatsDirty))
    service.record(session, uid, 'ko', '물', E.SEEN, 't')
    assert dirty(session) == set()  # ...confirmed
    service.record(session, uid, 'ko', '물', E.MARKED_KNOWN, 't')  # update
    assert dirty(session) == {(uid, a.id), (uid, b.id)}
    session.execute(delete(StatsDirty))
    session.delete(session.scalars(select(WordKnowledge).where(WordKnowledge.lemma == '밥')).one())
    session.flush()  # delete (e.g. rebuild removing a row)
    assert dirty(session) == {(uid, a.id)}
    assert ja.id not in {i for _, i in dirty(session)}


def test_mark_item_for_every_user(session: Session, uid: int) -> None:
    other = User(name='other')
    session.add(other)
    session.flush()
    a = item(session, 'a', ['밥'])
    session.execute(delete(StatsDirty))
    cache.mark_item(session, a.id)
    cache.mark_item(session, a.id)  # idempotent
    assert dirty(session) == {(uid, a.id), (other.id, a.id)}


def test_refresh_matches_live_stats_and_cleans_up(db: Database) -> None:
    with db.session() as s:
        uid = default_user_id(s)
        a, b = item(s, 'a', ['밥', '물']).id, item(s, 'b', ['물', '불']).id
        service.record(s, uid, 'ko', '물', E.MARKED_KNOWN, 't')
        assert cache.pending(s, uid) == 2
    assert cache.refresh(db) == 2 and cache.refresh(db) == 0
    with db.session() as s:
        assert cache.cached(s, uid) == stats(s, uid, [a, b])
        assert cache.cached(s, uid, [a]) == {a: stats(s, uid, [a])[a]}
        s.get_one(ContentItem, b).status = 'no_subtitles'  # e.g. the subtitles disappeared: no stats any more
        cache.mark_item(s, b)
    cache.refresh(db)
    with db.session() as s:
        assert set(cache.cached(s, uid)) == {a}


def test_small_batches(db: Database) -> None:
    with db.session() as s:
        uid = default_user_id(s)
        for n in range(5):
            item(s, f'i{n}', ['밥'])
    assert cache.refresh(db, batch=2) == 2
    with db.session() as s:
        assert cache.pending(s, uid) == 3


def test_failed_refresh_gives_the_work_back(db: Database) -> None:
    import pytest

    with db.session() as s:
        uid = default_user_id(s)
        item(s, 'a', ['밥'])
    real = cache.stats

    def broken(*a: object) -> None:
        raise RuntimeError('boom')

    cache.stats = broken  # type: ignore[assignment]
    try:
        with pytest.raises(RuntimeError):
            cache.refresh(db)
    finally:
        cache.stats = real  # type: ignore[assignment]
    with db.session() as s:
        assert cache.pending(s, uid) == 1


def test_a_change_during_refresh_is_not_lost(db: Database) -> None:
    """A knowledge change committed while refresh() computes re-marks the item (and doesn't have to wait)."""
    with db.session() as s:
        uid = default_user_id(s)
        a = item(s, 'a', ['밥'])
        aid = a.id
    real_stats = cache.stats

    def stats_and_meanwhile_learn(session: Session, user: int, ids: list[int]):  # type: ignore[no-untyped-def]
        with db.session() as other:  # another request, committed while refresh() is computing
            service.record(other, uid, 'ko', '밥', E.MARKED_KNOWN, 't')
        return real_stats(session, user, ids)

    cache.stats = stats_and_meanwhile_learn  # type: ignore[assignment]
    try:
        cache.refresh(db)
    finally:
        cache.stats = real_stats  # type: ignore[assignment]
    with db.session() as s:
        assert cache.pending(s, uid) == 1  # re-marked, not lost
    cache.refresh(db)
    with db.session() as s:
        assert cache.cached(s, uid)[aid].words_known == 1


def test_worker_runs_until_clean(db: Database) -> None:
    with db.session() as s:
        uid = default_user_id(s)
        for n in range(3):
            item(s, f'i{n}', ['밥'])
    w = cache.StatsWorker(db, batch=2)
    assert w.run_until_clean() == 3
    with db.session() as s:
        assert cache.pending(s, uid) == 0 and len(cache.cached(s, uid)) == 3
    w.poke()
