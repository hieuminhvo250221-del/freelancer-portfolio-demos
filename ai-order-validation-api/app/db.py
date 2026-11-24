"""SQLite storage layer for order, inventory, customer, and toggleable validation rules."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_RULES = [
    ("check_stock", 1, "Reject orders when requested quantity exceeds available stock."),
    ("check_customer_exists", 1, "Flag orders whose customer_id is not registered."),
    ("check_address_match", 1, "Flag orders whose shipping address differs from customer profile."),
    ("check_phone_match", 1, "Flag orders whose contact phone differs from customer profile."),
    ("check_duplicate_order", 1, "Reject duplicate order_id submissions."),
]


def get_connection(db_path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create schema tables if they do not already exist."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS products (
            sku TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            stock INTEGER NOT NULL,
            unit_price REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            shipping_address TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS validation_rules (
            rule_name TEXT PRIMARY KEY,
            enabled INTEGER NOT NULL,
            description TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS validation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            approved INTEGER NOT NULL,
            risk_level TEXT NOT NULL,
            issues_json TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    for rule_name, enabled, desc in DEFAULT_RULES:
        conn.execute(
            """
            INSERT OR IGNORE INTO validation_rules (rule_name, enabled, description)
            VALUES (?, ?, ?)
            """,
            (rule_name, enabled, desc),
        )
    conn.commit()


def seed_sample_data(conn: sqlite3.Connection) -> None:
    """Populate realistic sample inventory and customer records for local demos."""
    products = [
        ("SKU-100", "Wireless Mechanical Keyboard", 15, 79.0),
        ("SKU-200", "USB-C Docking Station", 2, 129.0),
        ("SKU-300", "Ergonomic Mouse", 0, 45.0),
    ]
    customers = [
        (
            "CUST-01",
            "Alex Rivera",
            "alex.rivera@example.com",
            "+1-555-0142",
            "742 Evergreen Terrace, Austin, TX 78701",
        ),
        (
            "CUST-02",
            "Priya Nair",
            "priya.nair@example.com",
            "+1-555-0199",
            "210 Market St, San Francisco, CA 94105",
        ),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO products (sku, name, stock, unit_price) VALUES (?, ?, ?, ?)",
        products,
    )
    conn.executemany(
        """
        INSERT OR IGNORE INTO customers
            (customer_id, full_name, email, phone, shipping_address)
        VALUES (?, ?, ?, ?, ?)
        """,
        customers,
    )
    conn.commit()


def fetch_rules_map(conn: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    rows = conn.execute(
        "SELECT rule_name, enabled, description FROM validation_rules ORDER BY rule_name"
    ).fetchall()
    return {
        row["rule_name"]: {
            "enabled": bool(row["enabled"]),
            "description": row["description"],
        }
        for row in rows
    }


def set_rule_enabled(
    conn: sqlite3.Connection, rule_name: str, enabled: bool
) -> dict[str, Any] | None:
    cur = conn.execute(
        "UPDATE validation_rules SET enabled = ? WHERE rule_name = ?",
        (1 if enabled else 0, rule_name),
    )
    conn.commit()
    if cur.rowcount == 0:
        return None
    row = conn.execute(
        "SELECT rule_name, enabled, description FROM validation_rules WHERE rule_name = ?",
        (rule_name,),
    ).fetchone()
    return {
        "rule_name": row["rule_name"],
        "enabled": bool(row["enabled"]),
        "description": row["description"],
    }


def record_validation_log(
    conn: sqlite3.Connection,
    order_id: str,
    customer_id: str,
    approved: bool,
    risk_level: str,
    issues: list[dict[str, str]],
    payload: dict[str, Any],
    created_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO validation_logs
            (order_id, customer_id, approved, risk_level, issues_json, payload_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            order_id,
            customer_id,
            1 if approved else 0,
            risk_level,
            json.dumps(issues),
            json.dumps(payload),
            created_at,
        ),
    )
    conn.commit()
