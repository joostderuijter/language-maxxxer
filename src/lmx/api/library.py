"""Library endpoints: what's in Jellyfin, how well the user can follow each episode, what to learn for it."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select

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


class SeriesOut(BaseModel):
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
    items = s.scalars(select(ContentItem)).all()
    uid = default_user_id(s)
    st = stats(s, uid, [i.id for i in items if i.status == 'analyzed'])
    out: dict[str, list[ContentItem]] = {}
    for it in items:
        out.setdefault(it.series, []).append(it)
    result: list[SeriesOut] = []
    for name, its in sorted(out.items(), key=lambda kv: kv[0].lower()):
        done = [st[i.id] for i in its if i.id in st]
        total = sum(x.words_total for x in done)
        result.append(
            SeriesOut(
                series=name,
                items=len(its),
                analyzed=len(done),
                coverage=sum(x.words_known for x in done) / total if total else None,
                one_new=sum(x.one_new for x in done),
            )
        )
    return result


@router.get('/series/{name}', response_model=list[ItemOut])
def series_items(name: str, s: Db) -> list[ItemOut]:
    items = s.scalars(
        select(ContentItem)
        .where(ContentItem.series == name)
        .order_by(ContentItem.season, ContentItem.episode, ContentItem.title)
    ).all()
    if not items:
        raise HTTPException(404, f'no series {name!r}')
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
