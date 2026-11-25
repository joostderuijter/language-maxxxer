from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from lmx import languages
from lmx.content.jellyfin import Episode
from lmx.content.library import Ingest, analyze, pending, sync
from lmx.content.store import Line, stats
from lmx.db import Database
from lmx.knowledge import service
from lmx.knowledge.events import EventKind
from lmx.models import ContentItem, ContentWord
from lmx.users import default_user_id


def ep(id_: str, path: str = '/m/a.mkv', subs: bool = True, title: str = 't', episode: int | None = 1) -> Episode:
    return Episode(id_, 'Show', 1, episode, title, path, 60.0, subs, True)


def items(s: Session) -> dict[str, ContentItem]:
    return {i.external_id: i for i in s.scalars(select(ContentItem))}


def test_sync_adds_updates_removes(session: Session) -> None:
    r = sync(session, [ep('a'), ep('b')], 'ko')
    assert (r.added, r.updated, r.removed) == (2, 0, 0)
    assert {i.status for i in items(session).values()} == {'new'}
    r = sync(session, [ep('a', title='renamed')], 'ko')
    assert (r.added, r.updated, r.removed) == (0, 1, 1)
    assert set(items(session)) == {'a'} and items(session)['a'].title == 'renamed'
    assert sync(session, [ep('a', title='renamed')], 'ko') == type(r)(0, 0, 0)  # nothing changed


def test_sync_reanalyses_when_needed(session: Session) -> None:
    sync(session, [ep('a'), ep('b', subs=False), ep('c')], 'ko')
    it = items(session)
    it['a'].status, it['b'].status, it['c'].status = 'analyzed', 'no_subtitles', 'error'
    sync(session, [ep('a', path='/m/new.mkv'), ep('b', subs=True), ep('c')], 'ko')
    it = items(session)
    assert (it['a'].status, it['a'].path) == ('new', '/m/new.mkv')  # file replaced
    assert it['b'].status == 'new'  # gained Korean subtitles (e.g. yt-shelf made a Whisper .ko.srt)
    assert it['c'].status == 'new'  # errors are retried


def test_no_subtitles_stays_when_still_none(session: Session) -> None:
    sync(session, [ep('a', subs=False)], 'ko')
    items(session)['a'].status = 'no_subtitles'
    sync(session, [ep('a', subs=False)], 'ko')
    assert items(session)['a'].status == 'no_subtitles'


def test_pending_new_and_outdated(session: Session) -> None:
    sync(session, [ep('a', episode=2), ep('b', episode=1), ep('c', episode=3), ep('d', episode=4)], 'ko')
    it = items(session)
    it['c'].status, it['c'].analyzer = 'analyzed', 'v1'
    it['d'].status, it['d'].analyzer = 'analyzed', 'v2'
    session.flush()
    assert pending(session, 'v2') == [it['b'].id, it['a'].id, it['c'].id]  # in episode order; d is up to date
    assert pending(session, 'v2', limit=1) == [it['b'].id]


LINES = [Line(0, 900, '밥을 먹었다.'), Line(1000, 1900, '소나기가 쏟아졌다.')]


def test_analyze_statuses(session: Session) -> None:
    pack = languages.get('ko')
    sync(session, [ep('a'), ep('b'), ep('c')], 'ko')
    it = items(session)
    analyze(session, it['a'], pack, lambda p: ('file:a.ko.srt', LINES))
    analyze(session, it['b'], pack, lambda p: None)

    def boom(p: Path) -> None:
        raise RuntimeError('ffmpeg exploded')

    analyze(session, it['c'], pack, boom)
    assert (it['a'].status, it['a'].subtitle, it['a'].analyzer) == ('analyzed', 'file:a.ko.srt', pack.version)
    assert (it['b'].status, it['b'].analyzer) == ('no_subtitles', pack.version)
    assert (it['c'].status, it['c'].detail) == ('error', 'RuntimeError: ffmpeg exploded')
    words = {w.key for w in session.scalars(select(ContentWord).where(ContentWord.item_id == it['a'].id))}
    assert {'밥', '먹다', '소나기', '쏟아지다'} <= words


def test_ingest_run_once_end_to_end(db: Database) -> None:
    eps = [ep('a', path='/m/a.mkv'), ep('b', path='/m/b.mkv', subs=False)]
    found = {'/m/a.mkv': ('file:a.ko.srt', LINES)}
    ing = Ingest(db, lambda: eps, languages.get('ko'), 'ko', find=lambda p: found.get(str(p)))
    ing.run_once()
    assert (ing.state.analysed, ing.state.error, ing.state.running) == (2, None, False)
    assert ing.state.last_result is not None and ing.state.last_result.added == 2
    with db.session() as s:
        uid = default_user_id(s)
        service.record(s, uid, 'ko', '밥', EventKind.MARKED_KNOWN, 'test')
        service.record(s, uid, 'ko', '먹다', EventKind.MARKED_KNOWN, 'test')
        a = items(s)['a']
        st = stats(s, uid, [a.id])[a.id]
        assert (st.sentences, st.one_new) == (2, 0) and st.new_words == 2  # 소나기 + 쏟아지다 in one line: 2T
        assert items(s)['b'].status == 'no_subtitles'
    ing.run_once()  # nothing new: nothing analysed again
    assert ing.state.analysed == 2


def test_ingest_reports_errors(db: Database) -> None:
    def broken() -> list[Episode]:
        raise ConnectionError('jellyfin down')

    ing = Ingest(db, broken, languages.get('ko'), 'ko')
    ing.run_once()
    assert ing.state.error == 'ConnectionError: jellyfin down' and not ing.state.running
    assert 'ConnectionError' in ing.state.log[-1]


@pytest.mark.skipif(not __import__('shutil').which('ffmpeg'), reason='needs ffmpeg')
def test_ingest_with_a_real_video(db: Database, tmp_path: Path) -> None:
    from .test_subtitles import make_video

    video = make_video(tmp_path, [('kor', '1\n00:00:00,100 --> 00:00:00,900\n밥을 먹었다.\n')])
    ing = Ingest(db, lambda: [ep('v', path=str(video))], languages.get('ko'), 'ko')
    ing.run_once()
    with db.session() as s:
        v = items(s)['v']
        assert (v.status, v.subtitle) == ('analyzed', 'stream:1')
