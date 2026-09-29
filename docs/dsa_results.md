# DSA Comparison: Linear Search vs Dictionary Lookup

Each row times a lookup of **every** transaction id in the set. Rows:

1. The first 20 records parsed from `data/modified_sms_v2.xml` (1000 repetitions).
2. All 1657 parsed records (10 repetitions).
3. 10000 synthetic records (parsed records reused with new ids) to show how each method scales.

| Records | Linear search (µs per lookup) | Dictionary lookup (µs per lookup) | Speedup |
|--------:|------------------------------:|----------------------------------:|--------:|
| 20 | 1.0547 | 0.2059 | 5.1x |
| 1657 | 68.1066 | 0.1418 | 480.5x |
| 10000 | 439.1186 | 0.1693 | 2593.6x |

Regenerate with `python -m dsa.search_compare`. Timings vary by machine.

## Why is dictionary lookup faster?

- **Linear search is O(n).** It compares the target id with each record in turn. On average it
  checks half the list, and all of it when the id is missing. Doubling the data doubles the work.
- **Dictionary lookup is O(1) on average.** A Python `dict` is a hash table. The id is hashed
  to a slot, so the lookup goes straight to the record however many records there are.
- Building the dictionary costs O(n) once. After that every lookup is cheap, so the index pays
  for itself as soon as more than a few lookups are made. The API keeps the dictionary updated on
  every POST, PUT and DELETE.

## Other structures that could improve search

- **Binary search on a list sorted by id (O(log n))** saves memory compared with a hash table and
  also supports range queries such as "ids 100–200".
- **Balanced binary search tree / B-tree (O(log n))** keeps keys ordered for range and
  date-based queries. Database indexes (e.g. MySQL InnoDB) use B+ trees.
- **Secondary hash indexes** (e.g. `transaction_type -> [ids]`, `transaction_ref -> id`) make
  filters like `GET /transactions?type=PAYMENT` fast instead of scanning every record.
- **Trie** for prefix searches on sender/receiver names or phone numbers.
