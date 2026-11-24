"""REST API HTTP server for order validation and live rule toggling."""
from __future__ import annotations

import json
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from app.db import fetch_rules_map, set_rule_enabled
from app.validator import validate_order


def create_handler(conn: sqlite3.Connection) -> type[BaseHTTPRequestHandler]:
    """Bind a SQLite connection to a thread-safe HTTP request handler."""

    class OrderValidationHandler(BaseHTTPRequestHandler):
        def _send_json(self, status: int, body: Any) -> None:
            raw = json.dumps(body, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _read_json_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            return json.loads(raw)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path.rstrip("/") or "/"
            if path == "/health":
                self._send_json(HTTPStatus.OK, {"status": "ok"})
                return

            if path == "/rules":
                self._send_json(HTTPStatus.OK, {"rules": fetch_rules_map(conn)})
                return

            if path == "/logs":
                rows = conn.execute(
                    """
                    SELECT order_id, customer_id, approved, risk_level, issues_json, created_at
                    FROM validation_logs
                    ORDER BY id DESC
                    LIMIT 25
                    """
                ).fetchall()
                logs = [
                    {
                        "order_id": r["order_id"],
                        "customer_id": r["customer_id"],
                        "approved": bool(r["approved"]),
                        "risk_level": r["risk_level"],
                        "issues": json.loads(r["issues_json"]),
                        "created_at": r["created_at"],
                    }
                    for r in rows
                ]
                self._send_json(HTTPStatus.OK, {"logs": logs})
                return

            if path.startswith("/orders/"):
                order_id = path.split("/orders/", 1)[1]
                row = conn.execute(
                    """
                    SELECT order_id, customer_id, approved, risk_level, issues_json, created_at
                    FROM validation_logs
                    WHERE order_id = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (order_id,),
                ).fetchone()
                if row is None:
                    self._send_json(
                        HTTPStatus.NOT_FOUND, {"error": f"Order {order_id} not found"}
                    )
                    return
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "order_id": row["order_id"],
                        "customer_id": row["customer_id"],
                        "approved": bool(row["approved"]),
                        "risk_level": row["risk_level"],
                        "issues": json.loads(row["issues_json"]),
                        "created_at": row["created_at"],
                    },
                )
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Endpoint not found"})

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path.rstrip("/")
            if path != "/orders/validate":
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Endpoint not found"})
                return
            try:
                payload = self._read_json_body()
            except json.JSONDecodeError as exc:
                self._send_json(
                    HTTPStatus.BAD_REQUEST, {"error": f"Invalid JSON: {exc}"}
                )
                return

            result = validate_order(conn, payload)
            status = HTTPStatus.OK if result["approved"] else HTTPStatus.UNPROCESSABLE_ENTITY
            self._send_json(status, result)

        def do_PATCH(self) -> None:  # noqa: N802
            path = urlparse(self.path).path.rstrip("/")
            if not path.startswith("/rules/"):
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Endpoint not found"})
                return
            rule_name = path.split("/rules/", 1)[1]
            try:
                payload = self._read_json_body()
            except json.JSONDecodeError as exc:
                self._send_json(
                    HTTPStatus.BAD_REQUEST, {"error": f"Invalid JSON: {exc}"}
                )
                return

            if "enabled" not in payload or not isinstance(payload["enabled"], bool):
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "JSON body must include boolean 'enabled'."},
                )
                return

            updated = set_rule_enabled(conn, rule_name, payload["enabled"])
            if updated is None:
                self._send_json(
                    HTTPStatus.NOT_FOUND, {"error": f"Rule {rule_name} not found"}
                )
                return
            self._send_json(HTTPStatus.OK, updated)

    return OrderValidationHandler


def build_server(
    conn: sqlite3.Connection, host: str = "127.0.0.1", port: int = 0
) -> ThreadingHTTPServer:
    """Create a configured ThreadingHTTPServer bound to host:port."""
    return ThreadingHTTPServer((host, port), create_handler(conn))
