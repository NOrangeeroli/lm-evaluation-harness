#!/usr/bin/env python3
"""Update all YAML files with correct doc_to_choice."""

import yaml
from pathlib import Path
import datasets
import re

# Task name mapping
TASK_NAME_MAPPING = {
    "boardgame qa": "boardgame_qa",
    "boolean expressions": "boolean_expressions",
    "buggy tables": "buggy_tables",
    "causal understanding": "causal_understanding",
    "disambiguation qa": "disambiguation_qa",
    "dyck languages": "dyck_languages",
    "geometric shapes": "geometric_shapes",
    "hyperbaton": "hyperbaton",
    "linguini": "linguini",
    "movie recommendation": "movie_recommendation",
    "multistep arithmetic": "multistep_arithmetic",
    "nycc": "nycc",
    "object counting": "object_counting",
    "object properties": "object_properties",
    "sarc triples": "sarc_triples",
    "shuffled objects": "shuffled_objects",
    "spatial reasoning": "spatial_reasoning",
    "sportqa": "sportqa",
    "temporal sequence": "temporal_sequence",
    "time arithmetic": "time_arithmetic",
    "web of lies": "web_of_lies",
    "word sorting": "word_sorting",
    "zebra puzzles": "zebra_puzzles",
}

def determine_doc_to_choice():
    """Determine doc_to_choice for each task."""
    dataset = datasets.load_dataset('BBEH/bbeh', split='train')
    task_choices = {}
    
    for task_name in TASK_NAME_MAPPING.keys():
        examples = [e for e in dataset if e['task'] == task_name][:100]
        if not examples:
            continue
        
        first_input = examples[0]['input']
        first_target = str(examples[0]['target'])
        all_targets = [str(e['target']) for e in examples]
        
        # Pattern 1: Answer 'X' if ... 'Y' if ... 'Z' if ...
        answer_match = re.search(r"Answer\s+['\"]([^'\"]+)['\"]\s+if.*?['\"]([^'\"]+)['\"]\s+if.*?['\"]([^'\"]+)['\"]", first_input, re.IGNORECASE | re.DOTALL)
        if answer_match:
            task_choices[task_name] = [answer_match.group(1), answer_match.group(2), answer_match.group(3)]
            continue
        
        # Pattern 2: Reply X or Y (with optional Ambiguous)
        reply_match = re.search(r"Reply\s+([^\s,]+)\s+or\s+([^\s,]+)", first_input, re.IGNORECASE)
        if reply_match:
            choices = [reply_match.group(1), reply_match.group(2)]
            if 'Ambiguous' in first_input or 'ambiguous' in first_input:
                choices.append('Ambiguous')
            task_choices[task_name] = choices
            continue
        
        # Pattern 3: Letter choices (A), (B), (C), etc.
        if first_target.startswith('(') and first_target.endswith(')') and len(first_target) == 3:
            letters = sorted(set(re.findall(r'\(([A-Z])\)', first_input)))
            if letters and 'A' in letters:
                max_letter = max([ord(l) for l in letters])
                task_choices[task_name] = [chr(i) for i in range(ord('A'), max_letter + 1)]
                continue
        
        # Pattern 4: Single letter (like hyperbaton)
        if len(first_target) == 1 and first_target.isalpha():
            if 'Options A-J' in first_input:
                choices = [chr(i) for i in range(ord('A'), ord('J') + 1)]
                if '(K)' in first_input or 'K)' in first_input or 'option K' in first_input.lower():
                    choices.append('K')
                task_choices[task_name] = choices
                continue
            elif 'Options A-K' in first_input:
                task_choices[task_name] = [chr(i) for i in range(ord('A'), ord('K') + 1)]
                continue
        
        # Pattern 5: Number + "No" (like dyck languages, word sorting)
        if (first_target.isdigit() or first_target == 'No') and 'Thought' in first_input:
            if 'Write "No"' in first_input or 'Write \\"No\\"' in first_input:
                # Get all unique step numbers from dataset
                unique_targets = sorted(set(all_targets))
                numbers = sorted([int(t) for t in unique_targets if t.isdigit()])
                choices = ['No'] + [str(n) for n in numbers]
                task_choices[task_name] = choices
                continue
    
    return task_choices

def update_yaml_files():
    """Update all YAML files with doc_to_choice."""
    yaml_dir = Path(__file__).parent
    task_choices = determine_doc_to_choice()
    
    print("Updating YAML files with doc_to_choice:\n")
    
    for task_name, choices in sorted(task_choices.items()):
        yaml_filename = TASK_NAME_MAPPING[task_name] + ".yaml"
        yaml_path = yaml_dir / yaml_filename
        
        if not yaml_path.exists():
            print(f"Warning: {yaml_filename} not found")
            continue
        
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Update doc_to_choice
        config['doc_to_choice'] = choices
        
        # Write back
        with open(yaml_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True, width=1000)
        
        choices_str = ', '.join([f'"{c}"' for c in choices])
        print(f"✓ {yaml_filename}: [{choices_str}]")
    
    print(f"\nUpdated {len(task_choices)} YAML files with doc_to_choice")

if __name__ == "__main__":
    update_yaml_files()

