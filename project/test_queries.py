"""Tests for queries.py — run with: pytest test_queries.py"""

from __future__ import annotations

import pytest

from constants import Record
from queries import (
    _parse_row,
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

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

RECORDS: list[Record] = [
    {"record_id": 1, "name": "Alice Demir",  "category": "books",       "region": "Marmara", "year": 2020, "score": 80, "value": 1000},
    {"record_id": 2, "name": "Bob Kaya",     "category": "electronics", "region": "Aegean",  "year": 2021, "score": 90, "value": 2000},
    {"record_id": 3, "name": "Alice Demir",  "category": "home",        "region": "Marmara", "year": 2020, "score": 70, "value": 1500},
    {"record_id": 4, "name": "Carol Yilmaz", "category": "books",       "region": "Aegean",  "year": 2022, "score": 85, "value":  500},
    {"record_id": 5, "name": "Dave Aydin",   "category": "electronics", "region": "Marmara", "year": 2021, "score": 90, "value": 3000},
]
# Records 1 & 3: same (name, year) → duplicate pair.
# Records 2 & 5: same score (90); record 2 wins tie-break (lower record_id).


# ---------------------------------------------------------------------------
# _parse_row
# ---------------------------------------------------------------------------

class TestParseRow:
    VALID_ROW = {
        "record_id": "1", "name": "Alice Demir", "category": "books",
        "region": "Marmara", "year": "2020", "score": "80", "value": "1000",
    }

    def test_numeric_fields_become_int(self):
        record = _parse_row(self.VALID_ROW)
        for field in ("record_id", "year", "score", "value"):
            assert isinstance(record[field], int), f"{field} should be int"

    def test_string_fields_remain_str(self):
        record = _parse_row(self.VALID_ROW)
        for field in ("name", "category", "region"):
            assert isinstance(record[field], str), f"{field} should be str"

    def test_values_are_correct(self):
        record = _parse_row(self.VALID_ROW)
        assert record["record_id"] == 1
        assert record["name"] == "Alice Demir"
        assert record["score"] == 80

    def test_missing_fields_raises(self):
        with pytest.raises(ValueError, match="Missing fields"):
            _parse_row({"record_id": "1", "name": "Alice"})

    def test_non_numeric_value_raises(self):
        bad = {**self.VALID_ROW, "score": "ninety"}
        with pytest.raises(ValueError):
            _parse_row(bad)


# ---------------------------------------------------------------------------
# load_dataset
# ---------------------------------------------------------------------------

class TestLoadDataset:
    HEADER = "record_id,name,category,region,year,score,value\n"

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_dataset(tmp_path / "nonexistent.csv")

    def test_missing_columns_raises(self, tmp_path):
        f = tmp_path / "bad.csv"
        f.write_text("record_id,name\n1,Alice\n")
        with pytest.raises(ValueError, match="missing required fields"):
            load_dataset(f)

    def test_loads_correct_count(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_text(self.HEADER + "1000001,Alice Demir,books,Marmara,2020,80,1000\n")
        assert len(load_dataset(f)) == 1

    def test_numeric_fields_parsed_as_int(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_text(self.HEADER + "1000001,Alice Demir,books,Marmara,2020,80,1000\n")
        record = load_dataset(f)[0]
        assert record["record_id"] == 1_000_001
        assert isinstance(record["record_id"], int)
        assert record["score"] == 80


# ---------------------------------------------------------------------------
# build_id_index
# ---------------------------------------------------------------------------

class TestBuildIdIndex:
    def test_all_ids_indexed(self):
        index = build_id_index(RECORDS)
        assert set(index.keys()) == {1, 2, 3, 4, 5}

    def test_correct_record_returned(self):
        index = build_id_index(RECORDS)
        assert index[3]["name"] == "Alice Demir"
        assert index[3]["score"] == 70

    def test_duplicate_id_prints_warning(self, capsys):
        dupes = RECORDS + [
            {"record_id": 1, "name": "Dup", "category": "books",
             "region": "Marmara", "year": 2020, "score": 50, "value": 500}
        ]
        build_id_index(dupes)
        assert "Warning" in capsys.readouterr().out

    def test_duplicate_id_later_record_wins(self, capsys):
        dupes = RECORDS + [
            {"record_id": 1, "name": "Later", "category": "books",
             "region": "Marmara", "year": 2020, "score": 50, "value": 500}
        ]
        index = build_id_index(dupes)
        assert index[1]["name"] == "Later"


# ---------------------------------------------------------------------------
# lookup_linear / lookup_dict
# ---------------------------------------------------------------------------

class TestLookup:
    def test_linear_found(self):
        result = lookup_linear(RECORDS, 3)
        assert result is not None
        assert result["name"] == "Alice Demir"
        assert result["score"] == 70

    def test_linear_not_found_returns_none(self):
        assert lookup_linear(RECORDS, 999) is None

    def test_dict_found(self):
        index = build_id_index(RECORDS)
        result = lookup_dict(index, 2)
        assert result is not None
        assert result["name"] == "Bob Kaya"

    def test_dict_not_found_returns_none(self):
        index = build_id_index(RECORDS)
        assert lookup_dict(index, 999) is None

    def test_linear_and_dict_agree(self):
        index = build_id_index(RECORDS)
        for record in RECORDS:
            rid = record["record_id"]
            assert lookup_linear(RECORDS, rid) == lookup_dict(index, rid)


# ---------------------------------------------------------------------------
# frequency_count
# ---------------------------------------------------------------------------

class TestFrequencyCount:
    def test_counts_are_correct(self):
        freqs = frequency_count(RECORDS, "category")
        assert freqs["books"] == 2
        assert freqs["electronics"] == 2
        assert freqs["home"] == 1

    def test_all_values_covered(self):
        freqs = frequency_count(RECORDS, "category")
        assert sum(freqs.values()) == len(RECORDS)

    def test_numeric_field_raises(self):
        with pytest.raises(ValueError, match="categorical"):
            frequency_count(RECORDS, "score")

    def test_unknown_field_raises(self):
        with pytest.raises(ValueError, match="Unknown field"):
            frequency_count(RECORDS, "nonexistent")


# ---------------------------------------------------------------------------
# find_duplicates_name_year
# ---------------------------------------------------------------------------

class TestFindDuplicates:
    def test_detects_known_duplicate(self):
        dupes = find_duplicates_name_year(RECORDS)
        assert ("Alice Demir", 2020) in dupes

    def test_duplicate_group_has_both_records(self):
        dupes = find_duplicates_name_year(RECORDS)
        group = dupes[("Alice Demir", 2020)]
        assert len(group) == 2
        assert {r["record_id"] for r in group} == {1, 3}

    def test_singles_not_included(self):
        dupes = find_duplicates_name_year(RECORDS)
        for group in dupes.values():
            assert len(group) >= 2

    def test_no_duplicates_returns_empty(self):
        unique = RECORDS[:1]
        assert find_duplicates_name_year(unique) == {}


# ---------------------------------------------------------------------------
# top_k_sort / top_k_heap
# ---------------------------------------------------------------------------

class TestTopK:
    def test_sort_k0_returns_empty(self):
        assert top_k_sort(RECORDS, 0) == []

    def test_heap_k0_returns_empty(self):
        assert top_k_heap(RECORDS, 0) == []

    def test_sort_k_negative_returns_empty(self):
        assert top_k_sort(RECORDS, -5) == []

    def test_sort_k1_is_highest_score(self):
        result = top_k_sort(RECORDS, 1)
        assert result[0]["score"] == 90

    def test_sort_tie_broken_by_lower_id(self):
        # Records 2 and 5 both score 90; record 2 (lower ID) must be first
        result = top_k_sort(RECORDS, 2)
        assert result[0]["record_id"] == 2
        assert result[1]["record_id"] == 5

    def test_heap_k1_is_highest_score(self):
        result = top_k_heap(RECORDS, 1)
        assert result[0]["score"] == 90

    def test_heap_tie_broken_by_lower_id(self):
        result = top_k_heap(RECORDS, 2)
        assert result[0]["record_id"] == 2
        assert result[1]["record_id"] == 5

    def test_k_exceeds_length_returns_all(self):
        assert len(top_k_sort(RECORDS, 100)) == len(RECORDS)
        assert len(top_k_heap(RECORDS, 100)) == len(RECORDS)

    def test_sort_and_heap_produce_same_ordering(self):
        for k in range(1, len(RECORDS) + 2):
            sort_ids = [r["record_id"] for r in top_k_sort(RECORDS, k)]
            heap_ids = [r["record_id"] for r in top_k_heap(RECORDS, k)]
            assert sort_ids == heap_ids, f"Mismatch at k={k}"

    def test_result_is_sorted_by_score_descending(self):
        result = top_k_sort(RECORDS, len(RECORDS))
        scores = [r["score"] for r in result]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# range_query_linear / range_query_binary
# ---------------------------------------------------------------------------

class TestRangeQuery:
    def test_linear_correct_results(self):
        result = range_query_linear(RECORDS, "score", 80, 90)
        ids = {r["record_id"] for r in result}
        assert ids == {1, 2, 4, 5}  # scores: 80, 90, 85, 90

    def test_linear_boundaries_are_inclusive(self):
        result = range_query_linear(RECORDS, "score", 80, 80)
        assert len(result) == 1
        assert result[0]["record_id"] == 1

    def test_linear_empty_range(self):
        assert range_query_linear(RECORDS, "score", 95, 100) == []

    def test_linear_low_gt_high_raises(self):
        with pytest.raises(ValueError, match="must be <="):
            range_query_linear(RECORDS, "score", 90, 80)

    def test_linear_non_numeric_field_raises(self):
        with pytest.raises(ValueError, match="numeric field"):
            range_query_linear(RECORDS, "name", 1, 5)

    def test_binary_matches_linear_for_all_ranges(self):
        sv, sr = build_sorted_numeric_index(RECORDS, "score")
        for lo, hi in [(40, 100), (80, 90), (85, 85), (50, 60), (95, 100)]:
            linear = {r["record_id"] for r in range_query_linear(RECORDS, "score", lo, hi)}
            binary = {r["record_id"] for r in range_query_binary(sv, sr, lo, hi)}
            assert linear == binary, f"Mismatch at range ({lo}, {hi})"

    def test_binary_low_gt_high_raises(self):
        sv, sr = build_sorted_numeric_index(RECORDS, "score")
        with pytest.raises(ValueError, match="must be <="):
            range_query_binary(sv, sr, 90, 80)

    def test_binary_empty_range(self):
        sv, sr = build_sorted_numeric_index(RECORDS, "score")
        assert range_query_binary(sv, sr, 95, 100) == []


# ---------------------------------------------------------------------------
# build_sorted_numeric_index
# ---------------------------------------------------------------------------

class TestBuildSortedIndex:
    def test_values_are_sorted(self):
        values, _ = build_sorted_numeric_index(RECORDS, "score")
        assert values == sorted(values)

    def test_records_aligned_with_values(self):
        values, records = build_sorted_numeric_index(RECORDS, "score")
        for v, r in zip(values, records):
            assert v == r["score"]

    def test_all_records_present(self):
        _, records = build_sorted_numeric_index(RECORDS, "score")
        assert {r["record_id"] for r in records} == {r["record_id"] for r in RECORDS}

    def test_non_numeric_field_raises(self):
        with pytest.raises(ValueError, match="numeric field"):
            build_sorted_numeric_index(RECORDS, "category")
