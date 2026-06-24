from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from airtouch4.service.error_resolver import RemoteErrorResolver, RemoteErrorResolverConfig


class RemoteErrorResolverTests(unittest.TestCase):
    def test_disabled_resolver_returns_local_apk_label(self) -> None:
        resolver = RemoteErrorResolver(RemoteErrorResolverConfig(enabled=False))

        error = resolver.describe(4608, 250)

        self.assertIsNotNone(error)
        self.assertEqual(error["label"], "Samsung Code:EA")
        self.assertEqual(error["source"], "local")

    def test_fresh_cache_enriches_local_label_and_description(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "error-cache.json"
            cache_path.write_text(
                json.dumps({
                    "version": 1,
                    "entries": {
                        "2048:149": {
                            "brand_id": 2048,
                            "code": 149,
                            "display": "U4",
                            "info": "Communication error between indoor and outdoor unit.",
                            "version": "1",
                            "fetched_at": 1000.0,
                        },
                    },
                }),
                encoding="utf-8",
            )
            resolver = RemoteErrorResolver(
                RemoteErrorResolverConfig(enabled=True, cache_path=cache_path, cache_ttl_seconds=3600.0),
                now=lambda: 1010.0,
            )

            error = resolver.describe(2048, 149)

            self.assertIsNotNone(error)
            self.assertEqual(error["label"], "Daikin Code:U4")
            self.assertEqual(error["description"], "Communication error between indoor and outdoor unit.")
            self.assertEqual(error["source"], "remote_cache")

    def test_gateway_errors_do_not_use_remote_resolution(self) -> None:
        called = False

        def fetcher(brand_id: int, code: int) -> dict[str, object] | None:
            nonlocal called
            called = True
            return {"display": "remote", "info": "remote"}

        resolver = RemoteErrorResolver(
            RemoteErrorResolverConfig(enabled=True),
            fetcher=fetcher,
        )

        error = resolver.resolve_now(4608, 65534)

        self.assertIsNotNone(error)
        self.assertFalse(called)
        self.assertEqual(error["display_code"], "FFFE")
        self.assertEqual(error["source"], "local")

    def test_resolve_now_writes_persistent_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "error-cache.json"

            def fetcher(brand_id: int, code: int) -> dict[str, object] | None:
                return {
                    "display": "EA",
                    "info": "Wired remote controller COM2 option setting error.",
                    "version": "1",
                }

            resolver = RemoteErrorResolver(
                RemoteErrorResolverConfig(enabled=True, cache_path=cache_path),
                fetcher=fetcher,
                now=lambda: 2000.0,
            )

            error = resolver.resolve_now(4608, 250)
            data = json.loads(cache_path.read_text(encoding="utf-8"))

            self.assertIsNotNone(error)
            self.assertEqual(error["description"], "Wired remote controller COM2 option setting error.")
            self.assertEqual(data["entries"]["4608:250"]["display"], "EA")
            self.assertEqual(data["entries"]["4608:250"]["info"], "Wired remote controller COM2 option setting error.")


if __name__ == "__main__":
    unittest.main()
