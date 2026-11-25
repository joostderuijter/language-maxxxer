import pytest

from lmx.content.names import clean_series, show_key

# the user's real Jellyfin series names (2026-11-25)
REAL = {
    'bae ten': 'bae ten',
    'I Am Solo 2019 1080p WEB-DL AAC2.0.H': 'I Am Solo',
    'I Am Solo 2023 BATCH KCW WEB-DL AAC.H': 'I Am Solo',
    'I Am Solo Love Forever S01 REPACK 1080p KCW WEB-DL AAC2.0.H': 'I Am Solo Love Forever',
    'I Am Solo Love Forever S06 REPACK 1080p KCW WEB-DL AAC2.0.H': 'I Am Solo Love Forever',
    'I am Solo, Love Forever': 'I am Solo, Love Forever',
    'Running Man': 'Running Man',
    'Running Man 2012 BATCH 1080p KCW WEB-DL AAC H': 'Running Man',
    'Running Man S01 1080p NF WEB-DL AAC2 0.H': 'Running Man',
    '나 혼자 산다 (2024 & 2025)': '나 혼자 산다',
    '나는솔로 (2024)': '나는솔로',
    '슈카월드': '슈카월드',
    'Keep Running': 'Keep Running',
}


@pytest.mark.parametrize(('raw', 'clean'), REAL.items())
def test_clean_series(raw: str, clean: str) -> None:
    assert clean_series(raw) == clean


def test_same_show_same_key() -> None:
    assert show_key('I am Solo, Love Forever') == show_key(
        'I Am Solo Love Forever S03 REPACK 1080p KCW WEB-DL AAC2.0.H'
    )
    assert show_key('Running Man S11 1080p NF WEB-DL AAC2 0.H') == show_key('Running Man') == 'runningman'
    assert show_key('I Am Solo 2019 1080p WEB-DL AAC2.0.H') != show_key('I Am Solo Love Forever')
    assert show_key('나 혼자 산다 (2024 & 2025)') == '나혼자산다'


@pytest.mark.parametrize('weird', ['', '   ', '(2024)', '...', 'S01'])
def test_never_empty(weird: str) -> None:
    assert clean_series(weird) and show_key(weird)
