"""Dataset generator for the CME7202 mini indexer project."""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

from constants import CATEGORIES, FIELDNAMES, FIRST_NAMES, LAST_NAMES, REGIONS, Record


def generate_records(
    size: int,
    seed: int,
    start_id: int = 1_000_001,
    duplicate_rate: float = 0.02,
) -> list[Record]:
    """
    Generate synthetic records.

    Duplicate rule supported by generation: duplicate (name, year) pairs.
    """
    rng = random.Random(seed)
    records: list[Record] = []

    for idx in range(size):
        record_id = start_id + idx

        if records and rng.random() < duplicate_rate:
            source = rng.choice(records)
            name = str(source["name"])
            year = int(source["year"])
        else:
            name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
            year = rng.randint(2018, 2025)

        records.append({
            "record_id": record_id,
            "name": name,
            "category": rng.choice(CATEGORIES),
            "region": rng.choice(REGIONS),
            "year": year,
            "score": rng.randint(40, 100),
            "value": rng.randint(500, 5000),
        })

    return records


def write_dataset(records: list[dict[str, int | str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(records)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate synthetic CSV dataset.")
    parser.add_argument("--size", type=int, default=100_000, help="Number of records to generate.")
    parser.add_argument("--seed", type=int, default=7202, help="Random seed for reproducibility.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/dataset_main.csv"),
        help="Output CSV path.",
    )
    parser.add_argument(
        "--start-id",
        type=int,
        default=1_000_001,
        help="Starting record_id value.",
    )
    parser.add_argument(
        "--duplicate-rate",
        type=float,
        default=0.02,
        help="Probability of reusing an existing (name, year) pair.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.size <= 0:
        parser.error("--size must be positive.")
    if not (0.0 <= args.duplicate_rate <= 1.0):
        parser.error("--duplicate-rate must be between 0 and 1.")

    records = generate_records(
        size=args.size,
        seed=args.seed,
        start_id=args.start_id,
        duplicate_rate=args.duplicate_rate,
    )
    write_dataset(records, args.output)

    print(f"Generated {len(records)} records.")
    print(f"Output: {args.output}")
    print(f"Seed: {args.seed}")


if __name__ == "__main__":
    main()
