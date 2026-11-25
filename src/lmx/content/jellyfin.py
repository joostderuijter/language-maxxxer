"""Read-only Jellyfin client: which episodes exist, where their files are, and whether they look Korean."""

import json
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

KOREAN = {'kor', 'ko', 'korean'}

Fetch = Callable[[str], Any]  # url -> parsed JSON (injectable for tests)


@dataclass(frozen=True)
class Episode:
    id: str
    series: str
    season: int | None
    episode: int | None
    title: str
    path: str
    duration_s: float | None
    korean_subs: bool  # a Korean subtitle track (embedded or a sidecar file Jellyfin found)
    korean_audio: bool


def _streams(item: dict[str, Any]) -> list[dict[str, Any]]:
    streams: list[dict[str, Any]] = list(item.get('MediaStreams') or [])
    if not streams:
        for src in item.get('MediaSources') or []:
            streams += src.get('MediaStreams') or []
    return streams


def parse_episodes(items: list[dict[str, Any]]) -> list[Episode]:
    """Jellyfin items -> episodes that look Korean (a Korean subtitle or audio track)."""
    out: list[Episode] = []
    for it in items:
        if not it.get('Path'):
            continue
        korean = {s.get('Type') for s in _streams(it) if (s.get('Language') or '').lower() in KOREAN}
        subs, audio = 'Subtitle' in korean, 'Audio' in korean
        if not (subs or audio):
            continue
        ticks = it.get('RunTimeTicks')
        out.append(
            Episode(
                id=it['Id'],
                series=it.get('SeriesName') or it.get('Name') or '?',
                season=it.get('ParentIndexNumber'),
                episode=it.get('IndexNumber'),
                title=it.get('Name') or '',
                path=it['Path'],
                duration_s=ticks / 10_000_000 if ticks else None,
                korean_subs=subs,
                korean_audio=audio,
            )
        )
    return out


@dataclass(frozen=True)
class WatchState:
    played: bool
    pct: float  # 0-100, how far into a half-watched episode
    last_played: str | None  # ISO timestamp


def parse_watch(items: list[dict[str, Any]]) -> dict[str, WatchState]:
    out: dict[str, WatchState] = {}
    for it in items:
        ud = it.get('UserData') or {}
        out[it['Id']] = WatchState(
            bool(ud.get('Played')), float(ud.get('PlayedPercentage') or 0.0), ud.get('LastPlayedDate')
        )
    return out


def pick_user(users: list[dict[str, Any]], name: str = '') -> dict[str, Any] | None:
    """The named user, else the first administrator, else the first user."""
    by_name = next((u for u in users if name and u.get('Name') == name), None)
    admin = next((u for u in users if (u.get('Policy') or {}).get('IsAdministrator')), None)
    return by_name or admin or (users[0] if users else None)


class Jellyfin:
    def __init__(self, url: str, api_key: str, fetch: Fetch | None = None):
        self.url, self.key = url.rstrip('/'), api_key
        self.fetch = fetch or self._http

    def _http(self, url: str) -> Any:  # pragma: no cover  (network; the client logic is tested with a fake fetch)
        req = urllib.request.Request(url, headers={'Authorization': f'MediaBrowser Token="{self.key}"'})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)

    def get(self, path: str, **params: str) -> Any:
        return self.fetch(f'{self.url}{path}?{urllib.parse.urlencode(params)}' if params else f'{self.url}{path}')

    def episodes(self) -> list[Episode]:
        data = self.get(
            '/Items',
            IncludeItemTypes='Episode',
            Recursive='true',
            Fields='Path,MediaStreams,MediaSources',
            EnableImages='false',
        )
        return parse_episodes(data.get('Items') or [])

    def watch_states(self, user: str = '') -> dict[str, WatchState]:
        """Watched and half-watched episodes of one Jellyfin user (read-only)."""
        u = pick_user(self.get('/Users') or [], user)
        if u is None:
            return {}
        out: dict[str, WatchState] = {}
        for flt in ('IsPlayed', 'IsResumable'):
            data = self.get(
                f'/Users/{u["Id"]}/Items',
                IncludeItemTypes='Episode',
                Recursive='true',
                Filters=flt,
                Fields='UserData',
                EnableImages='false',
            )
            out.update(parse_watch(data.get('Items') or []))
        return out
