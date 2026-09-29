# MoMo SMS Transactions API – Documentation

**Base URL:** `http://127.0.0.1:8000`
**Format:** JSON (`Content-Type: application/json; charset=utf-8`)
**Authentication:** HTTP Basic Auth is required on **every** endpoint.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/transactions`       | List all transactions (optional `?type=` filter) |
| GET    | `/transactions/{id}`  | Get a single transaction |
| POST   | `/transactions`       | Create a new transaction |
| PUT    | `/transactions/{id}`  | Update an existing transaction |
| DELETE | `/transactions/{id}`  | Delete a transaction |

---

## Authentication

Send an `Authorization` header with `Basic base64(username:password)`.
With curl, `-u username:password` builds this header for you.

```
Authorization: Basic YWRtaW46cGFzc3dvcmQxMjM=
```

Credentials are set by the `MOMO_API_USER` and `MOMO_API_PASS` environment variables
(local default: `admin` / `password123`).

A missing, malformed or wrong `Authorization` header returns **401**, whatever the endpoint:

```http
HTTP/1.0 401 Unauthorized
WWW-Authenticate: Basic realm="MoMo API"
Content-Type: application/json; charset=utf-8

{
  "error": "Unauthorized: invalid or missing credentials",
  "status": 401
}
```

---

## Transaction object

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique id, assigned by the server (read-only) |
| `transaction_type` | string | `INCOMING_MONEY`, `PAYMENT`, `TRANSFER`, `BANK_DEPOSIT`, `AIRTIME`, `BUNDLES`, `DIRECT_DEBIT`, `WITHDRAWAL`, `REVERSAL` (or any custom string on create) |
| `amount` | number | Transaction amount (> 0) |
| `currency` | string | Defaults to `RWF` |
| `sender` | string | Who sent the money |
| `receiver` | string | Who received the money |
| `fee` | number | Fee charged (≥ 0, defaults to 0) |
| `balance` | number | Account balance after the transaction (≥ 0) |
| `transaction_ref` | string | MoMo Financial Transaction Id / TxId, if the SMS has one |
| `timestamp` | string | ISO 8601 date-time, e.g. `2024-05-10T16:30:51` |
| `readable_date` | string | Human-readable date from the SMS backup |
| `address` | string | SMS sender address (`M-Money`) |
| `raw_body` | string | Original SMS text |

---

## 1. List transactions

**`GET /transactions`**

Optional query parameter: `type` (not case-sensitive), e.g. `/transactions?type=payment`.

**Request**
```bash
curl -u admin:password123 http://127.0.0.1:8000/transactions
```

**Response – 200 OK**
```json
{
  "count": 1657,
  "transactions": [
    {
      "id": 1,
      "transaction_type": "INCOMING_MONEY",
      "amount": 2000,
      "currency": "RWF",
      "sender": "Jane Smith",
      "receiver": "Account Holder",
      "fee": 0,
      "balance": 2000,
      "transaction_ref": "76662021700",
      "timestamp": "2024-05-10T16:30:51",
      "readable_date": "10 May 2024 4:30:58 PM",
      "address": "M-Money",
      "raw_body": "You have received 2000 RWF from Jane Smith (*********013) on your mobile money account at 2024-05-10 16:30:51. Message from sender: . Your new balance:2000 RWF. Financial Transaction Id: 76662021700."
    }
  ]
}
```

**Errors:** `401`

---

## 2. Get one transaction

**`GET /transactions/{id}`**

**Request**
```bash
curl -u admin:password123 http://127.0.0.1:8000/transactions/2
```

**Response – 200 OK**
```json
{
  "id": 2,
  "transaction_type": "PAYMENT",
  "amount": 1000,
  "currency": "RWF",
  "sender": "Account Holder",
  "receiver": "Jane Smith",
  "fee": 0,
  "balance": 1000,
  "transaction_ref": "73214484437",
  "timestamp": "2024-05-10T16:31:39",
  "readable_date": "10 May 2024 4:31:46 PM",
  "address": "M-Money",
  "raw_body": "TxId: 73214484437. Your payment of 1,000 RWF to Jane Smith 12845 has been completed at 2024-05-10 16:31:39. Your new balance: 1,000 RWF. Fee was 0 RWF.Kanda*182*16# wiyandikishe muri poromosiyo ya BivaMoMotima, ugire amahirwe yo gutsindira ibihembo bishimishije."
}
```

**Errors**
```json
// 404 Not Found
{ "error": "Transaction 999 not found", "status": 404 }

// 400 Bad Request (id is not a number)
{ "error": "Invalid transaction id 'abc': must be a positive integer", "status": 400 }
```

---

## 3. Create a transaction

**`POST /transactions`**

Required fields: `transaction_type`, `amount`. Optional: any other field in the table above except `id`.

**Request**
```bash
curl -u admin:password123 -X POST http://127.0.0.1:8000/transactions \
     -H "Content-Type: application/json" \
     -d '{"transaction_type":"PAYMENT","amount":2500,"sender":"Account Holder","receiver":"Kigali Coffee Shop","fee":0,"timestamp":"2024-06-01T10:00:00"}'
```
Windows: `curl.exe ... --data "@scripts/new_transaction.json"`

**Response – 201 Created** (header `Location: /transactions/1658`)
```json
{
  "id": 1658,
  "transaction_type": "PAYMENT",
  "amount": 2500,
  "sender": "Account Holder",
  "receiver": "Kigali Coffee Shop",
  "fee": 0,
  "timestamp": "2024-06-01T10:00:00",
  "currency": "RWF"
}
```

**Errors**
```json
// 400 – missing required field
{ "error": "Missing required field(s): transaction_type", "status": 400 }
// 400 – wrong type / value
{ "error": "'amount' must be a number", "status": 400 }
{ "error": "'amount' must be greater than 0", "status": 400 }
// 400 – field not in the schema
{ "error": "Unknown field(s): foo", "status": 400 }
// 400 – body is not JSON
{ "error": "Request body must be valid JSON", "status": 400 }
```

---

## 4. Update a transaction

**`PUT /transactions/{id}`**

Send only the fields to change. They are merged into the existing record and the `id` does not change.

**Request**
```bash
curl -u admin:password123 -X PUT http://127.0.0.1:8000/transactions/2 \
     -H "Content-Type: application/json" \
     -d '{"amount":3000,"receiver":"Simba Supermarket"}'
```

**Response – 200 OK**
```json
{
  "id": 2,
  "transaction_type": "PAYMENT",
  "amount": 3000,
  "currency": "RWF",
  "sender": "Account Holder",
  "receiver": "Simba Supermarket",
  "fee": 0,
  "balance": 1000,
  "transaction_ref": "73214484437",
  "timestamp": "2024-05-10T16:31:39",
  "readable_date": "10 May 2024 4:31:46 PM",
  "address": "M-Money",
  "raw_body": "TxId: 73214484437. Your payment of 1,000 RWF to Jane Smith 12845 has been completed at 2024-05-10 16:31:39. Your new balance: 1,000 RWF. Fee was 0 RWF.Kanda*182*16# wiyandikishe muri poromosiyo ya BivaMoMotima, ugire amahirwe yo gutsindira ibihembo bishimishije."
}
```

**Errors:** `400` (invalid JSON or field values, as for POST), `401`, `404` (unknown id).

---

## 5. Delete a transaction

**`DELETE /transactions/{id}`**

**Request**
```bash
curl -u admin:password123 -X DELETE http://127.0.0.1:8000/transactions/3
```

**Response – 200 OK**
```json
{
  "message": "Transaction 3 deleted",
  "transaction": {
    "id": 3,
    "transaction_type": "PAYMENT",
    "amount": 600,
    "currency": "RWF",
    "sender": "Account Holder",
    "receiver": "Samuel Carter",
    "fee": 0,
    "balance": 400,
    "transaction_ref": "51732411227",
    "timestamp": "2024-05-10T21:32:32",
    "...": "..."
  }
}
```

**Errors:** `401`, `404` (unknown or already deleted id), `400` (non-numeric id).

---

## Error codes summary

All errors use the same JSON shape: `{ "error": "<message>", "status": <code> }`.

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | Successful GET, PUT, DELETE |
| 201 | Created | Successful POST |
| 400 | Bad Request | Invalid JSON, missing/invalid fields, unknown fields, non-numeric id |
| 401 | Unauthorized | Missing, malformed or wrong Basic Auth credentials |
| 404 | Not Found | Transaction id does not exist, or unknown route |
| 405 | Method Not Allowed | e.g. `DELETE /transactions` or `POST /transactions/1` (response includes an `Allow` header) |
| 500 | Internal Server Error | Unexpected server failure |
