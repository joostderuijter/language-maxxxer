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

## Done since (2026-11-25, later)
- Library list from a per-user stats cache (ADR-5 option A: triggers on word_knowledge -> stats_dirty -> StatsWorker),
  show names cleaned/merged (series_key), index on occurrences.word_id. Library list 6 s -> 0.06 s.
- Next up (step 5, ADR-13): `recommend.py` + `/api/library/next` + NextUp on the landing page; watch status from
  Jellyfin (read-only, cached 60 s via util.cached_for).
- Agreed next (user, 2026-11-25): YouTube discovery via yt-dlp (channels you have + added ones; subtitles only, no
  video; auto-generated subs allowed as a rough estimate, badge), download through yt-shelf's API (optional setting).
  Then a player v1 (YouTube embed: exact time + pause -> interactive subtitles, popup dictionary, cards). Then Whisper.

## Where we paused (2026-11-25)
- Library live; first ingestion was running on the server (~1,977 Korean episodes from Jellyfin; 261 without Korean
  subtitles = shows kr-miner transcribed with its own Whisper, which language-maxxer can't see by design).
- Open question for the user: next do step 5 "Next up" (ADR-13, transparent ranking) or Whisper for episodes without
  subtitles (ADR-11, shared GPU first come first served, mark Whisper text as lower confidence) first.
- Known issue (strict xfail): 배신당했어 -> 배신 + 당하다 (needs a 당하다 derivation rule).

## Roadmap
v0.1 (2026-11-25): Korean pack, knowledge (events), CSV import, progress page, analyzer box. User's kr-miner word list
imported (20,122 words, 6,851 known) on the server via the CSV import.
Done: dictionary (KRDict built into the image, ADR-12; `GET /api/dictionary/{code}?lemma=…`, WordPanel; one-syllable
nouns are weak only when the dictionary lacks them). Local dev: build `dicts/ko-krdict.sqlite` with
`PYTHONPATH=src uv run --no-project --with pyarrow python -m lmx.languages.korean.krdict <parquet> dicts/ko-krdict.sqlite`.
KRDict also has 1,374 grammar expressions (kind='grammar') = the source for the grammar-point list later.
In progress: content library (user OK'd 2026-11-25: read-only Jellyfin key (kr-miner's for now) + read-only media
mounts; subtitles only this round, Whisper later; analysis versioned; transparent "next up" formula = ADR-13).
  Step 1 DONE: tables content_items/sentences/words/word_lemmas/occurrences (migration 0002), `content/store.py`
  (save_analysis, live stats per user: coverage, new words, 1T sentences; property test = same rules as
  comprehension.py). A sentence = one subtitle line.
  Step 2 DONE: `content/subtitles.py` (parse_srt, probe/pick_korean/extract via ffprobe+ffmpeg, sidecar .ko.srt;
  sidecar first (cheap), then embedded track). ffmpeg in the image + CI.
  Step 3 DONE: Jellyfin is the ONLY source (the yt-shelf folder is a Jellyfin library too): `content/jellyfin.py`
  (episodes with a Korean subtitle/audio track), `content/library.py` (sync: add/update/remove, re-analyse on file
  change / new Korean subs / errors; pending = new or analysed with another `pack.version`; analyze; Ingest worker
  with run_once/trigger/state). LanguagePack.version (Korean: ko<RULES>-kiwi<ver>-dict<rev>). Step 3 (old text): sources (Jellyfin client, folder) +
  background ingestion + analyzer version.
  Step 4 DONE: `api/library.py` router (status, sync, series, episodes with live stats, new words per episode),
  Library pages (/library, /library/[series]) with coverage bars, new-word chips -> WordPanel. Server: .env has
  LMX_JELLYFIN_API_KEY (copied from kr-miner's key), media mounted read-only at Jellyfin's paths.
  Step 4 (old): API + Library page. Step 5: "next up" (ADR-13).
Then: content library (Jellyfin + folders) with
lemma counts + coverage + "next up", Anki import of known words, reader. Later: grammar points (curated TOPIK list,
Kiwi patterns), vocabulary-size test, quizzes, automatic cards + feedback model, starter path (import a deck like
Refold KO1K as curriculum; generate an i+1-ordered starter set from content), YouTube discovery (subtitles only),
second language.
