# ADR-8: Frontend: SvelteKit 3 + TypeScript, static build

Status: accepted (2026-11-25)

## Decision
Built to static files (adapter-static, SPA fallback) and served by the FastAPI container: one image, no Node at runtime. SvelteKit 3 notes: config goes in the sveltekit() Vite plugin (no svelte.config.js), imports use #lib (package.json subpath imports) instead of $lib.

## Alternatives considered
React/Next: heavier; a Node server at runtime.
