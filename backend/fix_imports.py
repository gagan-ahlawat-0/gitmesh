#!/usr/bin/env python3
"""
Fix all import issues in the backend
"""
import os
import re
import glob

def fix_backend_imports():
    """Fix all backend.* imports to use relative imports"""
    
    # Find all Python files in the routes directory
    route_files = glob.glob("api/v1/routes/*.py")
    
    for file_path in route_files:
        print(f"Checking {file_path}...")
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            original_content = content
            
            # Fix backend.* imports
            content = re.sub(r'from backend\.([a-zA-Z_][a-zA-Z0-9_.]*) import', r'from \1 import', content)
            content = re.sub(r'import backend\.([a-zA-Z_][a-zA-Z0-9_.]*)', r'import \1', content)
            
            # Fix relative imports that go beyond top-level package
            content = re.sub(r'from \.\.\.\.([a-zA-Z_][a-zA-Z0-9_.]*) import', r'from \1 import', content)
            
            if content != original_content:
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"  ✅ Fixed imports in {file_path}")
            else:
                print(f"  ✓ No changes needed in {file_path}")
                
        except Exception as e:
            print(f"  ❌ Error processing {file_path}: {e}")

def fix_typing_imports():
    """Add missing typing imports"""
    
    route_files = glob.glob("api/v1/routes/*.py")
    
    for file_path in route_files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check if file uses List but doesn't import it
            if 'List[' in content and 'from typing import' in content:
                # Check if List is already imported
                typing_import_match = re.search(r'from typing import ([^\\n]+)', content)
                if typing_import_match:
                    imports = typing_import_match.group(1)
                    if 'List' not in imports:
                        # Add List to the import
                        new_imports = imports.rstrip() + ', List'
                        content = content.replace(
                            f'from typing import {imports}',
                            f'from typing import {new_imports}'
                        )
                        
                        with open(file_path, 'w') as f:
                            f.write(content)
                        print(f"  ✅ Added List import to {file_path}")
                        
        except Exception as e:
            print(f"  ❌ Error processing {file_path}: {e}")

if __name__ == "__main__":
    print("🔧 Fixing import issues...")
    fix_backend_imports()
    fix_typing_imports()
    print("✅ Import fixes completed!")