# Autonomous Agent System

An experimental autonomous agent with unrestricted terminal access, powered by OpenRouter AI and equipped with long-term memory.

## Features

- **Cross-Platform Support**: Works on Windows (PowerShell) and Linux (Bash)
- **Unrestricted Terminal Access**: Execute any shell command autonomously
- **Multi-Step Planning**: Break down complex goals into executable steps
- **Long-Term Memory**: ChromaDB-powered semantic search for learning from past experiences
- **Continuous Mode**: AI automatically generates new goals after completing current ones
- **LLM-Assisted Error Recovery**: Ask LLM for fixes when commands fail
- **Learning Storage**: Captures and stores insights for future use
- **Scratchpad System**: Persistent markdown notebook (`data/scratchpad.md`) for maintaining short-term context
- **Error Recovery**: Automatic retry logic with past solution lookup
- **State Persistence**: Resume from previous sessions
- **Rate Limiting**: Configurable delay between API calls
- **Output Limits**: Prevents memory issues from large command outputs
- **Comprehensive Logging**: Audit trails, state logs, and error tracking

## Architecture

- **OpenRouter Integration**: LLM-powered decision making
- **Vector Database**: Semantic memory with ChromaDB
- **Modular Design**: Separate components for execution, planning, memory, and context

## Setup

1. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

2. **Configure Environment**:
```bash
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

3. **Run Tests**:
```bash
pytest
```

4. **Run the Agent**:
```bash
# Start with default goal (continuous mode enabled by default)
python autonomous_agent.py

# Custom goal
python autonomous_agent.py --goal "Set up a Python web server"

# Resume from previous session
python autonomous_agent.py --resume

# Disable continuous mode (stop after completing goal)
python autonomous_agent.py --no-continuous

# View memory statistics
python autonomous_agent.py --memory-stats

# Reset agent (clear all memory/logs)
python reset_agent.py
```

## Continuous Mode

When `CONTINUOUS_MODE=true` (default), the agent will:
1. Complete the initial goal
2. Ask the LLM to generate a new goal based on accomplishments
3. Create a new plan for the generated goal
4. Repeat indefinitely until stopped

The AI considers:
- What was just accomplished
- Current capabilities and stored memories
- Self-improvement opportunities
- Useful tools and automation

## Safety

⚠️ **CAUTION**: This agent has unrestricted terminal access. 

**Recommended Setup**:
- Run in isolated VM environment (Windows/Linux)
- Regular VM snapshots
- Monitor resource usage
- Do not use on production systems

## Configuration

Key environment variables (`.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | (required) | Your OpenRouter API key |
| `OPENROUTER_MODEL` | `deepseek/deepseek-chat` | Model to use |
| `INITIAL_GOAL` | Build useful tools | Default goal |
| `CONTINUOUS_MODE` | `true` | Generate new goals after completion |
| `RATE_LIMIT_SECONDS` | `2.0` | Delay between API calls |
| `MAX_OUTPUT_SIZE` | `10000` | Max chars to keep from command output |
| `COMMAND_TIMEOUT` | `300` | Command timeout (seconds) |
| `MAX_RETRIES` | `3` | Max retry attempts |

## License

Experimental project - use at your own risk.
