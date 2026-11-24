import json
import tempfile
import time
import unittest
from pathlib import Path

from collector.client import (
    CollectorConfig,
    HttpStatusError,
    SourceSpec,
    collect_batch,
    write_snapshot_atomic,
)


class TestResilientCollector(unittest.TestCase):
    def test_recovers_from_transient_http_403(self):
        attempts = {"count": 0}

        def flaky_primary(item_id: str):
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise HttpStatusError(403, "Temporary 403")
            return {"id": item_id, "source_timestamp": time.time()}

        cfg = CollectorConfig(max_retries=3, base_backoff_s=0.05)
        results = collect_batch(
            ["GAME-1"],
            [SourceSpec("primary", flaky_primary)],
            config=cfg,
            sleep_fn=lambda _: None,
        )
        self.assertTrue(results[0].ok)
        self.assertEqual(results[0].source, "primary")
        self.assertEqual(results[0].attempts, 2)

    def test_falls_back_when_primary_exhausted_and_isolates_failures(self):
        def always_403(_item_id: str):
            raise HttpStatusError(403, "Blocked")

        def secondary(item_id: str):
            if item_id == "BAD-ITEM":
                raise HttpStatusError(404, "Missing")
            return {"id": item_id, "source_timestamp": time.time()}

        cfg = CollectorConfig(max_retries=2, base_backoff_s=0.05)
        results = collect_batch(
            ["GOOD-ITEM", "BAD-ITEM"],
            [SourceSpec("primary", always_403), SourceSpec("secondary", secondary)],
            config=cfg,
            sleep_fn=lambda _: None,
        )
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0].ok)
        self.assertEqual(results[0].source, "secondary")
        self.assertFalse(results[1].ok)
        self.assertIn("HTTP 404", results[1].error or "")

    def test_rejects_stale_payload_and_writes_atomic_json(self):
        stale_ts = time.time() - 120.0

        def stale_source(item_id: str):
            return {"id": item_id, "source_timestamp": stale_ts}

        def fresh_fallback(item_id: str):
            return {"id": item_id, "source_timestamp": time.time()}

        cfg = CollectorConfig(max_retries=1, max_source_age_s=30.0)
        results = collect_batch(
            ["ITEM-A"],
            [SourceSpec("stale", stale_source), SourceSpec("fresh", fresh_fallback)],
            config=cfg,
            sleep_fn=lambda _: None,
        )
        self.assertTrue(results[0].ok)
        self.assertEqual(results[0].source, "fresh")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "snapshot.json"
            write_snapshot_atomic(out_path, results)
            data = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(data["succeeded"], 1)
            self.assertEqual(data["failed"], 0)
            self.assertEqual(data["items"][0]["item_id"], "ITEM-A")


if __name__ == "__main__":
    unittest.main()
