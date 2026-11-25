""" "Next up": which analysed episodes to watch next (ADR-13). A transparent formula first; later it can learn from
behaviour (finished vs abandoned, lookups per minute).

score = 0.5 * coverage fit + 0.3 * learning value + 0.2 * continuation
- coverage fit: 1 inside 95-98 % known; falls to 0 at 85 %; above 98 % it falls slowly (to 0.5 at 100 %): too easy is
  less bad than too hard
- learning value: share of sentences with exactly one new word (1T), 30 % or more counts as full
- continuation: the episode you're halfway through, or the next one after the last episode you watched of a show
Watched episodes are left out; at most MAX_PER_SHOW per show, so the list isn't one show only.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from .content.jellyfin import WatchState
from .content.store import ItemStats

WEIGHTS = {'fit': 0.5, 'learn': 0.3, 'continue': 0.2}
SWEET = (0.95, 0.98)
TOO_HARD = 0.85
FULL_1T_SHARE = 0.3
MAX_PER_SHOW = 2


@dataclass(frozen=True)
class Candidate:
    item_id: int
    external_id: str  # Jellyfin item id
    series_key: str
    series: str
    season: int | None
    episode: int | None
    title: str
    stats: ItemStats


@dataclass(frozen=True)
class Recommendation:
    candidate: Candidate
    score: float
    parts: dict[str, float]
    reasons: tuple[str, ...]


def coverage_fit(c: float) -> float:
    lo, hi = SWEET
    if lo <= c <= hi:
        return 1.0
    if c < lo:
        return max(0.0, (c - TOO_HARD) / (lo - TOO_HARD))
    return max(0.5, 1.0 - 0.5 * (c - hi) / (1.0 - hi))


def learn_value(one_new: int, sentences: int) -> float:
    return 0.0 if sentences <= 0 else min(1.0, one_new / sentences / FULL_1T_SHARE)


def continuation(cands: Sequence[Candidate], watch: dict[str, WatchState]) -> dict[int, str]:
    """item_id -> reason, for half-watched episodes and the next episode after the last one watched, per show."""
    out: dict[int, str] = {}
    shows: dict[str, list[Candidate]] = {}
    for c in cands:
        shows.setdefault(c.series_key, []).append(c)
    for eps in shows.values():
        eps.sort(key=lambda c: (c.season or 0, c.episode or 0, c.title))
        seen = [i for i, c in enumerate(eps) if (w := watch.get(c.external_id)) and (w.played or w.pct > 0)]
        for c in eps:
            w = watch.get(c.external_id)
            if w and not w.played and w.pct > 0:
                out[c.item_id] = f'continue watching ({round(w.pct)}%)'
        if seen:
            nxt = next((c for c in eps[seen[-1] + 1 :] if not (watch.get(c.external_id) or _UNSEEN).played), None)
            if nxt is not None and nxt.item_id not in out:
                out[nxt.item_id] = f'next episode of {nxt.series}'
    return out


_UNSEEN = WatchState(False, 0.0, None)


def recommend(cands: Sequence[Candidate], watch: dict[str, WatchState], limit: int = 5) -> list[Recommendation]:
    cont = continuation(cands, watch)
    scored: list[Recommendation] = []
    for c in cands:
        if (watch.get(c.external_id) or _UNSEEN).played or c.stats.words_total == 0:
            continue
        cov = c.stats.coverage
        parts = {
            'fit': coverage_fit(cov),
            'learn': learn_value(c.stats.one_new, c.stats.sentences),
            'continue': 1.0 if c.item_id in cont else 0.0,
        }
        score = sum(WEIGHTS[k] * v for k, v in parts.items())
        reasons = [f'{cov * 100:.0f}% known' + (' (a stretch)' if cov < SWEET[0] else '')]
        if c.stats.one_new:
            reasons.append(f'{c.stats.one_new} sentences with one new word')
        if c.item_id in cont:
            reasons.append(cont[c.item_id])
        scored.append(Recommendation(c, round(score, 4), parts, tuple(reasons)))
    scored.sort(key=lambda r: (-r.score, r.candidate.series_key, r.candidate.season or 0, r.candidate.episode or 0))
    out: list[Recommendation] = []
    per_show: dict[str, int] = {}
    for r in scored:
        k = r.candidate.series_key
        if per_show.get(k, 0) < MAX_PER_SHOW:
            out.append(r)
            per_show[k] = per_show.get(k, 0) + 1
            if len(out) == limit:
                break
    return out
