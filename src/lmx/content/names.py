"""Show names from release folders: 'Running Man S11 1080p NF WEB-DL AAC2 0.H' -> 'Running Man' (from kr-miner)."""

import re

RELEASE_JUNK = re.compile(
    r'\s+(?:S\d{1,2}(?:E\d+)?|E\d{2,}|(?:19|20)\d{2}|BATCH|REPACK|\d{3,4}[pi]|WEB-?DL|HDTV|NF|KCW|AAC.*)\b.*$', re.I
)


def clean_series(name: str) -> str:
    """Release-folder junk and trailing '(…)' removed; never returns an empty name."""
    raw = (name or '').strip()
    out = raw.replace('.', ' ').strip()
    out = re.sub(r'(\s*\([^)]*\))+$', '', out).strip() or out  # 'Running Man (2011, E024-E074) (720p)'
    out = RELEASE_JUNK.sub('', out).strip()
    return re.sub(r'\s+', ' ', out) or raw or '?'


def show_key(name: str) -> str:
    """Same show across release folders: 'I am Solo, Love Forever' == 'I Am Solo Love Forever S01 …'."""
    return re.sub(r'[^0-9a-z가-힣]', '', clean_series(name).lower()) or '?'
