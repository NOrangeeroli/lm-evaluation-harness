#!/usr/bin/env python3
"""Test script for TruthQuest regex pattern."""

import re

# Mirror the logic used in _parse_truthquest_prediction:
# Find all "knight" and "knave", then look backwards for A-Z letters

def parse_truthquest_prediction(pred_str: str) -> dict:
    """Same logic as _parse_truthquest_prediction in utils.py"""
    s = (pred_str or "").strip()
    if not s:
        return {}
    result = {}
    
    # Find all occurrences of "knight" and "knave" (case-insensitive)
    s_lower = s.lower()
    
    # Collect all role word positions with their types
    role_positions = []
    for match in re.finditer(r'\bknight\b', s_lower):
        role_positions.append((match.start(), True))  # True = knight
    for match in re.finditer(r'\bknave\b', s_lower):
        role_positions.append((match.start(), False))  # False = knave
    
    # Sort by position
    role_positions.sort(key=lambda x: x[0])
    
    # For each role word, find letters in the segment before it
    prev_pos = 0
    for pos, is_knight in role_positions:
        # Look for A-Z letters between prev_pos and pos
        segment = s[prev_pos:pos]
        letters = re.findall(r'[A-Z]', segment)
        for letter in letters:
            result[letter] = is_knight
        prev_pos = pos
    
    return result

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
    ("A is a knight, B, C, and D are knaves.", {'A': True, 'B': False, 'C': False, 'D': False}),
]

print("Testing TruthQuest prediction parser")
print("=" * 80)

for i, (test_str, expected) in enumerate(test_cases, 1):
    print(f"\nTest {i}: {test_str}")
    result = parse_truthquest_prediction(test_str)
    if result:
        print(f"  Matched: {result}")
        print(f"  Expected: {expected}")
        print(f"  ✓ Match!" if result == expected else f"  ✗ Mismatch!")
    else:
        print("  No matches found")
        print(f"  Expected: {expected}")
        print("  ✗ No match!")
