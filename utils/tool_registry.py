import os
import ast
from pathlib import Path
from typing import Dict, List, Optional

class ToolRegistry:
    """
    Manages discovery and documentation of available tools.
    """
    
    def __init__(self, tools_dir: os.PathLike):
        self.tools_dir = Path(tools_dir)
        self._tools_cache: Dict[str, str] = {}
        
    def get_tools(self) -> List[str]:
        """List all python scripts in tools directory."""
        if not self.tools_dir.exists():
            return []
            
        return [
            f.name for f in self.tools_dir.glob("*.py")
            if f.is_file() and not f.name.startswith('_')
        ]
        
    def get_tool_description(self, filename: str) -> str:
        """Extract docstring from tool file."""
        if filename in self._tools_cache:
            return self._tools_cache[filename]
            
        path = self.tools_dir / filename
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse AST to get docstring safely without importing
            tree = ast.parse(content)
            docstring = ast.get_docstring(tree)
            
            if docstring:
                desc = docstring.strip()
            else:
                desc = "No description provided."
                
            self._tools_cache[filename] = desc
            return desc
            
        except Exception as e:
            return f"Error reading tool: {e}"
            
    def get_registry_prompt(self) -> str:
        """Generate the system prompt section for tools."""
        tools = self.get_tools()
        if not tools:
            return "No tools found."
            
        lines = ["Available Tools (Automatic Discovery):"]
        
        for tool in sorted(tools):
            desc = self.get_tool_description(tool)
            # Take just the first line of description for the summary list
            short_desc = desc.split('\n')[0]
            lines.append(f"- python tools/{tool} : {short_desc}")
            
        return "\n".join(lines)
