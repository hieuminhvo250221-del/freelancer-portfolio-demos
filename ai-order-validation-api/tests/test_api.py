import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from app.db import get_connection, init_db, seed_sample_data
from app.server import build_server


class TestOrderValidationAPI(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_orders.db"
        self.conn = get_connection(self.db_path)
        init_db(self.conn)
        seed_sample_data(self.conn)
        self.server = build_server(self.conn, host="127.0.0.1", port=0)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.conn.close()
        self.tmpdir.cleanup()

    def _request(self, method: str, path: str, body: dict | None = None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        req = urllib.request.Request(
            f"{self.base_url}{path}", data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_valid_order_approved_and_duplicate_blocked(self):
        order = {
            "order_id": "ORD-500",
            "customer_id": "CUST-01",
            "phone": "+1-555-0142",
            "shipping_address": "742 Evergreen Terrace, Austin, TX 78701",
            "items": [{"sku": "SKU-100", "quantity": 2}],
        }
        status, res = self._request("POST", "/orders/validate", order)
        self.assertEqual(status, 200)
        self.assertTrue(res["approved"])
        self.assertEqual(res["risk_level"], "LOW")
        self.assertEqual(res["estimated_total"], 158.0)

        # Duplicate order_id is rejected
        dup_status, dup_res = self._request("POST", "/orders/validate", order)
        self.assertEqual(dup_status, 422)
        self.assertFalse(dup_res["approved"])
        self.assertEqual(dup_res["issues"][0]["code"], "DUPLICATE_ORDER")

    def test_flags_mismatch_and_out_of_stock_and_supports_rule_toggle(self):
        flagged_order = {
            "order_id": "ORD-501",
            "customer_id": "CUST-02",
            "phone": "+1-555-9999",
            "shipping_address": "Different Address, NY",
            "items": [{"sku": "SKU-300", "quantity": 1}],
        }
        status, res = self._request("POST", "/orders/validate", flagged_order)
        self.assertEqual(status, 422)
        self.assertEqual(res["risk_level"], "HIGH")
        codes = {issue["code"] for issue in res["issues"]}
        self.assertEqual(codes, {"ADDRESS_MISMATCH", "PHONE_MISMATCH", "OUT_OF_STOCK"})

        # Disable address & phone checks via PATCH /rules/{name}
        s1, r1 = self._request("PATCH", "/rules/check_address_match", {"enabled": False})
        s2, r2 = self._request("PATCH", "/rules/check_phone_match", {"enabled": False})
        self.assertEqual(s1, 200)
        self.assertFalse(r1["enabled"])
        self.assertEqual(s2, 200)
        self.assertFalse(r2["enabled"])

        # Re-validate with in-stock item -> approved
        retried = dict(flagged_order)
        retried["order_id"] = "ORD-502"
        retried["items"] = [{"sku": "SKU-200", "quantity": 1}]
        ok_status, ok_res = self._request("POST", "/orders/validate", retried)
        self.assertEqual(ok_status, 200)
        self.assertTrue(ok_res["approved"])

        # Verify audit log lookup
        get_status, get_res = self._request("GET", "/orders/ORD-502")
        self.assertEqual(get_status, 200)
        self.assertTrue(get_res["approved"])


if __name__ == "__main__":
    unittest.main()
