import pytest
from utils.logger import AgentLogger, logger
import json

def test_logger_singleton():
    """Test that logger is a singleton."""
    logger1 = AgentLogger()
    logger2 = AgentLogger()
    assert logger1 is logger2
    assert logger1 is logger

def test_sensitive_redaction():
    """Test that sensitive data is properly redacted."""
    agent_logger = AgentLogger()
    
    test_cases = [
        # OpenRouter Key
        ("API Key: sk-or-v1-abcdef123456", "API Key: [REDACTED_OPENROUTER_KEY]"),
        # OpenAI Key
        ("Key: sk-1234567890abcdef", "Key: [REDACTED_API_KEY]"),
        # Generic API keys
        ('api_key="12345"', 'api_key=[REDACTED]'),
        ("api-key: 'secret'", "api-key: [REDACTED]"),
        # Password
        ('password = "secure123"', 'password = [REDACTED]'),
        # Bearer token
        ("Authorization: Bearer xyz.123.abc", "Authorization: Bearer [REDACTED]"),
        # No change needed
        ("Hello world", "Hello world"),
    ]
    
    for input_text, expected in test_cases:
        assert agent_logger._redact_sensitive(input_text) == expected

def test_logger_initialization():
    """Test lazy initialization."""
    # This assumes test is running first or we mock things
    # But fundamentally just check attributes exist
    assert hasattr(logger, 'log_llm_request')
    assert hasattr(logger, 'log_llm_response')
    assert hasattr(logger, 'log_command_execution')
    assert hasattr(logger, 'log_error')
