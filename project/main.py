"""Main command-line interface for dataset queries."""

from __future__ import annotations

import argparse
import json
from time import perf_counter

from queries import (
    Record,
    build_id_index,
    build_sorted_numeric_index,
    find_duplicates_name_year,
    frequency_count,
    load_dataset,
    lookup_dict,
    lookup_linear,
    range_query_binary,
    range_query_linear,
    top_k_heap,
    top_k_sort,
)


def format_record(record: Record | None) -> str:
    if record is None:
        return "Record not found."
    return json.dumps(record, ensure_ascii=False)


def print_records(records: list[Record], limit: int = 10) -> None:
    print(f"Count: {len(records)}")
    for record in records[:limit]:
        print(json.dumps(record, ensure_ascii=False))
    if len(records) > limit:
        print(f"... ({len(records) - limit} more records)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mini Data Indexer and Query Tool")
    parser.add_argument(
        "--dataset",
        default="data/dataset_main.csv",
        help="Dataset path used by query commands (default: data/dataset_main.csv).",
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--build",
        metavar="DATASET_PATH",
        help="Load and validate a dataset, then display statistics.",
    )
    group.add_argument("--lookup", type=int, metavar="RECORD_ID", help="Exact lookup by record_id.")
    group.add_argument("--freq", metavar="FIELD", help="Frequency count for a categorical field.")
    group.add_argument(
        "--duplicates",
        action="store_true",
        help="Detect duplicates using (name, year) rule.",
    )
    group.add_argument("--topk", type=int, metavar="K", help="Return top-k records by score.")
    group.add_argument(
        "--range",
        nargs=3,
        metavar=("FIELD", "LOW", "HIGH"),
        help="Range query on numeric field.",
    )
    return parser


def run_build(dataset_path: str) -> None:
    records = load_dataset(dataset_path)
    id_index = build_id_index(records)
    print(f"Dataset: {dataset_path}")
    print(f"Records: {len(records)}")
    print(f"Unique IDs: {len(id_index)}")
    print("Validation complete.")


def run_lookup(records: list[Record], record_id: int) -> None:
    id_index = build_id_index(records)

    start = perf_counter()
    linear_result = lookup_linear(records, record_id)
    linear_ms = (perf_counter() - start) * 1000

    start = perf_counter()
    dict_result = lookup_dict(id_index, record_id)
    dict_ms = (perf_counter() - start) * 1000

    print("Linear scan result:")
    print(format_record(linear_result))
    print(f"Linear lookup time: {linear_ms:.6f} ms")
    print()
    print("Dictionary-based result:")
    print(format_record(dict_result))
    print(f"Dictionary lookup time: {dict_ms:.6f} ms")


def run_frequency(records: list[Record], field: str) -> None:
    freqs = frequency_count(records, field)
    ordered = sorted(freqs.items(), key=lambda x: (-x[1], x[0]))
    print(f"Frequency count for field '{field}':")
    for key, count in ordered:
        print(f"{key}: {count}")


def run_duplicates(records: list[Record]) -> None:
    duplicates = find_duplicates_name_year(records)
    total_duplicate_records = sum(len(group) for group in duplicates.values())

    print("Duplicate rule: duplicate (name, year)")
    print(f"Duplicate groups: {len(duplicates)}")
    print(f"Records in duplicate groups: {total_duplicate_records}")
    print("Sample groups:")
    for idx, ((name, year), group) in enumerate(sorted(duplicates.items())[:10], start=1):
        record_ids = [int(record["record_id"]) for record in group[:5]]
        print(f"{idx}. ({name}, {year}) -> {len(group)} records, IDs sample: {record_ids}")


def run_topk(records: list[Record], k: int) -> None:
    start = perf_counter()
    sort_result = top_k_sort(records, k)
    sort_ms = (perf_counter() - start) * 1000

    start = perf_counter()
    heap_result = top_k_heap(records, k)
    heap_ms = (perf_counter() - start) * 1000

    same_ids = [r["record_id"] for r in sort_result] == [r["record_id"] for r in heap_result]
    print(f"Top-{k} by score (sorting-based):")
    print_records(sort_result, limit=min(10, k))
    print(f"Sorting-based time: {sort_ms:.6f} ms")
    print()
    print(f"Top-{k} by score (heap-based):")
    print_records(heap_result, limit=min(10, k))
    print(f"Heap-based time: {heap_ms:.6f} ms")
    print(f"Methods produce identical record_id ordering: {same_ids}")


def run_range(records: list[Record], field: str, low: int, high: int) -> None:
    start = perf_counter()
    linear_result = range_query_linear(records, field, low, high)
    linear_ms = (perf_counter() - start) * 1000

    start = perf_counter()
    sorted_values, sorted_records = build_sorted_numeric_index(records, field)
    build_index_ms = (perf_counter() - start) * 1000

    start = perf_counter()
    binary_result = range_query_binary(sorted_values, sorted_records, low, high)
    binary_ms = (perf_counter() - start) * 1000

    same_record_set = {r["record_id"] for r in linear_result} == {r["record_id"] for r in binary_result}

    print(f"Range query: {low} <= {field} <= {high}")
    print(f"Linear scan count: {len(linear_result)}")
    print(f"Linear scan time: {linear_ms:.6f} ms")
    print(f"Sorted-index build time: {build_index_ms:.6f} ms")
    print(f"Binary-search query count: {len(binary_result)}")
    print(f"Binary-search query time: {binary_ms:.6f} ms")
    print(f"Binary-search total (build + query): {build_index_ms + binary_ms:.6f} ms")
    print(f"Methods return identical record set: {same_record_set}")
    print()
    print("Sample output:")
    print_records(binary_result, limit=10)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.build:
            run_build(args.build)
            return

        records = load_dataset(args.dataset)

        if args.lookup is not None:
            run_lookup(records, args.lookup)
        elif args.freq:
            run_frequency(records, args.freq)
        elif args.duplicates:
            run_duplicates(records)
        elif args.topk is not None:
            run_topk(records, args.topk)
        elif args.range:
            field, low_str, high_str = args.range
            run_range(records, field, int(low_str), int(high_str))
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
