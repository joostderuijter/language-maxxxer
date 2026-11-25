import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from lmx import languages
from lmx.languages.base import LanguagePack

from .contract import check_dictionary, check_pack, check_tokens

SAMPLES = {
    'ko': [
        '무난하고 순차적으로 이렇게 했어요.',
        '맨손으로 깨끗하게 청소했다',
        '“그래서?” 배신당했어…',
        '   ',
        'Running Man 2026!',
        '1234 ㅋㅋㅋ ㅠㅠ',
        '안녕\n하세요\t반가워요',
    ],
}


@pytest.fixture(params=sorted(languages.available()))
def pack(request: pytest.FixtureRequest) -> LanguagePack:
    return languages.get(request.param)


def test_every_language_has_samples() -> None:
    assert set(SAMPLES) == set(languages.available()) == set(KNOWN_WORD)


KNOWN_WORD = {'ko': '밥'}


def test_contract(pack: LanguagePack) -> None:
    check_pack(pack, SAMPLES[pack.code])


def test_dictionary_contract(pack: LanguagePack) -> None:
    check_dictionary(pack, KNOWN_WORD[pack.code])


def test_registry() -> None:
    assert languages.available()['ko'] == 'Korean'
    assert languages.get('ko') is languages.get('ko')  # cached
    with pytest.raises(KeyError):
        languages.get('xx')


# random text: Hangul syllables + jamo + latin + punctuation + whitespace
text = st.text(
    alphabet=st.one_of(
        st.characters(min_codepoint=0xAC00, max_codepoint=0xD7A3),
        st.characters(min_codepoint=0x3131, max_codepoint=0x3163),
        st.sampled_from(list('abc XYZ 019 .,!?…~"\'()「」\n\t')),
    ),
    max_size=60,
)


@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(text)
def test_korean_never_breaks_the_contract(s: str) -> None:
    check_tokens(s, languages.get('ko').analyze(s))
