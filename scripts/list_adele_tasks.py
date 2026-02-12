#!/usr/bin/env python3
"""List ADeLe source-benchmark-task combinations and their answer formats from CSV."""

import argparse
import csv
from collections import defaultdict
from pathlib import Path


DEFAULT_CSV = (
    Path(__file__).resolve().parents[2]
    / "ADeLe-AIEvaluation"
    / "ADeLe_battery_data"
    / "ADeLe_batterry_v1dot0.csv"
)


def load_source_benchmark_tasks(
    csv_path: Path,
) -> dict[tuple[str, str, str], dict[str, str]]:
    """
    Load source-benchmark-task combinations, their answer formats,
    and one example prompt/groundtruth pair from CSV.
    
    Returns:
        Dict mapping (source, benchmark, task) ->
        {
            "answer_format": str,
            "prompt": str,
            "groundtruth": str,
        }
    """
    task_data: dict[tuple[str, str, str], dict[str, str]] = {}
    
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)

        # We now also expect prompt / groundtruth so we can print an example.
        required = {"source", "benchmark", "task", "answer_format", "prompt", "groundtruth"}
        if not reader.fieldnames or required - set(reader.fieldnames):
            raise ValueError(
                "CSV must include 'source', 'benchmark', 'task', 'answer_format', "
                "'prompt', and 'groundtruth' columns."
            )
        
        for row in reader:
            source = (row.get("source") or "").strip()
            benchmark = (row.get("benchmark") or "").strip()
            task = (row.get("task") or "").strip()
            answer_format = (row.get("answer_format") or "").strip()
            prompt = (row.get("prompt") or "").strip()
            groundtruth = (row.get("groundtruth") or "").strip()
            
            if not all([source, benchmark, task, answer_format]):
                continue
            
            key = (source, benchmark, task)
            # Store answer_format and the first non-empty example we see
            if key not in task_data:
                task_data[key] = {
                    "answer_format": answer_format,
                    "prompt": prompt,
                    "groundtruth": groundtruth,
                }
            else:
                # If we already saw this key but don't yet have a prompt/groundtruth,
                # backfill from this row if available.
                info = task_data[key]
                if not info.get("prompt") and prompt:
                    info["prompt"] = prompt
                if not info.get("groundtruth") and groundtruth:
                    info["groundtruth"] = groundtruth
    
    return task_data


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Print ADeLe source-benchmark-task combinations "
            "with their answer_format values from CSV file."
        )
    )
    parser.add_argument(
        "--csv",
        default=DEFAULT_CSV,
        help="Path to ADeLe CSV file "
        f"(default: {DEFAULT_CSV})",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv).expanduser()
    if not csv_path.is_file():
        parser.error(f"CSV not found: {csv_path}")

    print("Loading data from CSV...")
    task_data = load_source_benchmark_tasks(csv_path)
    
    if not task_data:
        print("No tasks found.")
        return

    # Group by source for better organization
    source_groups = defaultdict(lambda: defaultdict(dict))
    for (source, benchmark, task), info in task_data.items():
        source_groups[source][benchmark][task] = info

    print(f"Found {len(task_data)} unique source-benchmark-task combinations:\n")
    
    for source in sorted(source_groups):
        benchmarks = source_groups[source]
        print(f"Source: {source}")
        for benchmark in sorted(benchmarks):
            tasks = benchmarks[benchmark]
            print(f"  Benchmark: {benchmark}")
            for task in sorted(tasks):
                info = tasks[task]
                answer_format = info.get("answer_format", "")
                prompt = info.get("prompt", "")
                groundtruth = info.get("groundtruth", "")

                print(f"    - {source} - {benchmark} - {task}: {answer_format}")

                # Print one example question-groundtruth pair if available
                if prompt or groundtruth:
                    print("      Example prompt:")
                    if prompt:
                        print(f"        {prompt}")
                    else:
                        print("        <empty>")

                    print("      Example groundtruth:")
                    if groundtruth:
                        print(f"        {groundtruth}")
                    else:
                        print("        <empty>")
        print()


if __name__ == "__main__":
    main()

