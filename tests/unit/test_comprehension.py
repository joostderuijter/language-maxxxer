import pytest
from hypothesis import given
from hypothesis import strategies as st

from lmx.comprehension import analyse, counts, sentences
from lmx.knowledge.events import WordState
from lmx.languages.base import Token

S = WordState


def spans(text: str) -> list[str]:
    return [text[s:e] for s, e in sentences(text)]


@pytest.mark.parametrize(('text', 'want'), [
    ('', []),
    ('   ', []),
    ('안녕하세요.', ['안녕하세요.']),
    ('밥 먹었어? 응, 먹었어! 진짜…  좋아', ['밥 먹었어?', '응, 먹었어!', '진짜…', '좋아']),
    ('첫 줄\n둘째 줄\n\n셋째', ['첫 줄', '둘째 줄', '셋째']),
    ('"정말?" 그래.', ['"정말?"', '그래.']),
    ('3.5% 올랐다. 끝', ['3.5% 올랐다.', '끝']),          # no space after the dot: not a sentence end
    ('すごい。本当？うん', ['すごい。', '本当？', 'うん']),   # full-width punctuation (other languages later)
])  # fmt: skip
def test_sentences(text: str, want: list[str]) -> None:
    assert spans(text) == want


@given(st.text(alphabet=st.sampled_from(list('가나다 ab.?!…\n\t"」')), max_size=80))
def test_sentence_spans_are_ordered_trimmed_and_lose_no_text(text: str) -> None:
    got = sentences(text)
    last = 0
    for s, e in got:
        assert last <= s < e <= len(text)
        assert not text[s].isspace() and not text[e - 1].isspace()
        assert text[last:s].strip() == ''  # only whitespace between sentences
        last = e
    assert text[last:].strip() == ''


def tok(key: str, start: int, weak: bool = False) -> Token:
    return Token(key, start, start + len(key), (key,), 'noun', key, weak)


@pytest.mark.parametrize(('state', 'weak', 'want'), [
    (S.UNKNOWN, False, True), (S.SEEN, False, True), (S.LEARNING, False, True),
    (S.KNOWN, False, False), (S.IGNORED, False, False),
    (S.UNKNOWN, True, False),      # weak + no status: probably a name or filler
    (S.LEARNING, True, True),      # weak but the user has a card for it: counts
    (S.KNOWN, True, False),
])  # fmt: skip
def test_counts(state: WordState, weak: bool, want: bool) -> None:
    assert counts(tok('x', 0, weak), state) is want


def test_unknown_words_per_sentence_counted_once_by_key() -> None:
    text = '배신 배신 했다. 밥 국 먹다.'
    toks = [(tok('배신', 0), S.UNKNOWN), (tok('배신', 3), S.UNKNOWN), (tok('했다', 6), S.KNOWN),
            (tok('밥', 10), S.UNKNOWN), (tok('국', 12), S.SEEN), (tok('먹다', 14), S.KNOWN)]  # fmt: skip
    a, b = analyse(text, toks)
    assert (text[a.start : a.end], a.unknown) == ('배신 배신 했다.', ('배신',))  # 1T
    assert (text[b.start : b.end], b.unknown) == ('밥 국 먹다.', ('밥', '국'))  # 2T


def test_sentence_without_words() -> None:
    assert [s.unknown for s in analyse('ㅋㅋㅋ. 123!', [])] == [(), ()]
