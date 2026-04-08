# CME7202 — Mini Data Indexer and Query Tool

**Students:** Khalil Gharssallah, Houssem Djebbi  
**Program:** Master Students in Engineering  
**Python:** 3.11 or later (see [pyproject.toml](pyproject.toml))

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites and Setup](#2-prerequisites-and-setup)
3. [Project Structure](#3-project-structure)
4. [Architecture Overview](#4-architecture-overview)
5. [Dataset Specification](#5-dataset-specification)
6. [CLI Reference — main.py](#6-cli-reference--mainpy)
7. [API Reference](#7-api-reference)
   - [constants.py](#71-constantspy)
   - [queries.py](#72-queriespy)
   - [generator.py](#73-generatorpy)
   - [experiments.py](#74-experimentspy)
8. [Running Experiments](#8-running-experiments)
9. [Running Tests](#9-running-tests)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Overview

This project implements a mini in-memory data indexer and query tool for a synthetic CSV dataset. It was built to compare the performance of different data structures for five query types:

| Query type | Baseline | Improved |
|---|---|---|
| Exact ID lookup | Linear scan O(n) | Hash index O(1) |
| Frequency count | — | `Counter` one-pass |
| Duplicate detection | — | `defaultdict` grouping |
| Top-k by score | Full sort O(n log n) | Heap `nlargest` O(n log k) |
| Range query | Linear scan O(n) | Sorted index + bisect O(log n + r) |

All implementation uses the Python standard library only — no pandas, no database, no GUI.

---

## 2. Prerequisites and Setup

### Requirements

- Python **3.11 or later**
- `pytest` 7.0 or later (for running tests only)

On some Windows machines, replace `python` with `py` in all commands below.

### Install test dependency

```bash
pip install pytest
```

Or using the project's `pyproject.toml`:

```bash
pip install -e ".[dev]"
```

### Generate the datasets

All commands must be run from inside the `project/` directory.

```bash
# Small dataset — 3,000 records (required at project root for submission)
python generator.py --size 3000 --seed 7202 --output dataset_small.csv

# Main dataset — 100,000 records, used for experiments
python generator.py --size 100000 --seed 7202 --output data/dataset_main.csv
```

### Smoke test

```bash
python main.py --build dataset_small.csv
```

Expected output:

```
Dataset: dataset_small.csv
Records: 3000
Unique IDs: 3000
Validation complete.
```

---

## 3. Project Structure

```
project/
├── README.md             # This file — setup, usage, API reference
├── analysis.pdf          # Final report (submission)
├── main.py               # CLI entry point — all interactive query commands
├── generator.py          # Synthetic dataset generator
├── queries.py            # Core query and index functions
├── experiments.py        # Automated timing comparisons
├── dataset_small.csv     # 3,000-record dataset (required at root for submission)
├── dataset_spec.txt      # Dataset field specification
├── constants.py          # Shared schema: Record TypedDict, FIELDNAMES, name/category lists
├── analysis.md           # Project report (editable source)
├── test_queries.py       # pytest test suite (47 tests)
├── pyproject.toml        # Python version requirement and dev dependencies
├── data/
│   └── dataset_main.csv  # 100,000-record dataset (generate before running experiments)
└── results/
    ├── timings.csv        # Output of experiments.py
    └── sample_output.txt  # Example CLI outputs
```

---

## 4. Architecture Overview

### Module dependency graph

```
constants.py
  └── Record (TypedDict), FIELDNAMES, NUMERIC_FIELDS, name/category lists
        ▲               ▲               ▲
   queries.py      generator.py    experiments.py
        ▲                               ▲
     main.py                      (standalone CLI)
```

`constants.py` is the single source of truth for the data schema. No other module defines field names or the `Record` type.

### Data flow

```
generator.py
  generates → data/dataset_main.csv (CSV on disk)
                    │
                    ▼
            queries.load_dataset()
                    │
                    ▼
            list[Record]  ← held in memory for the lifetime of one command
            /        \
    build_id_index   range/topk/freq/dup functions
         │
    dict[int, Record]  ← used only by --lookup
```

### Key design decisions

**Single load per invocation.** `main.py` calls `load_dataset()` once and passes the list to all `run_*` functions. No function reloads from disk.

**Lazy indexing.** The hash index (`build_id_index`) is only built when `--lookup` is used, not for every command.

**Pure functions.** Every function in `queries.py` is pure (no side effects, no global state). This makes them independently testable and safe to call from both `main.py` and `experiments.py`.

**Fail-fast validation.** Invalid inputs raise `ValueError` or `FileNotFoundError` immediately, caught at the CLI boundary with a clean error message.

---

## 5. Dataset Specification

Each CSV record has exactly seven fields:

| Field | Type | Range / Values |
|---|---|---|
| `record_id` | int | Sequential, starts at `--start-id` (default 1,000,001) |
| `name` | str | `"FirstName LastName"` — 32 × 30 = 960 unique combinations |
| `category` | str | `books`, `electronics`, `home`, `fashion`, `sports`, `toys`, `grocery` |
| `region` | str | `Marmara`, `Aegean`, `Mediterranean`, `Central Anatolia`, `Black Sea`, `Southeast` |
| `year` | int | 2018 – 2025 |
| `score` | int | 40 – 100 |
| `value` | int | 500 – 5,000 |

**Duplicate rule used in this project:** two records are duplicates if both `name` and `year` match.

**Name pool sizing:** with 960 unique `(first, last)` combinations and 8 year values, there are 7,680 distinct `(name, year)` keys. On a 100,000-record dataset roughly 13 records share each key on average, making duplicate detection non-trivial.

---

## 6. CLI Reference — `main.py`

All commands load `--dataset` once before executing. Run from the `project/` directory.

### Global option

```
--dataset PATH    CSV file to query (default: data/dataset_main.csv)
```

---

### `--build PATH`

Load and validate a dataset, then print statistics. Uses its own path argument, independent of `--dataset`.

```bash
python main.py --build data/dataset_main.csv
```

Output:
```
Dataset: data/dataset_main.csv
Records: 100000
Unique IDs: 100000
Validation complete.
```

Exits with code `1` and an error message if the file is not found or fields are missing.

---

### `--lookup RECORD_ID`

Exact lookup by `record_id`. Runs both linear scan and dict-index lookup and prints timing for each.

```bash
python main.py --dataset data/dataset_main.csv --lookup 1000500
```

Output:
```
Linear scan result:
{"record_id": 1000500, "name": "...", ...}
Linear lookup time: X.XXXXXX ms

Dictionary-based result:
{"record_id": 1000500, "name": "...", ...}
Dictionary lookup time: X.XXXXXX ms
```

Prints `"Record not found."` if the ID does not exist.

---

### `--freq FIELD`

Frequency count for a categorical field. Accepted values: `name`, `category`, `region`.

```bash
python main.py --dataset data/dataset_main.csv --freq category
python main.py --dataset data/dataset_main.csv --freq region
```

Output (sorted by count descending, then alphabetically):
```
Frequency count for field 'category':
sports: 14412
electronics: 14395
...
```

Exits with error if a numeric field (`record_id`, `year`, `score`, `value`) is passed.

---

### `--duplicates`

Detect duplicate `(name, year)` groups and print a summary.

```bash
python main.py --dataset data/dataset_main.csv --duplicates
```

Output:
```
Duplicate rule: duplicate (name, year)
Duplicate groups: N
Records in duplicate groups: M
Sample groups:
1. (Alice Demir, 2020) -> 4 records, IDs sample: [1000123, ...]
...
```

Up to 10 sample groups are shown, sorted alphabetically.

---

### `--topk K`

Return the top-K records by `score` (descending). Ties are broken by `record_id` ascending. Runs both sort-based and heap-based methods.

```bash
python main.py --dataset data/dataset_main.csv --topk 10
python main.py --dataset data/dataset_main.csv --topk 100
```

Output:
```
Top-10 by score (sorting-based):
Count: 10
{"record_id": ..., "score": 100, ...}
...
Sorting-based time: X.XXXXXX ms

Top-10 by score (heap-based):
Count: 10
...
Heap-based time: X.XXXXXX ms
Methods produce identical record_id ordering: True
```

---

### `--range FIELD LOW HIGH`

Range query on a numeric field. Returns records where `LOW <= field <= HIGH`. Runs both linear scan and binary-search methods.

```bash
python main.py --dataset data/dataset_main.csv --range value 1000 3000
python main.py --dataset data/dataset_main.csv --range year 2020 2023
python main.py --dataset data/dataset_main.csv --range score 90 100
```

Accepted fields: `record_id`, `year`, `score`, `value`.

Output:
```
Range query: 1000 <= value <= 3000
Linear scan count: N
Linear scan time: X.XXXXXX ms
Sorted-index build time: X.XXXXXX ms
Binary-search query count: N
Binary-search query time: X.XXXXXX ms
Binary-search total (build + query): X.XXXXXX ms
Methods return identical record set: True

Sample output:
Count: N
{"record_id": ..., "value": 1000, ...}
...
```

Exits with error if `LOW > HIGH` or if the field is not numeric.

---

## 7. API Reference

### 7.1 `constants.py`

Shared schema definitions. Import from here — never redefine in other modules.

#### `FIELDNAMES: list[str]`

Ordered list of all record field names:
```python
["record_id", "name", "category", "region", "year", "score", "value"]
```

#### `NUMERIC_FIELDS: frozenset[str]`

Set of fields whose values are integers: `{"record_id", "year", "score", "value"}`.

#### `FIRST_NAMES`, `LAST_NAMES`, `CATEGORIES`, `REGIONS: list[str]`

Source pools used by `generator.py`. 32 first names × 30 last names = 960 unique name combinations.

#### `class Record(TypedDict)`

The schema for a single dataset record:

```python
class Record(TypedDict):
    record_id: int
    name:      str
    category:  str
    region:    str
    year:      int
    score:     int
    value:     int
```

All fields are required. Use this type for all annotations instead of `dict[str, int | str]`.

---

### 7.2 `queries.py`

All functions are pure (no side effects). Import `Record` via `from queries import Record` or `from constants import Record`.

---

#### `load_dataset(dataset_path: str | Path) -> list[Record]`

Load and parse a CSV file. All numeric fields are converted to `int` at parse time.

```python
records = load_dataset("data/dataset_main.csv")
```

**Raises:**
- `FileNotFoundError` — path does not exist
- `ValueError` — CSV is missing required columns, or a value cannot be parsed as `int`

---

#### `build_id_index(records: list[Record]) -> dict[int, Record]`

Build a hash index mapping `record_id → Record`.

```python
index = build_id_index(records)
```

**Note:** Prints a warning to stdout for each duplicate `record_id` encountered. The later record overwrites the earlier one.

**Complexity:** O(n) time, O(n) space.

---

#### `lookup_linear(records: list[Record], record_id: int) -> Record | None`

Find a record by `record_id` using sequential scan. Returns `None` if not found.

**Complexity:** O(n) per call.

---

#### `lookup_dict(id_index: dict[int, Record], record_id: int) -> Record | None`

Find a record by `record_id` using a pre-built hash index. Returns `None` if not found.

**Complexity:** O(1) average per call.

---

#### `frequency_count(records: list[Record], field: str) -> dict[str, int]`

Count occurrences of each value for a categorical field.

```python
freqs = frequency_count(records, "category")
# {"books": 14280, "electronics": 14395, ...}
```

**Raises:** `ValueError` if `field` is unknown or is a numeric field.  
**Complexity:** O(n) time, O(m) space where m = number of distinct values.

---

#### `find_duplicates_name_year(records: list[Record]) -> dict[tuple[str, int], list[Record]]`

Group records by `(name, year)` and return only groups with more than one member.

```python
dupes = find_duplicates_name_year(records)
# {("Alice Demir", 2020): [record1, record3], ...}
```

**Complexity:** O(n) expected time, O(n) space.

---

#### `top_k_sort(records: list[Record], k: int) -> list[Record]`

Return the top-k records by `score` descending using a full sort. Ties broken by `record_id` ascending. Returns `[]` if `k <= 0`.

**Complexity:** O(n log n) time.

---

#### `top_k_heap(records: list[Record], k: int) -> list[Record]`

Return the top-k records by `score` descending using `heapq.nlargest`. Same tie-breaking and return behavior as `top_k_sort`. Results are guaranteed identical to `top_k_sort`.

**Complexity:** O(n log k) time, O(k) auxiliary space.

---

#### `build_sorted_numeric_index(records: list[Record], field: str) -> tuple[list[int], list[Record]]`

Sort records by a numeric field and return the parallel `(values, records)` arrays required by `range_query_binary`. Records with equal field values are sub-sorted by `record_id`.

```python
sorted_values, sorted_records = build_sorted_numeric_index(records, "value")
```

**Raises:** `ValueError` if `field` is not in `NUMERIC_FIELDS`.  
**Complexity:** O(n log n) time, O(n) space.

---

#### `range_query_linear(records: list[Record], field: str, low: int, high: int) -> list[Record]`

Return all records where `low <= record[field] <= high` using a full scan.

**Raises:** `ValueError` if `field` is not numeric, or if `low > high`.  
**Complexity:** O(n) per call.

---

#### `range_query_binary(sorted_values: list[int], sorted_records: list[Record], low: int, high: int) -> list[Record]`

Return all records in range using binary search on a pre-sorted index. `sorted_values` and `sorted_records` must come from `build_sorted_numeric_index`.

**Raises:** `ValueError` if `low > high`.  
**Complexity:** O(log n + r) per call, where r = number of results.

---

### 7.3 `generator.py`

#### `generate_records(size, seed, start_id=1_000_001, duplicate_rate=0.02) -> list[Record]`

Generate a deterministic list of synthetic records.

| Parameter | Type | Description |
|---|---|---|
| `size` | int | Number of records to generate |
| `seed` | int | Random seed for full reproducibility |
| `start_id` | int | First `record_id` value (default 1,000,001) |
| `duplicate_rate` | float | Probability (0–1) of reusing an existing `(name, year)` pair |

Records are generated in sequential ID order. The name pool (960 combinations × 8 years = 7,680 keys) is sized to avoid birthday-paradox saturation on 100,000-record datasets.

#### `write_dataset(records: list[Record], output_path: Path) -> None`

Write records to a CSV file. Creates parent directories if they do not exist. Overwrites any existing file.

#### CLI

```bash
python generator.py [--size N] [--seed S] [--output PATH]
                    [--start-id ID] [--duplicate-rate R]
```

| Option | Default | Description |
|---|---|---|
| `--size` | 100,000 | Number of records |
| `--seed` | 7202 | Random seed |
| `--output` | `data/dataset_main.csv` | Output path |
| `--start-id` | 1,000,001 | First record_id |
| `--duplicate-rate` | 0.02 | Explicit duplicate injection rate |

---

### 7.4 `experiments.py`

Automates all required method comparisons and writes results to a CSV.

#### `_time_individually(fn, args_list) -> tuple[float, float, float]`

Internal timing helper. Runs one warmup call, then times each call in `args_list` individually.

Returns `(total_ms, avg_ms, stddev_ms)`.

**Note on sub-millisecond operations:** `perf_counter()` has ~0.0001 ms overhead per call. For operations under ~0.01 ms (e.g., dict lookup), stddev reflects timer noise as much as true variance. The averages remain accurate.

#### `measure_id_lookup(records, lookup_count, rng) -> list[TimingRow]`

Time `lookup_count` random ID lookups using both linear scan and dict index. Returns two `TimingRow` objects.

#### `measure_topk(records, k_values, repeats) -> list[TimingRow]`

Time top-k for each value in `k_values` using both sort and heap, each repeated `repeats` times. Returns two `TimingRow` objects per k value.

A separate correctness check (outside the timed section) verifies sort and heap produce identical results.

#### `measure_range_query(records, field, query_count, rng) -> list[TimingRow]`

Time `query_count` random range queries on `field` using linear scan and binary search. Returns three `TimingRow` objects: linear scan, index build (one-time), and binary search.

**Important:** To compare total cost fairly, add `sorted_index_build` time to `binary_search` total — the CSV has a dedicated row for this.

**Raises:** `ValueError` if `field` is not in `NUMERIC_FIELDS`.

#### `write_timings(rows: list[TimingRow], output_path: Path) -> None`

Write timing results to CSV. Prints a warning if the output file already exists (it will be overwritten).

CSV columns: `experiment`, `method`, `parameter`, `runs`, `total_time_ms`, `avg_time_ms`, `stddev_ms`, `notes`.

#### `class TimingRow`

```python
@dataclass
class TimingRow:
    experiment:   str    # e.g. "A_ID_lookup"
    method:       str    # e.g. "linear_scan"
    parameter:    str    # e.g. "1000_lookups"
    runs:         int
    total_time_ms: float
    avg_time_ms:  float
    stddev_ms:    float
    notes:        str
```

#### CLI

```bash
python experiments.py [--dataset PATH] [--output PATH] [--seed S]
                      [--lookups N] [--range-queries N]
                      [--topk-repeats N] [--topk-values K [K ...]]
                      [--range-field FIELD]
```

| Option | Default | Description |
|---|---|---|
| `--dataset` | `data/dataset_main.csv` | Input dataset |
| `--output` | `results/timings.csv` | Output CSV |
| `--seed` | 7202 | RNG seed for query generation |
| `--lookups` | 1000 | Number of random ID lookups |
| `--range-queries` | 500 | Number of random range queries |
| `--topk-repeats` | 30 | Repeats per top-k method per k |
| `--topk-values` | `10 100` | k values to test |
| `--range-field` | `value` | Numeric field for range comparison |

---

## 8. Running Experiments

```bash
# Default run (100k dataset, all defaults)
python experiments.py

# Custom run
python experiments.py \
  --dataset data/dataset_main.csv \
  --output results/timings.csv \
  --seed 7202 \
  --lookups 1000 \
  --range-queries 500 \
  --topk-repeats 30 \
  --topk-values 10 100 \
  --range-field value
```

Console output (one line per measurement):
```
Loaded records: 100000
Wrote timings: results/timings.csv
A_ID_lookup    | linear_scan      | 1000_lookups          | avg=X.XXXX ms  std=X.XXXX ms
A_ID_lookup    | dict_index       | 1000_lookups          | avg=X.XXXX ms  std=X.XXXX ms
B_top_k        | sorting          | k=10                  | avg=X.XXXX ms  std=X.XXXX ms
...
```

### Reading `timings.csv`

The range query experiment produces three rows. To compare total cost fairly:

```
linear_scan total      → stands alone (no preprocessing)
sorted_index_build     → one-time cost, add to binary_search total
binary_search total    → add sorted_index_build to get true total
```

The `notes` column of the `binary_search` row includes the pre-computed total.

---

## 9. Running Tests

```bash
# Run all 47 tests
pytest test_queries.py

# Verbose output
pytest test_queries.py -v

# Run a specific test class
pytest test_queries.py::TestRangeQuery -v
```

Test coverage covers every public function in `queries.py`:

| Test class | Functions covered |
|---|---|
| `TestParseRow` | `_parse_row` |
| `TestLoadDataset` | `load_dataset` |
| `TestBuildIdIndex` | `build_id_index` |
| `TestLookup` | `lookup_linear`, `lookup_dict` |
| `TestFrequencyCount` | `frequency_count` |
| `TestFindDuplicates` | `find_duplicates_name_year` |
| `TestTopK` | `top_k_sort`, `top_k_heap` |
| `TestRangeQuery` | `range_query_linear`, `range_query_binary` |
| `TestBuildSortedIndex` | `build_sorted_numeric_index` |

All tests use small in-memory fixtures (`RECORDS`, 5 entries). No dataset files are required to run tests.

---

## 10. Troubleshooting

### `ModuleNotFoundError: No module named 'constants'`

You are not running from the `project/` directory. All scripts must be run from there:

```bash
cd "path/to/project advanced structure data/project"
python main.py --build data/dataset_main.csv
```

---

### `FileNotFoundError: Dataset not found: data/dataset_main.csv`

The main dataset has not been generated yet. Run:

```bash
python generator.py --size 100000 --seed 7202 --output data/dataset_main.csv
```

---

### `Error: Dataset is missing required fields: [...]`

The CSV file is malformed or was generated by a different version of the code. Regenerate it:

```bash
python generator.py --size 100000 --seed 7202 --output data/dataset_main.csv
```

---

### `Error: low (X) must be <= high (Y)`

The `--range` arguments are in the wrong order. `LOW` must be ≤ `HIGH`:

```bash
# Wrong
python main.py --range score 100 40

# Correct
python main.py --range score 40 100
```

---

### `Error: Frequency counting requires a categorical field, got: score`

`--freq` only accepts categorical fields: `name`, `category`, `region`. For numeric distributions, use `--range` instead.

---

### `Warning: duplicate record_id N — later record overwrites earlier.`

The dataset has two records sharing the same `record_id`. This should not happen with datasets generated by `generator.py`. If you manually edited the CSV, check for duplicate ID rows. The dict-based lookup will return the last record seen for that ID; the linear scan will return the first.

---

### `Warning: overwriting existing results at results/timings.csv`

`experiments.py` found an existing `timings.csv` and overwrote it. This is expected on re-runs. If you want to preserve old results, rename the file first:

```bash
mv results/timings.csv results/timings_backup.csv
python experiments.py
```

---

### Tests fail with `ImportError`

Make sure pytest is installed and you are running from the `project/` directory:

```bash
pip install pytest
cd "path/to/project advanced structure data/project"
pytest test_queries.py
```

---

### Timing results are inconsistent between runs

Single-run timing measurements are sensitive to OS scheduling and background processes. To reduce variance:

- Close other applications during experiment runs.
- Use `--topk-repeats 50` or higher for more stable averages.
- Compare `avg_time_ms`, not `total_time_ms`, across runs with different `--lookups` or `--range-queries` counts.
- The `stddev_ms` column shows run-to-run variance for each measurement.

---

### `py` vs `python`

On Windows, if `python` is not recognized, use `py`:

```bash
py main.py --build data/dataset_main.csv
py generator.py --size 100000 --seed 7202
py experiments.py
py -m pytest test_queries.py
```

---

## 11. Submission Checklist

Before creating the ZIP file, run every step below from inside the `project/` directory.

**Step 1 — Generate the required datasets**

```bash
python generator.py --size 3000  --seed 7202 --output dataset_small.csv
python generator.py --size 100000 --seed 7202 --output data/dataset_main.csv
```

**Step 2 — Run the experiments and save results**

```bash
python experiments.py --dataset data/dataset_main.csv --output results/timings.csv
```

**Step 3 — Smoke-test every command**

```bash
python main.py --build dataset_small.csv
python main.py --dataset dataset_small.csv --lookup 1000100
python main.py --dataset dataset_small.csv --freq category
python main.py --dataset dataset_small.csv --duplicates
python main.py --dataset dataset_small.csv --topk 10
python main.py --dataset dataset_small.csv --range value 1000 3000
```

**Step 4 — Verify the required file tree exists**

```
project/
├── README.md             ✓
├── analysis.pdf          ✓
├── main.py               ✓
├── generator.py          ✓
├── queries.py            ✓
├── experiments.py        ✓
├── dataset_small.csv     ✓  ← must be here, not only in data/
├── dataset_spec.txt      ✓
└── results/
    ├── timings.csv       ✓
    └── sample_output.txt ✓
```

**Step 5 — Create the ZIP**

```bash
# From the parent directory of project/
zip -r "KhalilGharssallah-HoussemDjebbi.zip" project/
```

The large dataset (`data/dataset_main.csv`) may be excluded if it exceeds the upload limit. Include `generator.py`, `dataset_spec.txt`, and `dataset_small.csv`, and note regeneration instructions in the README.
