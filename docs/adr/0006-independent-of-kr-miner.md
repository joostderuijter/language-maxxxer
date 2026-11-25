# ADR-6: Fully independent of kr-miner

Status: accepted (replaces 'read-only coupling') (2026-11-25)

## Decision
No shared code package, no mount of kr-miner's data. kr-miner's ideas (1T, card model, idioms, sentence choice) are rebuilt as tested modules. Onboarding goes through product features any user gets: import a word list (CSV), import known words from Anki. When language-maxxer starts creating cards, kr-miner's auto-add is switched off (one writer per Anki deck).

## Alternatives considered
Read-only coupling to kr-miner's DB/transcripts: faster start, but ties the two together.
