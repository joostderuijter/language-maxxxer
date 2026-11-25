# ADR-4: Knowledge as an append-only event log plus derived state

Status: accepted (2026-11-25)

## Decision
knowledge_events (never updated) -> word_knowledge (state + confidence) via the pure reducer knowledge.events.apply. rebuild() recomputes everything from events, so reducer changes apply to history and every state is explainable.

## Alternatives considered
Only a status per word (kr-miner): simpler, but loses history that quizzes and vocabulary estimation need.
