"""
Script to find test files related to a list of Python files.

Usage:
    python find_related_test_files.py <file_with_list_of_files> <workspace_dir>

Example:
    python find_related_test_files.py backend_relevant_files.txt /path/to/workspace
"""

import os
import sys
import json
import re
from pathlib import Path


def normalize_path(path):
    """Normalize a file path to make it consistent for comparison."""
    return str(Path(path).resolve())


def get_module_name(file_path):
    """Extract the module name from a file path."""
    # Remove .py extension and convert path separators to dots
    base_name = os.path.splitext(file_path)[0]
    # Convert path separators to dots and return the module name
    return base_name.replace('/', '.').replace('\\', '.')


def find_test_files_for_path(file_path, workspace_dir):
    """Find test files that might be related to the given file path."""
    related_test_files = []
    
    # Get the file name without extension
    file_path = file_path.strip()
    file_name = os.path.basename(file_path)
    name_without_ext = os.path.splitext(file_name)[0]
    
    # Common test file naming patterns
    test_patterns = [
        f"test_{name_without_ext}.py",
        f"{name_without_ext}_test.py",
        f"tests_{name_without_ext}.py",
        f"{name_without_ext}_tests.py"
    ]
    
    # Get directory structure to help locate test files
    file_dir = os.path.dirname(file_path)
    module_parts = file_dir.split(os.sep)
    
    # Places to look for test files
    search_locations = [
        # Same directory
        file_dir,
        # Directory named 'tests' at the same level
        os.path.join(os.path.dirname(file_dir), 'tests'),
        # Directory named 'test' at the same level
        os.path.join(os.path.dirname(file_dir), 'test'),
        # Subdirectory named 'tests'
        os.path.join(file_dir, 'tests'),
        # Subdirectory named 'test'
        os.path.join(file_dir, 'test')
    ]
    
    # If we're in a module, also look in a tests directory with the same structure
    if 'backend' in module_parts:
        backend_index = module_parts.index('backend')
        # Look for tests directory structure that mirrors the module structure
        for test_root in ['tests', 'test']:
            module_path = module_parts[backend_index+1:]
            test_path = [workspace_dir, 'backend', test_root] + module_path
            search_locations.append(os.path.join(*test_path))
    
    # Search for test files in all potential locations
    for location in search_locations:
        if os.path.exists(location):
            for pattern in test_patterns:
                potential_test_file = os.path.join(location, pattern)
                if os.path.exists(potential_test_file):
                    related_test_files.append(potential_test_file)
    
    # Also look for test files that might import this module
    module_name = get_module_name(file_path)
    pattern = re.compile(r'(from|import)\s+([\w.]+\.)?' + re.escape(name_without_ext) + r'(\s+|\.|$)')
    
    # Walk through test directories to find files that might import this module
    for root, dirs, files in os.walk(os.path.join(workspace_dir, 'backend')):
        if 'test' in root or 'tests' in root:
            for file in files:
                if file.endswith('.py') and ('test' in file or 'Test' in file):
                    test_file_path = os.path.join(root, file)
                    try:
                        with open(test_file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if pattern.search(content):
                                related_test_files.append(test_file_path)
                    except Exception as e:
                        print(f"Error reading {test_file_path}: {e}", file=sys.stderr)
    
    # Normalize paths and remove duplicates
    normalized_test_files = [normalize_path(p) for p in related_test_files]
    return list(set(normalized_test_files))


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <file_with_list_of_files> <workspace_dir>")
        sys.exit(1)
    
    input_file_path = sys.argv[1]
    workspace_dir = sys.argv[2]
    
    all_test_files = []
    file_to_tests_map = {}
    
    try:
        # Read the list of files
        with open(input_file_path, 'r') as file_list:
            for line in file_list:
                file_path = line.strip()
                if file_path:
                    # Skip files that are already test files
                    if 'test' in file_path:
                        all_test_files.append(file_path)
                        continue
                    
                    # Find related test files
                    test_files = find_test_files_for_path(file_path, workspace_dir)
                    if test_files:
                        file_to_tests_map[file_path] = test_files
                        all_test_files.extend(test_files)
        
        # Remove duplicates while preserving order
        unique_test_files = []
        for file in all_test_files:
            if file not in unique_test_files:
                unique_test_files.append(file)
        
        # Write the list of test files
        with open('all_test_files.txt', 'w') as output_file:
            for test_file in unique_test_files:
                output_file.write(f"{test_file}\n")
        
        # Write the mapping for debugging/reference
        with open('test_files_mapping.json', 'w') as mapping_file:
            json.dump(file_to_tests_map, mapping_file, indent=2)
        
        print(f"Found {len(unique_test_files)} related test files.")
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()