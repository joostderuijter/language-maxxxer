# ADR-10: Own Anki note type and deck

Status: proposed (2026-11-25)

## Decision
language-maxxer gets its own note type ('Language Maxxer Sentence') and deck ('Language Maxxer::<language>'), created once from the laptop via a generated .apkg (one full sync); after that the headless writer never needs a schema change.

## Alternatives considered
Reuse 'Kimchi Sentence Mining' (no full sync, but tied to someone else's fields).
