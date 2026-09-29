"""In-memory transaction store.

Keeps both a list (insertion order, used for listing) and a dict index (id -> record,
used for O(1) lookups). All writes go through a lock so the threaded server is safe.
"""

import json
import os
import threading

from dsa.parse_xml import DEFAULT_JSON, DEFAULT_XML, parse_sms_xml

# Fields a client may set with POST / PUT. "id" is always assigned by the server.
REQUIRED_FIELDS = ("transaction_type", "amount")
ALLOWED_FIELDS = (
    "transaction_type", "amount", "currency", "sender", "receiver", "fee",
    "balance", "transaction_ref", "timestamp", "readable_date", "address", "raw_body",
)
NUMERIC_FIELDS = ("amount", "fee", "balance")


class ValidationError(ValueError):
    pass


def validate(payload, partial=False):
    """Check a request body and return only the allowed fields."""
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object")
    unknown = set(payload) - set(ALLOWED_FIELDS) - {"id"}
    if unknown:
        raise ValidationError(f"Unknown field(s): {', '.join(sorted(unknown))}")
    if not partial:
        missing = [f for f in REQUIRED_FIELDS if payload.get(f) in (None, "")]
        if missing:
            raise ValidationError(f"Missing required field(s): {', '.join(missing)}")
    for field in NUMERIC_FIELDS:
        if field in payload and payload[field] is not None:
            value = payload[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValidationError(f"'{field}' must be a number")
            if value < 0 or (field == "amount" and value == 0):
                raise ValidationError(f"'{field}' must be {'greater than 0' if field == 'amount' else 'non-negative'}")
    if "transaction_type" in payload and not isinstance(payload["transaction_type"], str):
        raise ValidationError("'transaction_type' must be a string")
    return {k: v for k, v in payload.items() if k in ALLOWED_FIELDS}


class TransactionStore:
    def __init__(self, records=None, persist_path=None):
        self._lock = threading.Lock()
        self._list = []
        self._index = {}
        self._persist_path = persist_path
        for record in records or []:
            self._list.append(record)
            self._index[record["id"]] = record
        self._next_id = max(self._index, default=0) + 1

    @classmethod
    def from_xml(cls, xml_path=DEFAULT_XML, persist_path=None):
        return cls(parse_sms_xml(xml_path), persist_path=persist_path)

    @classmethod
    def load(cls, json_path=DEFAULT_JSON, xml_path=DEFAULT_XML):
        """Load saved JSON if it exists, otherwise parse the XML."""
        if os.path.exists(json_path):
            with open(json_path, encoding="utf-8") as f:
                return cls(json.load(f), persist_path=json_path)
        return cls.from_xml(xml_path, persist_path=json_path)

    def _save(self):
        if self._persist_path:
            with open(self._persist_path, "w", encoding="utf-8") as f:
                json.dump(self._list, f, indent=2, ensure_ascii=False)

    def all(self, tx_type=None):
        with self._lock:
            if tx_type:
                return [t for t in self._list if str(t.get("transaction_type", "")).upper() == tx_type.upper()]
            return list(self._list)

    def get(self, tx_id):
        return self._index.get(tx_id)

    def create(self, payload):
        data = validate(payload)
        data.setdefault("currency", "RWF")
        data.setdefault("fee", 0)
        with self._lock:
            record = {"id": self._next_id, **data}
            self._next_id += 1
            self._list.append(record)
            self._index[record["id"]] = record
            self._save()
        return record

    def update(self, tx_id, payload):
        data = validate(payload, partial=True)
        with self._lock:
            record = self._index.get(tx_id)
            if record is None:
                return None
            record.update(data)
            self._save()
            return record

    def delete(self, tx_id):
        with self._lock:
            record = self._index.pop(tx_id, None)
            if record is None:
                return None
            self._list.remove(record)
            self._save()
            return record
