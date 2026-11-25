"""Per-user stats cache for library-wide views (ADR-5, option A).

Writers never update it directly: triggers on word_knowledge (migration 0004) and save_analysis()/mark_item() put
(user, item) pairs in stats_dirty; refresh() recomputes them (see its docstring for why nothing is ever lost).
Per-show views stay live (store.stats).
"""

import threading
from collections.abc import Sequence

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from ..db import Database
from ..models import ContentItem, ItemStatsCache, StatsDirty, now
from .store import ItemStats, mark_item, stats

__all__ = ['StatsWorker', 'cached', 'mark_item', 'pending', 'refresh']


def refresh(db: Database, batch: int = 200) -> int:
    """Recompute up to `batch` dirty (user, item) pairs. -> how many were processed (0 = cache is up to date).

    Three short transactions, so a "Know" click never waits for a whole batch: claim (delete the dirty rows), compute
    (read only; WAL lets writers continue), write the results. A change committed in between re-marks the item through
    the triggers, so the next round fixes any stale result. If computing fails, the claimed rows are put back.
    """
    with db.session() as s:
        rows = [(u, i) for u, i in s.execute(select(StatsDirty.user_id, StatsDirty.item_id).limit(batch))]
        for uid, iid in rows:
            s.execute(delete(StatsDirty).where(StatsDirty.user_id == uid, StatsDirty.item_id == iid))
    if not rows:
        return 0
    by_user: dict[int, list[int]] = {}
    for uid, iid in rows:
        by_user.setdefault(uid, []).append(iid)
    try:
        results: dict[int, tuple[list[int], dict[int, ItemStats]]] = {}
        with db.session() as s:
            for uid, ids in by_user.items():
                done = s.scalars(
                    select(ContentItem.id).where(ContentItem.id.in_(ids), ContentItem.status == 'analyzed')
                )
                results[uid] = (ids, stats(s, uid, sorted(done)))
        with db.session() as s:
            for uid, (ids, st) in results.items():
                s.execute(delete(ItemStatsCache).where(ItemStatsCache.user_id == uid, ItemStatsCache.item_id.in_(ids)))
                s.add_all(
                    ItemStatsCache(
                        user_id=uid,
                        item_id=iid,
                        sentences=x.sentences,
                        words_total=x.words_total,
                        words_known=x.words_known,
                        new_words=x.new_words,
                        one_new=x.one_new,
                        computed_at=now(),
                    )
                    for iid, x in st.items()
                )
    except BaseException:
        with db.session() as s:  # give the work back
            s.execute(
                insert(StatsDirty).values([{'user_id': u, 'item_id': i} for u, i in rows]).prefix_with('OR IGNORE')
            )
        raise
    return len(rows)


def cached(session: Session, user_id: int, item_ids: Sequence[int] | None = None) -> dict[int, ItemStats]:
    q = select(ItemStatsCache).where(ItemStatsCache.user_id == user_id)
    if item_ids is not None:
        q = q.where(ItemStatsCache.item_id.in_(item_ids))
    return {
        r.item_id: ItemStats(r.sentences, r.words_total, r.words_known, r.new_words, r.one_new)
        for r in session.scalars(q)
    }


def pending(session: Session, user_id: int) -> int:
    return session.scalar(select(func.count()).select_from(StatsDirty).where(StatsDirty.user_id == user_id)) or 0


class StatsWorker:
    """Keeps the cache fresh in the background: refresh() until clean, then wait for poke() (or poll)."""

    def __init__(self, db: Database, poll_s: float = 2.0, batch: int = 200):
        self.db, self.poll_s, self.batch = db, poll_s, batch
        self._wake = threading.Event()

    def run_until_clean(self) -> int:
        done = 0
        while True:
            n = refresh(self.db, self.batch)
            if n == 0:
                return done
            done += n

    def poke(self) -> None:
        self._wake.set()

    def start(self) -> threading.Thread:  # pragma: no cover  (the loop; run_until_clean is what's tested)
        def loop() -> None:
            while True:
                try:
                    self.run_until_clean()
                except Exception as e:
                    print(f'stats cache refresh failed: {e!r}')
                self._wake.wait(self.poll_s)
                self._wake.clear()

        t = threading.Thread(target=loop, daemon=True, name='stats-cache')
        t.start()
        return t
