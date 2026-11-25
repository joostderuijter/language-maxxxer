"""The knowledge reducer: (current state, event) -> new state. Pure, so it's easy to test and to replay.

States: unknown < seen < learning < known, plus ignored (names, noise: never counted, never quizzed).
Confidence (0..1) says how sure we are about the state; quizzes and Anki move it.
"""

from dataclasses import dataclass
from enum import StrEnum


class WordState(StrEnum):
    UNKNOWN = 'unknown'
    SEEN = 'seen'  # encountered / looked up, not studied
    LEARNING = 'learning'  # has a card that isn't mature yet
    KNOWN = 'known'
    IGNORED = 'ignored'


class EventKind(StrEnum):
    MARKED_KNOWN = 'marked_known'  # user says so, or imported as known
    MARKED_UNKNOWN = 'marked_unknown'  # user resets a word
    IGNORED = 'ignored'  # name, noise, not worth learning
    SEEN = 'seen'  # looked up / encountered
    CARD_ADDED = 'card_added'  # a flashcard exists
    MATURE = 'mature'  # Anki interval >= 21 days
    LAPSED = 'lapsed'  # forgotten in Anki
    QUIZ_RIGHT = 'quiz_right'
    QUIZ_WRONG = 'quiz_wrong'


@dataclass(frozen=True)
class Snapshot:
    state: WordState
    confidence: float


START = Snapshot(WordState.UNKNOWN, 0.0)
QUIZ_STEP = 0.15
KNOWN_AT = 0.8  # a quiz-driven word becomes known at this confidence


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def apply(current: Snapshot | None, kind: EventKind) -> Snapshot:
    s = current or START
    match kind:
        case EventKind.MARKED_KNOWN:
            return Snapshot(WordState.KNOWN, max(s.confidence, 0.9))
        case EventKind.MARKED_UNKNOWN:
            return Snapshot(WordState.UNKNOWN, 0.0)
        case EventKind.IGNORED:
            return Snapshot(WordState.IGNORED, 1.0)
        case EventKind.MATURE:
            if s.state == WordState.IGNORED:
                return s
            return Snapshot(WordState.KNOWN, max(s.confidence, 0.95))
        case EventKind.CARD_ADDED:
            if s.state in (WordState.KNOWN, WordState.IGNORED, WordState.LEARNING):
                return s
            return Snapshot(WordState.LEARNING, 0.5)
        case EventKind.SEEN:
            if s.state == WordState.UNKNOWN:
                return Snapshot(WordState.SEEN, 0.1)
            return s
        case EventKind.LAPSED | EventKind.QUIZ_WRONG:
            if s.state == WordState.IGNORED:
                return s
            if s.state == WordState.KNOWN:
                return Snapshot(WordState.LEARNING, 0.4)
            return Snapshot(s.state, _clamp(s.confidence - QUIZ_STEP))
        case EventKind.QUIZ_RIGHT:
            if s.state == WordState.IGNORED:
                return s
            conf = _clamp(s.confidence + QUIZ_STEP)
            if s.state == WordState.KNOWN or conf >= KNOWN_AT:
                return Snapshot(WordState.KNOWN, conf)
            return Snapshot(WordState.SEEN if s.state == WordState.UNKNOWN else s.state, conf)


def replay(kinds: list[EventKind]) -> Snapshot:
    s: Snapshot | None = None
    for k in kinds:
        s = apply(s, k)
    return s or START
