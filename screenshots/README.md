# Test Screenshots

Start the server in one terminal (`python -m api.server`) and run each command in a second terminal
(or run all of them with `scripts\curl_tests.ps1`). Save a screenshot of each result with the filename below.

| # | File | Test | Command (Windows: use `curl.exe`) | Expected |
|---|------|------|-----------------------------------|----------|
| 1 | `01_get_all_authenticated.png` | GET all with valid credentials | `curl -i -u admin:password123 http://127.0.0.1:8000/transactions` | `200 OK` + list |
| 2 | `02_get_one_authenticated.png` | GET one | `curl -i -u admin:password123 http://127.0.0.1:8000/transactions/1` | `200 OK` |
| 3 | `03_unauthorized_wrong_credentials.png` | Wrong password | `curl -i -u admin:wrongpass http://127.0.0.1:8000/transactions` | `401 Unauthorized` |
| 4 | `04_post_create.png` | POST | `curl -i -u admin:password123 -X POST -H "Content-Type: application/json" --data "@scripts/new_transaction.json" http://127.0.0.1:8000/transactions` | `201 Created` |
| 5 | `05_put_update.png` | PUT | `curl -i -u admin:password123 -X PUT -H "Content-Type: application/json" --data "@scripts/update_transaction.json" http://127.0.0.1:8000/transactions/1` | `200 OK`, updated fields |
| 6 | `06_delete.png` | DELETE | `curl -i -u admin:password123 -X DELETE http://127.0.0.1:8000/transactions/2` | `200 OK` |
| 7 | `07_dsa_comparison.png` | DSA benchmark | `python -m dsa.search_compare` | Timing table |
| 8 | `08_unit_tests.png` | Automated tests | `python -m unittest discover -s tests -v` | `OK` |

**Postman option:** under *Authorization* pick **Basic Auth** and enter `admin` / `password123`. Under *Body* pick
**raw → JSON** for POST/PUT.

Tip: `GET /transactions` returns all 1,657 records, which is a lot of output. For screenshot 1, capture the top so the
status line and `"count": 1657` show. You can also add a shorter filtered call such as `/transactions?type=REVERSAL`.

Tip: include the status line (e.g. `HTTP/1.0 401 Unauthorized`) in each screenshot. The `-i` flag prints it.
