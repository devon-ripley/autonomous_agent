import pytest
from pathlib import Path
import os
from config import Config

def test_config_attributes():
    """Test that Config has all required attributes."""
    # Reset validation state
    Config._validated = False
    
    # Check default attributes
    assert hasattr(Config, 'OPENROUTER_API_KEY')
    assert hasattr(Config, 'CONTINUOUS_MODE')
    assert hasattr(Config, 'RATE_LIMIT_SECONDS')
    assert hasattr(Config, 'MAX_OUTPUT_SIZE')
    assert hasattr(Config, 'COMMAND_TIMEOUT')
    assert hasattr(Config, 'TERMINAL_USERNAME')
    assert hasattr(Config, 'TERMINAL_PASSWORD')

def test_directory_creation():
    """Test that ensure_directories creates required folders."""
    Config.ensure_directories()
    
    assert Config.DATA_DIR.exists()
    assert Config.LOGS_DIR.exists()
    assert Config.STATE_DIR.exists()
    assert Config.PLANS_DIR.exists()
    assert Config.MEMORY_DIR.exists()
    assert Config.VECTOR_DB_DIR.exists()
    assert Config.SUMMARIES_DIR.exists()

def test_safe_parsing():
    """Test safe integer and float parsing indirectly via Config values."""
    from config import _safe_int, _safe_float
    
    # Test helper functions directly
    assert _safe_int("123", 0) == 123
    assert _safe_int("invalid", 10) == 10
    
    assert _safe_float("1.5", 0.0) == 1.5
    assert _safe_float("invalid", 2.5) == 2.5

def test_api_key_validation():
    """Test validation logic."""
    # Reset
    Config._validated = False
    original_key = Config.OPENROUTER_API_KEY
    
    try:
        # Test missing key raises error if required
        Config.OPENROUTER_API_KEY = ""
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY not found"):
            Config.validate(require_api_key=True)
            
        # Test valid key passes
        Config.OPENROUTER_API_KEY = "sk-test-key"
        Config._validated = False
        assert Config.validate(require_api_key=True) is True
        
    finally:
        # Restore original
        Config.OPENROUTER_API_KEY = original_key
        Config._validated = False
