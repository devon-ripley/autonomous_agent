"""
Command execution engine for running shell commands.
Handles subprocess management, timeouts, and output capture.
"""
import subprocess
import time
from dataclasses import dataclass
from typing import Optional
from config import Config


@dataclass
class ExecutionResult:
    """Result of a command execution."""
    command: str
    stdout: str
    stderr: str
    return_code: int
    execution_time: float
    success: bool
    timed_out: bool = False


class CommandExecutor:
    """Executes shell commands with timeout and output capture."""
    
    def __init__(self, shell: str = "bash"):
        """
        Initialize the command executor.
        
        Args:
            shell: Shell to use for command execution (bash, sh, etc.)
        """
        self.shell = shell
        self.running_processes = {}
    
    def _truncate_output(self, output: str) -> str:
        """Truncate output to configured max size."""
        max_size = Config.MAX_OUTPUT_SIZE
        if len(output) > max_size:
            truncated_msg = f"\n\n[OUTPUT TRUNCATED - {len(output) - max_size} chars omitted]"
            return output[:max_size] + truncated_msg
        return output
    
    def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        shell: Optional[str] = None,
        cwd: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Execute a shell command and return the result.
        
        Args:
            command: Command to execute
            timeout: Timeout in seconds (default from config)
            shell: Override default shell
            cwd: Working directory for command
            
        Returns:
            ExecutionResult with command output and status
        """
        timeout = timeout or Config.COMMAND_TIMEOUT
        shell_cmd = shell or self.shell
        
        start_time = time.time()
        timed_out = False
        
        try:
            # Execute command
            process = subprocess.Popen(
                command,
                shell=True,
                executable=f"/bin/{shell_cmd}" if shell_cmd else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd,
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                # Kill the process if it times out
                process.kill()
                stdout, stderr = process.communicate()
                timed_out = True
                stderr = f"[TIMEOUT after {timeout}s]\n{stderr}"
            
            execution_time = time.time() - start_time
            return_code = process.returncode
            
            # Truncate large outputs
            stdout = self._truncate_output(stdout)
            stderr = self._truncate_output(stderr)
            
            return ExecutionResult(
                command=command,
                stdout=stdout,
                stderr=stderr,
                return_code=return_code,
                execution_time=execution_time,
                success=(return_code == 0 and not timed_out),
                timed_out=timed_out,
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                command=command,
                stdout="",
                stderr=f"Execution error: {str(e)}",
                return_code=-1,
                execution_time=execution_time,
                success=False,
            )
    
    def execute_async(self, command: str, shell: Optional[str] = None) -> int:
        """
        Execute a command asynchronously and return process ID.
        
        Args:
            command: Command to execute
            shell: Override default shell
            
        Returns:
            Process ID
        """
        shell_cmd = shell or self.shell
        
        process = subprocess.Popen(
            command,
            shell=True,
            executable=f"/bin/{shell_cmd}" if shell_cmd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        
        pid = process.pid
        self.running_processes[pid] = process
        return pid
    
    def kill_process(self, process_id: int) -> bool:
        """
        Kill a running process by ID.
        
        Args:
            process_id: Process ID to kill
            
        Returns:
            True if process was killed, False if not found
        """
        if process_id in self.running_processes:
            process = self.running_processes[process_id]
            process.kill()
            del self.running_processes[process_id]
            return True
        return False
    
    def check_sudo_available(self) -> bool:
        """
        Check if sudo is available on the system.
        
        Returns:
            True if sudo is available
        """
        result = self.execute("which sudo", timeout=5)
        return result.success and result.stdout.strip() != ""
