#!/usr/bin/env python3
"""Test script for TruthQuest regex pattern."""

import re

# Mirror the logic used in _parse_truthquest_prediction: operate on lower-cased text
# and use a pattern over [a-z], then map back to upper-case.
# Work on a lower-cased copy so we can use simple [a-z]
pattern = r"([a-z])\s*(?:is|:|=)\s*.*?(knight|knave)"

test_cases = [
    ("A is a knight, B is a knave, and C is a knave.", {'A': True, 'B': False, 'C': False}),
    ("A is a knight", {'A': True}),
    ("B is a knave", {'B': False}),
    ("A is knight", {'A': True}),
    ("B is knave", {'B': False}),
    ("A is the knight", {'A': True}),
    ("B is the knave", {'B': False}),
    ("A is definitely a knight", {'A': True}),
    ("A is a knight, B is a knave, C is a knave, and D is a knight.", {'A': True, 'B': False, 'C': False, 'D': True}),
    ("A is a KNIGHT", {'A': True}),  # case insensitive
    ("B is a KNAVE", {'B': False}),   # case insensitive
    ("A: knight ;;; B:knave", {'A': True, 'B': False}),
]

print("Testing pattern:", pattern)
print("=" * 80)

for i, (test_str, expected) in enumerate(test_cases, 1):
    print(f"\nTest {i}: {test_str}")
    s_lower = test_str.lower()
    matches = list(re.finditer(pattern, s_lower))
    if matches:
        result = {}
        for match in matches:
            letter = match.group(1).upper()
            role = match.group(2).lower()
            result[letter] = role == "knight"
        print(f"  Matched: {result}")
        print(f"  Expected: {expected}")
        print(f"  ✓ Match!" if result == expected else f"  ✗ Mismatch!")
    else:
        print("  No matches found")
        print(f"  Expected: {expected}")
        print("  ✗ No match!")
