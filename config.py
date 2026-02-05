"""
Configuration management for autonomous agent.
Loads settings from environment variables and provides typed access.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def _safe_int(value: str, default: int) -> int:
    """Safely parse an integer from string, returning default on failure."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _safe_float(value: str, default: float) -> float:
    """Safely parse a float from string, returning default on failure."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


class Config:
    """Central configuration for the autonomous agent."""
    
    # API Configuration
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    
    # Agent Configuration
    INITIAL_GOAL: str = os.getenv("INITIAL_GOAL", "Build yourself into a personal assistant with useful tools")
    COMMAND_TIMEOUT: int = _safe_int(os.getenv("COMMAND_TIMEOUT", "300"), 300)
    MAX_RETRIES: int = _safe_int(os.getenv("MAX_RETRIES", "3"), 3)
    
    # Continuous Mode - Agent generates new goals after completing current one
    CONTINUOUS_MODE: bool = os.getenv("CONTINUOUS_MODE", "true").lower() == "true"
    
    # Rate Limiting
    RATE_LIMIT_SECONDS: float = _safe_float(os.getenv("RATE_LIMIT_SECONDS", "2.0"), 2.0)
    
    # Output Limits
    MAX_OUTPUT_SIZE: int = _safe_int(os.getenv("MAX_OUTPUT_SIZE", "10000"), 10000)  # Max chars to keep
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Directories
    BASE_DIR: Path = Path(__file__).parent
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = DATA_DIR / "logs"
    STATE_DIR: Path = DATA_DIR / "state"
    PLANS_DIR: Path = DATA_DIR / "plans"
    MEMORY_DIR: Path = DATA_DIR / "memory"
    VECTOR_DB_DIR: Path = MEMORY_DIR / "vector_db"
    SUMMARIES_DIR: Path = MEMORY_DIR / "summaries"
    SCRATCHPAD_FILE: Path = DATA_DIR / "scratchpad.md"
    
    # Auth
    SUDO_PASSWORD: str = os.getenv("SUDO_PASSWORD", "")
    
    # Memory Configuration
    MEMORY_TOP_K: int = _safe_int(os.getenv("MEMORY_TOP_K", "5"), 5)
    CONTEXT_MAX_TOKENS: int = _safe_int(os.getenv("CONTEXT_MAX_TOKENS", "8000"), 8000)
    
    # LLM Configuration
    TEMPERATURE: float = _safe_float(os.getenv("TEMPERATURE", "0.7"), 0.7)
    MAX_TOKENS: int = _safe_int(os.getenv("MAX_TOKENS", "4000"), 4000)
    
    # Terminal User Credentials (for sudo access)
    TERMINAL_USERNAME: str = os.getenv("TERMINAL_USERNAME", "")
    TERMINAL_PASSWORD: str = os.getenv("TERMINAL_PASSWORD", "")
    
    # Validation state
    _validated: bool = False
    
    @classmethod
    def ensure_directories(cls):
        """Create all necessary directories if they don't exist."""
        for dir_path in [
            cls.DATA_DIR,
            cls.LOGS_DIR,
            cls.STATE_DIR,
            cls.PLANS_DIR,
            cls.MEMORY_DIR,
            cls.VECTOR_DB_DIR,
            cls.SUMMARIES_DIR,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate(cls, require_api_key: bool = True):
        """
        Validate that required configuration is present.
        
        Args:
            require_api_key: Whether to require API key (False for tests/help)
        """
        if cls._validated:
            return True
            
        if require_api_key and not cls.OPENROUTER_API_KEY:
            raise ValueError(
                "OPENROUTER_API_KEY not found in environment. "
                "Please copy .env.example to .env and add your API key."
            )
        
        cls.ensure_directories()
        cls._validated = True
        return True
    
    @classmethod
    def is_valid(cls) -> bool:
        """Check if config is valid without raising exceptions."""
        return bool(cls.OPENROUTER_API_KEY)


# Don't validate on import - defer to startup
# This allows --help and tests to work without API key
