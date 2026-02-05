"""
Command execution engine for running shell commands.
Handles subprocess management, timeouts, and output capture.
Cross-platform support for Windows and Unix.
"""
import subprocess
import time
import platform
from dataclasses import dataclass
from typing import Optional, Dict
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
    
    # Platform detection
    IS_WINDOWS = platform.system() == "Windows"
    
    def __init__(self, shell: Optional[str] = None):
        """
        Initialize the command executor.
        
        Args:
            shell: Shell to use for command execution. Auto-detected if not specified.
                   Unix: bash, sh, zsh
                   Windows: cmd, powershell
        """
        self.shell = shell or self._detect_shell()
        self.running_processes: Dict[int, subprocess.Popen] = {}
        self.cwd: str = "."  # Track current working directory
    
    def _detect_shell(self) -> str:
        """Detect the appropriate shell for the current platform."""
        if self.IS_WINDOWS:
            # Prefer PowerShell on Windows, fallback to cmd
            try:
                result = subprocess.run(
                    ["powershell", "-Command", "echo test"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    return "powershell"
            except Exception:
                pass
            return "cmd"
        else:
            # Prefer bash on Unix, fallback to sh
            import shutil
            if shutil.which("bash"):
                return "bash"
            return "sh"
    
    def _get_executable(self, shell_cmd: str) -> Optional[str]:
        """Get the executable path for the given shell (cross-platform)."""
        if self.IS_WINDOWS:
            # Windows doesn't need explicit executable for shell=True
            return None
        else:
            # Unix systems need explicit executable path
            import shutil
            executable = shutil.which(shell_cmd)
            if executable:
                return executable
            # Fallback to common paths
            common_paths = [f"/bin/{shell_cmd}", f"/usr/bin/{shell_cmd}"]
            for path in common_paths:
                if subprocess.run(["test", "-x", path], capture_output=True).returncode == 0:
                    return path
            return None
    
    def cleanup_finished_processes(self) -> int:
        """
        Clean up finished async processes from tracking dict.
        
        Returns:
            Number of processes cleaned up
        """
        finished = []
        for pid, process in self.running_processes.items():
            if process.poll() is not None:  # Process has finished
                finished.append(pid)
        
        for pid in finished:
            del self.running_processes[pid]
        
        return len(finished)
    
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
        
        self.cleanup_finished_processes()
        
        start_time = time.time()
        timed_out = False
        
        # Determine working directory (prioritize arg, then state)
        current_cwd = cwd or self.cwd
        
        # Append CWD capture to command to track directory changes
        marker = "__CWD__:"
        original_command = command
        
        # Construct command with CWD capture based on shell
        if self.shell == "powershell":
            command = f"{command}; Write-Output '{marker}'$PWD"
        elif self.shell == "cmd":
            command = f"{command} & echo {marker}%CD%"
        else: # bash, sh
            command = f"{command}; echo '{marker}'$PWD"
            
        # Inject sudo -v for Linux if needed (keeps the logic we just added)
        if not self.IS_WINDOWS and "sudo" in command and Config.SUDO_PASSWORD:
             # Logic is complex with appended CWD. 
             # We want: echo pass | sudo -v && (command; echo CWD)
             # The previous logic prepended to 'command'.
             # Let's apply sudo logic to original_command first, then append CWD?
             pass # Logic handled below cleaner
        
        # handling sudo + persistent CWD
        if not self.IS_WINDOWS and "sudo" in original_command and Config.SUDO_PASSWORD:
            pass_str = Config.SUDO_PASSWORD.strip()
            # echo pass | sudo -S -v && (original_command; echo marker$PWD)
            # Use parentheses to ensure CWD capture happens even if command fails? 
            # Or just use semicolon.
            # safe_cmd: echo pass | sudo -S -v && { original_command; echo marker$PWD; }
            # But { } requires bash.
            command = f"echo '{pass_str}' | sudo -S -v && {command}"
        
        try:
            # Get cross-platform executable path
            executable = self._get_executable(shell_cmd)
            
            # Execute command
            process = subprocess.Popen(
                command,
                shell=True,
                executable=executable,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=current_cwd,
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
            
            # Extract new CWD from output
            if marker in stdout:
                parts = stdout.split(marker)
                # The marker + path should be at the end
                if len(parts) >= 2:
                    potential_cwd = parts[-1].strip()
                    # Validate it's a path
                    import os
                    if os.path.exists(potential_cwd):
                        self.cwd = potential_cwd
                    
                    # Remove the marker line from stdout for clean logging
                    # Reconstruct stdout without the last part
                    stdout = "".join(parts[:-1]).strip()
            
            execution_time = time.time() - start_time
            return_code = process.returncode
            
            # Truncate large outputs
            stdout = self._truncate_output(stdout)
            stderr = self._truncate_output(stderr)
            
            return ExecutionResult(
                command=original_command, # Log the original command
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
        executable = self._get_executable(shell_cmd)
        
        process = subprocess.Popen(
            command,
            shell=True,
            executable=executable,
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
        Check if sudo/elevated privileges are available on the system.
        
        Returns:
            True if sudo is available (Unix) or running as admin (Windows)
        """
        if self.IS_WINDOWS:
            # Check if running as administrator on Windows
            try:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            except Exception:
                return False
        else:
            # Check if sudo is available on Unix
            result = self.execute("which sudo", timeout=5)
            return result.success and result.stdout.strip() != ""

