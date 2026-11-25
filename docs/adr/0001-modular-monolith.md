# ADR-1: Modular monolith, one container, one process

Status: accepted (2026-11-25)

## Decision
FastAPI backend with modules languages/, knowledge/, content/, ingest/, anki/, recommend/, api/. Modules talk through their public functions only, never through each other's tables. Background work runs as an in-process job queue persisted in the DB.

## Alternatives considered
Separate worker + Redis/Celery: overkill for one user; revisit for a cloud deployment.
