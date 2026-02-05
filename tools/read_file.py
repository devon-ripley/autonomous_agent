#!/usr/bin/env python3
"""
Smart File Reader.
Reads specific lines or ranges from a file.
"""
import argparse
import sys
import os

def read_file(filepath, start_line=1, end_line=None, show_numbers=True):
    if not os.path.exists(filepath):
        return f"Error: File '{filepath}' not found."
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        total_lines = len(lines)
        start_index = max(0, start_line - 1)
        
        if end_line is None:
            end_index = total_lines
        else:
            end_index = min(total_lines, end_line)
            
        if start_index >= total_lines:
            return "EOF"
            
        output = []
        if show_numbers:
            width = len(str(end_index))
            for i in range(start_index, end_index):
                line_num = i + 1
                output.append(f"{line_num:>{width}} | {lines[i].rstrip()}")
        else:
            output = [lines[i].rstrip() for i in range(start_index, end_index)]
            
        return "\n".join(output)
        
    except Exception as e:
        return f"Error reading file: {e}"

def main():
    parser = argparse.ArgumentParser(description="Read file content with line numbers.")
    parser.add_argument("file", help="Path to file")
    parser.add_argument("range", nargs="?", help="Line range (e.g. 10-20) or start line")
    parser.add_argument("--no-numbers", action="store_true", help="Disable line numbers")
    
    args = parser.parse_args()
    
    start = 1
    end = None
    
    if args.range:
        if "-" in args.range:
            try:
                s, e = args.range.split("-")
                start = int(s) if s else 1
                end = int(e) if e else None
            except ValueError:
                print("Error: Invalid range format. Use start-end (e.g. 10-20)")
                sys.exit(1)
        else:
            try:
                start = int(args.range)
            except ValueError:
                print("Error: Invalid line number")
                sys.exit(1)
                
    print(read_file(args.file, start, end, not args.no_numbers))

if __name__ == "__main__":
    main()
