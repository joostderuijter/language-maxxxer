"""Golden tests: curated sentences -> expected words. Catches regressions from Kiwi upgrades or rule changes."""

from pathlib import Path
from typing import Any

import pytest
import yaml

from lmx import languages

GOLDEN = Path(__file__).parent / 'golden'


def load(code: str) -> dict[str, Any]:
    return yaml.safe_load((GOLDEN / f'{code}.yaml').read_text(encoding='utf-8'))


def actual(code: str, text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for t in languages.get(code).analyze(text):
        lemmas = list(t.lemmas)
        if t.weak:
            lemmas[-1] += ' (weak)'
        out.setdefault(t.surface, []).extend(lemmas)
    return out


def params(code: str, section: str) -> list[Any]:
    return [
        pytest.param(
            c['text'],
            c['words'],
            id=c['text'],
            marks=[pytest.mark.xfail(reason=c['reason'], strict=True)] if section == 'known_issues' else [],
        )
        for c in load(code)[section]
    ]


@pytest.mark.parametrize(('text', 'words'), params('ko', 'cases') + params('ko', 'known_issues'))
def test_korean(text: str, words: dict[str, list[str]]) -> None:
    assert actual('ko', text) == words
