"""Storing an item's analysis, and the live per-user statistics computed from it.

The rules are the same as lmx.comprehension (the analysis box): a word counts as known if the user knows or ignores
ANY of its candidate lemmas; a weak word the user has no status for doesn't count at all; the rest is "not known".
Here a sentence is a subtitle line (one cue), as kr-miner did.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from ..languages.base import Token
from ..models import ContentItem, ContentOccurrence, ContentSentence, ContentWord, ContentWordLemma, now


@dataclass(frozen=True)
class Line:
    start_ms: int
    end_ms: int
    text: str


@dataclass(frozen=True)
class ItemStats:
    sentences: int
    words_total: int  # word occurrences that count (tokens)
    words_known: int
    new_words: int  # distinct words not known yet
    one_new: int  # sentences with exactly one word not known yet (1T)

    @property
    def coverage(self) -> float:
        return self.words_known / self.words_total if self.words_total else 0.0


@dataclass(frozen=True)
class NewWord:
    key: str
    lemmas: tuple[str, ...]
    count: int
    first_idx: int
    state: str  # unknown | seen | learning


def save_analysis(
    session: Session, item: ContentItem, lines: Sequence[Line], tokens: Sequence[Sequence[Token]], analyzer: str
) -> None:
    """Replace the item's analysis. tokens[i] are the words of lines[i]."""
    if len(lines) != len(tokens):
        raise ValueError('one token list per line')
    session.execute(delete(ContentSentence).where(ContentSentence.item_id == item.id))
    session.execute(delete(ContentWord).where(ContentWord.item_id == item.id))
    sentences = [
        ContentSentence(item_id=item.id, idx=i, start_ms=ln.start_ms, end_ms=ln.end_ms, text=ln.text)
        for i, ln in enumerate(lines)
    ]
    session.add_all(sentences)
    words: dict[str, ContentWord] = {}
    lemmas: dict[str, dict[str, None]] = {}
    in_sentence: list[set[str]] = []
    for i, toks in enumerate(tokens):
        keys: set[str] = set()
        for t in toks:
            w = words.get(t.key)
            if w is None:
                w = words[t.key] = ContentWord(item_id=item.id, key=t.key, count=0, weak=True, first_idx=i)
            w.count += 1
            w.weak = w.weak and t.weak
            lemmas.setdefault(t.key, {}).update(dict.fromkeys(t.lemmas))
            keys.add(t.key)
        in_sentence.append(keys)
    session.add_all(words.values())
    session.flush()
    session.add_all(
        ContentWordLemma(word_id=words[k].id, lemma=lemma, ord=n)
        for k, ls in lemmas.items()
        for n, lemma in enumerate(ls)
    )
    session.add_all(
        ContentOccurrence(sentence_id=sentences[i].id, word_id=words[k].id)
        for i, keys in enumerate(in_sentence)
        for k in keys
    )
    item.status, item.analyzer, item.analyzed_at, item.detail = 'analyzed', analyzer, now(), None
    session.flush()


# Best state per content word for one user: rank 5 ignored, 4 known, 3 learning, 2 seen, 1 unknown / no status.
# "counts" = known, or not known but not (weak without a status) -- see the module docstring.
_WORD_STATE = """
WITH ws AS (
  SELECT w.id AS word_id, w.item_id, w.count, w.weak, w.key, w.first_idx,
         MAX(CASE k.state WHEN 'ignored' THEN 5 WHEN 'known' THEN 4 WHEN 'learning' THEN 3 WHEN 'seen' THEN 2
                          ELSE 1 END) AS rank
  FROM content_words w
  JOIN content_items i ON i.id = w.item_id
  JOIN content_word_lemmas l ON l.word_id = w.id
  LEFT JOIN word_knowledge k ON k.lemma = l.lemma AND k.user_id = :uid AND k.language = i.language
  WHERE w.item_id IN ({ids})
  GROUP BY w.id
), wc AS (
  SELECT *, rank >= 4 AS known, (rank >= 2 OR NOT weak) AS counts FROM ws
)
"""


def stats(session: Session, user_id: int, item_ids: Sequence[int]) -> dict[int, ItemStats]:
    """Live statistics per item for this user (items without an analysis get zeros)."""
    if not item_ids:
        return {}
    ids = ','.join(str(int(i)) for i in item_ids)
    words = session.execute(
        text(
            _WORD_STATE.format(ids=ids)
            + """SELECT item_id,
                       SUM(CASE WHEN counts THEN count ELSE 0 END),
                       SUM(CASE WHEN counts AND known THEN count ELSE 0 END),
                       SUM(CASE WHEN counts AND NOT known THEN 1 ELSE 0 END)
                FROM wc GROUP BY item_id"""
        ),
        {'uid': user_id},
    ).all()
    one_new = session.execute(
        text(
            _WORD_STATE.format(ids=ids)
            + """SELECT s.item_id, COUNT(*) FROM (
                   SELECT s.id, s.item_id FROM content_sentences s
                   JOIN content_occurrences o ON o.sentence_id = s.id
                   JOIN wc ON wc.word_id = o.word_id
                   WHERE wc.counts AND NOT wc.known
                   GROUP BY s.id HAVING COUNT(*) = 1) s
                 GROUP BY s.item_id"""
        ),
        {'uid': user_id},
    ).all()
    n_sent = session.execute(
        text(f'SELECT item_id, COUNT(*) FROM content_sentences WHERE item_id IN ({ids}) GROUP BY item_id')
    ).all()
    sent = {i: n for i, n in n_sent}
    t1 = {i: n for i, n in one_new}
    w = {i: (tot or 0, kn or 0, new or 0) for i, tot, kn, new in words}
    return {
        i: ItemStats(
            sentences=sent.get(i, 0),
            words_total=w.get(i, (0, 0, 0))[0],
            words_known=w.get(i, (0, 0, 0))[1],
            new_words=w.get(i, (0, 0, 0))[2],
            one_new=t1.get(i, 0),
        )
        for i in item_ids
    }


def new_words(session: Session, user_id: int, item_id: int, limit: int = 50) -> list[NewWord]:
    """The item's words the user doesn't know yet, most frequent first (learn these first for the biggest gain)."""
    rows = session.execute(
        text(
            _WORD_STATE.format(ids=int(item_id))
            + """SELECT wc.word_id, wc.key, wc.count, wc.first_idx, wc.rank FROM wc
                 WHERE wc.counts AND NOT wc.known ORDER BY wc.count DESC, wc.first_idx LIMIT :limit"""
        ),
        {'uid': user_id, 'limit': limit},
    ).all()
    lemmas: dict[int, list[str]] = {}
    if rows:
        for wid, lemma in session.execute(
            select(ContentWordLemma.word_id, ContentWordLemma.lemma)
            .where(ContentWordLemma.word_id.in_([r[0] for r in rows]))
            .order_by(ContentWordLemma.word_id, ContentWordLemma.ord)
        ):
            lemmas.setdefault(wid, []).append(lemma)
    state = {3: 'learning', 2: 'seen', 1: 'unknown'}
    return [
        NewWord(key=k, lemmas=tuple(lemmas.get(wid, [])), count=c, first_idx=f, state=state[r])
        for wid, k, c, f, r in rows
    ]
