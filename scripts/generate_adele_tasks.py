#!/usr/bin/env python3
"""
Generate per-benchmark task folders and YAML files for ADeLe tasks.
"""

import argparse
import importlib.util
import sys
from pathlib import Path

import yaml

# Import metadata module directly to avoid full lm_eval imports
adele_tasks_dir = Path(__file__).resolve().parent.parent / "lm_eval" / "tasks" / "adele"
spec = importlib.util.spec_from_file_location("metadata", adele_tasks_dir / "metadata.py")
metadata_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metadata_module)
get_benchmark_metadata = metadata_module.get_benchmark_metadata
sanitize_name = metadata_module.sanitize_name
sanitize_task_name = metadata_module.sanitize_task_name

ADELE_UTILS_FILE = Path(__file__).resolve().parent.parent / "lm_eval" / "tasks" / "adele" / "utils.py"

ADELE_TASKS_DIR = Path(__file__).resolve().parent.parent / "lm_eval" / "tasks" / "adele"


def get_template_name(answer_format: str) -> str:
    """Get the template name based on answer format."""
    if answer_format == "MC":
        return "_adele_template_mc.yaml"
    elif answer_format == "Open-ended":
        return "_adele_template_generate.yaml"
    else:
        raise ValueError(f"Unknown answer format: {answer_format}")


def sanitize_function_name(task_name: str) -> str:
    """Convert task name to a valid Python function name."""
    # Replace hyphens and spaces with underscores
    name = task_name.replace("-", "_").replace(" ", "_")
    # Remove any other invalid characters
    import re
    name = re.sub(r"[^\w]", "_", name)
    return name


def update_utils_file(all_task_names: set[str]) -> None:
    """Update utils.py to include process_docs functions for all tasks."""
    if not ADELE_UTILS_FILE.exists():
        print(f"Warning: {ADELE_UTILS_FILE} not found, skipping utils update")
        return
    
    # Read existing utils.py
    with ADELE_UTILS_FILE.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Find where to insert new functions (after the legacy ones)
    # Look for the line with process_docs_TimeQA_implicit
    insert_idx = None
    for i, line in enumerate(lines):
        if "process_docs_TimeQA_implicit = _create_process_docs_function" in line:
            # Find the end of the legacy function definitions
            insert_idx = i + 1
            # Skip blank lines
            while insert_idx < len(lines) and lines[insert_idx].strip() == "":
                insert_idx += 1
            # Skip any existing dynamically generated section
            while insert_idx < len(lines):
                stripped = lines[insert_idx].strip()
                if stripped.startswith("# Dynamically generated"):
                    # Skip until we find a non-comment, non-process_docs line
                    insert_idx += 1
                    while insert_idx < len(lines):
                        stripped = lines[insert_idx].strip()
                        if not stripped or stripped.startswith("#") or stripped.startswith("process_docs_"):
                            insert_idx += 1
                        else:
                            break
                    break
                elif stripped.startswith("process_docs_") and "=" in stripped:
                    insert_idx += 1
                else:
                    break
            break
    
    if insert_idx is None:
        # Try to find after doc_to_target_letter function
        for i, line in enumerate(lines):
            if "def doc_to_target_letter" in line:
                # Find the end of this function
                insert_idx = i + 1
                # Find the closing of the function (next def or end of file)
                while insert_idx < len(lines):
                    if lines[insert_idx].strip().startswith("def "):
                        break
                    insert_idx += 1
                break
    
    if insert_idx is None:
        # Just append at the end
        insert_idx = len(lines)
    
    # Check what functions already exist
    existing_funcs = set()
    for line in lines:
        if line.strip().startswith("process_docs_") and "=" in line:
            # Extract function name
            func_name = line.split("=")[0].strip()
            existing_funcs.add(func_name)
    
    # Generate function definitions for all tasks that don't exist
    new_func_defs = []
    added_count = 0
    for task_name in sorted(all_task_names):
        func_name = sanitize_function_name(task_name)
        full_func_name = f"process_docs_{func_name}"
        if full_func_name not in existing_funcs:
            # Escape quotes in task_name if needed
            task_name_escaped = task_name.replace('"', '\\"')
            new_func_defs.append(
                f'process_docs_{func_name} = _create_process_docs_function("{task_name_escaped}")'
            )
            added_count += 1
    
    if not new_func_defs:
        print("All process_docs functions already exist in utils.py")
        return
    
    # Insert the new functions
    insert_lines = ["\n", "# Dynamically generated process_docs functions for all tasks\n"]
    insert_lines.extend([f"{func_def}\n" for func_def in new_func_defs])
    
    # Insert at the found position
    lines[insert_idx:insert_idx] = insert_lines
    
    # Write back
    with ADELE_UTILS_FILE.open("w", encoding="utf-8") as f:
        f.writelines(lines)
    
    print(f"Updated {ADELE_UTILS_FILE} with {added_count} new process_docs functions")


def generate_task_yaml(
    benchmark_name: str,
    task_name: str,
    answer_format: str,
    output_path: Path,
    adele_tasks_dir: Path,
) -> None:
    """Generate a YAML file for a single task."""
    template_name = get_template_name(answer_format)
    task_id = sanitize_task_name(task_name)
    task_yaml_name = f"adele_{sanitize_name(benchmark_name)}_{task_id}"
    
    # Create description
    description = f"ADeLe {task_name} task from {benchmark_name} benchmark."
    
    # Create function name for process_docs
    func_name = sanitize_function_name(task_name)
    
    # Template path should be relative to the adele tasks directory
    # Since YAMLs are in subdirectories, we need to go up one level
    template_path = f"../{template_name}"
    
    # Create YAML content
    yaml_content = {
        "include": template_path,
        "task": task_yaml_name,
        "description": description,
        "process_docs": f"!function utils.process_docs_{func_name}",
    }
    
    # Write YAML file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        yaml.dump(yaml_content, f, default_flow_style=False, sort_keys=False)
        f.write("\n")


def generate_benchmark_group_yaml(
    benchmark_name: str,
    tasks: dict,
    output_path: Path,
) -> None:
    """Generate a group YAML file that aggregates all tasks in a benchmark."""
    benchmark_id = sanitize_name(benchmark_name)
    group_name = f"adele_{benchmark_id}"
    
    # Generate task IDs
    task_ids = []
    for task_name in sorted(tasks.keys()):
        task_id = sanitize_task_name(task_name)
        task_yaml_name = f"adele_{benchmark_id}_{task_id}"
        task_ids.append(task_yaml_name)
    
    # Create group YAML
    yaml_content = {
        "group": group_name,
        "task": task_ids,
        "aggregate_metric_list": [
            {
                "metric": "exact_match",
                "aggregation": "mean",
                "weight_by_size": True,
            }
        ],
        "metadata": {"version": "1.0"},
    }
    
    # Write group YAML file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        yaml.dump(yaml_content, f, default_flow_style=False, sort_keys=False)
        f.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate per-benchmark task folders and YAML files for ADeLe."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ADELE_TASKS_DIR,
        help=f"Output directory for generated YAMLs (default: {ADELE_TASKS_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be generated without writing files",
    )
    args = parser.parse_args()
    
    # Load metadata from HuggingFace
    print("Loading metadata from HuggingFace dataset...")
    try:
        benchmark_metadata = get_benchmark_metadata()
    except Exception as e:
        print(f"Error loading metadata: {e}")
        return
    
    if not benchmark_metadata:
        print("No benchmarks found.")
        return
    
    print(f"Found {len(benchmark_metadata)} benchmarks")
    
    # Collect all task names for utils.py update
    all_task_names = set()
    for tasks in benchmark_metadata.values():
        all_task_names.update(tasks.keys())
    
    # Update utils.py with all process_docs functions
    if not args.dry_run:
        update_utils_file(all_task_names)
    
    # Generate YAML files for each benchmark
    for benchmark_name, tasks in sorted(benchmark_metadata.items()):
        benchmark_dir = args.output_dir / sanitize_name(benchmark_name)
        
        if args.dry_run:
            print(f"\nWould create: {benchmark_dir}/")
        else:
            benchmark_dir.mkdir(parents=True, exist_ok=True)
            print(f"\nCreating: {benchmark_dir}/")
        
        # Generate task YAMLs
        for task_name, answer_format in sorted(tasks.items()):
            task_id = sanitize_task_name(task_name)
            yaml_path = benchmark_dir / f"{task_id}.yaml"
            
            if args.dry_run:
                print(f"  Would create: {yaml_path.name}")
            else:
                generate_task_yaml(
                    benchmark_name, task_name, answer_format, yaml_path, args.output_dir
                )
                print(f"  Created: {yaml_path.name}")
        
        # Generate group YAML
        group_yaml_path = benchmark_dir / f"_{sanitize_name(benchmark_name)}.yaml"
        if args.dry_run:
            print(f"  Would create group: {group_yaml_path.name}")
        else:
            generate_benchmark_group_yaml(
                benchmark_name, tasks, group_yaml_path
            )
            print(f"  Created group: {group_yaml_path.name}")
    
    print(f"\nDone! Generated YAMLs in {args.output_dir}")


if __name__ == "__main__":
    main()

