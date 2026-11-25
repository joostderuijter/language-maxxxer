"""Write the API's OpenAPI schema to openapi.json (input for the generated TypeScript client, ADR-7)."""

import json
import sys
import tempfile
from pathlib import Path

from lmx.api.app import create_app
from lmx.config import Settings

with tempfile.TemporaryDirectory() as d:
    schema = create_app(Settings(data_dir=Path(d))).openapi()
out = Path(sys.argv[1] if len(sys.argv) > 1 else 'openapi.json')
out.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
