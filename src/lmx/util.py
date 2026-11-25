"""Small helpers."""

import threading
import time
from collections.abc import Callable


def cached_for[T](seconds: float, fn: Callable[[], T], fallback: Callable[[], T]) -> Callable[[], T]:
    """fn() at most once per `seconds`; on an error the last good value (or fallback()) is returned instead, so a
    slow or unreachable dependency (Jellyfin) never breaks a page."""
    lock = threading.Lock()
    state: dict[str, tuple[float, T]] = {}

    def get() -> T:
        with lock:
            hit = state.get('v')
            if hit and time.monotonic() - hit[0] < seconds:
                return hit[1]
            try:
                value = fn()
            except Exception as e:
                print(f'cached_for: {e!r}')
                return hit[1] if hit else fallback()
            state['v'] = (time.monotonic(), value)
            return value

    return get
