import pytest
import json
from autonomous_agent import AutonomousAgent

class MockAgent(AutonomousAgent):
    def __init__(self):
        # Skip full init
        pass

def test_parse_valid_json_action():
    agent = MockAgent()
    response = """
    Here is my thought process.
    ```json
    {
        "reasoning": "I need to check the file.",
        "command": "ls -la",
        "expected": "List of files",
        "learning": "Always check dir first"
    }
    ```
    """
    
    result = agent._parse_action_response(response)
    
    assert result['command'] == "ls -la"
    assert result['reasoning'] == "I need to check the file."
    assert result['learning'] == "Always check dir first"

def test_parse_json_without_markdown():
    agent = MockAgent()
    response = """
    {
        "reasoning": "Raw JSON",
        "command": "echo hello"
    }
    """
    
    result = agent._parse_action_response(response)
    assert result['command'] == "echo hello"

def test_parse_malformed_json_recovery():
    """Test if regex fallback works or we catch errors."""
    agent = MockAgent()
    # Resume fallback logic? Or enforce JSON?
    # For now, if JSON fails, we might return None or try regex.
    # But we are replacing regex with JSON.
    pass
