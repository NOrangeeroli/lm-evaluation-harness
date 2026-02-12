#!/usr/bin/env python3
"""Check the number of choices for each MC task in ADeLe dataset."""

import re
import collections
from pathlib import Path

try:
    import datasets
except ImportError:
    print("Please install datasets: pip install datasets")
    exit(1)


def count_choices_in_prompt(prompt: str) -> int:
    """Count the number of choice letters (A, B, C, etc.) in a prompt."""
    # Look for patterns like "A)", "A.", "A:", "(A)", "[A]", etc.
    # Also look for "Option A", "Choice A", etc.
    patterns = [
        r'\b([A-J])[\.\):]',  # A), A., A:
        r'\(([A-J])\)',  # (A)
        r'\[([A-J])\]',  # [A]
        r'Option\s+([A-J])\b',  # Option A
        r'Choice\s+([A-J])\b',  # Choice A
    ]
    
    found_letters = set()
    for pattern in patterns:
        matches = re.findall(pattern, prompt, re.IGNORECASE)
        found_letters.update([m.upper() for m in matches])
    
    if not found_letters:
        return 0
    
    # Return the maximum letter index (A=1, B=2, etc.)
    max_letter = max(found_letters)
    return ord(max_letter) - ord('A') + 1


def analyze_mc_tasks():
    """Analyze MC tasks and count their choices."""
    print("Loading ADeLe dataset from HuggingFace...")
    try:
        # Try loading with streaming first
        dataset = datasets.load_dataset(
            "CFI-Kinds-of-Intelligence/ADeLe_battery_v1dot0", 
            split="train",
            streaming=True
        )
        use_streaming = True
    except Exception as e:
        print(f"Streaming failed: {e}, trying regular load...")
        dataset = datasets.load_dataset(
            "CFI-Kinds-of-Intelligence/ADeLe_battery_v1dot0", 
            split="train"
        )
        use_streaming = False
    
    # AGIEval MC tasks
    mc_tasks = [
        "LogiQA-en",
        "AQuA-RAT",
        "LSAT-AR",
        "LSAT-LR",
        "LSAT-RC",
        "SAT-En",
        "SAT-Math",
    ]
    
    task_choice_counts = collections.defaultdict(list)
    task_examples_seen = collections.defaultdict(int)
    
    print("Scanning dataset...")
    max_samples_per_task = 20
    
    if use_streaming:
        # Sample up to 20 examples per task
        for example in dataset:
            task_name = example.get("task", "")
            if task_name in mc_tasks and task_examples_seen[task_name] < max_samples_per_task:
                prompt = example.get("prompt", "")
                choice_count = count_choices_in_prompt(prompt)
                task_choice_counts[task_name].append(choice_count)
                task_examples_seen[task_name] += 1
                
                # Stop if we've seen all tasks
                if all(task_examples_seen[t] >= max_samples_per_task for t in mc_tasks):
                    break
    else:
        # Filter and sample
        for task_name in mc_tasks:
            task_examples = [ex for ex in dataset if ex.get("task") == task_name]
            if task_examples:
                for example in task_examples[:max_samples_per_task]:
                    prompt = example.get("prompt", "")
                    choice_count = count_choices_in_prompt(prompt)
                    task_choice_counts[task_name].append(choice_count)
    
    print("\n" + "="*60)
    print("Summary of choice counts (from sampled examples):")
    print("="*60)
    
    for task_name in mc_tasks:
        counts = task_choice_counts[task_name]
        if counts:
            unique_counts = sorted(set(counts))
            most_common = collections.Counter(counts).most_common(1)[0][0]
            print(f"{task_name:20s}: {most_common} choices (range: {min(counts)}-{max(counts)}, unique: {unique_counts}, samples: {len(counts)})")
        else:
            print(f"{task_name:20s}: No examples found")


if __name__ == "__main__":
    analyze_mc_tasks()
