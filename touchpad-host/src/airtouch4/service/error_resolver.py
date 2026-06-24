"""Local-first AirTouch AC error resolver with optional remote cache."""

from __future__ import annotations

import json
import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..error_codes import describe_ac_error

ERROR_LOOKUP_ENDPOINT = "https://update.airtouch.com.au/info/error"
SPECIAL_GATEWAY_ERRORS = {65534, 65535}

RemoteFetcher = Callable[[int, int], dict[str, Any] | None]
NowProvider = Callable[[], float]


@dataclass(frozen=True)
class RemoteErrorResolverConfig:
    enabled: bool = False
    cache_path: Path | None = None
    cache_ttl_seconds: float = 172800.0
    endpoint: str = ERROR_LOOKUP_ENDPOINT
    timeout: float = 3.0
    device_id: str = ""
    serial_number: str = ""


class RemoteErrorResolver:
    """Resolve AC errors from APK tables first, then enrich from cached remote data."""

    def __init__(
        self,
        config: RemoteErrorResolverConfig,
        *,
        fetcher: RemoteFetcher | None = None,
        now: NowProvider = time.time,
    ) -> None:
        self.config = config
        self._fetcher = fetcher
        self._now = now
        self._lock = threading.RLock()
        self._queue: queue.Queue[tuple[int, int] | None] = queue.Queue()
        self._pending: set[tuple[int, int]] = set()
        self._cache: dict[str, dict[str, Any]] = {}
        self._last_error: str | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._load_cache()

    def describe(self, brand_id: int | None, code: int | None) -> dict[str, Any] | None:
        local = describe_ac_error(brand_id, code)
        if local is None:
            return None
        code_int = int(local["code"])
        if not self.config.enabled or brand_id is None or code_int in SPECIAL_GATEWAY_ERRORS:
            local["source"] = "local"
            return local

        brand_int = int(brand_id)
        key = self._cache_key(brand_int, code_int)
        with self._lock:
            cached = self._fresh_entry(key)
        if cached is not None:
            return self._merge_remote(local, cached, "remote_cache")

        self._enqueue(brand_int, code_int)
        local["source"] = "local_pending_remote"
        return local

    def resolve_now(self, brand_id: int, code: int) -> dict[str, Any] | None:
        """Synchronously resolve one code; used by tests and targeted diagnostics."""

        local = describe_ac_error(brand_id, code)
        if local is None:
            return None
        code_int = int(code)
        if not self.config.enabled or code_int in SPECIAL_GATEWAY_ERRORS:
            local["source"] = "local"
            return local
        try:
            entry = self._fetch_remote(int(brand_id), code_int)
        except Exception as exc:
            self._set_last_error(exc)
            local["source"] = "local_remote_failed"
            return local
        if entry is None:
            local["source"] = "local_remote_empty"
            return local
        self._store_entry(entry)
        return self._merge_remote(local, entry, "remote_live")

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "enabled": self.config.enabled,
                "cache_path": str(self.config.cache_path) if self.config.cache_path is not None else None,
                "cache_entries": len(self._cache),
                "pending": len(self._pending),
                "last_error": self._last_error,
            }

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None and self._thread.is_alive():
            self._queue.put(None)
            self._thread.join(timeout=2.0)

    def _enqueue(self, brand_id: int, code: int) -> None:
        item = (brand_id, code)
        with self._lock:
            if item in self._pending:
                return
            self._pending.add(item)
            if self._thread is None or not self._thread.is_alive():
                self._stop.clear()
                self._thread = threading.Thread(target=self._worker, name="airtouch-error-resolver", daemon=True)
                self._thread.start()
        self._queue.put(item)

    def _worker(self) -> None:
        while not self._stop.is_set():
            try:
                item = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if item is None:
                self._queue.task_done()
                break
            brand_id, code = item
            try:
                entry = self._fetch_remote(brand_id, code)
                if entry is not None:
                    self._store_entry(entry)
            except Exception as exc:  # pragma: no cover - live network path
                self._set_last_error(exc)
            finally:
                with self._lock:
                    self._pending.discard(item)
                self._queue.task_done()

    def _fetch_remote(self, brand_id: int, code: int) -> dict[str, Any] | None:
        if self._fetcher is not None:
            payload = self._fetcher(brand_id, code)
        else:
            params = urlencode({
                "id": self.config.device_id,
                "brand": brand_id,
                "error": code,
                "sn": self.config.serial_number,
            })
            request = Request(
                f"{self.config.endpoint}?{params}",
                headers={"User-Agent": "AirTouch4TouchpadHost/1.0"},
            )
            with urlopen(request, timeout=max(0.5, self.config.timeout)) as response:
                payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            return None
        display = str(payload.get("display") or "").strip()
        info = str(payload.get("info") or "").strip()
        if not display and not info:
            return None
        return {
            "brand_id": brand_id,
            "code": code,
            "display": display,
            "info": info,
            "brand": str(payload.get("brand") or "").strip(),
            "version": str(payload.get("version") or "").strip(),
            "fetched_at": self._now(),
        }

    def _store_entry(self, entry: dict[str, Any]) -> None:
        key = self._cache_key(int(entry["brand_id"]), int(entry["code"]))
        with self._lock:
            self._cache[key] = dict(entry)
            self._last_error = None
            self._save_cache()

    def _fresh_entry(self, key: str) -> dict[str, Any] | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        fetched_at = float(entry.get("fetched_at") or 0.0)
        if self._now() - fetched_at > max(60.0, self.config.cache_ttl_seconds):
            return None
        return dict(entry)

    def _merge_remote(self, local: dict[str, Any], entry: dict[str, Any], source: str) -> dict[str, Any]:
        result = dict(local)
        display = str(entry.get("display") or result.get("display_code") or "").strip()
        info = str(entry.get("info") or result.get("description") or "").strip()
        brand = str(result.get("brand") or entry.get("brand") or "").strip()
        result["display_code"] = display
        result["description"] = info
        result["source"] = source
        result["remote_version"] = str(entry.get("version") or "").strip()
        result["label"] = f"{brand} Code:{display}" if brand else f"Code: {display}"
        return result

    def _load_cache(self) -> None:
        path = self.config.cache_path
        if path is None or not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self._set_last_error(exc)
            return
        entries = data.get("entries") if isinstance(data, dict) else None
        if isinstance(entries, dict):
            self._cache = {str(key): value for key, value in entries.items() if isinstance(value, dict)}

    def _save_cache(self) -> None:
        path = self.config.cache_path
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "entries": self._cache}
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        temp_path.replace(path)

    def _set_last_error(self, exc: Exception) -> None:
        with self._lock:
            self._last_error = f"{type(exc).__name__}: {exc}"

    @staticmethod
    def _cache_key(brand_id: int, code: int) -> str:
        return f"{brand_id}:{code}"
