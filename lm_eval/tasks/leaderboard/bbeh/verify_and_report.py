#!/usr/bin/env python3
"""Verify BBEH tasks match dataset exactly and generate comprehensive report."""

import datasets
import yaml
import os
from pathlib import Path
from collections import defaultdict

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent

def load_bbeh_dataset():
    """Load the BBEH dataset and extract all unique task names."""
    print("Loading BBEH/bbeh dataset...")
    dataset = datasets.load_dataset("BBEH/bbeh", split="train")
    
    # Get unique task names
    unique_tasks = set()
    tasks_examples = defaultdict(list)
    
    for example in dataset:
        task_name = example.get("task", None)
        if task_name:
            unique_tasks.add(task_name)
            tasks_examples[task_name].append(example)
    
    return sorted(unique_tasks), tasks_examples

def get_configured_tasks():
    """Extract configured tasks from _leaderboard_bbeh.yaml and utils.py."""
    # Read leaderboard config
    leaderboard_file = SCRIPT_DIR / "_leaderboard_bbeh.yaml"
    with open(leaderboard_file, 'r') as f:
        leaderboard_config = yaml.safe_load(f)
    
    configured_task_names = []
    for task in leaderboard_config.get('task', []):
        # Extract task name (e.g., "leaderboard_bbeh_boolean_expressions" -> "boolean_expressions")
        if task.startswith('leaderboard_bbeh_'):
            task_name = task.replace('leaderboard_bbeh_', '')
            configured_task_names.append(task_name)
    
    # Read utils.py to get the mapping from task names to BBEH dataset task names
    utils_file = SCRIPT_DIR / "utils.py"
    with open(utils_file, 'r') as f:
        utils_content = f.read()
    
    # Extract task name mappings from utils.py
    task_mappings = {}
    for line in utils_content.split('\n'):
        if 'process_docs_' in line and '=' in line and 'partial' in line:
            # Extract function name and task name
            # e.g., "process_docs_boolean_expressions = partial(process_docs, task_name="boolean expressions")"
            parts = line.split('=')
            if len(parts) >= 2:
                func_name = parts[0].strip().replace('process_docs_', '')
                # Extract task name from the partial call
                # Handle both "task_name=" and 'task_name=' cases
                right_side = '='.join(parts[1:])
                if 'task_name=' in right_side:
                    # Find the task_name value, handling quotes
                    task_name_start = right_side.find('task_name=') + len('task_name=')
                    # Skip whitespace
                    while task_name_start < len(right_side) and right_side[task_name_start] in ' \t':
                        task_name_start += 1
                    # Check for quote
                    quote_char = None
                    if task_name_start < len(right_side) and right_side[task_name_start] in ['"', "'"]:
                        quote_char = right_side[task_name_start]
                        task_name_start += 1
                    # Find the end
                    if quote_char:
                        task_name_end = right_side.find(quote_char, task_name_start)
                    else:
                        # Find comma or closing paren
                        task_name_end = len(right_side)
                        for char in [',', ')']:
                            idx = right_side.find(char, task_name_start)
                            if idx != -1 and idx < task_name_end:
                                task_name_end = idx
                    task_name_part = right_side[task_name_start:task_name_end].strip()
                    task_mappings[func_name] = task_name_part
    
    return configured_task_names, task_mappings

def get_yaml_fewshot_config(task_name):
    """Read fewshot config from the corresponding YAML file."""
    # Map task name to YAML file name
    yaml_file = SCRIPT_DIR / f"{task_name}.yaml"
    
    if not yaml_file.exists():
        return None, None
    
    # Read file as text first to extract fewshot config section
    with open(yaml_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Try to parse as YAML with custom loader that ignores !function tags
    yaml_content = None
    try:
        # Create a custom loader that ignores unknown tags
        class IgnoreUnknownLoader(yaml.SafeLoader):
            def ignore_unknown(self, node):
                return None
        
        IgnoreUnknownLoader.add_constructor('!function', IgnoreUnknownLoader.ignore_unknown)
        
        with open(yaml_file, 'r', encoding='utf-8') as f:
            yaml_content = yaml.load(f, Loader=IgnoreUnknownLoader)
    except yaml.YAMLError as e:
        # If YAML parsing fails, extract fewshot config from text
        fewshot_config_text = extract_fewshot_config_from_text(content)
        if fewshot_config_text:
            return {'_parse_error': True, '_raw_content': fewshot_config_text}, None
        return None, None
    
    if not yaml_content:
        return None, None
    
    fewshot_config = yaml_content.get('fewshot_config', {})
    output_type = None
    
    # Check if it includes a template
    if 'include' in yaml_content:
        template_file = SCRIPT_DIR / yaml_content['include']
        if template_file.exists():
            try:
                with open(template_file, 'r', encoding='utf-8') as tf:
                    template = yaml.safe_load(tf)
                    if template:
                        output_type = template.get('output_type', 'multiple_choice')
            except yaml.YAMLError:
                pass
    else:
        output_type = yaml_content.get('output_type', 'multiple_choice')
    
    return fewshot_config, output_type

def extract_fewshot_config_from_text(content):
    """Extract fewshot_config section from YAML text when parsing fails."""
    lines = content.split('\n')
    in_fewshot = False
    fewshot_lines = []
    indent_level = 0
    sample_count = 0
    max_samples_to_show = 3
    
    for i, line in enumerate(lines):
        if 'fewshot_config:' in line:
            in_fewshot = True
            fewshot_lines.append(line)
            # Determine indent level
            indent_level = len(line) - len(line.lstrip())
            continue
        
        if in_fewshot:
            # Check if we've moved to a different top-level key
            stripped = line.lstrip()
            if stripped:
                current_indent = len(line) - len(stripped)
                # Check if this is a new top-level key (same or less indentation as fewshot_config)
                if current_indent <= indent_level and ':' in line and not line.strip().startswith('-'):
                    # But allow continuation of samples list
                    if 'samples:' not in line and 'sampler:' not in line:
                        break
            fewshot_lines.append(line)
            
            # Count samples to limit output
            if line.strip().startswith('- input:'):
                sample_count += 1
                if sample_count > max_samples_to_show:
                    # Add ellipsis and stop
                    fewshot_lines.append("  ... (truncated)")
                    break
    
    if fewshot_lines:
        return '\n'.join(fewshot_lines)
    return None

def check_if_fewshot_matches_dataset(fewshot_samples, dataset_examples):
    """Check if fewshot examples appear to be from the dataset."""
    warnings = []
    
    if not fewshot_samples:
        return warnings
    
    # Get first few dataset examples for comparison
    dataset_inputs = [ex['input'] for ex in dataset_examples[:10]]
    
    for i, sample in enumerate(fewshot_samples):
        sample_input = sample.get('input', '')
        # Check if this input appears in the dataset
        for dataset_input in dataset_inputs:
            # Check for exact match or very close match (allowing for truncation)
            if sample_input == dataset_input or (len(sample_input) > 100 and sample_input[:200] in dataset_input):
                warnings.append(f"Fewshot example {i+1} appears to match a dataset example")
                break
    
    return warnings

def generate_report(dataset_tasks, tasks_examples, configured_tasks, task_mappings):
    """Generate the markdown report."""
    
    # Create reverse mapping: BBEH dataset task name -> configured task name
    reverse_mapping = {v: k for k, v in task_mappings.items()}
    
    # Find matches and mismatches
    dataset_task_set = set(dataset_tasks)
    configured_bbeh_names = set(task_mappings.values())
    
    missing_tasks = dataset_task_set - configured_bbeh_names
    extra_tasks = configured_bbeh_names - dataset_task_set
    
    # Note: Some configured tasks may map to the same BBEH task (e.g., tracking_shuffled_objects_*)
    # So we compare unique BBEH task names, not the number of configured tasks
    
    # Generate report
    report_lines = []
    report_lines.append("# BBEH Tasks Verification Report\n")
    report_lines.append("## Summary\n")
    report_lines.append(f"- **Total tasks in BBEH dataset**: {len(dataset_tasks)}")
    report_lines.append(f"- **Total configured task files**: {len(configured_tasks)}")
    report_lines.append(f"- **Unique BBEH tasks mapped**: {len(configured_bbeh_names)}")
    report_lines.append(f"- **Tasks in dataset but not configured**: {len(missing_tasks)}")
    if missing_tasks:
        for task in sorted(missing_tasks):
            report_lines.append(f"  - `{task}`")
    report_lines.append(f"- **Tasks configured but not in dataset**: {len(extra_tasks)}")
    if extra_tasks:
        for task in sorted(extra_tasks):
            report_lines.append(f"  - `{task}`")
    if not missing_tasks and not extra_tasks:
        report_lines.append("")
        report_lines.append("✅ **All tasks match exactly!**")
    report_lines.append("")
    
    # Process each task in the dataset (alphabetically)
    report_lines.append("## Task Details\n")
    
    for task_name in sorted(dataset_tasks):
        report_lines.append(f"### {task_name}\n")
        
        # Get dataset examples
        examples = tasks_examples[task_name]
        report_lines.append("#### First 3 Examples from Dataset:\n")
        
        for i, ex in enumerate(examples[:3], 1):
            input_text = ex['input']
            target_text = ex['target']
            
            # Truncate very long inputs for readability
            if len(input_text) > 500:
                input_text = input_text[:500] + "..."
            
            report_lines.append(f"**Example {i}:**")
            report_lines.append(f"```")
            report_lines.append(f"Input: {input_text}")
            report_lines.append(f"Target: {target_text}")
            report_lines.append(f"```")
            report_lines.append("")
        
        # Get fewshot config
        configured_task_name = reverse_mapping.get(task_name)
        if configured_task_name:
            fewshot_config, output_type = get_yaml_fewshot_config(configured_task_name)
            
            report_lines.append(f"#### Configuration:\n")
            report_lines.append(f"- **Task Type**: {output_type}")
            report_lines.append(f"- **Configured Task Name**: `{configured_task_name}`")
            report_lines.append("")
            
            if fewshot_config:
                report_lines.append("#### Current Fewshot Config:\n")
                
                # Check if there was a parse error
                if fewshot_config.get('_parse_error'):
                    report_lines.append("⚠️ **YAML parsing error - could not fully parse the file**")
                    report_lines.append("")
                    report_lines.append("Raw content preview:")
                    report_lines.append("```")
                    report_lines.append(fewshot_config.get('_raw_content', '')[:500])
                    report_lines.append("```")
                    report_lines.append("")
                else:
                    report_lines.append("```yaml")
                    try:
                        report_lines.append(yaml.dump(fewshot_config, default_flow_style=False, allow_unicode=True))
                    except Exception as e:
                        report_lines.append(f"# Error dumping YAML: {e}")
                        report_lines.append(str(fewshot_config)[:500])
                    report_lines.append("```")
                    report_lines.append("")
                    
                    # Check if fewshot examples match dataset
                    fewshot_samples = fewshot_config.get('samples', [])
                    warnings = check_if_fewshot_matches_dataset(fewshot_samples, examples)
                    
                    if warnings:
                        report_lines.append("#### ⚠️ Warnings:\n")
                        for warning in warnings:
                            report_lines.append(f"- {warning}")
                        report_lines.append("")
            else:
                report_lines.append("#### Current Fewshot Config:\n")
                report_lines.append("*No fewshot config found in YAML file*")
                report_lines.append("")
        else:
            report_lines.append("#### Configuration:\n")
            report_lines.append("⚠️ **This task is NOT configured in the YAML files**")
            report_lines.append("")
        
        report_lines.append("---")
        report_lines.append("")
    
    return "\n".join(report_lines)

def main():
    print("=" * 80)
    print("BBEH Tasks Verification and Report Generation")
    print("=" * 80)
    print()
    
    # Load dataset
    dataset_tasks, tasks_examples = load_bbeh_dataset()
    print(f"Found {len(dataset_tasks)} unique tasks in BBEH dataset:")
    for task in dataset_tasks:
        print(f"  - {task}")
    print()
    
    # Get configured tasks
    configured_tasks, task_mappings = get_configured_tasks()
    print(f"Found {len(configured_tasks)} configured tasks:")
    for task in configured_tasks:
        bbeh_name = task_mappings.get(task, "NOT MAPPED")
        print(f"  - {task} -> {bbeh_name}")
    print()
    
    # Generate report
    report = generate_report(dataset_tasks, tasks_examples, configured_tasks, task_mappings)
    
    # Write report
    report_file = SCRIPT_DIR / "BBEH_TASKS_VERIFICATION_REPORT.md"
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"Report generated: {report_file}")
    print()
    
    # Print summary
    configured_bbeh_names = set(task_mappings.values())
    dataset_task_set = set(dataset_tasks)
    
    missing = dataset_task_set - configured_bbeh_names
    extra = configured_bbeh_names - dataset_task_set
    
    if missing:
        print(f"⚠️  Missing tasks: {sorted(missing)}")
    if extra:
        print(f"⚠️  Extra tasks: {sorted(extra)}")
    if not missing and not extra:
        print("✅ All tasks match exactly!")

if __name__ == "__main__":
    main()

