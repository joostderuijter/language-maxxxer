"""Which language packs exist. Packs are created lazily (models can be slow to load) and cached."""

from collections.abc import Callable
from functools import cache

from .base import LanguagePack


def _korean() -> LanguagePack:
    from .korean import KoreanPack

    return KoreanPack()


FACTORIES: dict[str, tuple[str, Callable[[], LanguagePack]]] = {
    'ko': ('Korean', _korean),
}


def available() -> dict[str, str]:
    """code -> name"""
    return {code: name for code, (name, _) in FACTORIES.items()}


@cache
def get(code: str) -> LanguagePack:
    if code not in FACTORIES:
        raise KeyError(f'no language pack for {code!r}')
    return FACTORIES[code][1]()
