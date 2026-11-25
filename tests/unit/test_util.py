import pytest

from lmx import util
from lmx.util import cached_for


def test_cached_for_reuses_within_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [100.0]
    monkeypatch.setattr(util.time, 'monotonic', lambda: now[0])
    calls: list[int] = []
    get = cached_for(60, lambda: calls.append(1) or len(calls), fallback=lambda: -1)
    assert (get(), get()) == (1, 1)
    now[0] += 61
    assert get() == 2


def test_cached_for_survives_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [0.0]
    monkeypatch.setattr(util.time, 'monotonic', lambda: now[0])
    ok = [True]

    def fn() -> str:
        if not ok[0]:
            raise ConnectionError('jellyfin down')
        return 'fresh'

    get = cached_for(10, fn, fallback=lambda: 'fallback')
    ok[0] = False
    assert get() == 'fallback'  # never worked: fallback
    ok[0] = True
    assert get() == 'fresh'
    ok[0], now[0] = False, 20.0
    assert get() == 'fresh'  # stale beats broken
