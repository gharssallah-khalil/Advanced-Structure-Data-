"""Core query functions for the CME7202 mini indexer project."""

from __future__ import annotations

import csv
import heapq
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from pathlib import Path

from constants import FIELDNAMES, NUMERIC_FIELDS, Record


def _parse_row(row: dict[str, str]) -> Record:
    if missing := set(FIELDNAMES) - set(row):
        raise ValueError(f"Missing fields in row: {sorted(missing)}")
    return {
        "record_id": int(row["record_id"]),
        "name": row["name"],
        "category": row["category"],
        "region": row["region"],
        "year": int(row["year"]),
        "score": int(row["score"]),
        "value": int(row["value"]),
    }


def load_dataset(dataset_path: str | Path) -> list[Record]:
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    records: list[Record] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = set(FIELDNAMES) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Dataset is missing required fields: {sorted(missing)}")
        for row in reader:
            records.append(_parse_row(row))
    return records


def build_id_index(records: list[Record]) -> dict[int, Record]:
    index: dict[int, Record] = {}
    for record in records:
        rid = record["record_id"]
        if rid in index:
            print(f"Warning: duplicate record_id {rid} — later record overwrites earlier.")
        index[rid] = record
    return index


def lookup_linear(records: list[Record], record_id: int) -> Record | None:
    for record in records:
        if record["record_id"] == record_id:
            return record
    return None


def lookup_dict(id_index: dict[int, Record], record_id: int) -> Record | None:
    return id_index.get(record_id)


def frequency_count(records: list[Record], field: str) -> dict[str, int]:
    if field not in FIELDNAMES:
        raise ValueError(f"Unknown field: {field}")
    if field in NUMERIC_FIELDS:
        raise ValueError(f"Frequency counting requires a categorical field, got: {field}")
    return dict(Counter(record[field] for record in records))  # type: ignore[arg-type]


def find_duplicates_name_year(records: list[Record]) -> dict[tuple[str, int], list[Record]]:
    groups: defaultdict[tuple[str, int], list[Record]] = defaultdict(list)
    for record in records:
        key = (record["name"], record["year"])
        groups[key].append(record)
    return {key: group for key, group in groups.items() if len(group) > 1}


def top_k_sort(records: list[Record], k: int) -> list[Record]:
    if k <= 0:
        return []
    return sorted(records, key=lambda r: (-r["score"], r["record_id"]))[:k]


def top_k_heap(records: list[Record], k: int) -> list[Record]:
    if k <= 0:
        return []
    best = heapq.nlargest(k, records, key=lambda r: (r["score"], -r["record_id"]))
    best.sort(key=lambda r: (-r["score"], r["record_id"]))
    return best


def range_query_linear(records: list[Record], field: str, low: int, high: int) -> list[Record]:
    if field not in NUMERIC_FIELDS:
        raise ValueError(f"Range queries require numeric field, got: {field}")
    if low > high:
        raise ValueError(f"low ({low}) must be <= high ({high})")
    return [record for record in records if low <= int(record[field]) <= high]  # type: ignore[arg-type]


def build_sorted_numeric_index(
    records: list[Record], field: str
) -> tuple[list[int], list[Record]]:
    if field not in NUMERIC_FIELDS:
        raise ValueError(f"Range index requires numeric field, got: {field}")
    sorted_records = sorted(records, key=lambda r: (int(r[field]), r["record_id"]))  # type: ignore[arg-type]
    values = [int(record[field]) for record in sorted_records]  # type: ignore[arg-type]
    return values, sorted_records


def range_query_binary(
    sorted_values: list[int],
    sorted_records: list[Record],
    low: int,
    high: int,
) -> list[Record]:
    if low > high:
        raise ValueError(f"low ({low}) must be <= high ({high})")
    left = bisect_left(sorted_values, low)
    right = bisect_right(sorted_values, high)
    return sorted_records[left:right]
