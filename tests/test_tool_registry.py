import pytest
import os
from pathlib import Path
from utils.tool_registry import ToolRegistry

@pytest.fixture
def tools_dir(tmp_path):
    """Create a temporary tools directory with dummy tools."""
    d = tmp_path / "tools"
    d.mkdir()
    
    # Create a dummy tool
    (d / "dummy_tool.py").write_text('"""\nDummy Tool.\nA test tool.\n"""\nimport argparse\n')
    
    # Create a tool without docstring
    (d / "no_doc_tool.py").write_text('import sys\n')
    
    return d

def test_registry_discovery(tools_dir):
    registry = ToolRegistry(tools_dir)
    tools = registry.get_tools()
    
    assert "dummy_tool.py" in tools
    assert "no_doc_tool.py" in tools
    assert len(tools) == 2

def test_get_tool_description(tools_dir):
    registry = ToolRegistry(tools_dir)
    desc = registry.get_tool_description("dummy_tool.py")
    
    assert "Dummy Tool" in desc
    assert "A test tool" in desc

def test_get_all_documentation(tools_dir):
    registry = ToolRegistry(tools_dir)
    docs = registry.get_registry_prompt()
    
    assert "dummy_tool.py" in docs
    assert "Dummy Tool" in docs
    # Should handle tools with no docstring gracefully
    assert "no_doc_tool.py" in docs
