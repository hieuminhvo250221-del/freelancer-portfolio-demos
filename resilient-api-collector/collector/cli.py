"""CLI demo runner for the Resilient API Collector."""
from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

from collector.client import (
    CollectorConfig,
    HttpStatusError,
    SourceSpec,
    collect_batch,
    write_snapshot_atomic,
)


def _simulated_primary(item_id: str, state: dict[str, int]) -> dict[str, object]:
    """Simulate transient HTTP 403 and per-item failures for offline demo."""
    calls = state.get(item_id, 0) + 1
    state[item_id] = calls

    if item_id == "ITEM-101" and calls == 1:
        raise HttpStatusError(403, "Forbidden (rate/header blip)")
    if item_id == "ITEM-102":
        raise HttpStatusError(403, "Primary blocked for ITEM-102")
    if item_id == "ITEM-999":
        raise HttpStatusError(404, "Not Found")

    return {
        "id": item_id,
        "status": "active",
        "price": 49.90,
        "source_timestamp": time.time(),
    }


def _simulated_fallback(item_id: str) -> dict[str, object]:
    if item_id == "ITEM-999":
        raise HttpStatusError(404, "Not Found on fallback")
    return {
        "id": item_id,
        "status": "active",
        "price": 49.90,
        "source_timestamp": time.time(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Resilient API Collector demo")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/snapshot.json"),
        help="Destination path for atomic JSON snapshot",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    state: dict[str, int] = {}
    sources = [
        SourceSpec("primary_api", lambda item: _simulated_primary(item, state)),
        SourceSpec("fallback_api", _simulated_fallback),
    ]
    config = CollectorConfig(max_retries=2, base_backoff_s=0.1, max_source_age_s=30.0)

    results = collect_batch(["ITEM-101", "ITEM-102", "ITEM-999"], sources, config=config)
    write_snapshot_atomic(args.output, results)

    for res in results:
        status = f"OK via {res.source}" if res.ok else f"FAILED ({res.error})"
        print(f" - {res.item_id}: {status} [attempts={res.attempts}]")

    print(f"Snapshot written atomically to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
