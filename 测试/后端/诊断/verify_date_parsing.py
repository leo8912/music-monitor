import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from app.services.library import LibraryService

def test_date_parsing():
    lib = LibraryService()
    
    test_cases = [
        ("2026-01-07", "Standard date"),
        ("1736179200000", "Milliseconds timestamp (2025-01-06)"),
        ("1736179200", "Seconds timestamp"),
        ("2026", "Year only"),
        ("-28800000", "Invalid negative"),
        ("0", "Zero"),
        ("1970-01-01", "Epoch date"),
        ("", "Empty"),
        (None, "None")
    ]
    
    print("--- 验证 _parse_date 逻辑 ---")
    for d_str, desc in test_cases:
        res = lib._parse_date(d_str)
        print(f"Input: {d_str} ({desc}) -> Result: {res}")

if __name__ == "__main__":
    test_date_parsing()
