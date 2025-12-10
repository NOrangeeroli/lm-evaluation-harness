#!/usr/bin/env python3
"""Determine doc_to_choice for all BBEH tasks by analyzing the dataset."""

import datasets
import re
from collections import Counter

dataset = datasets.load_dataset('BBEH/bbeh', split='train')

# Get all unique tasks
tasks = sorted(set([e['task'] for e in dataset]))

task_choices = {}

for task_name in tasks:
    examples = [e for e in dataset if e['task'] == task_name][:50]  # Check more examples
    if not examples:
        continue
    
    first_input = examples[0]['input']
    first_target = str(examples[0]['target'])
    all_targets = [str(e['target']) for e in examples]
    
    print(f'\n=== {task_name} ===')
    print(f'First target: {first_target}')
    
    # Pattern 1: Answer 'X' if ... 'Y' if ... 'Z' if ...
    answer_match = re.search(r"Answer\s+['\"]([^'\"]+)['\"]\s+if.*?['\"]([^'\"]+)['\"]\s+if.*?['\"]([^'\"]+)['\"]", first_input, re.IGNORECASE | re.DOTALL)
    if answer_match:
        choices = [answer_match.group(1), answer_match.group(2), answer_match.group(3)]
        print(f'  Found answer pattern: {choices}')
        task_choices[task_name] = choices
        continue
    
    # Pattern 2: Reply X or Y (with optional Ambiguous)
    reply_match = re.search(r"Reply\s+([^\s,]+)\s+or\s+([^\s,]+)", first_input, re.IGNORECASE)
    if reply_match:
        choices = [reply_match.group(1), reply_match.group(2)]
        if 'Ambiguous' in first_input or 'ambiguous' in first_input:
            choices.append('Ambiguous')
        print(f'  Found reply pattern: {choices}')
        task_choices[task_name] = choices
        continue
    
    # Pattern 3: Letter choices (A), (B), (C), etc.
    if first_target.startswith('(') and first_target.endswith(')') and len(first_target) == 3:
        # Extract all letter options from input
        letters = sorted(set(re.findall(r'\(([A-Z])\)', first_input)))
        if letters and 'A' in letters:
            max_letter = max([ord(l) for l in letters])
            choices = [chr(i) for i in range(ord('A'), max_letter + 1)]
            print(f'  Found letter choices: {choices}')
            task_choices[task_name] = choices
            continue
    
    # Pattern 4: Single letter (like hyperbaton) - check for Options A-J or A-K
    if len(first_target) == 1 and first_target.isalpha():
        # Check for explicit option range
        if 'Options A-J' in first_input:
            choices = [chr(i) for i in range(ord('A'), ord('J') + 1)]
            if '(K)' in first_input or 'K)' in first_input or 'option K' in first_input.lower():
                choices.append('K')
            print(f'  Found single letter with options: {choices}')
            task_choices[task_name] = choices
            continue
        elif 'Options A-K' in first_input:
            choices = [chr(i) for i in range(ord('A'), ord('K') + 1)]
            print(f'  Found single letter with options: {choices}')
            task_choices[task_name] = choices
            continue
    
    # Pattern 5: Number + "No" (like dyck languages, word sorting)
    if (first_target.isdigit() or first_target == 'No') and 'Thought' in first_input:
        if 'Write "No"' in first_input or 'Write \\"No\\"' in first_input:
            # Get all unique targets
            unique_targets = sorted(set(all_targets))
            # Separate numbers and "No"
            numbers = sorted([int(t) for t in unique_targets if t.isdigit()])
            choices = ['No'] + [str(n) for n in numbers]
            print(f'  Found number + No choices: {choices}')
            task_choices[task_name] = choices
            continue
    
    # Pattern 6: Check if it's a generate_until task (comma-separated, complex formats)
    if ',' in first_target or len(first_target) > 20:
        print(f'  Likely generate_until (comma-separated or long): {first_target[:50]}...')
        continue
    
    print(f'  No clear pattern - might be generate_until')

print('\n\n=== FINAL doc_to_choice ===')
for task, choices in sorted(task_choices.items()):
    choices_str = ', '.join([f'"{c}"' for c in choices])
    print(f'{task}: [{choices_str}]')

