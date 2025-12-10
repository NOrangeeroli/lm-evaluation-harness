#!/usr/bin/env python3
"""
Fix process_docs format in all BBEH YAML files.
Changes from: process_docs: '!function ''utils.process_docs_XXX'''
To: process_docs: !function utils.process_docs_XXX
"""

import re
import os
from pathlib import Path

# Directory containing the YAML files
yaml_dir = Path(__file__).parent

# Pattern to match the old format (with quotes)
old_pattern1 = re.compile(r"process_docs: '!function ''utils\.process_docs_([^']+)''")
# Pattern to match trailing quote issue
old_pattern2 = re.compile(r"process_docs: !function utils\.process_docs_([^']+)'")

def fix_file(file_path):
    """Fix process_docs format in a single YAML file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = False
    
    # Fix the old quoted format
    if old_pattern1.search(content):
        content = old_pattern1.sub(r'process_docs: !function utils.process_docs_\1', content)
        modified = True
    
    # Fix trailing quote issue
    if old_pattern2.search(content):
        content = old_pattern2.sub(r'process_docs: !function utils.process_docs_\1', content)
        modified = True
    
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed: {file_path.name}")
        return True
    else:
        print(f"Already correct: {file_path.name}")
        return False

def main():
    """Fix all YAML files in the directory."""
    yaml_files = sorted(yaml_dir.glob("*.yaml"))
    
    # Exclude template files (those starting with _)
    yaml_files = [f for f in yaml_files if not f.name.startswith('_')]
    
    fixed_count = 0
    for yaml_file in yaml_files:
        if fix_file(yaml_file):
            fixed_count += 1
    
    print(f"\nTotal files fixed: {fixed_count}")
    print(f"Total files checked: {len(yaml_files)}")

if __name__ == "__main__":
    main()

