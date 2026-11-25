# ADR-11: Whisper on a shared GPU: first come, first served

Status: proposed (2026-11-25)

## Decision
kr-miner, yt-shelf and language-maxxer share one 6 GB GPU. Load the model only when enough GPU memory is free (nvidia-smi), unload when the queue is empty (same mechanism as yt-shelf).
