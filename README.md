# language-maxxer

Self-hosted immersion language learning. Korean first.

```sh
docker compose up -d --build     # http://localhost:8000, data in ./data
make test                        # all test layers (needs uv + node 22)
make e2e                         # end-to-end against the built image (needs Docker)
```

See `CLAUDE.md` for the project notes and `docs/adr/` for the architecture decisions.
