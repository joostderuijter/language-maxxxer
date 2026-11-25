# ADR-9: Tests on every layer; regressions must be caught

Status: accepted (2026-11-25)

## Decision
Static (ruff, pyright strict, svelte-check strict), unit (pytest, vitest), property-based (hypothesis), language golden + contract tests, migration tests, API integration (real app + temp SQLite), component tests, end-to-end against the built Docker image (Playwright, desktop + phone), CI on every push. Rules: a bug fix starts with a failing test; no feature without tests on its layer; coverage gate 90% (safety net, not the goal); known wrong behaviour is a strict xfail so a fix is noticed.
