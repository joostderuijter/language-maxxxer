import pytest

from lmx.knowledge.events import EventKind
from lmx.knowledge.importer import parse

E = EventKind


def test_names_and_numbers() -> None:
    items, skipped = parse('먹다,2\n가다,known\n배신,1\n사과,0\n광수,3\n학교,learning\n물,seen\n집,ignored\n')
    assert items == [
        ('먹다', E.MARKED_KNOWN),
        ('가다', E.MARKED_KNOWN),
        ('배신', E.SEEN),
        ('사과', E.CARD_ADDED),
        ('광수', E.IGNORED),
        ('학교', E.CARD_ADDED),
        ('물', E.SEEN),
        ('집', E.IGNORED),
    ]
    assert skipped == 0


def test_header_bom_blank_lines_and_spaces() -> None:
    items, skipped = parse('﻿lemma,state\n\n  먹다 , Known \n,2\n')
    assert items == [('먹다', E.MARKED_KNOWN)] and skipped == 0


def test_unknown_state_is_counted_but_not_imported() -> None:
    assert parse('먹다,unknown\n') == ([], 0)


@pytest.mark.parametrize('bad', ['먹다,7', '먹다', '먹다,kinda'])
def test_bad_state_is_skipped(bad: str) -> None:
    assert parse(bad) == ([], 1)


def test_quoted_lemma_with_comma() -> None:
    assert parse('"a, b",known') == ([('a, b', E.MARKED_KNOWN)], 0)
