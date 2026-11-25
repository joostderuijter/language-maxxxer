"""Settings from the environment (LMX_*). compose.yml lists every one with its default."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='LMX_')

    data_dir: Path = Path('data')
    database_url: str = ''  # default: sqlite file in data_dir
    static_dir: Path | None = None  # built frontend; None = API only (dev, tests)
    dict_dir: Path = Path('dicts')  # dictionaries built into the image (ADR-12), e.g. ko-krdict.sqlite

    @property
    def db_url(self) -> str:
        return self.database_url or f'sqlite:///{self.data_dir / "lmx.db"}'
