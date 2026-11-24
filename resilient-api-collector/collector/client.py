"""Resilient HTTP/API data collector with retry recovery, fallback, and fault isolation."""
from __future__ import annotations

import json
import logging
import os
import random
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = frozenset({403, 408, 429, 500, 502, 503, 504})

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


class CollectorError(Exception):
    """Base error for resilient collector failures."""


class HttpStatusError(CollectorError):
    """Raised when an HTTP endpoint returns an error status code."""

    def __init__(self, status_code: int, message: str = "") -> None:
        super().__init__(f"HTTP {status_code}: {message}".strip())
        self.status_code = status_code


class StaleDataError(CollectorError):
    """Raised when fetched payload exceeds freshness SLA thresholds."""


@dataclass(frozen=True)
class SourceSpec:
    """Defines a named API source and how to fetch an item payload."""

    name: str
    fetcher: Callable[[str], Mapping[str, Any]]


@dataclass(frozen=True)
class CollectorConfig:
    """Runtime configuration for retries, backoff, and freshness limits."""

    max_retries: int = 3
    base_backoff_s: float = 0.5
    max_backoff_s: float = 8.0
    max_source_age_s: float = 30.0
    max_receipt_age_s: float = 6.0


@dataclass
class ItemResult:
    """Result record for a single item after primary/fallback collection."""

    item_id: str
    ok: bool
    source: str | None = None
    payload: Mapping[str, Any] | None = None
    attempts: int = 0
    error: str | None = None
    collected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def default_http_json_get(
    url: str,
    headers: Mapping[str, str] | None = None,
    timeout_s: float = 10.0,
) -> dict[str, Any]:
    """Fetch and decode JSON from a URL using urllib with browser-like headers."""
    merged_headers = dict(DEFAULT_HEADERS)
    if headers:
        merged_headers.update(headers)

    req = urllib.request.Request(url, headers=merged_headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        raise HttpStatusError(exc.code, exc.reason) from exc
    except urllib.error.URLError as exc:
        raise CollectorError(f"Network error: {exc.reason}") from exc


def validate_freshness(
    payload: Mapping[str, Any],
    max_source_age_s: float,
    now_ts: float | None = None,
) -> float:
    """Validate that payload['source_timestamp'] is within max_source_age_s.

    Returns the computed age in seconds.
    """
    current = time.time() if now_ts is None else now_ts
    source_ts = payload.get("source_timestamp")
    if source_ts is None:
        return 0.0

    age_s = current - float(source_ts)
    if age_s > max_source_age_s:
        raise StaleDataError(
            f"Payload age {age_s:.2f}s exceeds limit {max_source_age_s:.2f}s"
        )
    return age_s


def fetch_with_retry(
    source: SourceSpec,
    item_id: str,
    config: CollectorConfig,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> tuple[Mapping[str, Any], int]:
    """Fetch an item from one source with exponential backoff + jitter on 403/429/5xx."""
    last_error: Exception | None = None
    for attempt in range(1, config.max_retries + 1):
        try:
            payload = source.fetcher(item_id)
            validate_freshness(payload, config.max_source_age_s)
            return payload, attempt
        except HttpStatusError as exc:
            last_error = exc
            if exc.status_code not in RETRYABLE_STATUS_CODES or attempt == config.max_retries:
                break
            delay = min(
                config.max_backoff_s,
                config.base_backoff_s * (2 ** (attempt - 1)),
            )
            jitter = random.uniform(0.0, delay * 0.25)
            logger.warning(
                "[%s] %s returned HTTP %s (attempt %d/%d); retrying in %.2fs",
                item_id,
                source.name,
                exc.status_code,
                attempt,
                config.max_retries,
                delay + jitter,
            )
            sleep_fn(delay + jitter)
        except (StaleDataError, CollectorError) as exc:
            last_error = exc
            logger.warning(
                "[%s] %s failed validation/fetch (attempt %d/%d): %s",
                item_id,
                source.name,
                attempt,
                config.max_retries,
                exc,
            )
            if attempt == config.max_retries:
                break
            sleep_fn(min(config.max_backoff_s, config.base_backoff_s))

    assert last_error is not None
    raise last_error


def collect_batch(
    item_ids: list[str],
    sources: list[SourceSpec],
    config: CollectorConfig | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> list[ItemResult]:
    """Collect a batch of items with per-item fault isolation and source fallback."""
    cfg = config or CollectorConfig()
    results: list[ItemResult] = []

    for item_id in item_ids:
        total_attempts = 0
        errors: list[str] = []
        succeeded = False

        for source in sources:
            try:
                payload, attempts = fetch_with_retry(
                    source, item_id, cfg, sleep_fn=sleep_fn
                )
                total_attempts += attempts
                results.append(
                    ItemResult(
                        item_id=item_id,
                        ok=True,
                        source=source.name,
                        payload=payload,
                        attempts=total_attempts,
                    )
                )
                succeeded = True
                break
            except Exception as exc:  # noqa: BLE001 — isolate per-item failure
                total_attempts += cfg.max_retries
                errors.append(f"{source.name}: {exc}")

        if not succeeded:
            combined = "; ".join(errors)
            logger.error("[%s] All sources failed: %s", item_id, combined)
            results.append(
                ItemResult(
                    item_id=item_id,
                    ok=False,
                    attempts=total_attempts,
                    error=combined,
                )
            )

    return results


def write_snapshot_atomic(output_path: Path, results: list[ItemResult]) -> None:
    """Write collection results atomically so readers never observe partial JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "succeeded": sum(1 for r in results if r.ok),
        "failed": sum(1 for r in results if not r.ok),
        "items": [
            {
                "item_id": r.item_id,
                "ok": r.ok,
                "source": r.source,
                "attempts": r.attempts,
                "error": r.error,
                "collected_at": r.collected_at,
                "payload": dict(r.payload) if r.payload is not None else None,
            }
            for r in results
        ],
    }

    fd, tmp_name = tempfile.mkstemp(
        dir=str(output_path.parent), prefix=".tmp_", suffix=".json"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(serializable, fh, indent=2)
        os.replace(tmp_name, output_path)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
