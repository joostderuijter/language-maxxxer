# language-maxxer

Self-hosted, immersion-focused language learning: what you know (words, later grammar), content at your level
(Jellyfin, YouTube), a reader with a pop-up dictionary, automatic Anki cards with a feedback model, quizzes that feed
the recommendations. Inspired by kr-miner (same user, `~/workspace/kr-miner`) but a separate product. Comparable to
Migaku / Kimchi Reader. Korean first; the architecture is multilingual (language packs).

## Working agreements (user, 2026-11-25)
- The user is a software engineer: **propose important architecture decisions** (docs/adr/) and discuss before building.
- **Tests on every layer, thorough. Regression bugs must be caught by the suite.** A bug fix starts with a failing
  test. No feature without tests on its layer. Known wrong behaviour = strict xfail (golden files: `known_issues`).
- Single user now, multi-user later: `user_id` on every knowledge table (default user 'me'), content shared.
- Packaged as one Docker image, easy to run locally (`docker compose up`). Cloud architecture only when it comes up.
- Local only: no cloud LLMs or paid APIs (same principle as kr-miner).
- No video player in the app for now (the user watches in Infuse on an Apple TV via Jellyfin).

## Layout
- `src/lmx/`: `config.py` (LMX_* env), `db.py` (engine, sessions, `migrate()`), `models.py`, `migrations/` (Alembic,
  inside the package so it ships in the image), `knowledge/` (events reducer, service, CSV importer),
  `languages/` (Protocol, registry, `korean/` = Kiwi), `api/` (FastAPI app factory + schemas), `users.py`.
- `frontend/`: SvelteKit 3 + TS (static). `src/lib/api/` = generated client (`schema.d.ts`) + thin wrappers.
  SvelteKit 3: config in `vite.config.ts` (`sveltekit({adapter})`), imports via `#lib/...` (no `$lib`).
- `tests/`: unit, languages (contract + golden), db (migrations), api (integration). `frontend/src/**/*.test.ts`
  (vitest), `frontend/e2e/` (Playwright against a running server; serial, tests only check changes they cause).
- `docs/adr/`: decisions.

## Commands
- `make test`: ruff, pyright strict, pytest (+coverage >= 90%), API drift check, svelte-check, vitest.
- `make e2e`: builds the image, runs it fresh, Playwright desktop + phone. Needs Docker.
- `make api-client` after changing the API (commit openapi.json + schema.d.ts).
- Dev: `uv run python -m lmx` (port 8000) + `cd frontend && npm run dev` (proxies /api).
- npm installs use `--before=<date two weeks ago>`; `openapi-typescript` has an npm override to accept TS 6.

## Deployment
- Home server: `/srv/language-maxxer` (container `language-maxxer`), https://lm.joost.im via caddy-docker-proxy
  labels (`tls internal`, Tailscale only, **no auth yet: never expose publicly**). `scripts/deploy.sh` = rsync (never
  `data/`/.env) + `docker compose -f compose.server.yml up -d --build` + health wait. Locally: `compose.yml` (port 8000).
- Never run the e2e suite against the live server (it imports test words into real data).
- Server rules (same as kr-miner/yt-shelf): only `/srv/language-maxxer` + this container; announce changes; no sudo.
- GitHub: `joostderuijter/language-maxxxer` (private; note the three x's), CI = .github/workflows/ci.yml.

## Roadmap
v0.1 (2026-11-25): Korean pack, knowledge (events), CSV import, progress page, analyzer box. User's kr-miner word list
imported (20,122 words, 6,851 known) on the server via the CSV import.
Done: dictionary (KRDict built into the image, ADR-12; `GET /api/dictionary/{code}?lemma=…`, WordPanel; one-syllable
nouns are weak only when the dictionary lacks them). Local dev: build `dicts/ko-krdict.sqlite` with
`PYTHONPATH=src uv run --no-project --with pyarrow python -m lmx.languages.korean.krdict <parquet> dicts/ko-krdict.sqlite`.
KRDict also has 1,374 grammar expressions (kind='grammar') = the source for the grammar-point list later.
Next: content library (Jellyfin + folders) with
lemma counts + coverage + "next up", Anki import of known words, reader. Later: grammar points (curated TOPIK list,
Kiwi patterns), vocabulary-size test, quizzes, automatic cards + feedback model, starter path (import a deck like
Refold KO1K as curriculum; generate an i+1-ordered starter set from content), YouTube discovery (subtitles only),
second language.
