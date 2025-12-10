#!/usr/bin/env python3
"""
Update YAML config files based on fewshot examples from generate_fewshot_report.py
"""
import re
import yaml
import os
import ast
from pathlib import Path

# Task name mapping from report to YAML filename
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

def get_fewshot_from_generate_script():
    """Get fewshot examples from generate_fewshot_report.py"""
    script_path = Path(__file__).parent / "generate_fewshot_report.py"
    with open(script_path, 'r') as f:
        content = f.read()
    
    task_fewshots = {}
    
    # Find all if/elif task_name blocks
    pattern = r'(?:if|elif) task_name == "([^"]+)":\s*fewshot_examples = \[(.*?)(?=\n\s+(?:elif|if task_name)|\n\s+else:|\n\s+def|\Z)'
    matches = re.finditer(pattern, content, re.DOTALL)
    
    for match in matches:
        task_name = match.group(1)
        examples_text = match.group(2)
        
        # Parse the examples - handle multiline strings with proper quote matching
        examples = []
        
        # Use a more robust approach: find all {"input": ... "target": ...} patterns
        # This pattern handles escaped quotes and newlines properly
        example_pattern = r'\{\s*"input":\s*"((?:[^"\\]|\\.|\\n)*?)",\s*"target":\s*"((?:[^"\\]|\\.|\\n)*?)"\s*\}'
        
        ex_matches = re.finditer(example_pattern, examples_text, re.DOTALL)
        for ex_match in ex_matches:
            input_text = ex_match.group(1)
            target_text = ex_match.group(2)
            
            # Unescape the strings
            input_text = input_text.replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'")
            target_text = target_text.replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'")
            
            examples.append({"input": input_text, "target": target_text})
        
        if examples:
            task_fewshots[task_name] = examples
    
    return task_fewshots

def determine_output_type(task_name, fewshot_examples):
    """Determine if task is multiple_choice or generate_until"""
    if not fewshot_examples:
        return "multiple_choice", "_fewshot_template_yaml"
    
    first_target = fewshot_examples[0].get("target", "")
    
    # Multiple choice indicators:
    # - Target starts with "(" and ends with ")" like "(A)", "(B)", etc.
    # - Target is a single letter like "A", "B", "C"
    if (first_target.startswith("(") and first_target.endswith(")")) or \
       (len(first_target) == 1 and first_target.isalpha()):
        return "multiple_choice", "_fewshot_template_yaml"
    
    # Generate until indicators:
    # - Target contains commas (like "yes, no, yes" or "A, A, A")
    # - Target is a number
    # - Target is "No" or "unknown"
    # - Target is a list format
    if "," in first_target or first_target.isdigit() or \
       first_target in ["No", "unknown", "proved", "disproved"] or \
       first_target.startswith("[") or " " in first_target:
        return "generate_until", "_fewshot_template_generate.yaml"
    
    # Default to multiple_choice
    return "multiple_choice", "_fewshot_template_yaml"

def update_yaml_file(task_name, fewshot_examples, yaml_dir):
    """Update or create a YAML file for a task"""
    yaml_filename = TASK_NAME_MAPPING[task_name] + ".yaml"
    yaml_path = yaml_dir / yaml_filename
    
    # Determine output_type and template
    output_type, template = determine_output_type(task_name, fewshot_examples)
    
    # Read existing YAML if it exists (handle errors gracefully)
    existing_config = {}
    if yaml_path.exists():
        try:
            with open(yaml_path, 'r') as f:
                existing_config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Could not parse {yaml_filename}, creating new one: {e}")
    
    # Build the new config
    config = {
        "fewshot_config": {
            "sampler": "first_n",
            "samples": fewshot_examples
        },
        "include": template,
        "task": f"leaderboard_bbeh_{TASK_NAME_MAPPING[task_name]}"
    }
    
    # Add process_docs if it exists or create default
    if "process_docs" in existing_config:
        config["process_docs"] = existing_config["process_docs"]
    else:
        config["process_docs"] = f"!function 'utils.process_docs_{TASK_NAME_MAPPING[task_name]}'"
    
    # Add task-specific fields (preserve from existing config)
    if "doc_to_choice" in existing_config:
        config["doc_to_choice"] = existing_config["doc_to_choice"]
    if "description" in existing_config:
        config["description"] = existing_config["description"]
    
    # Add doc_to_choice for boolean_expressions if missing
    if task_name == "boolean expressions" and "doc_to_choice" not in config:
        config["doc_to_choice"] = ["False", "True"]
    
    # Write the YAML file
    with open(yaml_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True, width=1000)
    
    print(f"Updated {yaml_filename}")

def main():
    yaml_dir = Path(__file__).parent
    
    # Get fewshot examples from the generate script
    task_fewshots = get_fewshot_from_generate_script()
    
    # Get list of tasks from report
    report_path = yaml_dir / "BBEH_FEWSHOT_PROMPTS_REPORT.md"
    with open(report_path, 'r') as f:
        content = f.read()
    
    tasks_in_report = re.findall(r'^\d+\. \*\*(.+?)\*\*', content, re.MULTILINE)
    
    print(f"Found {len(tasks_in_report)} tasks in report")
    print(f"Found {len(task_fewshots)} tasks with fewshot examples")
    
    # Update/create YAML files for tasks in report
    for task_name in tasks_in_report:
        if task_name in task_fewshots:
            update_yaml_file(task_name, task_fewshots[task_name], yaml_dir)
        else:
            print(f"Warning: No fewshot examples found for {task_name}")
    
    # Rename files that don't match
    rename_map = {
        "causal_judgement.yaml": "causal_understanding.yaml",
        "sports_understanding.yaml": "sportqa.yaml",
        "temporal_sequences.yaml": "temporal_sequence.yaml",
    }
    
    for old_name, new_name in rename_map.items():
        old_path = yaml_dir / old_name
        new_path = yaml_dir / new_name
        if old_path.exists() and not new_path.exists():
            print(f"Renaming {old_name} to {new_name}")
            old_path.rename(new_path)
    
    # Delete YAML files for tasks not in report
    existing_yamls = list(yaml_dir.glob("*.yaml"))
    for yaml_file in existing_yamls:
        if yaml_file.name.startswith("_") or yaml_file.name == "_leaderboard_bbeh.yaml":
            continue
        
        # Extract task name from filename
        task_base = yaml_file.stem
        # Find corresponding task name in mapping
        task_name_in_report = None
        for report_task, yaml_task in TASK_NAME_MAPPING.items():
            if yaml_task == task_base:
                task_name_in_report = report_task
                break
        
        if task_name_in_report not in tasks_in_report:
            print(f"Deleting stale YAML: {yaml_file.name}")
            yaml_file.unlink()

if __name__ == "__main__":
    main()
