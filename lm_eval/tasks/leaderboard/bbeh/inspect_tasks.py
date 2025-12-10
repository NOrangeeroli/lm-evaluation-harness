#!/usr/bin/env python3
"""Inspect all BBEH tasks and print sample counts, target values, and doc_to_choice information.

Usage:
    # From the lm-evaluation-harness directory:
    python3 -m lm_eval.tasks.leaderboard.bbeh.inspect_tasks
    
    # Or with PYTHONPATH:
    PYTHONPATH=/path/to/lm-evaluation-harness python3 inspect_tasks.py
"""

import sys
import os
from collections import Counter

# Add parent directory to path if needed
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

try:
    from lm_eval.tasks import TaskManager
except ImportError as e:
    print(f"Error importing lm_eval: {e}")
    print("\nPlease run this script from the lm-evaluation-harness directory,")
    print("or ensure lm_eval is installed/available in your Python path.")
    sys.exit(1)

def inspect_tasks():
    """Load and inspect all BBEH tasks."""
    task_manager = TaskManager()
    
    # Get list of all BBEH tasks
    try:
        # Try to get task list from the group
        task_list = task_manager.get_task_list("leaderboard_bbeh")
    except Exception as e:
        print(f"Error getting task list: {e}")
        # Fallback: manually list BBEH tasks
        task_list = [
            "leaderboard_bbeh_boardgame_qa",
            "leaderboard_bbeh_boolean_expressions",
            "leaderboard_bbeh_causal_understanding",
            "leaderboard_bbeh_disambiguation_qa",
            "leaderboard_bbeh_dyck_languages",
            "leaderboard_bbeh_geometric_shapes",
            "leaderboard_bbeh_hyperbaton",
            "leaderboard_bbeh_movie_recommendation",
            "leaderboard_bbeh_nycc",
            "leaderboard_bbeh_object_properties",
            "leaderboard_bbeh_sarc_triples",
            "leaderboard_bbeh_shuffled_objects",
            "leaderboard_bbeh_web_of_lies",
            "leaderboard_bbeh_zebra_puzzles",
        ]
    
    # Load each task individually
    task_dict = {}
    for task_name in task_list:
        try:
            loaded = task_manager.load_task_or_group(task_name)
            # load_task_or_group returns a dict with task_name as key
            if isinstance(loaded, dict) and task_name in loaded:
                task = loaded[task_name]
            elif isinstance(loaded, dict) and len(loaded) == 1:
                task = list(loaded.values())[0]
            elif hasattr(loaded, 'task_dict'):
                # It's a group, skip it
                continue
            else:
                task = loaded
            task_dict[task_name] = task
        except Exception as e:
            print(f"Warning: Could not load {task_name}: {e}")
            continue
    
    print("=" * 80)
    print("BBEH TASKS INSPECTION REPORT")
    print("=" * 80)
    print()
    
    total_samples = 0
    tasks_with_issues = []
    
    for task_name, task in sorted(task_dict.items()):
        print(f"\n{'='*80}")
        print(f"Task: {task_name}")
        print(f"{'='*80}")
        
        try:
            # Check if task is actually a Task instance
            if not hasattr(task, 'config'):
                print(f"  ⚠️  Task is not a Task instance (type: {type(task)})")
                if isinstance(task, dict):
                    print(f"     Task dict keys: {list(task.keys())}")
                continue
            
            # Basic info
            print(f"Output type: {task.config.output_type}")
            print(f"Has training docs: {task.has_training_docs()}")
            print(f"Has validation docs: {task.has_validation_docs()}")
            print(f"Has test docs: {task.has_test_docs()}")
            
            # Sample count
            num_samples = len(task.eval_docs)
            total_samples += num_samples
            print(f"Number of eval samples: {num_samples}")
            
            # doc_to_choice info
            if task.config.doc_to_choice:
                if callable(task.config.doc_to_choice):
                    # It's a function, try to get choices from first doc
                    try:
                        first_doc = task.eval_docs[0]
                        choices = task.doc_to_choice(first_doc)
                        print(f"doc_to_choice (function): {len(choices)} choices")
                        print(f"  Choices: {choices[:10]}{'...' if len(choices) > 10 else ''}")
                    except Exception as e:
                        print(f"doc_to_choice (function) - Error getting choices: {e}")
                else:
                    # It's a list
                    choices = task.config.doc_to_choice
                    print(f"doc_to_choice (list): {len(choices)} choices")
                    print(f"  Choices: {choices[:10]}{'...' if len(choices) > 10 else ''}")
            else:
                print("doc_to_choice: None (generate_until task)")
            
            # Check target values
            print("\nTarget value analysis:")
            targets = []
            target_types = []
            for i, doc in enumerate(task.eval_docs[:100]):  # Check first 100
                try:
                    target = task.doc_to_target(doc)
                    targets.append(str(target))
                    target_types.append(type(target).__name__)
                except Exception as e:
                    print(f"  Error getting target for doc {i}: {e}")
            
            if targets:
                target_counter = Counter(targets)
                type_counter = Counter(target_types)
                print(f"  Unique targets (first 100 docs): {len(target_counter)}")
                print(f"  Target types: {dict(type_counter)}")
                print(f"  Most common targets: {target_counter.most_common(10)}")
                
                # Check if targets match doc_to_choice
                if task.config.doc_to_choice:
                    if callable(task.config.doc_to_choice):
                        try:
                            first_doc = task.eval_docs[0]
                            choices = task.doc_to_choice(first_doc)
                        except:
                            choices = []
                    else:
                        choices = task.config.doc_to_choice
                    
                    if choices:
                        choices_set = set(str(c) for c in choices)
                        targets_set = set(targets)
                        missing_in_choices = targets_set - choices_set
                        if missing_in_choices:
                            print(f"  ⚠️  WARNING: {len(missing_in_choices)} target values not in doc_to_choice!")
                            print(f"     Missing: {list(missing_in_choices)[:10]}{'...' if len(missing_in_choices) > 10 else ''}")
                            tasks_with_issues.append((task_name, missing_in_choices))
                        else:
                            print(f"  ✅ All targets match doc_to_choice")
            
            # Show first example
            print("\nFirst example:")
            try:
                first_doc = task.eval_docs[0]
                text = task.doc_to_text(first_doc)
                target = task.doc_to_target(first_doc)
                print(f"  Input (first 200 chars): {text[:200]}...")
                print(f"  Target: {target} (type: {type(target).__name__})")
            except Exception as e:
                print(f"  Error showing example: {e}")
                
        except Exception as e:
            print(f"  ❌ ERROR inspecting task: {e}")
            import traceback
            traceback.print_exc()
            tasks_with_issues.append((task_name, f"Error: {e}"))
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total tasks: {len(task_dict)}")
    print(f"Total samples: {total_samples}")
    print(f"Average samples per task: {total_samples / len(task_dict):.1f}")
    
    if tasks_with_issues:
        print(f"\n⚠️  Tasks with issues: {len(tasks_with_issues)}")
        for task_name, issue in tasks_with_issues:
            print(f"  - {task_name}: {issue}")
    else:
        print("\n✅ All tasks loaded successfully!")

if __name__ == "__main__":
    inspect_tasks()

