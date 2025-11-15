#!/usr/bin/env python
"""
Script to automatically fix common flake8 issues
"""

import os
import re
from pathlib import Path


def fix_trailing_whitespace(content):
    """Remove trailing whitespace from lines"""
    lines = content.split('\n')
    return '\n'.join(line.rstrip() for line in lines)


def fix_blank_lines_at_end(content):
    """Ensure exactly one newline at end of file"""
    content = content.rstrip('\n')
    return content + '\n'


def fix_tabs_to_spaces(content):
    """Replace tabs with 4 spaces"""
    return content.replace('\t', '    ')


def fix_bare_except(content):
    """Replace bare except with except Exception"""
    # Match 'except:' but not 'except Exception:' or 'except SomeClass:'
    pattern = r'(\s+)(except)(\s*)(:)'
    replacement = r'\1except Exception\4'
    return re.sub(pattern, replacement, content)


def fix_f_string_placeholders(content):
    """Fix f-strings without placeholders to regular strings"""
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        # Look for f-strings without {
        if 'f"' in line or "f'" in line:
            # Check if the line has any { } placeholders
            match = re.search(r'f(["\'])([^"\']*)\1', line)
            if match:
                quote = match.group(1)
                text = match.group(2)
                # If no placeholders, remove the f
                if '{' not in text:
                    line = line.replace(f'f{quote}', quote)
        fixed_lines.append(line)

    return '\n'.join(fixed_lines)


def process_file(filepath):
    """Process a single file to fix flake8 issues"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Apply fixes
        content = fix_trailing_whitespace(content)
        content = fix_tabs_to_spaces(content)
        content = fix_bare_except(content)
        content = fix_f_string_placeholders(content)
        content = fix_blank_lines_at_end(content)

        # Only write if changed
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {filepath}")
            return True
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False


def main():
    """Main function"""
    # Get all Python files
    python_files = []
    base_dir = Path(__file__).parent

    for root, dirs, files in os.walk(base_dir):
        # Skip venv, __pycache__, migrations, etc.
        dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git', 'node_modules', 'staticfiles']]

        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                python_files.append(filepath)

    print(f"Found {len(python_files)} Python files")
    print("=" * 60)

    fixed_count = 0
    for filepath in python_files:
        if process_file(filepath):
            fixed_count += 1

    print("=" * 60)
    print(f"Fixed {fixed_count} files")


if __name__ == '__main__':
    main()
