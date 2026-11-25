# ADR-7: Typed API client generated from OpenAPI

Status: accepted (2026-11-25)

## Decision
openapi.json is exported from the backend (scripts/export_openapi.py) and turned into frontend/src/lib/api/schema.d.ts. The frontend only calls the API through that client. CI fails when the committed client doesn't match the backend (make api-check).

## Alternatives considered
Hand-written fetch calls: drift between backend and frontend goes unnoticed.
