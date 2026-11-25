"""The language pack interface."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Token:
    """One learnable word in a text.

    surface: the text as written (text[start:end]), e.g. 무난하고
    lemmas: candidate dictionary forms, most specific first (무난하다, 무난). The word counts as known if ANY is.
    pos: coarse part of speech: noun | verb | adjective | adverb | other
    key: groups forms that should share one flashcard (배신 / 배신하다 -> 배신)
    weak: only counts if the user's word list has an opinion on it (names, interjections, likely mis-splits)
    """

    surface: str
    start: int
    end: int
    lemmas: tuple[str, ...]
    pos: str
    key: str
    weak: bool = False
    tags: tuple[str, ...] = field(default=())  # pack-specific detail (e.g. Kiwi tags), for debugging


class LanguagePack(Protocol):
    code: str  # ISO 639-1, e.g. 'ko'
    name: str  # e.g. 'Korean'

    def analyze(self, text: str) -> list[Token]:
        """Learnable words in `text`, in order. Must be deterministic."""
        ...

    def analyze_many(self, texts: list[str]) -> list[list[Token]]:
        """Same as analyze() for many texts (packs may batch)."""
        ...
