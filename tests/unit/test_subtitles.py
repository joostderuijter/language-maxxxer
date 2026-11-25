"""Subtitle parsing, Korean track choice, and real extraction with ffmpeg from a generated video."""

import shutil
import subprocess
from pathlib import Path

import pytest

from lmx.content.store import Line
from lmx.content.subtitles import Stream, extract, korean_subtitles, parse_srt, pick_korean, probe, sidecar

SRT = """﻿1
00:00:01,000 --> 00:00:02,500
<i>안녕하세요</i>

2
00:00:03,000 --> 00:00:04,000
{\\an8}첫 줄
둘째 줄

3
00:00:05,000 --> 00:00:06,000
♪ ♪

4
00:01:02,345 --> 01:00:00,000
끝
"""


def test_parse_srt() -> None:
    assert parse_srt(SRT) == [
        Line(1000, 2500, '안녕하세요'),
        Line(3000, 4000, '첫 줄 둘째 줄'),
        Line(62345, 3600000, '끝'),
    ]


def test_parse_srt_windows_line_endings_vtt_and_missing_index() -> None:
    vtt = (
        'WEBVTT\r\n\r\n00:00:01.000 --> 00:00:02.000 align:start\r\n좋아\r\n\r\n'
        '00:00:00.500 --> 00:00:00.900\r\n먼저\r\n'
    )
    assert parse_srt(vtt) == [Line(500, 900, '먼저'), Line(1000, 2000, '좋아')]


def test_parse_srt_garbage() -> None:
    assert parse_srt('') == [] and parse_srt('no timing here\n\nstill none') == []


def S(index: int, lang: str = 'kor', codec: str = 'subrip', title: str = '', forced: bool = False) -> Stream:
    return Stream(index, codec, lang, title, forced)


@pytest.mark.parametrize(
    ('streams', 'want'),
    [
        ([], None),
        ([S(2, 'eng')], None),
        ([S(2, codec='hdmv_pgs_subtitle')], None),  # image subtitles can't be read
        ([S(2, forced=True)], None),  # forced = only the foreign-language bits
        ([S(2, title='Korean (SDH)'), S(3)], 3),  # normal before SDH
        ([S(4), S(3, lang='ko')], 3),  # otherwise the first
        ([S(2, lang='eng'), S(5, lang='korean', codec='ass')], 5),
    ],
)
def test_pick_korean(streams: list[Stream], want: int | None) -> None:
    got = pick_korean(streams)
    assert (got.index if got else None) == want


def test_sidecar(tmp_path: Path) -> None:
    video = tmp_path / 'S01E01 - x [abc].mkv'
    assert sidecar(video) is None
    (tmp_path / 'S01E01 - x [abc].ko.srt').write_text('x')
    assert sidecar(video) == tmp_path / 'S01E01 - x [abc].ko.srt'


needs_ffmpeg = pytest.mark.skipif(not shutil.which('ffmpeg'), reason='needs ffmpeg (installed in CI and the image)')


def make_video(tmp_path: Path, tracks: list[tuple[str, str]]) -> Path:
    """A 1-second video with subtitle tracks [(language, srt text)]."""
    args = ['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=black:s=64x64:d=1']
    for i, (_, text) in enumerate(tracks):
        p = tmp_path / f'track{i}.srt'
        p.write_text(text, encoding='utf-8')
        args += ['-i', str(p)]
    args += ['-map', '0:v']
    for i, (lang, _) in enumerate(tracks):
        args += ['-map', f'{i + 1}:s', f'-metadata:s:s:{i}', f'language={lang}']
    out = tmp_path / 'video.mkv'
    subprocess.run([*args, '-c:s', 'srt', str(out)], check=True)
    return out


@needs_ffmpeg
def test_probe_and_extract_from_a_real_video(tmp_path: Path) -> None:
    video = make_video(
        tmp_path,
        [
            ('eng', '1\n00:00:00,000 --> 00:00:00,500\nHello\n'),
            ('kor', '1\n00:00:00,100 --> 00:00:00,900\n밥 먹었어?\n'),
        ],
    )
    streams = probe(video)
    assert [(s.language, s.codec) for s in streams] == [('eng', 'subrip'), ('kor', 'subrip')]
    ko = pick_korean(streams)
    assert ko is not None
    assert extract(video, ko) == [Line(100, 900, '밥 먹었어?')]
    assert korean_subtitles(video) == (f'stream:{ko.index}', [Line(100, 900, '밥 먹었어?')])


@needs_ffmpeg
def test_sidecar_when_no_korean_track(tmp_path: Path) -> None:
    video = make_video(tmp_path, [('eng', '1\n00:00:00,000 --> 00:00:00,500\nHello\n')])
    assert korean_subtitles(video) is None
    (tmp_path / 'video.ko.srt').write_text('1\n00:00:00,000 --> 00:00:00,800\n좋아요\n', encoding='utf-8')
    assert korean_subtitles(video) == ('file:video.ko.srt', [Line(0, 800, '좋아요')])


def test_missing_file_uses_sidecar_only(tmp_path: Path) -> None:
    (tmp_path / 'gone.ko.srt').write_text('1\n00:00:00,000 --> 00:00:00,800\n네\n', encoding='utf-8')
    assert korean_subtitles(tmp_path / 'gone.mkv') == ('file:gone.ko.srt', [Line(0, 800, '네')])
    assert korean_subtitles(tmp_path / 'nothing.mkv') is None
