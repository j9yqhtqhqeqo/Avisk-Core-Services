#!/usr/bin/env python3
"""Fix remaining SQL parameter placeholders in InsightGeneratorDBManager.py"""

import re


def fix_sql_file(file_path):
    print(f"Processing {file_path}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Fix remaining patterns - being more specific

    # 1. Fix patterns like "where sector_id = ?"
    content = re.sub(r'where sector_id\s*=\s*\?',
                     'where sector_id = %s', content)

    # 2. Fix patterns like "and year = ?"
    content = re.sub(r'and\s+year\s*=\s*\?', 'and year = %s', content)

    # 3. Fix patterns like "where year = ?"
    content = re.sub(r'where\s+year\s*=\s*\?', 'where year = %s', content)

    # 4. Fix patterns like "doc.year = ?"
    content = re.sub(r'doc\.year\s*=\s*\?', 'doc.year = %s', content)

    # 5. Fix patterns like "insights.year = ?"
    content = re.sub(r'insights\.year\s*=\s*\?', 'insights.year = %s', content)

    # 6. Fix patterns in SQL INSERT VALUES clauses - specifically for timestamp patterns
    content = re.sub(r'CURRENT_TIMESTAMP,\s*\?',
                     'CURRENT_TIMESTAMP, %s', content)

    # 7. Fix "where map.sector_id = ?"
    content = re.sub(r'map\.sector_id\s*=\s*\?', 'map.sector_id = %s', content)

    # 8. Fix any remaining standalone ? in SQL contexts (but not in comments)
    # Only replace ? that are not in commented lines and are likely SQL parameters
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # Skip commented lines
        if line.strip().startswith('#'):
            continue

        # Replace ? that are clearly SQL parameters (surrounded by SQL keywords)
        if any(keyword in line.lower() for keyword in ['where', 'and', 'set', 'values', 'select']):
            # Only replace ? that are clearly parameters (not in strings or comments)
            if "= ?" in line and not line.strip().startswith('#'):
                lines[i] = line.replace("= ?", "= %s")
            elif " ?" in line and "'" not in line.split(' ?')[0].split('=')[-1]:
                # More careful replacement for cases like "column = ?"
                lines[i] = re.sub(r'\s+\?(?=\s|$|,|\))', ' %s', line)

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
    file_path = "DBEntities/InsightGeneratorDBManager.py"
    if fix_sql_file(file_path):
        print("✅ Fixed remaining SQL parameter placeholders")
    else:
        print("ℹ️  All SQL parameter placeholders appear to already be fixed")


if __name__ == "__main__":
    main()
