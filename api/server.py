"""MoMo SMS Transactions REST API built on Python's http.server.

Endpoints (all require HTTP Basic Auth):
    GET    /transactions            list all transactions (optional ?type=PAYMENT)
    GET    /transactions/{id}       get one transaction
    POST   /transactions            create a transaction
    PUT    /transactions/{id}       update a transaction
    DELETE /transactions/{id}       delete a transaction

Usage:
    python -m api.server [--host 127.0.0.1] [--port 8000]
"""

import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from api.auth import REALM, check_basic_auth
from api.store import TransactionStore, ValidationError

COLLECTION_RE = re.compile(r"^/transactions/?$")
ITEM_RE = re.compile(r"^/transactions/(?P<id>[^/]+)/?$")
MAX_BODY_BYTES = 1_000_000


class TransactionHandler(BaseHTTPRequestHandler):
    server_version = "MoMoAPI/1.0"
    store = None  # set by make_server()

    # ---------- helpers ----------
    def _send_json(self, status, payload, extra_headers=None):
        body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status, message, extra_headers=None):
        self._send_json(status, {"error": message, "status": status}, extra_headers)

    def _authorized(self):
        if check_basic_auth(self.headers.get("Authorization")):
            return True
        self._error(401, "Unauthorized: invalid or missing credentials",
                    {"WWW-Authenticate": f'Basic realm="{REALM}"'})
        return False

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            raise ValidationError("Request body is required")
        if length > MAX_BODY_BYTES:
            raise ValidationError("Request body too large")
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValidationError("Request body must be valid JSON")

    def _route(self):
        """Return (kind, id) where kind is 'collection', 'item', 'bad_id' or None."""
        path = urlparse(self.path).path
        if COLLECTION_RE.match(path):
            return "collection", None
        match = ITEM_RE.match(path)
        if match:
            raw_id = match.group("id")
            return ("item", int(raw_id)) if raw_id.isdigit() else ("bad_id", raw_id)
        return None, None

    def _dispatch(self, method):
        if not self._authorized():
            return
        kind, tx_id = self._route()
        if kind is None:
            return self._error(404, f"Route not found: {urlparse(self.path).path}")
        if kind == "bad_id":
            return self._error(400, f"Invalid transaction id '{tx_id}': must be a positive integer")
        handler = getattr(self, f"_{method.lower()}_{kind}", None)
        if handler is None:
            allowed = "GET, POST" if kind == "collection" else "GET, PUT, DELETE"
            return self._error(405, f"Method {method} not allowed on this resource", {"Allow": allowed})
        try:
            handler(tx_id) if kind == "item" else handler()
        except ValidationError as exc:
            self._error(400, str(exc))

    # ---------- endpoint handlers ----------
    def _get_collection(self):
        query = parse_qs(urlparse(self.path).query)
        tx_type = query.get("type", [None])[0]
        items = self.store.all(tx_type)
        self._send_json(200, {"count": len(items), "transactions": items})

    def _get_item(self, tx_id):
        record = self.store.get(tx_id)
        if record is None:
            return self._error(404, f"Transaction {tx_id} not found")
        self._send_json(200, record)

    def _post_collection(self):
        record = self.store.create(self._read_json())
        self._send_json(201, record, {"Location": f"/transactions/{record['id']}"})

    def _put_item(self, tx_id):
        payload = self._read_json()
        if self.store.get(tx_id) is None:
            return self._error(404, f"Transaction {tx_id} not found")
        record = self.store.update(tx_id, payload)
        if record is None:
            return self._error(404, f"Transaction {tx_id} not found")
        self._send_json(200, record)

    def _delete_item(self, tx_id):
        record = self.store.delete(tx_id)
        if record is None:
            return self._error(404, f"Transaction {tx_id} not found")
        self._send_json(200, {"message": f"Transaction {tx_id} deleted", "transaction": record})

    # ---------- HTTP verbs ----------
    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def do_PATCH(self):
        self._dispatch("PATCH")


def make_server(host="127.0.0.1", port=8000, store=None):
    handler = type("BoundHandler", (TransactionHandler,), {"store": store or TransactionStore.load()})
    return ThreadingHTTPServer((host, port), handler)


def main():
    parser = argparse.ArgumentParser(description="MoMo SMS Transactions REST API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    httpd = make_server(args.host, args.port)
    print(f"MoMo API running on http://{args.host}:{args.port}/transactions  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
