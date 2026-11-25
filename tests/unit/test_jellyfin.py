from typing import Any
from urllib.parse import parse_qs, urlparse

from lmx.content.jellyfin import Episode, Jellyfin, parse_episodes


def item(
    id_: str, streams: list[dict[str, Any]], *, path: str | None = '/media/x.mkv', nested: bool = False, **kw: Any
) -> dict[str, Any]:
    it: dict[str, Any] = {
        'Id': id_,
        'Name': f'ep {id_}',
        'SeriesName': 'Running Man',
        'ParentIndexNumber': 11,
        'IndexNumber': 3,
        'RunTimeTicks': 36_000_000_000,
        **kw,
    }
    if path:
        it['Path'] = path
    it['MediaSources' if nested else 'MediaStreams'] = [{'MediaStreams': streams}] if nested else streams
    return it


KO_SUB = {'Type': 'Subtitle', 'Language': 'kor'}
KO_AUDIO = {'Type': 'Audio', 'Language': 'kor'}
EN_SUB = {'Type': 'Subtitle', 'Language': 'eng'}


def test_parse_keeps_korean_episodes_only() -> None:
    eps = parse_episodes(
        [
            item('a', [KO_SUB, EN_SUB]),
            item('b', [KO_AUDIO]),
            item('c', [EN_SUB, {'Type': 'Audio', 'Language': 'eng'}]),  # not Korean
            item('d', [KO_SUB], path=None),  # no file
            item('e', [{'Type': 'Subtitle', 'Language': 'KO'}], nested=True),
        ]
    )
    assert [(e.id, e.korean_subs, e.korean_audio) for e in eps] == [
        ('a', True, False),
        ('b', False, True),
        ('e', True, False),
    ]
    assert eps[0] == Episode('a', 'Running Man', 11, 3, 'ep a', '/media/x.mkv', 3600.0, True, False)


def test_parse_missing_fields() -> None:
    (ep,) = parse_episodes([{'Id': 'x', 'Path': '/p.mkv', 'MediaStreams': [KO_SUB]}])
    assert (ep.series, ep.season, ep.episode, ep.title, ep.duration_s) == ('?', None, None, '', None)


def test_client_asks_for_episodes_with_streams() -> None:
    calls: list[str] = []

    def fetch(url: str) -> Any:
        calls.append(url)
        return {'Items': [item('a', [KO_SUB])]}

    eps = Jellyfin('http://jellyfin:8096/', 'key', fetch).episodes()
    assert [e.id for e in eps] == ['a']
    u = urlparse(calls[0])
    q = parse_qs(u.query)
    assert (u.netloc, u.path) == ('jellyfin:8096', '/Items')
    assert q['IncludeItemTypes'] == ['Episode'] and q['Recursive'] == ['true'] and 'MediaStreams' in q['Fields'][0]


def test_client_without_params() -> None:
    assert Jellyfin('http://j', 'k', lambda url: url).get('/System/Info') == 'http://j/System/Info'
