# MoMo SMS Transactions REST API

A secure REST API for Mobile Money (MoMo) SMS transaction records. It is built with plain Python
(`http.server`) and uses the standard library only, with no third-party packages.

- Parses `modified_sms_v2.xml` into JSON objects
- Full CRUD on `/transactions`
- Every endpoint is protected with HTTP Basic Authentication
- Compares linear search with dictionary lookup (DSA)

## Team

| Name | GitHub | Role |
|------|--------|------|
| [Member 1] | [@username] | [e.g. XML parsing] |
| [Member 2] | [@username] | [e.g. API endpoints & auth] |
| [Member 3] | [@username] | [e.g. DSA & testing] |

**Team participation sheet:** [link]

## Project Structure

```
momo-sms-rest-api/
├── api/
│   ├── server.py          # HTTP server and CRUD route handlers
│   ├── auth.py            # Basic Authentication check
│   └── store.py           # In-memory store (list + dict index) and input validation
├── dsa/
│   ├── parse_xml.py       # XML -> list of JSON objects
│   └── search_compare.py  # Linear search vs dictionary lookup benchmark
├── data/
│   ├── modified_sms_v2.xml
│   └── transactions.json  # parsed output (created by dsa.parse_xml)
├── docs/
│   ├── api_docs.md        # Endpoint documentation
│   ├── dsa_results.md     # Benchmark results and reflection
│   ├── report.html        # Report source
│   └── report.pdf         # Final PDF report
├── scripts/               # curl test scripts + sample request bodies
├── screenshots/           # Test screenshots
├── tests/test_api.py      # Automated endpoint tests
└── README.md
```

## Setup

Requirements: **Python 3.8+**. Nothing to install.

```bash
git clone [repository-url]
cd momo-sms-rest-api
```

1. **Dataset.** `data/modified_sms_v2.xml` is the course dataset (1,691 SMS). The parser extracts
   1,657 transactions and skips 34 non-transaction messages (OTP codes, bundle notices, etc.).

2. **Parse the XML into JSON:**
   ```bash
   python -m dsa.parse_xml
   ```
   This writes `data/transactions.json` and prints a count per transaction type.

3. **(Optional) set credentials.** The default is `admin` / `password123`.
   ```bash
   # macOS / Linux
   export MOMO_API_USER=myuser MOMO_API_PASS=mysecret
   # Windows PowerShell
   $env:MOMO_API_USER="myuser"; $env:MOMO_API_PASS="mysecret"
   ```

4. **Start the API:**
   ```bash
   python -m api.server            # http://127.0.0.1:8000
   python -m api.server --port 9000
   ```

> Changes made through POST/PUT/DELETE are saved to `data/transactions.json`.
> To reset the data, run `python -m dsa.parse_xml` again.

## Using the API

```bash
curl -u admin:password123 http://127.0.0.1:8000/transactions
curl -u admin:password123 http://127.0.0.1:8000/transactions/1
curl -u admin:password123 "http://127.0.0.1:8000/transactions?type=PAYMENT"
curl -u admin:password123 -X POST -H "Content-Type: application/json" \
     -d '{"transaction_type":"PAYMENT","amount":2500,"receiver":"Kigali Coffee Shop"}' \
     http://127.0.0.1:8000/transactions
curl -u admin:password123 -X PUT -H "Content-Type: application/json" \
     -d '{"amount":3000}' http://127.0.0.1:8000/transactions/1
curl -u admin:password123 -X DELETE http://127.0.0.1:8000/transactions/2
```

On Windows PowerShell use `curl.exe`, or run the whole set with:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\curl_tests.ps1
```

See [docs/api_docs.md](docs/api_docs.md) for request and response examples and error codes.

## Testing

```bash
python -m unittest discover -s tests -v   # 16 tests: CRUD, auth (401), validation (400), 404, 405
python -m dsa.search_compare              # DSA benchmark -> docs/dsa_results.md
```

## DSA Results (summary)

| Records | Linear search | Dictionary lookup | Speedup |
|--------:|--------------:|------------------:|--------:|
| 20      | 1.05 µs       | 0.21 µs           | 5.1×    |
| 1,657   | 68.11 µs      | 0.14 µs           | 481×    |
| 10,000  | 439.12 µs     | 0.17 µs           | 2,594×  |

Linear search is O(n), and a dictionary (hash table) lookup is O(1) on average.
The reflection is in [docs/dsa_results.md](docs/dsa_results.md).

## Security Note

Basic Auth is used for this assignment. It only base64-encodes credentials and sends them with every request,
so it must be used over HTTPS. A production system should use JWT or OAuth 2.0. See the PDF report for details.
