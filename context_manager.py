"""
Context manager for maintaining agent state and conversation history.
Integrates with long-term memory for relevant context retrieval.
"""
import json
import time
import tiktoken
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from config import Config
from memory_system import LongTermMemory
from utils.logger import logger


class ContextManager:
    """
    Manages conversation context and agent state.
    Optimizes context window and retrieves relevant memories.
    """
    
    def __init__(self, memory: LongTermMemory):
        """
        Initialize context manager.
        
        Args:
            memory: Long-term memory system
        """
        self.memory = memory
        self.conversation_history: List[Dict[str, str]] = []
        self.execution_history: List[Dict] = []
        self.state_file = Config.STATE_DIR / "agent_state.json"
        
        # Token counter for managing context window
        try:
            self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        except:
            self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def add_message(self, role: str, content: str):
        """
        Add a message to conversation history.
        
        Args:
            role: Role (system, user, assistant)
            content: Message content
        """
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_execution(self, execution: Dict):
        """
        Add an execution record to history.
        
        Args:
            execution: Dict with command, result, success
        """
        execution['timestamp'] = datetime.now().isoformat()
        self.execution_history.append(execution)
        
        # Store in long-term memory ONLY if there is a specific learning
        # This prevents trivial commands (ls, cd) from generating expensive embeddings
        if execution.get('learning') and str(execution.get('learning')).strip():
            self.memory.store_experience(
                {
                    "command": execution.get('command', ''),
                    "success": str(execution.get('success', False)),
                    "output": execution.get('output', '')[:500],  # Truncate
                    "learning": execution.get('learning', ''),
                },
                category="experience"
            )
    
    def get_context_for_llm(
        self,
        max_tokens: Optional[int] = None,
        include_memories: bool = True,
        query: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Get optimized context for LLM within token limit.
        
        Args:
            max_tokens: Maximum tokens to use (default from config)
            include_memories: Whether to include relevant memories
            query: Query for retrieving relevant memories
            
        Returns:
            List of messages for LLM
        """
        max_tokens = max_tokens or Config.CONTEXT_MAX_TOKENS
        
        messages = []
        
        # Always include recent conversation history
        recent_messages = self._get_recent_within_budget(
            self.conversation_history,
            max_tokens - 1000  # Reserve tokens for memories
        )
        messages.extend(recent_messages)
        
        # Add relevant memories if requested
        if include_memories and query:
            memories = self.memory.recall_similar(query, limit=3)
            if memories:
                memory_text = self._format_memories(memories)
                messages.append({
                    "role": "system",
                    "content": f"Relevant past experiences:\n{memory_text}"
                })
        
        return messages
    
    def get_recent_results(self, count: int = 5) -> List[Dict]:
        """
        Get recent execution results.
        
        Args:
            count: Number of recent results to return
            
        Returns:
            List of recent execution dicts
        """
        return self.execution_history[-count:] if self.execution_history else []
    
    def get_relevant_memories(self, query: str, limit: int = 3) -> List[Dict]:
        """
        Retrieve relevant memories for a query.
        
        Args:
            query: Query text
            limit: Maximum number of memories
            
        Returns:
            List of relevant memory entries
        """
        start_time = time.time()
        results = self.memory.recall_similar(query, limit=limit)
        duration = time.time() - start_time
        if duration > 0.5:
             logger.log_info(f"[bold yellow][MEMORY][/bold yellow] Retrieval took {duration:.2f}s")
        return results
    
    def get_scratchpad_content(self) -> str:
        """
        Get the current content of the scratchpad.
        Creates file if it doesn't exist.
        """
        path = Config.SCRATCHPAD_FILE
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Scratchpad\n\nUse this space for notes, todo lists, and temporary variables.", encoding='utf-8')
        
        try:
            return path.read_text(encoding='utf-8')
        except Exception as e:
            logger.log_error(e, "Failed to read scratchpad")
            return ""
    
    def save_state(self, additional_data: Optional[Dict] = None):
        """
        Save current state to disk.
        
        Args:
            additional_data: Additional data to save
        """
        state = {
            "timestamp": datetime.now().isoformat(),
            "conversation_history": self.conversation_history[-50:],  # Last 50
            "execution_history": self.execution_history[-100:],  # Last 100
            "memory_stats": self.memory.get_statistics(),
        }
        
        if additional_data:
            state.update(additional_data)
        
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.log_debug(f"State saved to {self.state_file}")
    
    def load_state(self) -> Optional[Dict]:
        """
        Load state from disk.
        
        Returns:
            Loaded state dict or None
        """
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            self.conversation_history = state.get('conversation_history', [])
            self.execution_history = state.get('execution_history', [])
            
            logger.log_debug("State loaded from disk")
            return state
        
        return None
    
    def _get_recent_within_budget(
        self,
        messages: List[Dict],
        max_tokens: int
    ) -> List[Dict[str, str]]:
        """Get recent messages that fit within token budget."""
        result = []
        current_tokens = 0
        
        # Process in reverse to get most recent first
        for msg in reversed(messages):
            msg_tokens = self._count_tokens(msg.get('content', ''))
            if current_tokens + msg_tokens > max_tokens:
                break
            result.insert(0, {"role": msg['role'], "content": msg['content']})
            current_tokens += msg_tokens
        
        return result
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        try:
            return len(self.encoding.encode(text))
        except:
            # Fallback: rough estimate
            return len(text) // 4
    
    def _format_memories(self, memories: List[Dict]) -> str:
        """Format memories for inclusion in context."""
        formatted = []
        for i, mem in enumerate(memories, 1):
            content = mem.get('content', '')
            metadata = mem.get('metadata', {})
            formatted.append(f"{i}. {content}")
            if metadata.get('success'):
                formatted.append(f"   Result: Success")
        
        return "\n".join(formatted)
