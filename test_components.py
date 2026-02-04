"""
Test script to verify autonomous agent components.
Run this to test basic functionality before running the full agent.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


def test_config():
    """Test configuration system."""
    print("\n=== Testing Configuration ===")
    try:
        from config import Config
        
        # Test that we can import without validation
        assert hasattr(Config, 'OPENROUTER_API_KEY'), "Config missing API key attr"
        assert hasattr(Config, 'CONTINUOUS_MODE'), "Config missing continuous mode"
        assert hasattr(Config, 'RATE_LIMIT_SECONDS'), "Config missing rate limit"
        assert hasattr(Config, 'MAX_OUTPUT_SIZE'), "Config missing output limit"
        
        # Ensure directories
        Config.ensure_directories()
        assert Config.DATA_DIR.exists(), "Data directory not created"
        
        print("✓ Configuration loaded successfully")
        print(f"  Model: {Config.OPENROUTER_MODEL}")
        print(f"  Continuous Mode: {Config.CONTINUOUS_MODE}")
        print(f"  Rate Limit: {Config.RATE_LIMIT_SECONDS}s")
        print(f"  Data directory: {Config.DATA_DIR}")
        
        # Check if API key is set
        if Config.OPENROUTER_API_KEY:
            print("  ✓ API key is set")
            return True
        else:
            print("  ⚠ API key not set (set in .env)")
            return "warning"
            
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


def test_executor():
    """Test command executor."""
    print("\n=== Testing Command Executor ===")
    try:
        from config import Config
        Config.ensure_directories()
        
        from executor import CommandExecutor
        executor = CommandExecutor()
        
        # Test simple command
        result = executor.execute("echo 'Hello from autonomous agent'", timeout=5)
        assert result.success, "Command execution failed"
        assert "Hello from autonomous agent" in result.stdout, "Unexpected output"
        
        # Test output truncation
        assert hasattr(executor, '_truncate_output'), "Missing truncation method"
        
        print("✓ Command executor working")
        print(f"  Execution time: {result.execution_time:.3f}s")
        return True
    except Exception as e:
        print(f"✗ Executor test failed: {e}")
        return False


def test_llm_client():
    """Test OpenRouter client."""
    print("\n=== Testing OpenRouter Client ===")
    try:
        from config import Config
        
        if not Config.OPENROUTER_API_KEY:
            print("⚠ Skipped - OPENROUTER_API_KEY not set")
            return "skipped"
        
        Config.validate()
        
        from openrouter_client import OpenRouterClient
        client = OpenRouterClient()
        
        # Verify rate limiting is present
        assert hasattr(client, '_apply_rate_limit'), "Missing rate limit method"
        assert hasattr(client, '_last_request_time'), "Missing rate limit tracking"
        
        messages = [
            {"role": "user", "content": "Reply with just the word 'SUCCESS' and nothing else."}
        ]
        
        response = client.send_message(messages)
        assert response['content'], "No response from LLM"
        
        print("✓ OpenRouter client working")
        print(f"  Model: {response.get('model', 'unknown')}")
        print(f"  Response: {response['content'][:100]}")
        print(f"  Rate limiting: enabled ({Config.RATE_LIMIT_SECONDS}s)")
        return True
    except Exception as e:
        print(f"✗ LLM client test failed: {e}")
        print("  Make sure OPENROUTER_API_KEY is set in .env")
        return False


def test_memory():
    """Test long-term memory system."""
    print("\n=== Testing Long-Term Memory ===")
    try:
        from config import Config
        Config.ensure_directories()
        
        from memory_system import LongTermMemory
        memory = LongTermMemory()
        
        # Store a test experience
        memory.store_experience({
            "command": "echo 'test'",
            "success": "True",
            "output": "test",
        }, category="experience")
        
        # Try to recall it
        results = memory.recall_similar("echo test", limit=1)
        
        # Test error solutions method
        assert hasattr(memory, 'get_error_solutions'), "Missing error solutions method"
        
        stats = memory.get_statistics()
        print("✓ Memory system working")
        print(f"  Total memories: {stats['total']}")
        print(f"  Experiences: {stats['experiences']}")
        return True
    except Exception as e:
        print(f"✗ Memory test failed: {e}")
        return False


def test_logger():
    """Test logging system."""
    print("\n=== Testing Logger ===")
    try:
        from utils.logger import logger, AgentLogger
        
        # Test lazy initialization
        assert AgentLogger._instance is not None, "Singleton not created"
        
        # Test that logger doesn't fail before directories exist
        from config import Config
        Config.ensure_directories()
        
        # Test new logging methods
        assert hasattr(logger, 'log_new_goal'), "Missing log_new_goal method"
        assert hasattr(logger, 'log_learning'), "Missing log_learning method"
        
        logger.log_info("Test message - component test")
        
        print("✓ Logger working")
        print("  Lazy initialization: enabled")
        print("  New goal logging: available")
        print("  Learning logging: available")
        return True
    except Exception as e:
        print(f"✗ Logger test failed: {e}")
        return False


def test_response_parsing():
    """Test multi-line response parsing."""
    print("\n=== Testing Response Parsing ===")
    try:
        from autonomous_agent import AutonomousAgent
        
        # Create a mock agent just to test parsing
        # This won't actually initialize the LLM client etc without validation
        
        # Test the regex patterns directly
        import re
        
        test_response = """REASONING: This is a multi-line
reasoning that spans
multiple lines.
COMMAND: echo "hello world" && echo "goodbye"
EXPECTED: It should print both messages
on separate lines.
LEARNING: Multi-line commands work well
when properly escaped."""
        
        patterns = {
            'reasoning': r'REASONING:\s*(.*?)(?=\n(?:COMMAND|EXPECTED|LEARNING):|$)',
            'command': r'COMMAND:\s*(.*?)(?=\n(?:REASONING|EXPECTED|LEARNING):|$)',
            'expected': r'EXPECTED:\s*(.*?)(?=\n(?:REASONING|COMMAND|LEARNING):|$)',
            'learning': r'LEARNING:\s*(.*?)(?=\n(?:REASONING|COMMAND|EXPECTED):|$)',
        }
        
        result = {}
        for field, pattern in patterns.items():
            match = re.search(pattern, test_response, re.DOTALL | re.IGNORECASE)
            if match:
                result[field] = match.group(1).strip()
        
        assert 'reasoning' in result, "Failed to parse reasoning"
        assert 'multiple lines' in result['reasoning'], "Multi-line not captured"
        assert 'command' in result, "Failed to parse command"
        assert 'learning' in result, "Failed to parse learning"
        
        print("✓ Response parsing working")
        print(f"  Parsed {len(result)} fields")
        print(f"  Multi-line support: enabled")
        return True
    except Exception as e:
        print(f"✗ Response parsing test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("AUTONOMOUS AGENT - COMPONENT TESTS (v2.0)")
    print("="*60)
    
    results = {
        "Config": test_config(),
        "Logger": test_logger(),
        "Executor": test_executor(),
        "Response Parsing": test_response_parsing(),
        "Memory": test_memory(),
        "LLM Client": test_llm_client(),
    }
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for component, passed in results.items():
        if passed == True:
            status = "✓ PASS"
        elif passed == "warning":
            status = "⚠ WARN"
        elif passed == "skipped":
            status = "○ SKIP"
        else:
            status = "✗ FAIL"
            all_passed = False
        print(f"{component:20s} {status}")
    
    print("="*60)
    
    if all_passed:
        print("\n✓ All tests passed! Ready to run the autonomous agent.")
        print("\nNew features in this version:")
        print("  • Multi-line response parsing")
        print("  • Continuous mode with AI-generated goals")
        print("  • LLM-assisted error recovery")
        print("  • Learning storage to memory")
        print("  • Rate limiting")
        print("  • Output size limits")
        print("\nNext steps:")
        print("  1. Review .env configuration")
        print("  2. Run: python autonomous_agent.py --goal 'Your goal here'")
        print("  3. Use --no-continuous to disable continuous mode")
        return 0
    else:
        print("\n✗ Some tests failed. Please fix errors before running the agent.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
