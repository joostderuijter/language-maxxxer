#!/usr/bin/env bash
# Deploy to the home server: copy the code (never data/ or .env), rebuild, wait until healthy.
set -euo pipefail
HOST=joost@192.168.1.100
DIR=/srv/language-maxxer
URL=https://lm.joost.im
cd "$(dirname "$0")/.."
rsync -a --delete --exclude .git --exclude data --exclude .env --exclude .venv --exclude '.*_cache' \
  --exclude __pycache__ --exclude node_modules --exclude frontend/build --exclude frontend/.svelte-kit \
  --exclude frontend/test-results --exclude frontend/playwright-report --exclude .claude ./ "$HOST:$DIR/"
ssh "$HOST" "mkdir -p $DIR/data && cd $DIR && docker compose -f compose.server.yml up -d --build 2>&1 | tail -1 &&
  for i in \$(seq 90); do curl -skf -m 3 -o /dev/null $URL/api/health && echo up && exit 0; sleep 2; done;
  echo NOT UP; docker logs --tail 30 language-maxxer; exit 1"
