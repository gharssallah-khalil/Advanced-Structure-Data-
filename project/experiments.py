"""Performance experiments for the required task comparisons."""

from __future__ import annotations

import argparse
import csv
import random
import statistics
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from constants import NUMERIC_FIELDS
from queries import (
    Record,
    build_id_index,
    build_sorted_numeric_index,
    load_dataset,
    lookup_dict,
    lookup_linear,
    range_query_binary,
    range_query_linear,
    top_k_heap,
    top_k_sort,
)


@dataclass
class TimingRow:
    experiment: str
    method: str
    parameter: str
    runs: int
    total_time_ms: float
    avg_time_ms: float
    stddev_ms: float
    notes: str

    def to_dict(self) -> dict[str, str | int]:
        return {
            "experiment": self.experiment,
            "method": self.method,
            "parameter": self.parameter,
            "runs": self.runs,
            "total_time_ms": f"{self.total_time_ms:.6f}",
            "avg_time_ms": f"{self.avg_time_ms:.6f}",
            "stddev_ms": f"{self.stddev_ms:.6f}",
            "notes": self.notes,
        }


def _time_individually(
    fn: Callable[..., object],
    args_list: list[tuple[object, ...]],
) -> tuple[float, float, float]:
    """
    Run fn once as warmup, then time each call individually.
    Returns (total_ms, avg_ms, stddev_ms).

    Warmup uses args_list[0], which primes CPython's internal dispatch
    and any interpreter-level caches. For data-cache effects on large
    lists the warmup is representative since query IDs are random.

    Note: per-call perf_counter() overhead is ~0.0001 ms; treat stddev
    as an approximation for sub-millisecond operations.
    """
    fn(*args_list[0])  # warmup
    times: list[float] = []
    for args in args_list:
        t0 = perf_counter()
        fn(*args)
        times.append((perf_counter() - t0) * 1000)
    total = sum(times)
    avg = statistics.mean(times)
    std = statistics.stdev(times) if len(times) > 1 else 0.0
    return total, avg, std


def measure_id_lookup(
    records: list[Record],
    lookup_count: int,
    rng: random.Random,
) -> list[TimingRow]:
    id_index = build_id_index(records)
    record_ids = [record["record_id"] for record in records]
    query_ids = [rng.choice(record_ids) for _ in range(lookup_count)]

    linear_total, linear_avg, linear_std = _time_individually(
        lookup_linear, [(records, qid) for qid in query_ids]
    )
    dict_total, dict_avg, dict_std = _time_individually(
        lookup_dict, [(id_index, qid) for qid in query_ids]
    )

    return [
        TimingRow(
            experiment="A_ID_lookup",
            method="linear_scan",
            parameter=f"{lookup_count}_lookups",
            runs=lookup_count,
            total_time_ms=linear_total,
            avg_time_ms=linear_avg,
            stddev_ms=linear_std,
            notes="Lookup by record_id with sequential scan.",
        ),
        TimingRow(
            experiment="A_ID_lookup",
            method="dict_index",
            parameter=f"{lookup_count}_lookups",
            runs=lookup_count,
            total_time_ms=dict_total,
            avg_time_ms=dict_avg,
            stddev_ms=dict_std,
            notes="Lookup by record_id using hash map.",
        ),
    ]


def measure_topk(
    records: list[Record],
    k_values: Iterable[int],
    repeats: int,
) -> list[TimingRow]:
    rows: list[TimingRow] = []
    for k in k_values:
        # Each method: 1 warmup + repeats timed calls (inside _time_individually)
        sort_total, sort_avg, sort_std = _time_individually(
            top_k_sort, [(records, k)] * repeats
        )
        heap_total, heap_avg, heap_std = _time_individually(
            top_k_heap, [(records, k)] * repeats
        )

        # Correctness check outside the timed section
        sort_result = top_k_sort(records, k)
        heap_result = top_k_heap(records, k)
        same_ids = (
            [r["record_id"] for r in sort_result] == [r["record_id"] for r in heap_result]
        )

        rows.extend([
            TimingRow(
                experiment="B_top_k",
                method="sorting",
                parameter=f"k={k}",
                runs=repeats,
                total_time_ms=sort_total,
                avg_time_ms=sort_avg,
                stddev_ms=sort_std,
                notes="Sort entire dataset by score descending.",
            ),
            TimingRow(
                experiment="B_top_k",
                method="heap",
                parameter=f"k={k}",
                runs=repeats,
                total_time_ms=heap_total,
                avg_time_ms=heap_avg,
                stddev_ms=heap_std,
                notes=f"heapq.nlargest top-k. same_result={same_ids}",
            ),
        ])
    return rows


def measure_range_query(
    records: list[Record],
    field: str,
    query_count: int,
    rng: random.Random,
) -> list[TimingRow]:
    if field not in NUMERIC_FIELDS:
        raise ValueError(f"Range queries require numeric field, got: {field}")

    values = [int(record[field]) for record in records]  # type: ignore[arg-type]
    min_value, max_value = min(values), max(values)

    ranges: list[tuple[int, int]] = []
    for _ in range(query_count):
        a = rng.randint(min_value, max_value)
        b = rng.randint(min_value, max_value)
        ranges.append((min(a, b), max(a, b)))

    linear_total, linear_avg, linear_std = _time_individually(
        range_query_linear, [(records, field, lo, hi) for lo, hi in ranges]
    )

    index_start = perf_counter()
    sorted_values, sorted_records = build_sorted_numeric_index(records, field)
    build_index_ms = (perf_counter() - index_start) * 1000

    binary_total, binary_avg, binary_std = _time_individually(
        range_query_binary, [(sorted_values, sorted_records, lo, hi) for lo, hi in ranges]
    )

    # Validate correctness on first 20 ranges
    validation_ok = all(
        {r["record_id"] for r in range_query_linear(records, field, lo, hi)}
        == {r["record_id"] for r in range_query_binary(sorted_values, sorted_records, lo, hi)}
        for lo, hi in ranges[:20]
    )

    return [
        TimingRow(
            experiment="C_range_query",
            method="linear_scan",
            parameter=f"{field},{query_count}_queries",
            runs=query_count,
            total_time_ms=linear_total,
            avg_time_ms=linear_avg,
            stddev_ms=linear_std,
            notes=f"Range filter by {field} with full scan.",
        ),
        TimingRow(
            experiment="C_range_query",
            method="sorted_index_build",
            parameter=f"build_index_{field}",
            runs=1,
            total_time_ms=build_index_ms,
            avg_time_ms=build_index_ms,
            stddev_ms=0.0,
            notes="One-time preprocessing sort cost (add to binary_search total for fair comparison).",
        ),
        TimingRow(
            experiment="C_range_query",
            method="binary_search",
            parameter=f"{field},{query_count}_queries",
            runs=query_count,
            total_time_ms=binary_total,
            avg_time_ms=binary_avg,
            stddev_ms=binary_std,
            notes=(
                f"Bisect on sorted {field}. validated={validation_ok}. "
                f"Total with build={build_index_ms + binary_total:.2f} ms"
            ),
        ),
    ]


def write_timings(rows: list[TimingRow], output_path: Path) -> None:
    if output_path.exists():
        print(f"Warning: overwriting existing results at {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "experiment", "method", "parameter", "runs",
                "total_time_ms", "avg_time_ms", "stddev_ms", "notes",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_dict())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run required performance comparisons.")
    parser.add_argument("--dataset", default="data/dataset_main.csv", help="Main dataset CSV path.")
    parser.add_argument("--output", type=Path, default=Path("results/timings.csv"), help="Output CSV path.")
    parser.add_argument("--seed", type=int, default=7202, help="Random seed for query generation.")
    parser.add_argument("--lookups", type=int, default=1000, help="Number of random ID lookups.")
    parser.add_argument("--range-queries", type=int, default=500, help="Number of random range queries.")
    parser.add_argument("--topk-repeats", type=int, default=30, help="Repeats for each top-k method.")
    parser.add_argument(
        "--topk-values",
        type=int,
        nargs="+",
        default=[10, 100],
        metavar="K",
        help="K values to test for top-k comparison (default: 10 100).",
    )
    parser.add_argument("--range-field", default="value", help="Numeric field for range comparison.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        records = load_dataset(args.dataset)
        rng = random.Random(args.seed)

        rows: list[TimingRow] = []
        rows.extend(measure_id_lookup(records, args.lookups, rng))
        rows.extend(measure_topk(records, args.topk_values, args.topk_repeats))
        rows.extend(measure_range_query(records, args.range_field, args.range_queries, rng))
        write_timings(rows, args.output)

        print(f"Loaded records: {len(records)}")
        print(f"Wrote timings: {args.output}")
        for row in rows:
            print(
                f"{row.experiment:14s} | {row.method:17s} | {row.parameter:22s} | "
                f"avg={row.avg_time_ms:.4f} ms  std={row.stddev_ms:.4f} ms"
            )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
