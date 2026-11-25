"""Library endpoints: what's in Jellyfin, how well the user can follow each episode, what to learn for it."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select

from ..content import cache
from ..content.library import Ingest
from ..content.store import ItemStats, new_words, stats
from ..models import ContentItem
from ..users import default_user_id
from .deps import Db

router = APIRouter(prefix='/api/library')


class LibraryStatus(BaseModel):
    enabled: bool  # false: no Jellyfin API key configured
    running: bool
    last_sync: float | None
    analysed: int  # since the app started
    current: str | None
    error: str | None
    items: dict[str, int]  # per status: new | analyzed | no_subtitles | error
    stats_pending: int  # episodes whose cached coverage is being recomputed (the library list may lag a moment)


class SeriesOut(BaseModel):
    key: str  # stable id of the show (release folders merged): use it in /series/{key}
    series: str
    items: int
    analyzed: int
    coverage: float | None  # words known / words, over all analysed episodes (None: nothing analysed yet)
    one_new: int  # sentences with exactly one new word, all episodes together


class ItemOut(BaseModel):
    id: int
    series: str
    season: int | None
    episode: int | None
    title: str
    status: str
    subtitle: str | None
    duration_s: float | None
    coverage: float | None
    new_words: int
    one_new: int
    sentences: int


class NewWordOut(BaseModel):
    key: str
    lemmas: list[str]
    count: int
    state: str


def ingest_of(request: Request) -> Ingest | None:
    return getattr(request.app.state, 'ingest', None)


@router.get('/status', response_model=LibraryStatus)
def status(request: Request, s: Db) -> LibraryStatus:
    ing = ingest_of(request)
    rows = s.execute(select(ContentItem.status, func.count()).group_by(ContentItem.status))
    counts: dict[str, int] = {status: n for status, n in rows}
    st = ing.state if ing else None
    return LibraryStatus(
        enabled=ing is not None,
        running=bool(st and st.running),
        last_sync=st.last_sync if st else None,
        analysed=st.analysed if st else 0,
        current=st.current if st else None,
        error=st.error if st else None,
        items={k: counts.get(k, 0) for k in ('new', 'analyzed', 'no_subtitles', 'error')},
        stats_pending=cache.pending(s, default_user_id(s)),
    )


@router.post('/sync', status_code=202)
def sync_now(request: Request) -> dict[str, bool]:
    ing = ingest_of(request)
    if ing is None:
        raise HTTPException(409, 'no Jellyfin API key configured (LMX_JELLYFIN_API_KEY)')
    ing.trigger()
    return {'ok': True}


def _item_out(it: ContentItem, x: ItemStats) -> ItemOut:
    return ItemOut(
        id=it.id,
        series=it.series,
        season=it.season,
        episode=it.episode,
        title=it.title,
        status=it.status,
        subtitle=it.subtitle,
        duration_s=it.duration_s,
        coverage=x.coverage if it.status == 'analyzed' else None,
        new_words=x.new_words,
        one_new=x.one_new,
        sentences=x.sentences,
    )


@router.get('/series', response_model=list[SeriesOut])
def series(s: Db) -> list[SeriesOut]:
    """All shows, from the stats cache (instant; may lag a moment behind a knowledge change)."""
    items = s.scalars(select(ContentItem)).all()
    st = cache.cached(s, default_user_id(s))
    groups: dict[str, list[ContentItem]] = {}
    for it in items:
        groups.setdefault(it.series_key or it.series, []).append(it)
    out: list[SeriesOut] = []
    for key, its in groups.items():
        names: dict[str, int] = {}
        for it in its:
            names[it.series] = names.get(it.series, 0) + 1
        done = [st[i.id] for i in its if i.status == 'analyzed' and i.id in st]
        total = sum(x.words_total for x in done)
        out.append(
            SeriesOut(
                key=key,
                series=max(names, key=lambda n: (names[n], n)),  # the most common spelling
                items=len(its),
                analyzed=sum(i.status == 'analyzed' for i in its),
                coverage=sum(x.words_known for x in done) / total if total else None,
                one_new=sum(x.one_new for x in done),
            )
        )
    return sorted(out, key=lambda x: x.series.lower())


@router.get('/series/{key}', response_model=list[ItemOut])
def series_items(key: str, s: Db) -> list[ItemOut]:
    """One show's episodes with LIVE stats (fast per show)."""
    items = s.scalars(
        select(ContentItem)
        .where(ContentItem.series_key == key)
        .order_by(ContentItem.season, ContentItem.episode, ContentItem.title)
    ).all()
    if not items:
        raise HTTPException(404, f'no show {key!r}')
    st = stats(s, default_user_id(s), [i.id for i in items])
    return [_item_out(i, st[i.id]) for i in items]


@router.get('/items/{item_id}/words', response_model=list[NewWordOut])
def item_words(item_id: int, s: Db, limit: Annotated[int, Query(ge=1, le=500)] = 50) -> list[NewWordOut]:
    if s.get(ContentItem, item_id) is None:
        raise HTTPException(404)
    return [
        NewWordOut(key=w.key, lemmas=list(w.lemmas), count=w.count, state=w.state)
        for w in new_words(s, default_user_id(s), item_id, limit)
    ]
