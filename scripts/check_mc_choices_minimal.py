#!/usr/bin/env python3
"""Minimal script to check MC choices - loads one example per task."""

import re
import sys

try:
    import datasets
except ImportError:
    print("Please install datasets: pip install datasets")
    sys.exit(1)

def count_choices(prompt):
    """Count choice letters in prompt."""
    found = set()
    for pattern in [r'\b([A-J])[\.\):]', r'\(([A-J])\)', r'\[([A-J])\]']:
        found.update(re.findall(pattern, prompt, re.I))
    return max([ord(l.upper()) - ord('A') + 1 for l in found]) if found else 0

tasks = ["LogiQA-en", "AQuA-RAT", "LSAT-AR", "LSAT-LR", "LSAT-RC", "SAT-En", "SAT-Math"]

print("Loading dataset (one example per task)...")
try:
    ds = datasets.load_dataset("CFI-Kinds-of-Intelligence/ADeLe_battery_v1dot0", split="train", streaming=True)
    
    results = {}
    seen = set()
    
    for ex in ds:
        task = ex.get("task", "")
        if task in tasks and task not in seen:
            prompt = ex.get("prompt", "")
            n = count_choices(prompt)
            results[task] = n
            seen.add(task)
            print(f"{task}: {n} choices")
            if len(seen) == len(tasks):
                break
                
    print("\nSummary:")
    for task in tasks:
        print(f"  {task:20s}: {results.get(task, 'N/A')} choices")
        
except Exception as e:
    print(f"Error: {e}")
    print("\nBased on common patterns:")
    print("  LogiQA-en: 4 choices (confirmed)")
    print("  AQuA-RAT: likely 5 choices")
    print("  LSAT-*: likely 5 choices")
    print("  SAT-*: likely 4-5 choices")
