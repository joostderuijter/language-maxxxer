"""The KRDict parser, builder and lookups (against the hand-written fixture rows)."""

from pathlib import Path

import pytest

from lmx.languages.dictionary import Idiom
from lmx.languages.korean import krdict

from ..conftest import fixture_rows


@pytest.fixture(scope='module')
def kd(tmp_path_factory: pytest.TempPathFactory) -> krdict.KrDict:
    path = tmp_path_factory.mktemp('kd') / 'k.sqlite'
    krdict.build(fixture_rows(), path, {'source': 'test', 'revision': 'r1'})
    return krdict.KrDict(path)


def test_fields_split_only_on_known_keys() -> None:
    f = krdict.fields('표제어: 밥, 구분: 단어, 뜻풀이: 쌀, 보리 등의 곡식, 영어 대역어: rice')
    assert f == {'표제어': '밥', '구분': '단어', '뜻풀이': '쌀, 보리 등의 곡식', '영어 대역어': 'rice'}


def test_longest_key_wins() -> None:
    f = krdict.fields('표제어: 밥, 영어 대역어: rice, 영어 대역어 뜻풀이: Cooked grain, really.')
    assert f['영어 대역어'] == 'rice' and f['영어 대역어 뜻풀이'] == 'Cooked grain, really.'


def test_unknown_key_stays_in_the_value() -> None:
    assert krdict.fields('어휘 등급: 고급, 검색용 이형태: 무난타')['어휘 등급'] == '고급, 검색용 이형태: 무난타'


@pytest.mark.parametrize(('raw', 'want'), [('초급', 'beginner'), ('중급, 검색용 이형태: 복스', 'intermediate'),
                                           ('고급', 'advanced'), ('없음', ''), ('', '')])  # fmt: skip
def test_level(raw: str, want: str) -> None:
    assert krdict.level(raw) == want


def test_build_counts_and_meta(kd: krdict.KrDict) -> None:
    meta = kd.meta()
    assert meta['source'] == 'test' and meta['revision'] == 'r1'
    assert (meta['senses'], meta['idioms']) == ('10', '2')  # 12 rows: 2 idioms + 10 senses (incl. grammar, phrase)


def test_homographs_in_order_with_all_fields(kd: krdict.KrDict) -> None:
    eye, snow = kd.senses('눈')
    assert (eye.gloss, snow.gloss) == ('eye', 'snow')
    assert eye.pos == 'noun' and eye.level == 'beginner' and eye.pronunciation == '눈'
    assert eye.definition.startswith('The sensory organ') and eye.native.startswith('사람이나 동물의')
    assert eye.examples == ('지수는 눈이 크다.', '눈을 감아 봐.')  # only <문장> examples, not <구>
    assert snow.native.startswith('기온이 영도 이하로 내려갈 때, 공기 중의')  # comma inside a value


def test_hanja_origin_and_level(kd: krdict.KrDict) -> None:
    (s,) = kd.senses('청소하다')
    assert (s.origin, s.pos, s.gloss) == ('淸掃하다', 'verb', 'clean')
    (m,) = kd.senses('무난하다')
    assert (m.level, m.pos) == ('advanced', 'adjective')


def test_grammar_and_phrases_are_not_word_senses(kd: krdict.KrDict) -> None:
    assert kd.senses('-아서') == [] and kd.senses('눈에 띄다') == []
    assert not kd.has('-아서') and kd.has('밥')


def test_idioms(kd: krdict.KrDict) -> None:
    assert kd.idioms('눈') == [
        Idiom('눈이 높다', 'idiom', 'have high standards', 'To have a habit of looking only for good things.',
              '정도 이상의 좋은 것만 찾는 버릇이 있다.'),
        Idiom('눈 감으면 코 베어 갈 세상', 'proverb', '', 'The world is a harsh place.', '세상인심이 고약하다.'),
    ]  # fmt: skip
    assert kd.idioms('밥') == []


def test_unknown_word(kd: krdict.KrDict) -> None:
    assert kd.senses('없는말') == [] and kd.idioms('없는말') == [] and not kd.has('없는말')


def test_missing_dictionary_is_empty_not_an_error(tmp_path: Path) -> None:
    for kd in (krdict.KrDict(tmp_path / 'nope.sqlite'), krdict.KrDict(None)):
        assert not kd.available
        assert kd.senses('밥') == [] and kd.idioms('눈') == [] and kd.meta() == {} and not kd.has('밥')


def test_rows_without_headword_or_bad_idiom_are_skipped(tmp_path: Path) -> None:
    rows = ['구분: 단어, 뜻풀이: x', '표제어: 눈, 구분: 부표제어, 부표제어: 괄호 없음', '표제어: 물, 구분: 단어']
    n = krdict.build(rows, tmp_path / 'k.sqlite')
    assert n == (1, 0)


def test_rebuild_replaces_the_file(tmp_path: Path) -> None:
    p = tmp_path / 'k.sqlite'
    krdict.build(fixture_rows(), p)
    krdict.build(['표제어: 물, 구분: 단어, 영어 대역어: water'], p)
    assert krdict.KrDict(p).meta()['senses'] == '1'
