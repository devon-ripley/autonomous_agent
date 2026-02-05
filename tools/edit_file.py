#!/usr/bin/env python3
"""
File Editing Tool for Autonomous Agent.
Allows safe search-and-replace operations on files.
"""
import argparse
import sys
import os

def edit_file(filepath, search_text, replace_text, dry_run=False):
    """
    Replace all occurrences of search_text with replace_text in filepath.
    Returns True if changes were made.
    """
    if not os.path.exists(filepath):
        print(f"Error: File '{filepath}' not found.")
        return False
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if search_text not in content:
            print(f"Error: Search text not found in '{filepath}'.")
            # Hints for debugging
            if len(content) < 1000:
                print("File content:")
                print(content)
            return False
            
        new_content = content.replace(search_text, replace_text)
        
        if dry_run:
            print(f"Dry run: Would replace '{search_text}' with '{replace_text}'")
            return True
            
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        print(f"Successfully modified '{filepath}'.")
        return True
        
    except Exception as e:
        print(f"Error editing file: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Edit a file by replacing text.")
    parser.add_argument("file", help="Path to the file to edit")
    parser.add_argument("--search", "-s", required=True, help="Text to search for (exact match)")
    parser.add_argument("--replace", "-r", required=True, help="Text to replace with")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without modifying")
    
    args = parser.parse_args()
    
    # Handle literal newlines in arguments if passed as strings like "line1\nline2"
    search_text = args.search.replace("\\n", "\n")
    replace_text = args.replace.replace("\\n", "\n")
    
    success = edit_file(args.file, search_text, replace_text, args.dry_run)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
