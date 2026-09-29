"""Parse MoMo SMS records from modified_sms_v2.xml into a list of dictionaries.

Each <sms> element's body is classified by transaction type and the key fields
(amount, sender, receiver, fee, balance, timestamp, reference) are extracted.

Usage:
    python -m dsa.parse_xml [path/to/modified_sms_v2.xml]
Writes data/transactions.json and prints a short summary.
"""

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_XML = os.path.join(ROOT_DIR, "data", "modified_sms_v2.xml")
DEFAULT_JSON = os.path.join(ROOT_DIR, "data", "transactions.json")

ACCOUNT_HOLDER = "Account Holder"

# Order matters: the first matching pattern decides the transaction type.
PATTERNS = [
    ("INCOMING_MONEY", re.compile(
        r"You have received (?P<amount>[\d,]+) RWF from (?P<sender>.+?)(?: \(|\. )")),
    ("BANK_DEPOSIT", re.compile(
        r"A bank deposit of (?P<amount>[\d,]+) RWF has been added")),
    ("AIRTIME", re.compile(
        r"Your payment of (?P<amount>[\d,]+) RWF to Airtime")),
    ("BUNDLES", re.compile(
        r"Your payment of (?P<amount>[\d,]+) RWF to (?P<receiver>Bundles and Packs)")),
    # Merchant-initiated debit, e.g. "A transaction of 600 RWF by ITEC Ltd on your MOMO account"
    ("DIRECT_DEBIT", re.compile(
        r"A transaction of (?P<amount>[\d,]+) RWF by (?P<receiver>.+?) on your MOMO account")),
    ("REVERSAL", re.compile(
        r"Your transaction to (?P<sender>.+?) \(\d+\) with (?P<amount>[\d,]+) RWF has been reversed")),
    ("PAYMENT", re.compile(
        r"Your payment of (?P<amount>[\d,]+) RWF to (?P<receiver>.+?)(?: \d+)? has been completed")),
    # Short format, e.g. "You have made a payment of 2000 RWF to Kigali Coffee Shop."
    ("PAYMENT", re.compile(
        r"You have made a payment of (?P<amount>[\d,]+) RWF to (?P<receiver>.+?)\. ")),
    ("TRANSFER", re.compile(
        r"(?P<amount>[\d,]+) RWF transferred to (?P<receiver>.+?) \(")),
    # Short format, e.g. "You have transferred 10000 RWF to Alice Mukamana."
    ("TRANSFER", re.compile(
        r"You have transferred (?P<amount>[\d,]+) RWF to (?P<receiver>.+?)(?: \(|\. )")),
    ("WITHDRAWAL", re.compile(
        r"via agent: (?P<receiver>.+?) withdrawn (?P<amount>[\d,]+) RWF")),
]

BALANCE_RE = re.compile(r"new balance\s*(?:is\s*)?:?\s*([\d,]+) RWF", re.IGNORECASE)
FEE_RE = re.compile(r"Fee(?: was| paid)?\s*:?\s*([\d,]+) RWF", re.IGNORECASE)
TXID_RE = re.compile(r"(?:Financial Transaction Id|Transaction Id|TxId)\s*:?\s*(\d+)", re.IGNORECASE)
DATE_RE = re.compile(r"at (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")


def _clean_name(name):
    """Collapse extra spaces and drop trailing punctuation / payment tokens."""
    if not name:
        return None
    name = re.sub(r"\s+with token.*$", "", name)
    return " ".join(name.split()).rstrip(",.") or None


def _to_number(text):
    return int(text.replace(",", "")) if text else None


def _timestamp(body, date_ms):
    """Prefer the date written in the SMS body; fall back to the XML date attribute."""
    match = DATE_RE.search(body)
    if match:
        return datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S").isoformat()
    if date_ms and date_ms.isdigit():
        return datetime.fromtimestamp(int(date_ms) / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    return None


def parse_body(body):
    """Classify one SMS body and extract its fields. Returns None for non-transaction SMS."""
    for tx_type, pattern in PATTERNS:
        match = pattern.search(body)
        if not match:
            continue
        groups = match.groupdict()
        incoming = tx_type in ("INCOMING_MONEY", "BANK_DEPOSIT", "REVERSAL")
        if tx_type == "BANK_DEPOSIT":
            sender, receiver = "Bank", ACCOUNT_HOLDER
        elif tx_type == "AIRTIME":
            sender, receiver = ACCOUNT_HOLDER, "Airtime"
        elif incoming:
            sender, receiver = groups.get("sender"), ACCOUNT_HOLDER
        else:
            sender, receiver = ACCOUNT_HOLDER, groups.get("receiver")

        fee = FEE_RE.search(body)
        balance = BALANCE_RE.search(body)
        txid = TXID_RE.search(body)
        return {
            "transaction_type": tx_type,
            "amount": _to_number(groups["amount"]),
            "currency": "RWF",
            "sender": _clean_name(sender),
            "receiver": _clean_name(receiver),
            "fee": _to_number(fee.group(1)) if fee else 0,
            "balance": _to_number(balance.group(1)) if balance else None,
            "transaction_ref": txid.group(1) if txid else None,
        }
    return None


def parse_sms_xml(xml_path=DEFAULT_XML):
    """Parse the XML file and return a list of transaction dictionaries with sequential ids."""
    tree = ET.parse(xml_path)
    transactions = []
    skipped = 0
    for sms in tree.getroot().iter("sms"):
        body = sms.get("body", "") or ""
        fields = parse_body(body)
        if fields is None:
            skipped += 1
            continue
        record = {"id": len(transactions) + 1}
        record.update(fields)
        record["timestamp"] = _timestamp(body, sms.get("date"))
        record["readable_date"] = sms.get("readable_date")
        record["address"] = sms.get("address")
        record["raw_body"] = body
        transactions.append(record)
    if skipped:
        print(f"Skipped {skipped} non-transaction SMS", file=sys.stderr)
    return transactions


def save_json(transactions, json_path=DEFAULT_JSON):
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(transactions, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_XML
    records = parse_sms_xml(path)
    save_json(records)
    print(f"Parsed {len(records)} transactions -> {DEFAULT_JSON}")
    counts = {}
    for r in records:
        counts[r["transaction_type"]] = counts.get(r["transaction_type"], 0) + 1
    for tx_type, n in sorted(counts.items()):
        print(f"  {tx_type:<15} {n}")
    if records:
        print("\nFirst record:")
        print(json.dumps(records[0], indent=2, ensure_ascii=False))
