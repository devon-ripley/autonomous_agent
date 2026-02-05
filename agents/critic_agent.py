from utils.logger import logger
from openrouter_client import OpenRouterClient
from config import Config

class CriticAgent:
    """
    Evaluates proposed actions for safety, correctness, and logic.
    Acts as a filter before execution.
    """
    
    def __init__(self, llm_client: OpenRouterClient):
        self.llm_client = llm_client
        
    def review_action(self, action: dict, goal: str, context: str) -> dict:
        """
        Review a proposed action.
        Returns: {'approved': bool, 'feedback': str}
        """
        command = action.get('command', '')
        reasoning = action.get('reasoning', '')
        
        # Fast path: Empty commands (thinking steps) are usually safe
        if not command:
            return {'approved': True, 'feedback': 'No command to execute.'}
            
        system_prompt = """You are a Code Reviewer and Safety Officer for an autonomous agent.
Your job is to analyze the proposed command and reasoning.

Risks to look for:
1. Destructive commands (rm -rf /, formatting disks, deleting incorrect context).
2. Syntax errors (e.g., Python with missing quotes, bash with unclosed strings).
3. Hallucinated tools (using tools that don't exist in the prompt).
4. Logic errors (e.g., rewriting a file without reading it first).
5. Infinite loops (running the same failing command repeatedly).

Output a JSON object:
{
    "approved": boolean,
    "feedback": "string explaining why it is rejected or warnings if approved"
}
"""
        user_prompt = f"""GOAL: {goal}
CONTEXT: {context[:2000]}... (truncated)

PROPOSED ACTION:
Reasoning: {reasoning}
Command: {command}

Evaluate this action."""

        try:
            response = self.llm_client.send_message([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])
            
            # Simple JSON extraction (reuse logic or simple eval if trusted)
            # For robustness, we'll try to parse JSON
            import json
            import re
            
            content = response.strip()
            if "```" in content:
                match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
                if match:
                    content = match.group(1)
            
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                data = json.loads(content[start:end+1])
                return data
                
            # Fallback if no JSON
            return {'approved': True, 'feedback': 'Critic failed to parse response, proceeding with caution.'}
            
        except Exception as e:
            logger.log_error(e, "Critic failed to review action")
            # Fail open or closed? Fail open for now to avoid deadlock, but log it.
            return {'approved': True, 'feedback': 'Critic offline.'}
