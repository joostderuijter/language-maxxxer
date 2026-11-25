"""uv run python -m lmx [--host 0.0.0.0] [--port 8000]"""

import argparse

import uvicorn

from .api.app import create_app


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=8000)
    a = ap.parse_args()
    uvicorn.run(create_app(), host=a.host, port=a.port)


if __name__ == '__main__':
    main()
