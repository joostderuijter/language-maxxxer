# Architecture decisions

Proposed decisions are discussed with the user (a software engineer) before they are built.

- [ADR-1: Modular monolith, one container, one process](0001-modular-monolith.md): accepted
- [ADR-2: SQLite + SQLAlchemy 2.0 + Alembic migrations; multi-user ready](0002-sqlite-sqlalchemy-alembic.md): accepted
- [ADR-3: Language packs behind a Protocol with a shared contract suite](0003-language-packs.md): accepted
- [ADR-4: Knowledge as an append-only event log plus derived state](0004-knowledge-event-log.md): accepted
- [ADR-5: Content analysis stored as lemma counts per item](0005-content-lemma-counts.md): accepted (not built yet)
- [ADR-6: Fully independent of kr-miner](0006-independent-of-kr-miner.md): accepted (replaces 'read-only coupling')
- [ADR-7: Typed API client generated from OpenAPI](0007-generated-api-client.md): accepted
- [ADR-8: Frontend: SvelteKit 3 + TypeScript, static build](0008-sveltekit-static.md): accepted
- [ADR-9: Tests on every layer; regressions must be caught](0009-testing.md): accepted
- [ADR-10: Own Anki note type and deck](0010-anki-note-type.md): proposed
- [ADR-11: Whisper on a shared GPU: first come, first served](0011-gpu-sharing.md): proposed
- [ADR-12: Dictionaries are built into the Docker image](0012-dictionaries-in-image.md): accepted
- [ADR-13: "Next up" is a transparent formula (for now)](0013-next-up-ranking.md): accepted
