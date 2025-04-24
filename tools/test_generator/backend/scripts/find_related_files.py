#!/usr/bin/env python3
"""
Script to analyze import dependencies of Python files.
Usage: python find_related_files.py <file_list> <project_root>
"""

import ast
import os
import sys
import json
from collections import defaultdict

def find_imports(file_path):
    """Analyze a Python file and find all imports."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        tree = ast.parse(content)
        imports = []
        
        for node in ast.walk(tree):
            # Handle import statements (import x, import x.y)
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            
            # Handle from import statements (from x import y)
            elif isinstance(node, ast.ImportFrom):
                module = node.module if node.module else ''
                for name in node.names:
                    if module:
                        imports.append(f"{module}.{name.name}")
                    else:
                        imports.append(name.name)
        
        return imports
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}", file=sys.stderr)
        return []

def resolve_import_to_filepath(import_name, base_path):
    """Try to convert an import name to an actual file path."""
    parts = import_name.split('.')
    
    # First strategy: Try various combinations of the import path to find a matching file
    for i in range(len(parts), 0, -1):
        # Convert import path to file path
        path_parts = parts[:i]
        file_path = os.path.join(base_path, *path_parts) + '.py'
        
        if os.path.exists(file_path):
            return file_path
            
        # Check if it might be a package with __init__.py
        dir_path = os.path.join(base_path, *path_parts)
        init_path = os.path.join(dir_path, '__init__.py')
        
        if os.path.exists(init_path):
            return init_path
    
    # Second strategy: Try looking in parent directories
    # Start with the original base path and go up to 3 parent directories
    current_path = base_path
    for _ in range(3):  # Try up to 3 parent directories
        parent_path = os.path.dirname(current_path)
        if parent_path == current_path:  # We've reached the root directory
            break
        current_path = parent_path
        
        # Try the same resolution logic but with the parent directory
        for i in range(len(parts), 0, -1):
            path_parts = parts[:i]
            file_path = os.path.join(current_path, *path_parts) + '.py'
            
            if os.path.exists(file_path):
                return file_path
                
            # Check if it might be a package with __init__.py
            dir_path = os.path.join(current_path, *path_parts)
            init_path = os.path.join(dir_path, '__init__.py')
            
            if os.path.exists(init_path):
                return init_path
    
    # Third strategy: Handle cases like 'core.models' where 'core' is a package
    # This searches from the base directory and iterates through possible combinations
    for i in range(len(parts)):
        prefix_parts = parts[:i]
        suffix_parts = parts[i:]
        
        if not prefix_parts:  # Skip empty prefix
            continue
            
        # Try to find the prefix directory
        prefix_dir = os.path.join(base_path, *prefix_parts)
        
        if os.path.isdir(prefix_dir):
            # Now try to resolve the suffix in this directory
            file_path = os.path.join(prefix_dir, *suffix_parts) + '.py'
            
            if os.path.exists(file_path):
                return file_path
                
            # Check for package with __init__.py
            dir_path = os.path.join(prefix_dir, *suffix_parts)
            init_path = os.path.join(dir_path, '__init__.py')
            
            if os.path.exists(init_path):
                return init_path
    
    # Could not resolve to a file
    return None

def find_related_files(file_path, project_root):
    """Find all files related to the given file through imports."""
    direct_imports = find_imports(file_path)
    related_files = set()
    
    for import_name in direct_imports:
        file = resolve_import_to_filepath(import_name, project_root)
        if file:
            # Convert to relative path from project root
            rel_path = os.path.relpath(file, project_root)
            related_files.add(rel_path)
    
    return related_files

def process_files_from_list(file_list_path, project_root):
    """Process a list of files and find all related files."""
    with open(file_list_path, 'r') as f:
        interesting_files = [line.strip() for line in f if line.strip()]
    
    # Dictionary to store each file and its dependencies
    dependencies_map = defaultdict(set)
    all_related_files = set()
    
    for file in interesting_files:
        # Normalize file path to be relative to project root
        if os.path.isabs(file):
            rel_file = os.path.relpath(file, project_root)
        else:
            rel_file = file
        full_path = os.path.join(project_root, rel_file)
        
        # Only process Python files
        if os.path.exists(full_path) and full_path.endswith('.py'):
            related = find_related_files(full_path, project_root)
            dependencies_map[rel_file] = related
            all_related_files.update(related)
    
    # Write results to a JSON file to maintain structure
    with open('dependencies_map.json', 'w') as f:
        json.dump({k: list(v) for k, v in dependencies_map.items()}, f, indent=2)
    
    # Write all related files to a text file
    with open('all_related_files.txt', 'w') as f:
        for file in sorted(all_related_files):
            f.write(f"{file}\n")
    
    # Write all files (original + related) to a file
    all_files = set(interesting_files).union(all_related_files)
    with open('all_files.txt', 'w') as f:
        for file in sorted(all_files):
            f.write(f"{file}\n")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <file_list> <project_root>")
        sys.exit(1)
    
    file_list = sys.argv[1]
    project_root = sys.argv[2]
    process_files_from_list(file_list, project_root)
    print("Analysis completed. Results written to:")
    print("- dependencies_map.json: map of each file with its dependencies")
    print("- all_related_files.txt: list of all related files")
    print("- all_files.txt: combined list of original and related files")