"""The contract EVERY language pack must satisfy (ADR-3). Used by test_contract.py for each registered pack."""

from lmx.languages.base import LanguagePack, Token

POS = {'noun', 'verb', 'adjective', 'adverb', 'other'}


def check_tokens(text: str, tokens: list[Token]) -> None:
    last_start = -1
    for t in tokens:
        assert 0 <= t.start < t.end <= len(text), f'span out of range: {t}'
        assert text[t.start : t.end] == t.surface, f'surface does not match span: {t!r}'
        assert t.surface == t.surface.strip(), f'surface has surrounding space: {t!r}'
        assert t.lemmas, f'no lemmas: {t!r}'
        assert all(lemma and lemma == lemma.strip() for lemma in t.lemmas), f'empty/padded lemma: {t!r}'
        assert len(set(t.lemmas)) == len(t.lemmas), f'duplicate lemmas: {t!r}'
        assert t.pos in POS, f'unknown pos: {t!r}'
        assert t.key, f'empty key: {t!r}'
        assert t.start >= last_start, 'tokens out of order'
        last_start = t.start


def check_pack(pack: LanguagePack, samples: list[str]) -> None:
    assert pack.code and pack.name
    for text in samples:
        a = pack.analyze(text)
        check_tokens(text, a)
        assert pack.analyze(text) == a, 'not deterministic'
    assert pack.analyze_many(samples) == [pack.analyze(t) for t in samples], 'analyze_many differs from analyze'
    assert pack.analyze_many([]) == []
    assert pack.analyze('') == []
