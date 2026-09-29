#!/usr/bin/env bash
# Run the API first:  python -m api.server
# Then run:           bash scripts/curl_tests.sh
BASE="http://127.0.0.1:8000"
USER="${MOMO_API_USER:-admin}"
PASS="${MOMO_API_PASS:-password123}"
cd "$(dirname "$0")"

echo "=== 1. GET all transactions (valid credentials) ==="
curl -i -u "$USER:$PASS" "$BASE/transactions"

echo; echo "=== 2. GET one transaction ==="
curl -i -u "$USER:$PASS" "$BASE/transactions/1"

echo; echo "=== 3. Unauthorized: wrong credentials ==="
curl -i -u "admin:wrongpass" "$BASE/transactions"

echo; echo "=== 4. POST new transaction ==="
curl -i -u "$USER:$PASS" -X POST -H "Content-Type: application/json" \
     --data @new_transaction.json "$BASE/transactions"

echo; echo "=== 5. PUT update transaction 1 ==="
curl -i -u "$USER:$PASS" -X PUT -H "Content-Type: application/json" \
     --data @update_transaction.json "$BASE/transactions/1"

echo; echo "=== 6. DELETE transaction 2 ==="
curl -i -u "$USER:$PASS" -X DELETE "$BASE/transactions/2"

echo; echo "=== 7. GET deleted transaction (expect 404) ==="
curl -i -u "$USER:$PASS" "$BASE/transactions/2"
