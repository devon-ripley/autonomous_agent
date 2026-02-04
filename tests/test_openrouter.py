import pytest
import os
from unittest.mock import MagicMock, patch
from openrouter_client import OpenRouterClient
from config import Config

def test_client_init_skips_without_key():
    """Test that client warns or works without key (depending on validation)."""
    # If we unset the key, it should still init but maybe fail on send
    original_key = Config.OPENROUTER_API_KEY
    Config.OPENROUTER_API_KEY = ""
    
    try:
        # Just init shouldn't fail if we don't validate in init
        client = OpenRouterClient()
        # We can't check client.api_key directly as it's not stored
        assert client.client is not None
    finally:
        Config.OPENROUTER_API_KEY = original_key

@patch('openrouter_client.OpenAI')
def test_send_message_mock(mock_openai):
    """Test sending a message with mocked OpenAI client."""
    # Setup mock response
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = "Test response"
    mock_completion.model = "test-model"
    
    # Mock the usage object and its model_dump method
    mock_usage = MagicMock()
    mock_usage.total_tokens = 15
    mock_usage.prompt_tokens = 10
    mock_usage.completion_tokens = 5
    mock_usage.model_dump.return_value = {
        "total_tokens": 15,
        "prompt_tokens": 10,
        "completion_tokens": 5
    }
    mock_completion.usage = mock_usage
    
    # Configure the mock client
    mock_instance = mock_openai.return_value
    mock_instance.chat.completions.create.return_value = mock_completion
    
    # Run test
    client = OpenRouterClient()
    response = client.send_message([{"role": "user", "content": "hi"}])
    
    assert response['content'] == "Test response"
    assert response['model'] == "test-model"
    # Now this should work because we mocked model_dump()
    assert response['usage']['total_tokens'] == 15
    
    # Verify call
    mock_instance.chat.completions.create.assert_called_once()

def test_rate_limiting_logic():
    """Test that rate limiting tracking works."""
    client = OpenRouterClient()
    assert hasattr(client, '_last_request_time')
    assert hasattr(client, '_apply_rate_limit')
