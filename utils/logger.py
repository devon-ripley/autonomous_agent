"""
Comprehensive logging system for the autonomous agent.
Provides structured logging with multiple outputs and log levels.
Uses lazy initialization to avoid side effects on import.
"""
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from rich.console import Console
from rich.logging import RichHandler


class AgentLogger:
    """Multi-level logging system for the autonomous agent."""
    
    _instance: Optional['AgentLogger'] = None
    _initialized: bool = False
    
    # Patterns to redact from logs (regex patterns)
    SENSITIVE_PATTERNS = [
        (r'(sk-or-v1-[a-zA-Z0-9]+)', '[REDACTED_OPENROUTER_KEY]'),  # OpenRouter keys
        (r'(sk-[a-zA-Z0-9]{10,})', '[REDACTED_API_KEY]'),  # OpenAI-style keys
        (r'(api[_-]?key["\s:=]+)["\']?([^"\'\s,}]+)', r'\1[REDACTED]'),  # Generic API keys
        (r'(password["\s:=]+)["\']?([^"\'\s,}]+)', r'\1[REDACTED]'),  # Passwords
        (r'(secret["\s:=]+)["\']?([^"\'\s,}]+)', r'\1[REDACTED]'),  # Secrets
        (r'(token["\s:=]+)["\']?([^"\'\s,}]+)', r'\1[REDACTED]'),  # Tokens
        (r'(bearer\s+)([a-zA-Z0-9._-]+)', r'\1[REDACTED]'),  # Bearer tokens
    ]
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern - only one logger instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, name: str = "agent"):
        """Initialize the logging system (lazy - only on first use)."""
        if AgentLogger._initialized:
            return
            
        self.name = name
        self.console = Console()
        self._loggers_created = False
        
        # Don't create loggers yet - wait until first use
        self.audit_logger = None
        self.state_logger = None
        self.error_logger = None
        self.debug_logger = None
        self.console_logger = None
    
    def _redact_sensitive(self, text: str) -> str:
        """Redact sensitive information from text before logging."""
        import re
        result = text
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result
    
    def _ensure_initialized(self):
        """Lazily initialize loggers on first use."""
        if self._loggers_created:
            return
        
        # Import config here to avoid circular imports
        from config import Config
        Config.ensure_directories()
        
        # Create loggers
        self.audit_logger = self._setup_logger("audit", Config.LOGS_DIR / "audit.log")
        self.state_logger = self._setup_logger("state", Config.LOGS_DIR / "state.log")
        self.error_logger = self._setup_logger("error", Config.LOGS_DIR / "error.log")
        self.debug_logger = self._setup_logger("debug", Config.LOGS_DIR / "debug.log")
        
        # Console logger with rich formatting
        self.console_logger = logging.getLogger("console")
        self.console_logger.setLevel(logging.INFO)
        if not self.console_logger.handlers:
            console_handler = RichHandler(console=self.console, rich_tracebacks=True)
            console_handler.setFormatter(logging.Formatter("%(message)s"))
            self.console_logger.addHandler(console_handler)
        
        self._loggers_created = True
    
    def _setup_logger(self, name: str, log_file: Path) -> logging.Logger:
        """Set up a logger with file handler."""
        from config import Config
        
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # Only add handler if not already present
        if not logger.handlers:
            handler = logging.FileHandler(log_file, encoding='utf-8')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def log_llm_request(self, messages: list, model: str):
        """Log an LLM request with sensitive data redacted."""
        self._ensure_initialized()
        self.audit_logger.info(f"LLM Request to {model}")
        # Redact sensitive data from messages before logging
        redacted_messages = self._redact_sensitive(json.dumps(messages, indent=2))
        self.audit_logger.debug(f"Messages: {redacted_messages}")
    
    def log_llm_response(self, response: str, usage: Dict = None):
        """Log an LLM response with sensitive data redacted."""
        self._ensure_initialized()
        self.audit_logger.info("LLM Response received")
        # Redact sensitive data from response before logging
        redacted_response = self._redact_sensitive(response)
        self.audit_logger.debug(f"Response: {redacted_response}")
        if usage:
            self.audit_logger.info(f"Token usage: {usage}")
    
    def log_command_execution(self, command: str):
        """Log command execution."""
        self._ensure_initialized()
        self.audit_logger.info(f"Executing command: {command}")
        self.console_logger.info(f"[bold cyan]→ Executing:[/bold cyan] {command}")
    
    def log_command_result(self, result: Any):
        """Log command execution result."""
        self._ensure_initialized()
        status = "✓ Success" if result.success else "✗ Failed"
        color = "green" if result.success else "red"
        
        self.audit_logger.info(
            f"Command result - Status: {status}, "
            f"Return Code: {result.return_code}, "
            f"Time: {result.execution_time:.2f}s"
        )
        self.audit_logger.debug(f"STDOUT: {result.stdout}")
        if result.stderr:
            self.audit_logger.debug(f"STDERR: {result.stderr}")
        
        self.console_logger.info(f"[bold {color}]{status}[/bold {color}] ({result.execution_time:.2f}s)")
        
        if not result.success:
            self.error_logger.error(
                f"Command failed: {result.command}\n"
                f"Return code: {result.return_code}\n"
                f"STDERR: {result.stderr}"
            )
    
    def log_plan_update(self, plan: Dict):
        """Log plan creation or update."""
        self._ensure_initialized()
        self.state_logger.info(f"Plan updated: {plan.get('goal', 'Unknown goal')}")
        self.state_logger.debug(f"Plan details: {json.dumps(plan, indent=2, default=str)}")
    
    def log_memory_operation(self, operation: str, details: str):
        """Log memory system operations."""
        self._ensure_initialized()
        self.state_logger.info(f"Memory {operation}: {details}")
    
    def log_error(self, error: Exception, context: str = ""):
        """Log an error with context."""
        self._ensure_initialized()
        self.error_logger.error(f"{context}: {str(error)}", exc_info=True)
        self.console_logger.error(f"[bold red]Error:[/bold red] {str(error)}")
    
    def log_info(self, message: str):
        """Log an informational message."""
        self._ensure_initialized()
        self.debug_logger.info(message)
        self.console_logger.info(message)
    
    def log_debug(self, message: str):
        """Log a debug message."""
        self._ensure_initialized()
        self.debug_logger.debug(message)
    
    def log_agent_start(self, goal: str):
        """Log agent startup."""
        self._ensure_initialized()
        msg = f"""
╔═══════════════════════════════════════════════════════════════╗
║           AUTONOMOUS AGENT STARTED                            ║
╚═══════════════════════════════════════════════════════════════╝
Goal: {goal}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.audit_logger.info("=" * 50)
        self.audit_logger.info("AGENT SESSION STARTED")
        self.audit_logger.info(f"Goal: {goal}")
        self.audit_logger.info("=" * 50)
        self.console_logger.info(f"[bold green]{msg}[/bold green]")
    
    def log_agent_stop(self, reason: str):
        """Log agent shutdown."""
        self._ensure_initialized()
        self.audit_logger.info("=" * 50)
        self.audit_logger.info(f"AGENT SESSION ENDED - Reason: {reason}")
        self.audit_logger.info("=" * 50)
        self.console_logger.info(f"[bold yellow]Agent stopped: {reason}[/bold yellow]")
    
    def log_new_goal(self, old_goal: str, new_goal: str):
        """Log when agent generates a new goal."""
        self._ensure_initialized()
        self.audit_logger.info(f"New goal generated")
        self.audit_logger.info(f"Old: {old_goal}")
        self.audit_logger.info(f"New: {new_goal}")
        self.console_logger.info(f"[bold magenta]🎯 New Goal:[/bold magenta] {new_goal}")
    
    def log_learning(self, learning: str):
        """Log a learning that was stored to memory."""
        self._ensure_initialized()
        self.state_logger.info(f"Learning stored: {learning}")
        self.console_logger.info(f"[bold blue]💡 Learned:[/bold blue] {learning[:100]}...")


def get_logger() -> AgentLogger:
    """Get the global logger instance (creates on first call)."""
    return AgentLogger()


# For backward compatibility - lazy singleton
logger = AgentLogger()
