"""The knowledge reducer: explicit cases + properties that must hold for ANY sequence of events."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from lmx.knowledge.events import KNOWN_AT, QUIZ_STEP, START, EventKind, Snapshot, WordState, apply, replay

E, S = EventKind, WordState


@pytest.mark.parametrize(
    ('events', 'state'),
    [
        ([], S.UNKNOWN),
        ([E.SEEN], S.SEEN),
        ([E.SEEN, E.CARD_ADDED], S.LEARNING),
        ([E.CARD_ADDED, E.MATURE], S.KNOWN),
        ([E.MARKED_KNOWN], S.KNOWN),
        ([E.MARKED_KNOWN, E.LAPSED], S.LEARNING),  # forgotten in Anki: back to learning
        ([E.MARKED_KNOWN, E.QUIZ_WRONG], S.LEARNING),
        ([E.MARKED_KNOWN, E.CARD_ADDED], S.KNOWN),  # a new card doesn't make a known word "learning"
        ([E.MARKED_KNOWN, E.SEEN], S.KNOWN),
        ([E.IGNORED, E.MATURE], S.IGNORED),  # ignored stays ignored...
        ([E.IGNORED, E.QUIZ_RIGHT, E.QUIZ_WRONG, E.LAPSED, E.CARD_ADDED, E.SEEN], S.IGNORED),
        ([E.IGNORED, E.MARKED_KNOWN], S.KNOWN),  # ...until the user says otherwise
        ([E.IGNORED, E.MARKED_UNKNOWN], S.UNKNOWN),
        ([E.MARKED_KNOWN, E.MARKED_UNKNOWN], S.UNKNOWN),
        ([E.QUIZ_RIGHT], S.SEEN),  # one right answer isn't knowing a word
        ([E.QUIZ_RIGHT] * 6, S.KNOWN),  # enough right answers is
    ],
)
def test_states(events: list[EventKind], state: WordState) -> None:
    assert replay(events).state == state


def test_quiz_steps_and_threshold() -> None:
    s = apply(None, E.QUIZ_RIGHT)
    assert s.confidence == pytest.approx(QUIZ_STEP)
    n = 0
    s = START
    while s.state != S.KNOWN:
        s = apply(s, E.QUIZ_RIGHT)
        n += 1
    assert s.confidence >= KNOWN_AT and n == 6


def test_mature_keeps_higher_confidence() -> None:
    assert apply(Snapshot(S.KNOWN, 0.99), E.MATURE).confidence == 0.99
    assert apply(Snapshot(S.LEARNING, 0.5), E.MATURE).confidence == 0.95


def test_wrong_answer_lowers_confidence_but_not_below_zero() -> None:
    s = apply(apply(None, E.QUIZ_RIGHT), E.QUIZ_WRONG)
    assert s.confidence == 0.0 and s.state == S.SEEN
    assert apply(s, E.QUIZ_WRONG).confidence == 0.0


events = st.lists(st.sampled_from(list(EventKind)), max_size=40)


@given(events)
def test_confidence_always_between_0_and_1(kinds: list[EventKind]) -> None:
    s: Snapshot | None = None
    for k in kinds:
        s = apply(s, k)
        assert 0.0 <= s.confidence <= 1.0


@given(events)
def test_replay_equals_step_by_step(kinds: list[EventKind]) -> None:
    s: Snapshot | None = None
    for k in kinds:
        s = apply(s, k)
    assert replay(kinds) == (s or START)


@given(events, st.sampled_from([E.MARKED_KNOWN, E.MARKED_UNKNOWN, E.IGNORED]))
def test_explicit_user_choice_always_wins(kinds: list[EventKind], last: EventKind) -> None:
    want = {E.MARKED_KNOWN: S.KNOWN, E.MARKED_UNKNOWN: S.UNKNOWN, E.IGNORED: S.IGNORED}[last]
    assert replay([*kinds, last]).state == want


@given(events)
def test_ignored_only_left_by_user_choice(kinds: list[EventKind]) -> None:
    s = replay([E.IGNORED, *kinds])
    if not ({E.MARKED_KNOWN, E.MARKED_UNKNOWN} & set(kinds)):
        assert s.state == S.IGNORED
