from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from lmx import languages
from lmx.api.app import create_app
from lmx.config import Settings
from lmx.db import Database, migrate
from lmx.languages.korean import krdict
from lmx.users import default_user_id

FIXTURES = Path(__file__).parent / 'fixtures'


def fixture_rows() -> list[str]:
    """The hand-written test dictionary (export format; a literal \\n in the file is a newline in the value)."""
    lines = (FIXTURES / 'ko_dict_rows.txt').read_text(encoding='utf-8').splitlines()
    return [line.replace('\\n', '\n') for line in lines if line.strip()]


@pytest.fixture(scope='session', autouse=True)
def test_dictionaries(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """Every test runs with the small fixture dictionary (never the real one, never the network)."""
    d = tmp_path_factory.mktemp('dicts')
    krdict.build(fixture_rows(), d / 'ko-krdict.sqlite', {'source': 'test fixture'})
    mp = pytest.MonkeyPatch()
    mp.setenv('LMX_DICT_DIR', str(d))
    languages.get.cache_clear()
    yield d
    languages.get.cache_clear()
    mp.undo()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / 'data')


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as c:
        yield c


@pytest.fixture
def db(tmp_path: Path) -> Database:
    url = f'sqlite:///{tmp_path / "test.db"}'
    migrate(url)
    return Database(url)


@pytest.fixture
def session(db: Database) -> Iterator[Session]:
    with db.session() as s:
        yield s


@pytest.fixture
def uid(session: Session) -> int:
    return default_user_id(session)
