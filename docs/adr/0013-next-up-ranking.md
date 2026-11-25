# ADR-13: "Next up" is a transparent formula (for now)

Status: accepted (2026-11-25)

## Decision
`lmx/recommend.py`: for every analysed episode the user hasn't fully watched (watch status read-only from Jellyfin,
cached 60 s; an unreachable Jellyfin falls back to the last good answer):

    score = 0.5 * coverage fit + 0.3 * learning value + 0.2 * continuation

- coverage fit: 1 inside 95-98 % known, 0 at 85 %, slowly down to 0.5 at 100 % (too easy beats too hard)
- learning value: share of sentences with exactly one new word; 30 % or more = full marks
- continuation: the half-watched episode, or the next episode after the last one watched, per show
At most 2 per show. Every recommendation carries its reasons ("96% known · 340 sentences with one new word · next
episode of Running Man") and an "Open in Jellyfin" link (LMX_JELLYFIN_PUBLIC_URL).

Stats come from the per-user cache (ADR-5 option A), so the landing page stays instant.

## Later
Learn the weights from behaviour (finished vs abandoned, lookups per minute), speaking rate (words per minute from
subtitle timings), YouTube candidates in the same list (discovery via yt-dlp, download via yt-shelf).

## Alternatives considered
A learned model from day one: no behaviour data yet, and an unexplainable list is hard to trust or debug.
