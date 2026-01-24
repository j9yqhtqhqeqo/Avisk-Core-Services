#!/usr/bin/env python3
"""
Script to fix all remaining SQL parameter placeholders from ? to %s
in InsightGeneratorDBManager.py and fix parameter passing.
"""
import re


def fix_sql_placeholders():
    file_path = "/Users/mohanganadal/Avisk/Avisk-Core-Services/DBEntities/InsightGeneratorDBManager.py"

    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()

    # Replace SQL parameter placeholders ? with %s
    # This pattern looks for ? in SQL contexts (between quotes)
    content = re.sub(r"'([^']*)\?", r"'\1%s", content)
    content = re.sub(r'"([^"]*)\?', r'"\1%s', content)

    # Fix cursor.execute calls with multiple separate parameters
    # Pattern: cursor.execute(sql, param1, param2, ...)
    # Replace with: cursor.execute(sql, (param1, param2, ...))

    # Find all cursor.execute calls with multiple parameters
    execute_pattern = r'cursor\.execute\(([^,]+),\s*([^)]+)\)'

    def fix_execute_params(match):
        sql_part = match.group(1)
        params_part = match.group(2)

        # Check if parameters are already in tuple format
        if params_part.strip().startswith('(') and params_part.strip().endswith(')'):
            return match.group(0)  # Already correct

        # Count commas to see if we have multiple parameters
        param_count = params_part.count(',') + 1

        if param_count > 1:
            # Multiple parameters - wrap in tuple
            return f'cursor.execute({sql_part}, ({params_part}))'
        else:
            # Single parameter - wrap in tuple
            return f'cursor.execute({sql_part}, ({params_part},))'

    content = re.sub(execute_pattern, fix_execute_params, content)

    # Write the file back
    with open(file_path, 'w') as f:
        f.write(content)

    print("✅ Fixed all SQL parameter placeholders and cursor.execute calls")


if __name__ == "__main__":
    fix_sql_placeholders()
