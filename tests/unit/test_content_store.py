"""Content analysis storage + live statistics. The SQL must agree with lmx.comprehension (property test)."""

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lmx.comprehension import counts
from lmx.content.store import Line, NewWord, new_words, save_analysis, stats
from lmx.db import Database
from lmx.knowledge import service
from lmx.knowledge.events import EventKind, WordState
from lmx.languages.base import Token
from lmx.models import ContentItem, ContentOccurrence, ContentWord, ContentWordLemma, User
from lmx.users import default_user_id

E = EventKind


def tok(key: str, lemmas: tuple[str, ...] | None = None, weak: bool = False) -> Token:
    return Token(key, 0, len(key), lemmas or (key,), 'noun', key, weak)


def item(s: Session, name: str = 'E01', language: str = 'ko') -> ContentItem:
    it = ContentItem(language=language, source='folder', external_id=name, series='Show', title=name, path=f'/{name}')
    s.add(it)
    s.flush()
    return it


def lines(n: int) -> list[Line]:
    return [Line(i * 1000, i * 1000 + 900, f'line {i}') for i in range(n)]


def test_save_aggregates_words(session: Session) -> None:
    it = item(session)
    save_analysis(
        session,
        it,
        lines(3),
        [[tok('배신', ('배신하다', '배신')), tok('밥')], [tok('배신'), tok('거', weak=True)], [tok('거', weak=False)]],
        'ko-1',
    )
    w = {x.key: x for x in session.scalars(select(ContentWord))}
    assert (w['배신'].count, w['배신'].first_idx, w['밥'].count, w['거'].count) == (2, 0, 1, 2)
    assert w['거'].weak is False  # weak only if EVERY occurrence was weak
    lem = (
        session.execute(
            select(ContentWordLemma.lemma)
            .where(ContentWordLemma.word_id == w['배신'].id)
            .order_by(ContentWordLemma.ord)
        )
        .scalars()
        .all()
    )
    assert lem == ['배신하다', '배신']  # union of candidates, first-seen order kept
    assert session.scalar(select(func.count()).select_from(ContentOccurrence)) == 5
    assert (it.status, it.analyzer) == ('analyzed', 'ko-1')


def test_save_replaces_previous_analysis(session: Session) -> None:
    it = item(session)
    save_analysis(session, it, lines(2), [[tok('a')], [tok('b')]], 'v1')
    save_analysis(session, it, lines(1), [[tok('c')]], 'v2')
    assert [w.key for w in session.scalars(select(ContentWord))] == ['c']
    assert stats(session, default_user_id(session), [it.id])[it.id].sentences == 1


def test_save_needs_one_token_list_per_line(session: Session) -> None:
    import pytest

    with pytest.raises(ValueError):
        save_analysis(session, item(session), lines(2), [[]], 'v')


def test_stats_and_new_words(session: Session, uid: int) -> None:
    it = item(session)
    save_analysis(
        session,
        it,
        lines(4),
        [
            [tok('밥'), tok('먹다')],  # 1 new (밥): 1T
            [tok('밥'), tok('소나기'), tok('먹다')],  # 2 new
            [tok('먹다'), tok('광수', weak=True)],  # 0 new (weak name without status doesn't count)
            [tok('무난', ('무난하다', '무난'))],  # known via its 2nd candidate
        ],
        'v',
    )
    service.record_many(
        session, uid, 'ko', [('먹다', E.MARKED_KNOWN), ('무난', E.MARKED_KNOWN), ('소나기', E.CARD_ADDED)], 'test'
    )
    st_ = stats(session, uid, [it.id])[it.id]
    assert (st_.sentences, st_.words_total, st_.words_known, st_.new_words, st_.one_new) == (4, 7, 4, 2, 1)
    assert round(st_.coverage, 3) == round(4 / 7, 3)
    assert new_words(session, uid, it.id) == [
        NewWord('밥', ('밥',), 2, 0, 'unknown'),
        NewWord('소나기', ('소나기',), 1, 1, 'learning'),
    ]
    assert new_words(session, uid, it.id, limit=1)[0].key == '밥'


def test_stats_are_per_user_and_per_language(session: Session, uid: int) -> None:
    ko, ja = item(session, 'ko'), item(session, 'ja', language='ja')
    for it in (ko, ja):
        save_analysis(session, it, lines(1), [[tok('밥')]], 'v')
    service.record(session, uid, 'ko', '밥', E.MARKED_KNOWN, 'test')
    other = User(name='other')
    session.add(other)
    session.flush()
    s = stats(session, uid, [ko.id, ja.id])
    assert (s[ko.id].words_known, s[ja.id].words_known) == (1, 0)  # Korean knowledge doesn't apply to Japanese
    assert stats(session, other.id, [ko.id])[ko.id].words_known == 0


def test_stats_for_unanalysed_or_no_items(session: Session, uid: int) -> None:
    it = item(session)
    assert stats(session, uid, [it.id])[it.id].coverage == 0.0
    assert stats(session, uid, []) == {}
    assert new_words(session, uid, it.id) == []


# --- property: the SQL agrees with the comprehension rules for any content and any knowledge -----------------------
VOCAB = {
    f'w{i}': (tuple(f'l{i}{c}' for c in 'ab'[: 1 + i % 2]), i % 5 == 0) for i in range(12)
}  # key -> (lemmas, weak)
STATES = [None, E.MARKED_KNOWN, E.IGNORED, E.SEEN, E.CARD_ADDED, E.MARKED_UNKNOWN]
RANK = {WordState.IGNORED: 5, WordState.KNOWN: 4, WordState.LEARNING: 3, WordState.SEEN: 2, WordState.UNKNOWN: 1}


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    content=st.lists(st.lists(st.sampled_from(sorted(VOCAB)), max_size=6), min_size=1, max_size=8),
    knowledge=st.dictionaries(
        st.sampled_from([lem for ls, _ in VOCAB.values() for lem in ls]), st.sampled_from(STATES[1:]), max_size=10
    ),
)
def test_sql_matches_comprehension_rules(
    db: Database, content: list[list[str]], knowledge: dict[str, EventKind]
) -> None:
    with db.session() as s:
        default_user_id(s)  # the default user exists; the property test uses its own user
        it = item(s, f'p{s.scalar(select(func.count()).select_from(ContentItem))}')
        toks = [[tok(k, VOCAB[k][0], VOCAB[k][1]) for k in ln] for ln in content]
        save_analysis(s, it, lines(len(content)), toks, 'v')
        user = User(name=f'u{it.id}')
        s.add(user)
        s.flush()
        for lemma, kind in knowledge.items():
            service.record(s, user.id, 'ko', lemma, kind, 'test')

        def state(t: Token) -> WordState:
            states = [service.state_of(s, user.id, 'ko', lem).state for lem in t.lemmas]
            return max(states, key=lambda x: RANK[x])

        total = known = 0
        new: set[str] = set()
        one_new = 0
        for ln in toks:
            missing: set[str] = set()
            for t in ln:
                st_ = state(t)
                is_known = st_ in (WordState.KNOWN, WordState.IGNORED)
                if is_known or counts(t, st_):
                    total += 1
                    known += is_known
                if counts(t, st_):
                    missing.add(t.key)
            new |= missing
            one_new += len(missing) == 1
        got = stats(s, user.id, [it.id])[it.id]
        assert (got.words_total, got.words_known, got.new_words, got.one_new) == (total, known, len(new), one_new)
