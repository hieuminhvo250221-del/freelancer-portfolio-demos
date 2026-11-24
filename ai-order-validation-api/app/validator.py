"""Order and customer validation rule engine."""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db import fetch_rules_map, record_validation_log


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _normalize_phone(value: str) -> str:
    return re.sub(r"\D+", "", value)


def validate_order(
    conn: sqlite3.Connection,
    order: dict[str, Any],
) -> dict[str, Any]:
    """Run enabled validation rules against an incoming order payload and log the result."""
    order_id = str(order.get("order_id", "")).strip()
    customer_id = str(order.get("customer_id", "")).strip()
    shipping_address = str(order.get("shipping_address", "")).strip()
    contact_phone = str(order.get("phone", "")).strip()
    items = order.get("items") or []

    issues: list[dict[str, str]] = []
    if not order_id:
        issues.append({"code": "MISSING_ORDER_ID", "message": "order_id is required."})
    if not customer_id:
        issues.append({"code": "MISSING_CUSTOMER_ID", "message": "customer_id is required."})
    if not isinstance(items, list) or len(items) == 0:
        issues.append({"code": "EMPTY_ITEMS", "message": "At least one line item is required."})

    rules = fetch_rules_map(conn)

    # 1. Duplicate order check
    if order_id and rules.get("check_duplicate_order", {}).get("enabled", True):
        existing = conn.execute(
            "SELECT id FROM validation_logs WHERE order_id = ? AND approved = 1 LIMIT 1",
            (order_id,),
        ).fetchone()
        if existing is not None:
            issues.append(
                {
                    "code": "DUPLICATE_ORDER",
                    "message": f"Order {order_id} was already approved previously.",
                }
            )

    # 2. Customer profile, address, and phone verification
    customer = None
    if customer_id:
        customer = conn.execute(
            "SELECT * FROM customers WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()

    if customer is None:
        if customer_id and rules.get("check_customer_exists", {}).get("enabled", True):
            issues.append(
                {
                    "code": "UNKNOWN_CUSTOMER",
                    "message": f"Customer {customer_id} not found in CRM table.",
                }
            )
    else:
        if rules.get("check_address_match", {}).get("enabled", True):
            if _normalize_text(shipping_address) != _normalize_text(
                customer["shipping_address"]
            ):
                issues.append(
                    {
                        "code": "ADDRESS_MISMATCH",
                        "message": "Shipping address does not match verified customer profile.",
                    }
                )
        if rules.get("check_phone_match", {}).get("enabled", True):
            if _normalize_phone(contact_phone) != _normalize_phone(customer["phone"]):
                issues.append(
                    {
                        "code": "PHONE_MISMATCH",
                        "message": "Contact phone does not match verified customer profile.",
                    }
                )

    # 3. Line-item SKU and stock verification
    estimated_total = 0.0
    if isinstance(items, list) and rules.get("check_stock", {}).get("enabled", True):
        for entry in items:
            sku = str(entry.get("sku", "")).strip()
            qty = int(entry.get("quantity", 0))
            if qty <= 0:
                issues.append(
                    {
                        "code": "INVALID_QUANTITY",
                        "message": f"Quantity for {sku or 'unknown SKU'} must be positive.",
                    }
                )
                continue

            product = conn.execute(
                "SELECT sku, name, stock, unit_price FROM products WHERE sku = ?",
                (sku,),
            ).fetchone()
            if product is None:
                issues.append(
                    {"code": "UNKNOWN_SKU", "message": f"SKU {sku} does not exist."}
                )
                continue

            if qty > int(product["stock"]):
                issues.append(
                    {
                        "code": "OUT_OF_STOCK",
                        "message": (
                            f"Requested {qty} of {sku} ({product['name']}), "
                            f"but only {product['stock']} in stock."
                        ),
                    }
                )
            estimated_total += float(product["unit_price"]) * qty

    approved = len(issues) == 0
    if approved:
        risk_level = "LOW"
    elif any(i["code"] in {"OUT_OF_STOCK", "DUPLICATE_ORDER", "UNKNOWN_SKU"} for i in issues):
        risk_level = "HIGH"
    else:
        risk_level = "MEDIUM"

    timestamp = datetime.now(timezone.utc).isoformat()
    record_validation_log(
        conn=conn,
        order_id=order_id or "UNKNOWN",
        customer_id=customer_id or "UNKNOWN",
        approved=approved,
        risk_level=risk_level,
        issues=issues,
        payload=order,
        created_at=timestamp,
    )

    return {
        "order_id": order_id,
        "customer_id": customer_id,
        "approved": approved,
        "risk_level": risk_level,
        "estimated_total": round(estimated_total, 2),
        "issues": issues,
        "checked_at": timestamp,
    }
