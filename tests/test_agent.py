import pytest
from autonomous_agent import AutonomousAgent
from unittest.mock import MagicMock, patch

def test_response_parsing_regex():
    """Test the multi-line regex parsing logic isolated from the agent."""
    # We can test the private static method logic by instantiating or just replicating the logic
    # Since it's an instance method, we need an instance or access to the function.
    # The method uses `self`? No, let's check. 
    # It seems to be an instance method but doesn't use self state for the parsing itself usually.
    
    # Let's mock the dependencies to init the agent
    with patch('autonomous_agent.Config'), \
         patch('autonomous_agent.logger'), \
         patch('autonomous_agent.ContextManager'), \
         patch('autonomous_agent.LongTermMemory'), \
         patch('autonomous_agent.OpenRouterClient'), \
         patch('autonomous_agent.CommandExecutor'), \
         patch('autonomous_agent.Planner'):
         
        agent = AutonomousAgent()
        
        test_response_complex = """
REASONING: This is a complex reasoning block
that spans multiple lines
and includes "quotes" and symbols.
COMMAND: echo 'hello' && \
echo 'world'
EXPECTED: Output on
two lines
LEARNING: Multi-line parsing is
robust.
"""
        parsed = agent._parse_action_response(test_response_complex)
        
        assert "spans multiple lines" in parsed['reasoning']
        assert "echo 'hello'" in parsed['command']
        assert "echo 'world'" in parsed['command']
        assert "two lines" in parsed['expected']
        assert "robust" in parsed['learning']

def test_parse_missing_fields():
    """Test parsing when some fields are missing."""
    with patch('autonomous_agent.Config'), \
         patch('autonomous_agent.logger'), \
         patch('autonomous_agent.ContextManager'), \
         patch('autonomous_agent.LongTermMemory'), \
         patch('autonomous_agent.OpenRouterClient'), \
         patch('autonomous_agent.CommandExecutor'), \
         patch('autonomous_agent.Planner'):
         
        agent = AutonomousAgent()
        
        # Only command
        response = "COMMAND: echo test"
        parsed = agent._parse_action_response(response)
        assert parsed['command'] == "echo test"
        
        # Reasoning and Command
        response = "REASONING: Because.\nCOMMAND: do it"
        parsed = agent._parse_action_response(response)
        assert parsed['reasoning'] == "Because."
        assert parsed['command'] == "do it"
