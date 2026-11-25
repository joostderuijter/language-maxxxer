"""The HTTP API end to end (real app, real SQLite in a temp dir)."""

from pathlib import Path

from fastapi.testclient import TestClient

from lmx.api.app import create_app
from lmx.config import Settings


def test_health(client: TestClient) -> None:
    r = client.get('/api/health')
    assert r.status_code == 200 and r.json() == {'ok': True, 'version': '0.1.0'}


def test_languages(client: TestClient) -> None:
    (ko,) = client.get('/api/languages').json()
    assert (ko['code'], ko['name'], ko['dictionary']['source']) == ('ko', 'Korean', 'test fixture')


def test_dictionary_lookup_first_known_candidate(client: TestClient) -> None:
    r = client.get('/api/dictionary/ko', params={'lemma': ['없는말', '눈']}).json()
    assert r['lemma'] == '눈'
    assert [s['gloss'] for s in r['senses']] == ['eye', 'snow']
    assert r['senses'][0]['examples'] == ['지수는 눈이 크다.', '눈을 감아 봐.']
    assert r['senses'][0]['level'] == 'beginner'
    assert [i['text'] for i in r['idioms']] == ['눈이 높다', '눈 감으면 코 베어 갈 세상']


def test_dictionary_lookup_unknown_and_validation(client: TestClient) -> None:
    assert client.get('/api/dictionary/ko', params={'lemma': ['없는말']}).json() == {
        'lemma': '없는말', 'senses': [], 'idioms': []}  # fmt: skip
    assert client.get('/api/dictionary/ko').status_code == 422
    assert client.get('/api/dictionary/ko', params={'lemma': ['a'] * 11}).status_code == 422
    assert client.get('/api/dictionary/xx', params={'lemma': ['a']}).status_code == 404


def test_progress_starts_at_zero(client: TestClient) -> None:
    p = client.get('/api/progress/ko').json()
    assert p['words_known'] == 0 and set(p['by_state']) == {'unknown', 'seen', 'learning', 'known', 'ignored'}


def test_unknown_language_is_404(client: TestClient) -> None:
    assert client.get('/api/progress/xx').status_code == 404
    assert client.post('/api/analyze', json={'language': 'xx', 'text': 'a'}).status_code == 404
    assert (
        client.post('/api/knowledge/events', json={'language': 'xx', 'lemma': 'a', 'kind': 'seen'}).status_code == 404
    )
    assert client.post('/api/knowledge/import', json={'language': 'xx', 'csv': ''}).status_code == 404


def test_import_then_progress_then_analyze(client: TestClient) -> None:
    r = client.post('/api/knowledge/import', json={'language': 'ko', 'csv': '먹다,2\n가다,known\n배신,1\nx,bogus'})
    assert r.json() == {'imported': 3, 'skipped': 1}
    p = client.get('/api/progress/ko').json()
    assert p['words_known'] == 2 and p['by_state']['seen'] == 1
    tokens = client.post('/api/analyze', json={'language': 'ko', 'text': '밥을 먹고 배신했다'}).json()['tokens']
    assert [(t['surface'], t['lemma'], t['state']) for t in tokens] == [
        ('밥을', '밥', 'unknown'),
        ('먹고', '먹다', 'known'),
        ('배신했다', '배신', 'seen'),
    ]


def test_best_known_candidate_wins(client: TestClient) -> None:
    client.post('/api/knowledge/events', json={'language': 'ko', 'lemma': '무난', 'kind': 'marked_known'})
    t = client.post('/api/analyze', json={'language': 'ko', 'text': '무난하고'}).json()['tokens'][0]
    assert (t['lemmas'], t['lemma'], t['state']) == (['무난하다', '무난'], '무난', 'known')


def test_event_endpoint(client: TestClient) -> None:
    r = client.post('/api/knowledge/events', json={'language': 'ko', 'lemma': ' 광수 ', 'kind': 'ignored'})
    assert r.json() == {'lemma': '광수', 'state': 'ignored', 'confidence': 1.0}
    assert client.get('/api/progress/ko').json()['by_state']['ignored'] == 1


def test_validation(client: TestClient) -> None:
    assert client.post('/api/knowledge/events', json={'language': 'ko', 'lemma': '', 'kind': 'seen'}).status_code == 422
    assert (
        client.post('/api/knowledge/events', json={'language': 'ko', 'lemma': 'a', 'kind': 'nope'}).status_code == 422
    )
    assert client.post('/api/analyze', json={'language': 'ko', 'text': 'x' * 20_001}).status_code == 422


def test_data_survives_restart(settings: Settings) -> None:
    with TestClient(create_app(settings)) as c:
        c.post('/api/knowledge/events', json={'language': 'ko', 'lemma': '먹다', 'kind': 'marked_known'})
    with TestClient(create_app(settings)) as c:
        assert c.get('/api/progress/ko').json()['words_known'] == 1


def test_openapi_lists_the_api(client: TestClient) -> None:
    paths = client.get('/openapi.json').json()['paths']
    assert {
        '/api/health',
        '/api/languages',
        '/api/progress/{code}',
        '/api/analyze',
        '/api/knowledge/events',
        '/api/knowledge/import',
    } <= set(paths)


def test_serves_frontend_with_spa_fallback(tmp_path: Path) -> None:
    static = tmp_path / 'static'
    (static / '_app').mkdir(parents=True)
    (static / 'index.html').write_text('<html>app</html>')
    (static / '_app' / 'x.js').write_text('js')
    (static / 'favicon.png').write_bytes(b'png')
    with TestClient(create_app(Settings(data_dir=tmp_path / 'd', static_dir=static))) as c:
        assert c.get('/').text == '<html>app</html>'
        assert c.get('/some/client/route').text == '<html>app</html>'
        assert c.get('/_app/x.js').text == 'js'
        assert c.get('/favicon.png').content == b'png'
        assert c.get('/../../etc/passwd').text == '<html>app</html>'
        assert c.get('/api/nope').status_code == 404
        assert c.get('/api/health').json()['ok'] is True


def test_no_frontend_means_api_only(client: TestClient) -> None:
    assert client.get('/').status_code == 404
