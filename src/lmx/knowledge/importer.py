"""Import a word list ("lemma,state" lines), e.g. an export from another tool. Onboarding for new users."""

import csv
import io

from .events import EventKind

STATE_EVENTS: dict[str, EventKind | None] = {
    'known': EventKind.MARKED_KNOWN,
    '2': EventKind.MARKED_KNOWN,
    'learning': EventKind.CARD_ADDED,
    '0': EventKind.CARD_ADDED,
    'seen': EventKind.SEEN,
    '1': EventKind.SEEN,
    'ignored': EventKind.IGNORED,
    '3': EventKind.IGNORED,
    'unknown': None,
}


def parse(text: str) -> tuple[list[tuple[str, EventKind]], int]:
    """-> ([(lemma, event)], number of skipped lines). Blank lines and a header row are ignored."""
    items: list[tuple[str, EventKind]] = []
    skipped = 0
    for row in csv.reader(io.StringIO(text.lstrip('﻿'))):
        if not row or not row[0].strip():
            continue
        lemma = row[0].strip()
        state = row[1].strip().lower() if len(row) > 1 else ''
        if lemma.lower() in ('lemma', 'word') and state in ('state', 'status'):
            continue
        if state not in STATE_EVENTS:
            skipped += 1
            continue
        kind = STATE_EVENTS[state]
        if kind is not None:
            items.append((lemma, kind))
    return items, skipped
