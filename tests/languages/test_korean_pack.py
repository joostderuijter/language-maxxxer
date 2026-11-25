"""Korean-specific behaviour that depends on the dictionary."""

from pathlib import Path

from lmx.languages.korean.pack import KoreanPack


def weak(pack: KoreanPack, text: str) -> dict[str, bool]:
    return {t.surface: t.weak for t in pack.analyze(text)}


def test_one_syllable_noun_is_weak_only_when_the_dictionary_lacks_it(test_dictionaries: Path) -> None:
    with_dict = KoreanPack(test_dictionaries / 'ko-krdict.sqlite')
    without = KoreanPack(None)
    assert weak(with_dict, '밥을 먹었다')['밥을'] is False
    assert weak(without, '밥을 먹었다')['밥을'] is True  # no dictionary: can't tell a word from a mis-split
    assert weak(with_dict, '물을 마셨다')['물을'] is True  # 물 isn't in the fixture dictionary


def test_lookup_idioms_and_info(test_dictionaries: Path) -> None:
    pack = KoreanPack(test_dictionaries / 'ko-krdict.sqlite')
    assert [s.gloss for s in pack.lookup('눈')] == ['eye', 'snow']
    assert [i.text for i in pack.idioms('눈')] == ['눈이 높다', '눈 감으면 코 베어 갈 세상']
    assert pack.dictionary_info()['source'] == 'test fixture'


def test_no_dictionary_still_analyzes() -> None:
    pack = KoreanPack(None)
    assert pack.lookup('밥') == [] and pack.dictionary_info() == {}
    assert [t.lemmas for t in pack.analyze('먹었다')] == [('먹다',)]
