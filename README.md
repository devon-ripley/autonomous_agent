# Autonomous Agent System

An experimental autonomous agent with unrestricted terminal access, powered by OpenRouter AI and equipped with long-term memory.

## Features

- **Cross-Platform Support**: Works on Windows (PowerShell) and Linux (Bash)
- **Safe Execution**: **Critic Agent** reviews every command for danger (e.g., `rm -rf /`) before execution
- **Dynamic Tool Registry**: Self-evolving architecture that auto-discovers Python tools in `tools/`
- **Web Capabilities**: Built-in **Web Search** and **Web Scraper** to solve errors autonomously
- **Smart Analysis**: Tools for structure mapping (`list_structure`) and surgical file reading (`read_file`)
- **Robust Protocol**: Uses strict JSON communication to eliminate syntax errors
- **Stateful Shell**: Persists `cd` changes and session state just like a real terminal
- **Long-Term Memory**: ChromaDB-powered semantic search for learning from past experiences
- **Continuous Mode**: AI automatically generates new goals after completing current ones
- **Scratchpad System**: Persistent markdown notebook (`data/scratchpad.md`) for context tracking

## Architecture

- **Multi-Agent Brain**:
    - **Planner**: Decomposes high-level goals
    - **Executor**: Converting intent into shell commands
    - **Critic**: Safety filter and code reviewer
- **OpenRouter Integration**: LLM-powered decision making
- **Vector Database**: Semantic memory with ChromaDB
- **Tool Registry**: Dynamic plugin system for agent capabilities

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

## Docker Setup (Recommended)

For a safe, isolated environment, run the agent in Docker:

```bash
# Build and start
docker compose up --build -d

# Attach to the container output (to see logs)
docker compose logs -f

# OR to interact with shell (if using tty)
docker attach auto_agent
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
