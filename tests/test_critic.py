import pytest
import json
from agents.critic_agent import CriticAgent
from unittest.mock import MagicMock

class MockLLM:
    def send_message(self, messages, **kwargs):
        # Inspect the user prompt (last message) to decide response
        user_content = messages[-1]['content']
        if "rm -rf /" in user_content:
            return '{"approved": false, "feedback": "Too dangerous"}'
        return '{"approved": true, "feedback": "Safe"}'

def test_critic_approval():
    llm = MockLLM()
    critic = CriticAgent(llm)
    
    action = {"command": "ls -la", "reasoning": "Check files"}
    result = critic.review_action(action, "goal", "context")
    
    assert result['approved'] is True

def test_critic_rejection():
    llm = MockLLM()
    critic = CriticAgent(llm)
    
    action = {"command": "rm -rf /", "reasoning": "Delete everything"}
    result = critic.review_action(action, "goal", "context")
    
    assert result['approved'] is False
    assert "dangerous" in result['feedback']
    
def test_critic_json_parsing():
    # Test with cleaner JSON
    mock_llm = MagicMock()
    mock_llm.send_message.return_value = '{"approved": true}'
    critic = CriticAgent(mock_llm)
    result = critic.review_action({}, "", "")
    assert result['approved'] is True
