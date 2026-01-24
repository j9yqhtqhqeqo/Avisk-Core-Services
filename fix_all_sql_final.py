#!/usr/bin/env python3
"""Complete SQL parameter placeholder fix for all DBEntities files"""

import re
import os


def fix_sql_file(file_path):
    print(f"Processing {file_path}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Comprehensive pattern replacements for SQL parameter placeholders
    replacements = [
        # Standard WHERE clause patterns
        (r'where\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s*=\s*\?', r'where \1 = %s'),
        (r'and\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s*=\s*\?', r'and \1 = %s'),
        (r'=\s*\?(?=\s|$|,|\))', r'= %s'),

        # SQL Server bracket notation
        (r'where\s+([a-zA-Z_][a-zA-Z0-9_.]*)\.?\[([a-zA-Z_][a-zA-Z0-9_]*)\]\s*=\s*\?',
         r'where \1.\2 = %s'),
        (r'and\s+([a-zA-Z_][a-zA-Z0-9_.]*)\.?\[([a-zA-Z_][a-zA-Z0-9_]*)\]\s*=\s*\?',
         r'and \1.\2 = %s'),

        # Standalone ? in SQL contexts
        (r'(\s)=\?\s*\\', r'\1= %s\\'),
    ]

    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)

    # Handle specific SQL patterns with \\ line continuations
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # Skip commented lines
        if line.strip().startswith('#'):
            continue

        # Handle SQL lines with backslash continuation that contain ?
        if '\\' in line and '?' in line and ('where' in line.lower() or 'and' in line.lower()):
            # Replace patterns like "= ?\"
            line = re.sub(r'=\s*\?\s*\\', '= %s\\', line)
            lines[i] = line

    content = '\n'.join(lines)

    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Updated {file_path}")
        return True
    else:
        print(f"ℹ️  No changes needed in {file_path}")
        return False


def main():
    db_entities_dir = "DBEntities"
    python_files = [f for f in os.listdir(
        db_entities_dir) if f.endswith('.py')]

    updated_files = []
    for file in python_files:
        file_path = os.path.join(db_entities_dir, file)
        if fix_sql_file(file_path):
            updated_files.append(file)

    if updated_files:
        print(f"\n✅ Updated {len(updated_files)} files:")
        for file in updated_files:
            print(f"  - {file}")
    else:
        print("\nℹ️  All SQL parameter placeholders appear to already be fixed")


if __name__ == "__main__":
    main()
