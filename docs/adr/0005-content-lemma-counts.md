# ADR-5: Content analysis stored as lemma counts per item

Status: accepted (not built yet) (2026-11-25)

## Decision
content_lemmas(item, lemma, count) + sentences with timestamps; coverage is a live SQL join against the user's knowledge, so it updates the moment a word becomes known.

## Alternatives considered
Precomputed coverage per item: stale after every learned word.
