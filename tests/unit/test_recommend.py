import pytest
from hypothesis import given
from hypothesis import strategies as st

from lmx.content.jellyfin import WatchState
from lmx.content.store import ItemStats
from lmx.recommend import Candidate, continuation, coverage_fit, learn_value, recommend


@pytest.mark.parametrize(
    ('c', 'want'),
    [(0.95, 1.0), (0.965, 1.0), (0.98, 1.0), (0.85, 0.0), (0.5, 0.0), (0.90, 0.5), (1.0, 0.5), (0.99, 0.75)],
)
def test_coverage_fit(c: float, want: float) -> None:
    assert coverage_fit(c) == pytest.approx(want)


@given(st.floats(0, 1), st.floats(0, 1))
def test_coverage_fit_bounds_and_harder_is_never_better(a: float, b: float) -> None:
    assert 0.0 <= coverage_fit(a) <= 1.0
    lo, hi = sorted((a, b))
    if hi <= 0.95:
        assert coverage_fit(lo) <= coverage_fit(hi)  # below the sweet spot: more known = better


@pytest.mark.parametrize(
    ('one_new', 'sentences', 'want'), [(0, 0, 0.0), (0, 100, 0.0), (15, 100, 0.5), (30, 100, 1.0), (90, 100, 1.0)]
)
def test_learn_value(one_new: int, sentences: int, want: float) -> None:
    assert learn_value(one_new, sentences) == pytest.approx(want)


def cand(
    n: int, show: str = 'rm', cov: float = 0.96, one_new: int = 30, sentences: int = 100, season: int | None = 1
) -> Candidate:
    known = round(cov * 1000)
    return Candidate(
        n, f'j{show}{n}', show, show.upper(), season, n, f'E{n:02d}', ItemStats(sentences, 1000, known, 10, one_new)
    )


W = WatchState


def test_continuation_half_watched_and_next_episode() -> None:
    eps = [cand(1), cand(2), cand(3), cand(4)]
    watch = {'jrm1': W(True, 0, None), 'jrm2': W(False, 34.2, None)}
    assert continuation(eps, watch) == {2: 'continue watching (34%)', 3: 'next episode of RM'}


def test_continuation_skips_watched_episodes_and_needs_history() -> None:
    eps = [cand(1), cand(2), cand(3)]
    assert continuation(eps, {}) == {}
    assert continuation(eps, {'jrm1': W(True, 0, None), 'jrm2': W(True, 0, None)}) == {3: 'next episode of RM'}
    assert continuation(eps, {'jrm3': W(True, 0, None)}) == {}  # watched the last one: nothing next


def test_continuation_uses_episode_order_not_input_order() -> None:
    eps = [cand(3), cand(1), cand(2)]
    assert continuation(eps, {'jrm1': W(True, 0, None)}) == {2: 'next episode of RM'}


def test_recommend_orders_explains_and_filters() -> None:
    eps = [
        cand(1, cov=0.96),  # watched: out
        cand(2, cov=0.96),  # next episode after a watched one
        cand(3, cov=0.80),  # too hard
        cand(1, show='wm', cov=0.97, one_new=30),
        cand(2, show='wm', cov=0.99, one_new=5),
        cand(3, show='wm', cov=0.0, sentences=0),  # nothing analysable: out
    ]
    eps[5] = Candidate(99, 'x', 'wm', 'WM', 1, 9, 'E09', ItemStats(0, 0, 0, 0, 0))
    recs = recommend(eps, {'jrm1': W(True, 0, None)}, limit=10)
    ids = [(r.candidate.series_key, r.candidate.episode) for r in recs]
    assert ('rm', 1) not in ids and ('wm', 9) not in ids
    assert ids[0] == ('rm', 2)  # sweet spot + learning value + continuation
    assert recs[0].reasons == ('96% known', '30 sentences with one new word', 'next episode of RM')
    assert recs[0].score == pytest.approx(1.0)
    hard = next(r for r in recs if r.candidate.episode == 3 and r.candidate.series_key == 'rm')
    assert hard.reasons[0] == '80% known (a stretch)' and hard.parts['fit'] == 0.0
    assert all(0 <= r.score <= 1 for r in recs)
    assert [r.score for r in recs] == sorted((r.score for r in recs), reverse=True)


def test_at_most_two_per_show_and_limit() -> None:
    eps = [cand(i) for i in range(1, 6)] + [cand(i, show='wm', cov=0.90) for i in range(1, 4)]
    recs = recommend(eps, {}, limit=3)
    assert [r.candidate.series_key for r in recs] == ['rm', 'rm', 'wm']
    assert recommend(eps, {}, limit=10) and len(recommend(eps, {}, limit=10)) == 4
    assert recommend([], {}) == []


def test_stretch_label_agrees_with_the_shown_number() -> None:
    """94.9 % is shown as '95%': calling it a stretch next to that number contradicts itself."""
    almost = Candidate(1, 'j', 's', 'S', 1, 1, 'E', ItemStats(100, 1000, 949, 5, 10))
    assert recommend([almost], {})[0].reasons[0] == '95% known'
    under = Candidate(2, 'k', 's', 'S', 1, 2, 'E', ItemStats(100, 1000, 944, 5, 10))
    assert recommend([under], {})[0].reasons[0] == '94% known (a stretch)'
