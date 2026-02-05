#!/usr/bin/env python3
"""
Code Structure Analyzer.
Lists classes and functions in a file to give a high-level overview.
"""
import argparse
import ast
import os
import sys

def get_structure(filepath):
    if not os.path.exists(filepath):
        return f"Error: File '{filepath}' not found."
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        tree = ast.parse(content)
        lines = content.splitlines()
        
        output = [f"File: {filepath}"]
        
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                output.append(f"C: {node.name} (Line {node.lineno})")
                # Get docstring
                doc = ast.get_docstring(node)
                if doc:
                    output.append(f"   \"\"\"{doc.splitlines()[0]}...\"\"\"")
                
                # Get methods
                for child in node.body:
                    if isinstance(child, ast.FunctionDef):
                        args = [a.arg for a in child.args.args]
                        output.append(f"   M: {child.name}({', '.join(args)}) (Line {child.lineno})")
                        
            elif isinstance(node, ast.FunctionDef):
                args = [a.arg for a in node.args.args]
                output.append(f"F: {node.name}({', '.join(args)}) (Line {node.lineno})")
                doc = ast.get_docstring(node)
                if doc:
                    output.append(f"   \"\"\"{doc.splitlines()[0]}...\"\"\"")
                    
        return "\n".join(output)
        
    except Exception as e:
        return f"Error parsing file: {e}"

def main():
    parser = argparse.ArgumentParser(description="List code structure (classes/functions)")
    parser.add_argument("file", help="Python file to analyze")
    
    args = parser.parse_args()
    print(get_structure(args.file))

if __name__ == "__main__":
    main()
