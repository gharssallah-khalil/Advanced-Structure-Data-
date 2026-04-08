"""Shared constants for the CME7202 mini indexer project."""

from __future__ import annotations

from typing import TypedDict

FIELDNAMES: list[str] = ["record_id", "name", "category", "region", "year", "score", "value"]
NUMERIC_FIELDS: frozenset[str] = frozenset({"record_id", "year", "score", "value"})

# 32 × 30 = 960 unique name combinations × 8 years = 7,680 possible (name, year) keys.
# This is sufficient headroom for the 100k-record main dataset.
FIRST_NAMES: list[str] = [
    "Elif", "Can", "Ayse", "Mert", "Deniz", "Zeynep", "Ece", "Burak",
    "Melis", "Kerem", "Derya", "Seda", "Emre", "Irem", "Yigit", "Asli",
    "Baris", "Ceren", "Doga", "Emir", "Fatma", "Gokhan", "Hande", "Ilker",
    "Jale", "Kaan", "Lale", "Mustafa", "Nilay", "Onur", "Pinar", "Ramazan",
]

LAST_NAMES: list[str] = [
    "Demir", "Kaya", "Yilmaz", "Aydin", "Tas", "Polat", "Sahin", "Gunes",
    "Celik", "Kurt", "Arslan", "Yaman", "Aksoy", "Tekin", "Bulut", "Cakir",
    "Dogan", "Erdogan", "Findik", "Gurcan", "Hamit", "Ilhan", "Kaplan",
    "Liman", "Mutlu", "Narin", "Ozdemir", "Pektas", "Rana", "Simsek",
]

CATEGORIES: list[str] = ["books", "electronics", "home", "fashion", "sports", "toys", "grocery"]
REGIONS: list[str] = [
    "Marmara", "Aegean", "Mediterranean", "Central Anatolia", "Black Sea", "Southeast",
]


class Record(TypedDict):
    """A single dataset record with statically-typed fields."""

    record_id: int
    name: str
    category: str
    region: str
    year: int
    score: int
    value: int
