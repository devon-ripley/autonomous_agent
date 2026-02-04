import pytest
import sys
import subprocess
from executor import CommandExecutor, ExecutionResult

def test_executor_init():
    """Test executor initialization and shell detection."""
    executor = CommandExecutor()
    assert executor.shell is not None
    assert executor.shell in ["bash", "sh", "cmd", "powershell", "zsh"]
    
    # Test specific shell override
    custom_executor = CommandExecutor(shell="custom_shell")
    assert custom_executor.shell == "custom_shell"

def test_shell_detection_logic():
    """Test the logic of shell detection."""
    executor = CommandExecutor()
    
    if sys.platform == "win32":
        # On Windows, should be powershell or cmd
        assert executor._detect_shell() in ["powershell", "cmd"]
        assert executor.IS_WINDOWS is True
    else:
        # On Unix, should be bash or sh
        assert executor._detect_shell() in ["bash", "sh", "zsh"]
        assert executor.IS_WINDOWS is False

def test_command_execution():
    """Test basic command execution."""
    executor = CommandExecutor()
    
    # Simple echo command works cross-platform (mostly through shell=True)
    if sys.platform == "win32":
        cmd = "echo 'test execution'"
    else:
        cmd = "echo 'test execution'"
        
    result = executor.execute(cmd, timeout=5)
    
    assert result.success
    assert result.return_code == 0
    assert "test execution" in result.stdout

def test_async_execution_and_cleanup():
    """Test async execution and cleanup."""
    executor = CommandExecutor()
    
    # Start a process that sleeps briefly
    if sys.platform == "win32":
        cmd = "powershell -Command Start-Sleep -Seconds 1"
    else:
        cmd = "sleep 1"
        
    pid = executor.execute_async(cmd)
    assert pid > 0
    assert pid in executor.running_processes
    
    # Wait for it to likely finish
    import time
    time.sleep(1.5)
    
    # Cleanup
    cleaned_count = executor.cleanup_finished_processes()
    assert cleaned_count >= 1
    assert pid not in executor.running_processes

def test_output_truncation():
    """Test that large output is truncated."""
    executor = CommandExecutor()
    
    # Create a long string
    long_output = "a" * 15000
    truncated = executor._truncate_output(long_output)
    
    # Should be shorter than original if it exceeded limit (default 10000)
    from config import Config
    if len(long_output) > Config.MAX_OUTPUT_SIZE:
        assert len(truncated) < len(long_output)
        assert "OUTPUT TRUNCATED" in truncated
