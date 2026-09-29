"""Compare linear search and dictionary lookup for finding transactions by id.

Usage:
    python -m dsa.search_compare
Prints a results table and writes docs/dsa_results.md.
"""

import os
import random
import timeit

from dsa.parse_xml import DEFAULT_XML, ROOT_DIR, parse_sms_xml

RESULTS_MD = os.path.join(ROOT_DIR, "docs", "dsa_results.md")
REPEATS = 1000


def linear_search(transactions, tx_id):
    """O(n): scan the list until the id matches."""
    for tx in transactions:
        if tx["id"] == tx_id:
            return tx
    return None


def build_index(transactions):
    """Build an id -> transaction dictionary (done once, O(n))."""
    return {tx["id"]: tx for tx in transactions}


def dict_lookup(index, tx_id):
    """O(1) on average: hash the key and jump to its bucket."""
    return index.get(tx_id)


def synthetic_records(base, size):
    """Repeat the parsed records with fresh ids to test larger inputs."""
    return [dict(base[i % len(base)], id=i + 1) for i in range(size)]


def benchmark(transactions, repeats=REPEATS):
    index = build_index(transactions)
    ids = [tx["id"] for tx in transactions]

    # Correctness: both methods must return the same record for every id.
    for tx_id in ids:
        assert linear_search(transactions, tx_id) is dict_lookup(index, tx_id)
    assert linear_search(transactions, -1) is None and dict_lookup(index, -1) is None

    # Time a lookup of every id in the list, repeated `repeats` times.
    lin = timeit.timeit(lambda: [linear_search(transactions, i) for i in ids], number=repeats)
    dic = timeit.timeit(lambda: [dict_lookup(index, i) for i in ids], number=repeats)
    lookups = len(ids) * repeats
    return {
        "n": len(transactions),
        "linear_us": lin / lookups * 1e6,
        "dict_us": dic / lookups * 1e6,
        "speedup": lin / dic if dic else float("inf"),
    }


def main():
    records = parse_sms_xml(DEFAULT_XML)
    if len(records) < 20:
        raise SystemExit(f"Need at least 20 records for the comparison, found {len(records)}")

    random.seed(1)
    results = [
        benchmark(records[:20]),                                   # assignment minimum
        benchmark(records, repeats=10),                            # full parsed dataset
        benchmark(synthetic_records(records, 10000), repeats=1),   # scaled-up test
    ]

    header = f"{'Records':>8} | {'Linear search (us/lookup)':>26} | {'Dict lookup (us/lookup)':>24} | {'Speedup':>8}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(f"{r['n']:>8} | {r['linear_us']:>26.4f} | {r['dict_us']:>24.4f} | {r['speedup']:>7.1f}x")

    write_markdown(results)
    print(f"\nResults written to {RESULTS_MD}")


def write_markdown(results):
    rows = "\n".join(
        f"| {r['n']} | {r['linear_us']:.4f} | {r['dict_us']:.4f} | {r['speedup']:.1f}x |" for r in results
    )
    content = f"""# DSA Comparison: Linear Search vs Dictionary Lookup

Each row times a lookup of **every** transaction id in the set. Rows:

1. The first {results[0]['n']} records parsed from `data/modified_sms_v2.xml` ({REPEATS} repetitions).
2. All {results[1]['n']} parsed records (10 repetitions).
3. {results[2]['n']} synthetic records (parsed records reused with new ids) to show how each method scales.

| Records | Linear search (µs per lookup) | Dictionary lookup (µs per lookup) | Speedup |
|--------:|------------------------------:|----------------------------------:|--------:|
{rows}

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
"""
    with open(RESULTS_MD, "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    main()
