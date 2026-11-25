# ADR-12: Dictionaries are built into the Docker image

Status: accepted (2026-11-25, chosen by the user)

## Decision
Each language pack's dictionary is an SQLite file built at image build time from a pinned source: the Dockerfile's
`dicts` stage downloads it (`ADD --checksum=sha256:…`, so a changed upstream file fails the build) and runs the pack's
builder (`python -m lmx.languages.korean.krdict`, only needs pyarrow). The app reads it read-only from LMX_DICT_DIR.
A missing dictionary is not an error: lookups return nothing and the app still runs.

Korean: KRDict via huggingface.co/datasets/hac541309/basic_korean_dict, revision 1ba2996…, CC BY-SA 3.0 (attribution
in the app footer): 71,742 senses (words, phrases, grammar) + 3,194 idioms/proverbs, Korean + English, with level
(beginner/intermediate/advanced), Hanja and example sentences. 29 MB.

Tests never use the network or the real dictionary: a hand-written fixture (tests/fixtures/ko_dict_rows.txt) is built
for every test run. The real build is covered by the Docker build and the e2e suite.

## Alternatives considered
- Download on first start into /data: smaller image, but needs internet at startup and a slow first start.
- Commit the built file: simplest, but bloats the repo with every update.
