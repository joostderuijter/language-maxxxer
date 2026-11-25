"""How much of a text the user can follow: sentences and the not-yet-known words in each.

A "1T" sentence has exactly one word the user doesn't know yet: the best sentences to learn a word from (i+1).
Not known = unknown, seen or learning (a word with an immature card still counts). A weak word (name, filler, likely
mis-split) only counts when the user has a status for it. The same word twice, or two forms sharing a key
(배신 / 배신하다), count once.
"""

import re
from dataclasses import dataclass

from .knowledge.events import WordState
from .languages.base import Token

NOT_KNOWN = {WordState.UNKNOWN, WordState.SEEN, WordState.LEARNING}
CLOSERS = '"\'”’」』)]'
# a sentence ends after . ? ! … plus any closing quotes/brackets, followed by whitespace; after full-width 。？！
# (Chinese/Japanese write no space after them) with or without whitespace; and at every line break
SENTENCE_END = re.compile(rf'(?P<end>[.?!…][{re.escape(CLOSERS)}]*)\s+|(?P<cjk>[。？！][{re.escape(CLOSERS)}]*)\s*|\n+')


@dataclass(frozen=True)
class Sentence:
    start: int
    end: int
    unknown: tuple[str, ...]  # keys of the not-known words, in order of first appearance


def sentences(text: str) -> list[tuple[int, int]]:
    """Sentence spans (start, end), surrounding whitespace trimmed, empty ones dropped."""
    out: list[tuple[int, int]] = []
    pos = 0
    for m in [*SENTENCE_END.finditer(text), None]:
        if m is None:
            end = len(text)
        elif m.group('end') or m.group('cjk'):
            end = m.end('end') if m.group('end') else m.end('cjk')  # the punctuation + closers stay in the sentence
        else:
            end = m.start()
        s, e = pos, end
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if s < e:
            out.append((s, e))
        pos = m.end() if m else len(text)
    return out


def counts(token: Token, state: WordState) -> bool:
    """Does this word count as not known?"""
    if state not in NOT_KNOWN:
        return False
    return not (token.weak and state == WordState.UNKNOWN)


def analyse(text: str, tokens: list[tuple[Token, WordState]]) -> list[Sentence]:
    out: list[Sentence] = []
    for s, e in sentences(text):
        keys: dict[str, None] = {}
        for t, state in tokens:
            if s <= t.start < e and counts(t, state):
                keys.setdefault(t.key)
        out.append(Sentence(s, e, tuple(keys)))
    return out
