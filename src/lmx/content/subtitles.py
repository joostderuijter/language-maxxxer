"""Korean subtitles for a video: an embedded text track (ffprobe/ffmpeg) or a sidecar file (video.ko.srt).

Preference: an embedded Korean text track (normal over SDH, never 'forced'), then a sidecar .ko/.kor/.korean .srt
(e.g. yt-shelf's YouTube or Whisper subtitles).
"""

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .store import Line

TEXT_CODECS = {'subrip', 'srt', 'ass', 'ssa', 'mov_text', 'webvtt'}
KOREAN = {'kor', 'ko', 'korean'}
SIDECAR = ('.ko.srt', '.kor.srt', '.korean.srt', '.ko-KR.srt')
TIME = re.compile(r'(\d+):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d+):(\d{2}):(\d{2})[,.](\d{3})')
TAGS = re.compile(r'<[^>]+>|\{\\[^}]*\}')  # <i>, <font …>, {\an8}
ONLY_NOISE = re.compile(r'^[\s\W♪♬]*$')  # nothing readable left (punctuation, music notes)


@dataclass(frozen=True)
class Stream:
    index: int
    codec: str
    language: str
    title: str
    forced: bool


def _ms(h: str, m: str, s: str, ms: str) -> int:
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms)


def parse_srt(text: str) -> list[Line]:
    """SRT (or the cue part of WebVTT) -> lines with start/end in ms. Tags removed, multi-line cues joined."""
    out: list[Line] = []
    for block in re.split(r'\n\s*\n', text.lstrip('﻿').replace('\r\n', '\n').replace('\r', '\n')):
        rows = block.strip().split('\n')
        for i, row in enumerate(rows):
            m = TIME.search(row)
            if m:
                g = m.groups()
                body = ' '.join(TAGS.sub('', r).strip() for r in rows[i + 1 :])
                body = re.sub(r'\s+', ' ', body).strip()
                if body and not ONLY_NOISE.match(body):
                    out.append(Line(_ms(*g[:4]), _ms(*g[4:]), body))
                break
    return sorted(out, key=lambda ln: ln.start_ms)


def probe(path: Path) -> list[Stream]:
    """Subtitle streams of a video file."""
    out = subprocess.run(
        [
            'ffprobe',
            '-v',
            'error',
            '-select_streams',
            's',
            '-show_entries',
            'stream=index,codec_name:stream_tags=language,title:stream_disposition=forced',
            '-of',
            'json',
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    ).stdout
    streams: list[Stream] = []
    for s in json.loads(out or '{}').get('streams', []):
        tags = s.get('tags') or {}
        streams.append(
            Stream(
                int(s['index']),
                s.get('codec_name', ''),
                (tags.get('language') or '').lower(),
                tags.get('title') or '',
                bool((s.get('disposition') or {}).get('forced')),
            )
        )
    return streams


def pick_korean(streams: list[Stream]) -> Stream | None:
    """The best Korean text track: not forced, not image-based; normal before SDH / closed captions."""
    ok = [s for s in streams if s.language in KOREAN and s.codec in TEXT_CODECS and not s.forced]
    ok.sort(key=lambda s: ('sdh' in s.title.lower() or 'cc' in s.title.lower().split(), s.index))
    return ok[0] if ok else None


def extract(path: Path, stream: Stream) -> list[Line]:
    out = subprocess.run(
        ['ffmpeg', '-v', 'error', '-i', str(path), '-map', f'0:{stream.index}', '-f', 'srt', '-'],
        capture_output=True,
        check=True,
        timeout=300,
    ).stdout
    return parse_srt(out.decode('utf-8', errors='replace'))


def sidecar(path: Path) -> Path | None:
    for suffix in SIDECAR:
        p = path.with_name(path.stem + suffix)
        if p.is_file():
            return p
    return None


def korean_subtitles(path: Path) -> tuple[str, list[Line]] | None:
    """-> (where they came from, lines), or None if the video has no Korean subtitles."""
    stream = pick_korean(probe(path)) if path.is_file() else None
    if stream is not None:
        lines = extract(path, stream)
        if lines:
            return f'stream:{stream.index}', lines
    side = sidecar(path)
    if side is not None:
        lines = parse_srt(side.read_text(encoding='utf-8', errors='replace'))
        if lines:
            return f'file:{side.name}', lines
    return None
