#!/usr/bin/env python3
"""Check the number of choices for each MC task in ADeLe dataset - simple version."""

import re
import collections

try:
    import datasets
except ImportError:
    print("Please install datasets: pip install datasets")
    exit(1)


def count_choices_in_prompt(prompt: str) -> int:
    """Count the number of choice letters (A, B, C, etc.) in a prompt."""
    # Look for patterns like "A)", "A.", "A:", "(A)", "[A]", etc.
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
    print("Loading ADeLe dataset from HuggingFace (streaming mode)...")
    
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
    max_samples = 10  # Just check 10 examples per task
    
    try:
        dataset = datasets.load_dataset(
            "CFI-Kinds-of-Intelligence/ADeLe_battery_v1dot0", 
            split="train",
            streaming=True
        )
        
        print("Scanning dataset for MC tasks...")
        for example in dataset:
            task_name = example.get("task", "")
            if task_name in mc_tasks and task_examples_seen[task_name] < max_samples:
                prompt = example.get("prompt", "")
                if prompt:
                    choice_count = count_choices_in_prompt(prompt)
                    task_choice_counts[task_name].append(choice_count)
                    task_examples_seen[task_name] += 1
                    
                    if task_examples_seen[task_name] == 1:
                        # Show first example snippet
                        snippet = prompt[:150].replace('\n', ' ')
                        print(f"  {task_name}: first example snippet: {snippet}...")
                
                # Stop if we've seen all tasks
                if all(task_examples_seen[t] >= max_samples for t in mc_tasks):
                    break
    except Exception as e:
        print(f"Error: {e}")
        return
    
    print("\n" + "="*70)
    print("Summary of choice counts:")
    print("="*70)
    
    for task_name in mc_tasks:
        counts = task_choice_counts[task_name]
        if counts:
            unique_counts = sorted(set(counts))
            most_common = collections.Counter(counts).most_common(1)[0][0]
            print(f"{task_name:20s}: {most_common} choices (samples: {len(counts)}, range: {min(counts)}-{max(counts)})")
        else:
            print(f"{task_name:20s}: No examples found")


if __name__ == "__main__":
    analyze_mc_tasks()
