"""Settings from the environment (LMX_*). compose.yml lists every one with its default."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='LMX_')

    data_dir: Path = Path('data')
    database_url: str = ''  # default: sqlite file in data_dir
    static_dir: Path | None = None  # built frontend; None = API only (dev, tests)
    dict_dir: Path = Path('dicts')  # dictionaries built into the image (ADR-12), e.g. ko-krdict.sqlite
    jellyfin_url: str = 'http://jellyfin:8096'
    jellyfin_api_key: str = ''  # read-only use; empty = no library
    jellyfin_public_url: str = ''  # how YOU open Jellyfin (e.g. https://tv.joost.im), for "Open in Jellyfin" links
    jellyfin_user: str = ''  # whose watch status to use; empty = the first administrator
    library_language: str = 'ko'  # the language Jellyfin's content is analysed as
    library_interval_s: float = 3600  # how often to sync with Jellyfin (plus on demand)
    library_autostart: bool = True  # start the background worker (tests turn it off)

    @property
    def db_url(self) -> str:
        return self.database_url or f'sqlite:///{self.data_dir / "lmx.db"}'
