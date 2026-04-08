# CME7202 - Advanced Data Structures
## Midterm Replacement Project

**Project:** Mini Data Indexer and Query Tool  
**Students:** Khalil Gharssallah, Houssem Djebbi  
**Program:** Master Students in Engineering

## 1. Approach
Our objective was to implement the required queries with clear data-structure choices, then validate these choices experimentally.

### 1.1 Data Representation
- Dataset is stored as a list of records (`list[dict]`) loaded from CSV.
- Each record has exactly the required fields:
  `record_id, name, category, region, year, score, value`.

### 1.2 Chosen Structures and Methods
- **Exact lookup by ID**
  - Baseline: linear scan over list.
  - Improved: hash index (`dict[int, record]`).
  - Reason: hash table gives expected `O(1)` query time after one `O(n)` build.

- **Frequency counting**
  - Used `collections.Counter` on a categorical field (`category` or `region`).
  - Reason: direct and efficient one-pass counting.

- **Duplicate detection**
  - Rule used: duplicate `(name, year)`.
  - Structure: `defaultdict(list)` grouping by `(name, year)`.
  - Reason: grouping by key is simple and linear-time.

- **Top-k by score**
  - Method A: full sort by score descending.
  - Method B: `heapq.nlargest(k, ...)`.
  - Reason: sorting is straightforward baseline, heap is asymptotically better for small `k`.

- **Range query on numeric field (`value`)**
  - Method A: linear filtering.
  - Method B: sort once + binary search with `bisect_left/bisect_right`.
  - Reason: preprocessing cost can be amortized over repeated queries.

### 1.3 Engineering Notes
- Standard Python library only (no pandas, no DB, no GUI).
- CLI entry points support all required commands.
- Deterministic generation via explicit random seed.

## 2. Correctness Arguments
We give short correctness claims for each task.

### Claim 1: Exact Lookup Correctness
- **Linear scan:** returns a record iff some record has matching `record_id`, because all records are checked sequentially.
- **Dictionary lookup:** for index `I[id] = record`, query returns exactly the record mapped to that key, or `None` if key is absent.

### Claim 2: Frequency Count Correctness
For each record, exactly one increment is applied to the selected categorical value. Therefore, final counts equal true occurrence frequencies.

### Claim 3: Duplicate Detection Correctness
All records with same `(name, year)` are inserted into the same group key. A key is reported iff its group size is greater than 1, which is exactly the duplicate definition used.

### Claim 4: Top-k Correctness
- Sorting-based method globally orders records by score descending, so first `k` are top-k.
- Heap-based method (`nlargest`) returns the `k` elements with largest keys.
- We validate equivalence in experiments (`same_result=True`).

### Claim 5: Range Query Correctness
- Linear method includes exactly records satisfying `a <= value <= b`.
- Binary method finds the leftmost index of `a` and rightmost index after `b` in sorted values, then returns exactly that slice.
- Validation in experiments confirms returned sets match (`validated=True`).

## 3. Complexity Analysis
Let:
- `n` = number of records
- `m` = number of distinct categorical values
- `k` = requested top-k size
- `r` = number of records in range-query result

| Task | Method | Time Complexity | Space Complexity |
| :-- | :-- | :-- | :-- |
| ID lookup | Linear scan | O(n) per query | O(1) extra |
| ID lookup | Dictionary index | Build O(n), query O(1) average | O(n) |
| Frequency count | Counter | O(n) | O(m) |
| Duplicate detection | Group by (name, year) | O(n) expected | O(n) worst case |
| Top-k | Full sort | O(n log n) | O(n) |
| Top-k | Heap (nlargest) | O(n log k) | O(k) auxiliary |
| Range query | Linear scan | O(n) per query | O(1) extra |
| Range query | Sorted + binary search | Preprocess O(n log n), query O(log n + r) | O(n) |

## 4. Experiments and Discussion
### 4.1 Setup
- Python 3.11.9
- Main dataset size: 100,000 records
- Random seed: 7202
- Results file: `results/timings.csv`

### 4.2 Measured Results
From the timing file:

- **A) ID lookup (1000 random queries)**
  - Linear: `5.909339 ms` per lookup
  - Dictionary: `0.000560 ms` per lookup
  - Speedup: about `10,552x`

- **B) Top-k**
  - `k=10`: sort `84.384000 ms`, heap `36.204703 ms` -> heap about `2.33x` faster
  - `k=100`: sort `73.243140 ms`, heap `38.119893 ms` -> heap about `1.92x` faster

- **C) Range query on `value` (500 queries)**
  - Linear: `14.243093 ms` per query
  - Binary query (after preprocessing): `0.347548 ms` per query
  - One-time preprocess cost: `118.018400 ms`
  - Query-time speedup: about `40.98x`

### 4.3 Interpretation
- Hash indexing is the dominant improvement for repeated exact lookups.
- Heap top-k is better than full sorting when `k` is much smaller than `n`.
- Sorted index + binary search is strongly beneficial for repeated range queries.
- Break-even for range preprocessing is very low:
  around `9` queries already compensate the one-time sort cost.

## 5. AI Usage Disclosure
AI was used according to assignment rules.

- **Tool used:** OpenAI Codex (GPT-5 based assistant).
- **How it was used:** brainstorming structure, debugging support, and language polishing.
- **Student responsibility:** all logic, outputs, and report statements were reviewed and verified by us before submission.

We confirm:
- no fabricated measurements,
- no hidden AI usage,
- and full understanding of submitted code and report.
