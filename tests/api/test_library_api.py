from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lmx.api.app import create_app
from lmx.config import Settings
from lmx.content.jellyfin import Episode
from lmx.content.library import Ingest
from lmx.content.store import Line

EPISODES = [
    Episode('a1', 'Running Man', 11, 1, 'E01', '/m/a1.mkv', 4000.0, True, True),
    Episode('a2', 'Running Man', 11, 2, 'E02', '/m/a2.mkv', 4000.0, True, True),
    Episode('b1', '나 혼자 산다', 1, 1, 'E01', '/m/b1.mkv', 3000.0, False, True),
]
SUBS = {
    '/m/a1.mkv': ('stream:3', [Line(0, 900, '밥을 먹었다.'), Line(1000, 1900, '소나기가 왔다.')]),
    '/m/a2.mkv': ('file:a2.ko.srt', [Line(0, 900, '소나기가 쏟아졌다.')]),
}


@pytest.fixture
def lib(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(
        Settings(data_dir=tmp_path / 'd', library_autostart=False),
        episodes=lambda: EPISODES,
        find=lambda p: SUBS.get(str(p)),
    )
    ingest: Ingest = app.state.ingest
    ingest.run_once()
    with TestClient(app) as c:
        c.post('/api/knowledge/import', json={'language': 'ko', 'csv': '밥,known\n먹다,known\n오다,known'})
        app.state.stats.run_until_clean()  # what the background worker does
        yield c


def test_status(lib: TestClient) -> None:
    st = lib.get('/api/library/status').json()
    assert st['enabled'] is True and st['running'] is False and st['error'] is None
    assert st['analysed'] == 3 and st['items'] == {'new': 0, 'analyzed': 2, 'no_subtitles': 1, 'error': 0}
    assert st['stats_pending'] == 0


def test_series(lib: TestClient) -> None:
    s = {x['series']: x for x in lib.get('/api/library/series').json()}
    assert (s['Running Man']['key'], s['나 혼자 산다']['key']) == ('runningman', '나혼자산다')
    assert (s['Running Man']['items'], s['Running Man']['analyzed']) == (2, 2)
    # words: 밥 먹다 (known) 소나기 오다(known) | 소나기 쏟아지다 -> 3 of 6 known; 1T: "소나기가 왔다."
    assert s['Running Man']['coverage'] == pytest.approx(3 / 6) and s['Running Man']['one_new'] == 1
    assert (s['나 혼자 산다']['analyzed'], s['나 혼자 산다']['coverage']) == (0, None)


def test_series_items_and_words(lib: TestClient) -> None:
    items = lib.get('/api/library/series/runningman').json()
    assert [(i['title'], i['status'], i['subtitle'], i['sentences']) for i in items] == [
        ('E01', 'analyzed', 'stream:3', 2),
        ('E02', 'analyzed', 'file:a2.ko.srt', 1),
    ]
    assert items[0]['coverage'] == pytest.approx(3 / 4) and (items[0]['new_words'], items[0]['one_new']) == (1, 1)
    words = lib.get(f'/api/library/items/{items[1]["id"]}/words').json()
    assert [w['key'] for w in words] == ['소나기', '쏟아지다']
    assert lib.get(f'/api/library/items/{items[1]["id"]}/words', params={'limit': 1}).json()[0]['key'] == '소나기'
    nohs = lib.get('/api/library/series/나혼자산다').json()
    assert (nohs[0]['status'], nohs[0]['coverage']) == ('no_subtitles', None)


def test_learning_a_word_changes_coverage_live(lib: TestClient) -> None:
    before = lib.get('/api/library/series/runningman').json()[1]
    lib.post('/api/knowledge/events', json={'language': 'ko', 'lemma': '소나기', 'kind': 'marked_known'})
    after = lib.get('/api/library/series/runningman').json()[1]  # per-show view: live, no waiting
    assert (before['new_words'], after['new_words']) == (2, 1)
    assert after['coverage'] > before['coverage'] and after['one_new'] == 1


def test_library_list_catches_up_through_the_cache(lib: TestClient) -> None:
    def cov() -> float:
        return next(x for x in lib.get('/api/library/series').json() if x['key'] == 'runningman')['coverage']

    before = cov()
    lib.post('/api/knowledge/events', json={'language': 'ko', 'lemma': '소나기', 'kind': 'marked_known'})
    assert lib.get('/api/library/status').json()['stats_pending'] == 2  # both episodes contain 소나기
    assert cov() == before  # not recomputed yet: the list lags...
    lib.app.state.stats.run_until_clean()  # type: ignore[attr-defined]
    assert lib.get('/api/library/status').json()['stats_pending'] == 0
    assert cov() == pytest.approx(5 / 6)  # ...until the worker has run


def test_not_found(lib: TestClient) -> None:
    assert lib.get('/api/library/series/nope').status_code == 404
    assert lib.get('/api/library/items/9999/words').status_code == 404
    assert lib.get('/api/library/items/1/words', params={'limit': 0}).status_code == 422


def test_sync_triggers_the_worker(lib: TestClient) -> None:
    assert lib.post('/api/library/sync').status_code == 202


def test_disabled_without_jellyfin_key(client: TestClient) -> None:
    st = client.get('/api/library/status').json()
    assert st['enabled'] is False and st['items'] == {'new': 0, 'analyzed': 0, 'no_subtitles': 0, 'error': 0}
    assert st['stats_pending'] == 0
    assert client.post('/api/library/sync').status_code == 409
    assert client.get('/api/library/series').json() == []


def test_jellyfin_key_enables_the_library(tmp_path: Path) -> None:
    app = create_app(Settings(data_dir=tmp_path / 'd', jellyfin_api_key='k', library_autostart=False))
    assert app.state.ingest is not None
