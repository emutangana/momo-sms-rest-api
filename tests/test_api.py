"""End-to-end tests: start the server on a free port and call every endpoint.

Run with:  python -m unittest discover -s tests -v
"""

import base64
import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.auth import DEFAULT_PASS, DEFAULT_USER  # noqa: E402
from api.server import make_server  # noqa: E402
from api.store import TransactionStore  # noqa: E402
from dsa.search_compare import build_index, dict_lookup, linear_search  # noqa: E402


def auth_header(user=DEFAULT_USER, password=DEFAULT_PASS):
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


class ApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.pop("MOMO_API_USER", None)
        os.environ.pop("MOMO_API_PASS", None)
        cls.store = TransactionStore.from_xml()  # no persistence: tests never touch data files
        cls.httpd = make_server("127.0.0.1", 0, cls.store)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def request(self, method, path, body=None, headers=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers or {})
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read()), resp.headers
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read()), err.headers

    # --- authentication ---
    def test_missing_credentials_returns_401(self):
        status, body, headers = self.request("GET", "/transactions")
        self.assertEqual(status, 401)
        self.assertIn("Basic", headers.get("WWW-Authenticate", ""))

    def test_wrong_credentials_returns_401(self):
        status, _, _ = self.request("GET", "/transactions", headers=auth_header("admin", "wrong"))
        self.assertEqual(status, 401)

    def test_malformed_auth_header_returns_401(self):
        status, _, _ = self.request("GET", "/transactions", headers={"Authorization": "Basic !!!notbase64"})
        self.assertEqual(status, 401)

    def test_write_endpoints_require_auth(self):
        for method, path in (("POST", "/transactions"), ("PUT", "/transactions/1"), ("DELETE", "/transactions/1")):
            status, _, _ = self.request(method, path, body={"transaction_type": "PAYMENT", "amount": 1})
            self.assertEqual(status, 401, method)

    # --- read ---
    def test_list_transactions(self):
        status, body, _ = self.request("GET", "/transactions", headers=auth_header())
        self.assertEqual(status, 200)
        self.assertGreaterEqual(body["count"], 20)
        self.assertEqual(body["count"], len(body["transactions"]))

    def test_filter_by_type(self):
        status, body, _ = self.request("GET", "/transactions?type=payment", headers=auth_header())
        self.assertEqual(status, 200)
        self.assertTrue(all(t["transaction_type"] == "PAYMENT" for t in body["transactions"]))

    def test_get_one_transaction(self):
        status, body, _ = self.request("GET", "/transactions/1", headers=auth_header())
        self.assertEqual(status, 200)
        self.assertEqual(body["id"], 1)
        for field in ("transaction_type", "amount", "sender", "receiver", "timestamp"):
            self.assertIn(field, body)

    def test_get_missing_returns_404(self):
        status, _, _ = self.request("GET", "/transactions/99999", headers=auth_header())
        self.assertEqual(status, 404)

    def test_invalid_id_returns_400(self):
        status, _, _ = self.request("GET", "/transactions/abc", headers=auth_header())
        self.assertEqual(status, 400)

    def test_unknown_route_returns_404(self):
        status, _, _ = self.request("GET", "/users", headers=auth_header())
        self.assertEqual(status, 404)

    def test_method_not_allowed(self):
        status, _, headers = self.request("DELETE", "/transactions", headers=auth_header())
        self.assertEqual(status, 405)
        self.assertEqual(headers.get("Allow"), "GET, POST")

    # --- create / update / delete ---
    def test_crud_lifecycle(self):
        new = {"transaction_type": "PAYMENT", "amount": 2500, "sender": "Account Holder",
               "receiver": "Kigali Coffee Shop", "timestamp": "2024-06-01T10:00:00"}
        status, created, headers = self.request("POST", "/transactions", body=new, headers=auth_header())
        self.assertEqual(status, 201)
        tx_id = created["id"]
        self.assertEqual(headers.get("Location"), f"/transactions/{tx_id}")
        self.assertEqual(created["currency"], "RWF")

        status, updated, _ = self.request("PUT", f"/transactions/{tx_id}", body={"amount": 3000},
                                          headers=auth_header())
        self.assertEqual(status, 200)
        self.assertEqual(updated["amount"], 3000)
        self.assertEqual(updated["receiver"], "Kigali Coffee Shop")

        status, _, _ = self.request("DELETE", f"/transactions/{tx_id}", headers=auth_header())
        self.assertEqual(status, 200)
        status, _, _ = self.request("GET", f"/transactions/{tx_id}", headers=auth_header())
        self.assertEqual(status, 404)
        status, _, _ = self.request("DELETE", f"/transactions/{tx_id}", headers=auth_header())
        self.assertEqual(status, 404)

    def test_post_validation_errors(self):
        cases = [
            {"amount": 100},                                        # missing transaction_type
            {"transaction_type": "PAYMENT", "amount": "abc"},       # amount not a number
            {"transaction_type": "PAYMENT", "amount": -5},          # negative amount
            {"transaction_type": "PAYMENT", "amount": 5, "x": 1},   # unknown field
            [1, 2, 3],                                              # not an object
        ]
        for body in cases:
            status, _, _ = self.request("POST", "/transactions", body=body, headers=auth_header())
            self.assertEqual(status, 400, body)

    def test_post_invalid_json_returns_400(self):
        status, _, _ = self.request("POST", "/transactions", raw=b"{not json", headers=auth_header())
        self.assertEqual(status, 400)

    def test_put_missing_returns_404(self):
        status, _, _ = self.request("PUT", "/transactions/99999", body={"amount": 10}, headers=auth_header())
        self.assertEqual(status, 404)


class SearchTestCase(unittest.TestCase):
    def test_linear_and_dict_agree(self):
        records = TransactionStore.from_xml().all()
        self.assertGreaterEqual(len(records), 20)
        index = build_index(records)
        for r in records:
            self.assertIs(linear_search(records, r["id"]), dict_lookup(index, r["id"]))
        self.assertIsNone(linear_search(records, -1))
        self.assertIsNone(dict_lookup(index, -1))


if __name__ == "__main__":
    unittest.main()
