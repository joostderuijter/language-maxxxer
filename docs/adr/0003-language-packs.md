# ADR-3: Language packs behind a Protocol with a shared contract suite

Status: accepted (2026-11-25)

## Decision
LanguagePack.analyze(text) -> [Token(surface, start, end, lemmas, pos, key, weak)]. Every pack must pass tests/languages/contract.py (spans match the text, non-empty unique lemmas, deterministic, batch == single) plus its own golden file. Korean = Kiwi (rules learned in kr-miner).

## Alternatives considered
Language-specific code paths everywhere: fast for Korean, impossible to add a second language.
