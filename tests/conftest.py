from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from lmx.api.app import create_app
from lmx.config import Settings
from lmx.db import Database, migrate
from lmx.users import default_user_id


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
