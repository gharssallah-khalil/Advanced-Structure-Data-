# Advanced-Structure-Data-
Mini Data Indexer and Query Tool
# ⚡ Mini Data Indexer & Query Tool

![Python Version](https://img.shields.io/badge/Python-3.11.9-blue.svg)
![Course](https://img.shields.io/badge/Course-Advanced%20Data%20Structures-orange.svg)
![Focus](https://img.shields.io/badge/Focus-Algorithm%20Optimization-green.svg)

## 📖 Overview
The **Mini Data Indexer and Query Tool** is a high-performance Python application designed to analyze and optimize data querying techniques. Developed for the *CME7202 - Advanced Data Structures* Master's course, this project demonstrates the dramatic performance gains achieved by replacing baseline linear operations with optimal data structures.

The tool processes a dataset of **100,000 records** and benchmarks the execution time of various common data operations, proving the efficiency of Hash Indexes, Heaps, and Binary Search algorithms over standard linear scans and full sorts.

## 🧠 Data Structures & Algorithms Implemented

* **Hash Indexing (O(1) Lookups):** Replaced linear scanning with Python dictionaries for exact ID lookups.
* **Min/Max Heaps (O(n log k)):** Utilized `heapq.nlargest` to extract Top-K records by score, bypassing the overhead of full dataset sorting.
* **Binary Search (O(log n)):** Implemented `bisect_left` and `bisect_right` on a pre-sorted index to handle numeric range queries instantly.
* **Hash Mapping:** Grouped records using `defaultdict` for duplicate detection (based on name and year) and utilized `collections.Counter` for rapid frequency counting.

## 📊 Performance Benchmarks
The project includes a rigorous empirical timing analysis (`results/timings.csv`) tested on a dataset of 100,000 records. 

| Query Type | Baseline Method | Optimized Method | Speedup | Note |
| :--- | :--- | :--- | :--- | :--- |
| **Exact ID Lookup** | Linear Scan (5.909 ms) | Hash Dictionary (0.0005 ms) | **~10,552x** | Hash indexing dominates repeated lookups. |
| **Top-K Elements** | Full Sort (84.38 ms) | Heapq (36.20 ms) | **~2.33x** | Heap outperforms sorting when *k=10*. |
| **Numeric Range** | Linear Filter (14.24 ms) | Binary Search (0.34 ms) | **~40.98x** | Preprocessing pays off after just ~9 queries. |

## 🚀 Installation & Usage

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/yourusername/mini-data-indexer.git](https://github.com/yourusername/mini-data-indexer.git)
   cd mini-data-indexer
