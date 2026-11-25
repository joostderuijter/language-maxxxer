"""Dictionary types shared by all language packs."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Sense:
    """One meaning of a headword.

    gloss: short translation ('eye'); definition: translated definition sentence; native: definition in the language
    itself. level: the dictionary's difficulty label normalised to beginner | intermediate | advanced | '' (unknown).
    """

    headword: str
    pos: str  # noun | verb | adjective | adverb | other (same vocabulary as Token.pos)
    gloss: str
    definition: str
    native: str = ''
    level: str = ''
    origin: str = ''  # e.g. Hanja for Sino-Korean words
    pronunciation: str = ''
    examples: tuple[str, ...] = field(default=())


@dataclass(frozen=True)
class Idiom:
    """A fixed expression or proverb that contains a headword."""

    text: str
    kind: str  # idiom | proverb
    gloss: str
    definition: str
    native: str = ''
