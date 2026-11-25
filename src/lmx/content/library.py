"""Keeping the library in sync with Jellyfin and analysing what's new or outdated (in the background, ADR-1)."""

import threading
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from ..db import Database
from ..languages.base import LanguagePack
from ..models import ContentItem, now
from .jellyfin import Episode
from .store import Line, save_analysis
from .subtitles import korean_subtitles

SOURCE = 'jellyfin'
Finder = Callable[[Path], tuple[str, list[Line]] | None]


@dataclass(frozen=True)
class SyncResult:
    added: int
    updated: int
    removed: int


def sync(session: Session, episodes: list[Episode], language: str) -> SyncResult:
    """Make content_items match Jellyfin's Korean episodes. Changed files, and episodes that gained Korean subtitles,
    are analysed again; earlier errors are retried."""
    have = {i.external_id: i for i in session.scalars(select(ContentItem).where(ContentItem.source == SOURCE))}
    added = updated = 0
    seen: set[str] = set()
    for ep in episodes:
        seen.add(ep.id)
        it = have.get(ep.id)
        if it is None:
            session.add(
                ContentItem(
                    language=language,
                    source=SOURCE,
                    external_id=ep.id,
                    series=ep.series,
                    season=ep.season,
                    episode=ep.episode,
                    title=ep.title,
                    path=ep.path,
                    duration_s=ep.duration_s,
                    status='new',
                )
            )
            added += 1
            continue
        retry = it.path != ep.path or it.status == 'error' or (it.status == 'no_subtitles' and ep.korean_subs)
        changed = (it.series, it.season, it.episode, it.title, it.duration_s) != (
            ep.series,
            ep.season,
            ep.episode,
            ep.title,
            ep.duration_s,
        )
        if retry or changed:
            it.series, it.season, it.episode, it.title, it.path, it.duration_s = (
                ep.series,
                ep.season,
                ep.episode,
                ep.title,
                ep.path,
                ep.duration_s,
            )
            if retry:
                it.status = 'new'
            it.updated_at = now()
            updated += 1
    gone = [i.id for k, i in have.items() if k not in seen]
    if gone:
        session.execute(delete(ContentItem).where(ContentItem.id.in_(gone)))
    session.flush()
    return SyncResult(added, updated, len(gone))


def pending(session: Session, version: str, limit: int = 100) -> list[int]:
    """Items to analyse: new ones, and analysed ones whose analysis is from another pack version."""
    q = (
        select(ContentItem.id)
        .where(or_(ContentItem.status == 'new', (ContentItem.status == 'analyzed') & (ContentItem.analyzer != version)))
        .order_by(ContentItem.series, ContentItem.season, ContentItem.episode, ContentItem.id)
        .limit(limit)
    )
    return list(session.scalars(q))


def analyze(session: Session, item: ContentItem, pack: LanguagePack, find: Finder = korean_subtitles) -> None:
    """Subtitles -> analysis. Sets status analyzed / no_subtitles / error."""
    try:
        found = find(Path(item.path))
    except Exception as e:  # ffmpeg failed, file unreadable, ...
        item.status, item.detail, item.updated_at = 'error', f'{type(e).__name__}: {e}'[:500], now()
        return
    if found is None:
        item.status, item.subtitle, item.analyzer, item.detail = 'no_subtitles', None, pack.version, None
        item.updated_at = now()
        return
    where, lines = found
    item.subtitle = where
    save_analysis(session, item, lines, pack.analyze_many([ln.text for ln in lines]), pack.version)


@dataclass
class IngestState:
    running: bool = False
    last_sync: float | None = None
    last_result: SyncResult | None = None
    analysed: int = 0
    current: str | None = None
    error: str | None = None
    log: list[str] = field(default_factory=list[str])


class Ingest:
    """Background worker: sync with Jellyfin, then analyse pending items one by one. trigger() = run now."""

    def __init__(
        self,
        db: Database,
        episodes: Callable[[], list[Episode]],
        pack: LanguagePack,
        language: str,
        interval_s: float = 3600,
        find: Finder = korean_subtitles,
    ):
        self.db, self.episodes, self.pack, self.language = db, episodes, pack, language
        self.interval_s, self.find = interval_s, find
        self.state = IngestState()
        self._wake = threading.Event()
        self._lock = threading.Lock()

    def run_once(self) -> None:
        with self._lock:
            self.state.running, self.state.error = True, None
            try:
                eps = self.episodes()
                with self.db.session() as s:
                    self.state.last_result = sync(s, eps, self.language)
                self.state.last_sync = time.time()
                while True:
                    with self.db.session() as s:
                        ids = pending(s, self.pack.version, limit=1)
                        if not ids:
                            break
                        item = s.get_one(ContentItem, ids[0])
                        self.state.current = f'{item.series} {item.title}'
                        analyze(s, item, self.pack, self.find)
                    self.state.analysed += 1
            except Exception as e:
                self.state.error = f'{type(e).__name__}: {e}'
                self.state.log = [*self.state.log, traceback.format_exc()][-5:]
            finally:
                self.state.running, self.state.current = False, None

    def trigger(self) -> None:
        self._wake.set()

    def start(self) -> threading.Thread:  # pragma: no cover  (the loop; run_once is what's tested)
        def loop() -> None:
            while True:
                self.run_once()
                self._wake.wait(self.interval_s)
                self._wake.clear()

        t = threading.Thread(target=loop, daemon=True, name='ingest')
        t.start()
        return t
