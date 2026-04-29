import threading
import time
from typing import Any, Callable


_CACHE_LOCK = threading.RLock()
_CACHE: dict[str, tuple[float, Any]] = {}
_LAST_PRUNE_AT = 0.0
_PRUNE_INTERVAL_SECONDS = 30.0


def build_cache_key(*parts: Any) -> str:
    normalized_parts = [str(part).strip() for part in parts if str(part).strip()]
    return "::".join(normalized_parts)


def cached_call(key: str, ttl_seconds: int | float, factory: Callable[[], Any]) -> Any:
    ttl = float(ttl_seconds or 0)
    if ttl <= 0:
        return factory()

    now = time.monotonic()
    with _CACHE_LOCK:
        cached_entry = _CACHE.get(key)
        if cached_entry is not None:
            expires_at, value = cached_entry
            if expires_at > now:
                return value
            _CACHE.pop(key, None)

    value = factory()
    with _CACHE_LOCK:
        _CACHE[key] = (time.monotonic() + ttl, value)
        _maybe_prune_locked()
    return value


def invalidate_cache_key(key: str) -> None:
    with _CACHE_LOCK:
        _CACHE.pop(str(key or "").strip(), None)


def invalidate_cache_prefix(prefix: str) -> int:
    normalized_prefix = str(prefix or "").strip()
    if not normalized_prefix:
        return 0

    with _CACHE_LOCK:
        keys_to_delete = [key for key in _CACHE.keys() if key.startswith(normalized_prefix)]
        for key in keys_to_delete:
            _CACHE.pop(key, None)
    return len(keys_to_delete)


def _maybe_prune_locked() -> None:
    global _LAST_PRUNE_AT

    now = time.monotonic()
    if now - _LAST_PRUNE_AT < _PRUNE_INTERVAL_SECONDS:
        return

    expired_keys = [key for key, (expires_at, _) in _CACHE.items() if expires_at <= now]
    for key in expired_keys:
        _CACHE.pop(key, None)

    _LAST_PRUNE_AT = now
