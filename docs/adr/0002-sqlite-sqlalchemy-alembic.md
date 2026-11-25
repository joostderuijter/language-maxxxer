# ADR-2: SQLite + SQLAlchemy 2.0 + Alembic migrations; multi-user ready

Status: accepted (2026-11-25)

## Decision
Schema changes only via versioned Alembic migrations (tested: models == migrations, down/up, data survives). Every knowledge table has user_id (single default user 'me' for now); content tables will be shared between users.

## Alternatives considered
Postgres from the start: more robust, but an extra container and more backup hassle for no gain now. SQLAlchemy keeps the switch cheap.
