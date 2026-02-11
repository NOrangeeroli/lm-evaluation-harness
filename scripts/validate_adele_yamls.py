#!/usr/bin/env python3
"""
Validate that all ADeLe task YAMLs are correctly generated and match the dataset.
"""

import argparse
import yaml
from pathlib import Path

# Add parent directory to path to import from lm_eval
import sys

adele_tasks_dir = Path(__file__).resolve().parent.parent / "lm_eval" / "tasks" / "adele"
sys.path.insert(0, str(adele_tasks_dir.parent.parent.parent))

try:
    from lm_eval.tasks.adele.metadata import get_benchmark_metadata, sanitize_name, sanitize_task_name
except ImportError as e:
    print(f"Warning: Could not import metadata module: {e}")
    print("This script requires the datasets library to be installed.")
    sys.exit(1)


def validate_yaml_file(yaml_path: Path, expected_task_name: str, expected_answer_format: str) -> tuple[bool, list[str]]:
    """Validate a single YAML file."""
    errors = []
    
    if not yaml_path.exists():
        return False, [f"YAML file not found: {yaml_path}"]
    
    try:
        with yaml_path.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        return False, [f"Error parsing YAML: {e}"]
    
    # Check required fields
    required_fields = ["include", "task", "description", "process_docs"]
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")
    
    # Check process_docs format
    if "process_docs" in config:
        process_docs = config["process_docs"]
        if not isinstance(process_docs, str) or not process_docs.startswith("!function utils.process_docs_"):
            errors.append(f"Invalid process_docs format: {process_docs}")
    
    # Check include points to correct template
    if "include" in config:
        include = config["include"]
        if expected_answer_format == "MC":
            if include != "_adele_template_mc.yaml":
                errors.append(f"MC task should include _adele_template_mc.yaml, got {include}")
        elif expected_answer_format == "Open-ended":
            if include != "_adele_template_generate.yaml":
                errors.append(f"Open-ended task should include _adele_template_generate.yaml, got {include}")
    
    return len(errors) == 0, errors


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate ADeLe task YAML files."
    )
    parser.add_argument(
        "--tasks-dir",
        type=Path,
        default=adele_tasks_dir,
        help=f"Directory containing ADeLe task YAMLs (default: {adele_tasks_dir})",
    )
    args = parser.parse_args()
    
    print("Loading metadata from HuggingFace dataset...")
    try:
        benchmark_metadata = get_benchmark_metadata()
    except Exception as e:
        print(f"Error loading metadata: {e}")
        return
    
    if not benchmark_metadata:
        print("No benchmarks found.")
        return
    
    print(f"Validating YAMLs for {len(benchmark_metadata)} benchmarks...\n")
    
    all_valid = True
    total_tasks = 0
    validated_tasks = 0
    
    for benchmark_name, tasks in sorted(benchmark_metadata.items()):
        benchmark_id = sanitize_name(benchmark_name)
        benchmark_dir = args.tasks_dir / benchmark_id
        
        if not benchmark_dir.exists():
            print(f"❌ Benchmark directory not found: {benchmark_dir}")
            all_valid = False
            continue
        
        print(f"Checking {benchmark_name} ({len(tasks)} tasks)...")
        
        for task_name, answer_format in sorted(tasks.items()):
            total_tasks += 1
            task_id = sanitize_task_name(task_name)
            yaml_path = benchmark_dir / f"{task_id}.yaml"
            
            is_valid, errors = validate_yaml_file(yaml_path, task_name, answer_format)
            
            if is_valid:
                validated_tasks += 1
                print(f"  ✓ {task_name}")
            else:
                all_valid = False
                print(f"  ✗ {task_name}:")
                for error in errors:
                    print(f"    - {error}")
    
    print(f"\n{'='*60}")
    print(f"Summary: {validated_tasks}/{total_tasks} tasks validated")
    
    if all_valid:
        print("✓ All YAMLs are valid!")
        return 0
    else:
        print("✗ Some YAMLs have errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())

