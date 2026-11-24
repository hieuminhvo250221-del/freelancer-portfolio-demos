"""CLI demo and local server launcher for Order Validation API."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db import get_connection, init_db, seed_sample_data
from app.server import build_server
from app.validator import validate_order


def run_demo(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    init_db(conn)
    seed_sample_data(conn)

    sample_orders = [
        {
            "order_id": "ORD-1001",
            "customer_id": "CUST-01",
            "phone": "+1-555-0142",
            "shipping_address": "742 Evergreen Terrace, Austin, TX 78701",
            "items": [{"sku": "SKU-100", "quantity": 2}],
        },
        {
            "order_id": "ORD-1002",
            "customer_id": "CUST-02",
            "phone": "+1-555-0000",
            "shipping_address": "999 Unknown Rd, Miami, FL 33101",
            "items": [{"sku": "SKU-300", "quantity": 1}],
        },
    ]

    for order in sample_orders:
        res = validate_order(conn, order)
        print(json.dumps(res, indent=2))
    conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Order Validation REST API")
    parser.add_argument("--db", type=Path, default=Path("data/orders.db"))
    parser.add_argument("--serve", action="store_true", help="Start live HTTP server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    if not args.serve:
        run_demo(args.db)
        return 0

    args.db.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(args.db)
    init_db(conn)
    seed_sample_data(conn)
    server = build_server(conn, host=args.host, port=args.port)
    print(f"Order Validation API listening on http://{args.host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
