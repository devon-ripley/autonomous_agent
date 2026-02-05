"""
Autonomous Agent - Main execution loop.
Orchestrates planning, execution, and learning in an autonomous loop.

Features:
- Multi-line LLM response parsing
- Proper resume from previous state
- Continuous mode with AI-generated goals
- LLM-assisted error recovery
- Learning storage to memory
"""
import argparse
import sys
import re
import time
import signal
from typing import Optional, Dict
from datetime import datetime

from config import Config
from openrouter_client import OpenRouterClient
from executor import CommandExecutor, ExecutionResult
from planner import Planner
from context_manager import ContextManager
from memory_system import LongTermMemory
from utils.logger import logger


class AutonomousAgent:
    """Main autonomous agent with unrestricted terminal access."""
    
    def __init__(self, goal: Optional[str] = None):
        """
        Initialize the autonomous agent.
        
        Args:
            goal: Initial goal for the agent
        """
        self.goal = goal or Config.INITIAL_GOAL
        self.running = False
        self.iteration_count = 0
        self.goals_completed = 0
        
        # Initialize components
        logger.log_info("Initializing autonomous agent...")
        
        self.llm_client = OpenRouterClient()
        self.executor = CommandExecutor()
        self.memory = LongTermMemory()
        self.context = ContextManager(self.memory)
        self.planner = Planner(self.llm_client)
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.log_info("Agent initialized successfully")
    
    def start(self, resume: bool = False):
        """
        Start the autonomous agent loop.
        
        Args:
            resume: Whether to resume from previous state
        """
        self.running = True
        logger.log_agent_start(self.goal)
        
        # Load previous state if resuming
        if resume:
            state = self.context.load_state()
            if state:
                logger.log_info("Resumed from previous state")
                # Restore previous goal if available
                if state.get('goal'):
                    self.goal = state['goal']
                # Load previous plan if available
                plan_id = state.get('plan_id')
                if plan_id:
                    loaded_plan = self.planner.load_plan(plan_id)
                    if loaded_plan:
                        logger.log_info(f"Loaded previous plan: {loaded_plan.goal}")
                    else:
                        logger.log_info("Could not load previous plan, creating new one")
        
        # Create initial plan if none exists
        if not self.planner.current_plan:
            logger.log_info("Creating initial plan...")
            self.planner.create_plan(self.goal)
        
        # Main autonomous loop
        try:
            while self.running:
                self._execute_iteration()
                
                # Check if plan completed
                if self.planner.is_goal_achieved():
                    self.goals_completed += 1
                    logger.log_info(f"Goal #{self.goals_completed} achieved!")
                    
                    # In continuous mode, generate a new goal
                    if Config.CONTINUOUS_MODE:
                        new_goal = self._generate_next_goal()
                        if new_goal:
                            logger.log_new_goal(self.goal, new_goal)
                            self.goal = new_goal
                            self.planner.create_plan(self.goal)
                        else:
                            logger.log_info("Could not generate new goal, stopping")
                            self.running = False
                    else:
                        self.running = False
                
                # Periodically save state
                if self.iteration_count % 5 == 0:
                    self._save_state()
        
        except Exception as e:
            logger.log_error(e, "Critical error in agent loop")
        
        finally:
            self._shutdown()
    
    def _execute_iteration(self):
        """Execute one iteration of the agent loop."""
        self.iteration_count += 1
        logger.log_info(f"\n{'='*60}\nIteration {self.iteration_count}\n{'='*60}")
        
        # Get next step from planner
        step = self.planner.get_next_step()
        
        if not step:
            logger.log_info("No more steps in current plan")
            return
        
        logger.log_info(f"Current step: {step.description}")
        
        # If step has no command, ask LLM for next action
        if not step.command:
            command_info = self._get_next_action(step)
            if command_info:
                step.command = command_info.get('command')
                reasoning = command_info.get('reasoning', '')
                learning = command_info.get('learning', '')
                
                logger.log_info(f"Reasoning: {reasoning}")
                
                # Store learning to memory
                if learning and learning.strip():
                    self._store_learning(learning, step.description)
        
        # Execute the command
        if step.command and step.command.strip():
            result = self._execute_command(step.command)
            
            # Update step with result
            self.planner.update_step_result(
                step.id,
                result,
                success=result.success
            )
            
            # Record execution in context
            execution_record = {
                'command': step.command,
                'success': result.success,
                'output': result.stdout[:500] if result.success else result.stderr[:500],
                'step_description': step.description,
            }
            self.context.add_execution(execution_record)
            
            # Handle failures
            if not result.success:
                self._handle_failure(step, result)
        else:
            logger.log_info("No command to execute, moving to next step")
            self.planner.update_step_result(step.id, "Skipped", success=True)
    
    def _get_next_action(self, step) -> Optional[dict]:
        """
        Ask LLM for the next action to take.
        
        Args:
            step: Current step
            
        Returns:
            Dict with command, reasoning, expected, learning
        """
        # Build context for LLM
        recent_results = self.context.get_recent_results(count=3)
        relevant_memories = self.context.get_relevant_memories(
            query=f"{self.goal} {step.description}",
            limit=3
        )
        
        # Format recent commands
        recent_commands_text = "\n".join([
            f"- {r['command']}: {'Success' if r['success'] else 'Failed'}\n  Output: {r.get('output', '')[:200]}"
            for r in recent_results
        ])
        
        # Format memories
        memories_text = "\n".join([
            f"- {m.get('content', '')[:200]}"
            for m in relevant_memories
        ])
        
        # Get scratchpad content
        scratchpad = self.context.get_scratchpad_content()
        
        # Build prompt
        system_prompt = f"""You are an autonomous agent with unrestricted terminal access on a Linux VM.
Your goal: {self.goal}

You can execute any bash/shell command. You should:
1. Break down complex goals into step-by-step plans
2. Execute commands to make progress
3. Learn from command outputs and past experiences
4. Adapt your plan based on results
5. Be resourceful and creative
6. Remember useful patterns and solutions for future use
7. Use 'data/scratchpad.md' to keep notes, todo lists, and track temporary state (use reading/writing commands)"""
        
        user_prompt = f"""Current Step: {step.description}
Expected Outcome: {step.expected_outcome}

Current Scratchpad (data/scratchpad.md):
{scratchpad}

Recent Command History:
{recent_commands_text if recent_commands_text else "No recent commands"}

Relevant Past Experiences:
{memories_text if memories_text else "No relevant memories yet"}

Provide your next action in this EXACT format:
REASONING: <why this action helps achieve the goal, including any relevant past learnings>
COMMAND: <exact bash/shell command to execute>
EXPECTED: <what you expect to happen>
LEARNING: <what you learned that should be remembered for the future - leave empty if nothing notable>

Important: Each field can span multiple lines. Start each field with its label followed by a colon.
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            logger.log_llm_request(messages, self.llm_client.model)
            start_time = time.time()
            
            with logger.spinner("Thinking..."):
                response = self.llm_client.send_message(messages)
                
            duration = time.time() - start_time
            logger.log_info(f"[bold purple][THINKING][/bold purple] Request took {duration:.2f}s")
            logger.log_llm_response(response['content'], response.get('usage'))
            
            # Parse response with multi-line support
            return self._parse_action_response(response['content'])
            
        except Exception as e:
            logger.log_error(e, "Failed to get next action from LLM")
            return None
    
    def _parse_action_response(self, response: str) -> dict:
        """
        Parse LLM response for action details with multi-line support.
        
        Uses regex to extract fields that may span multiple lines.
        """
        result = {}
        
        # Pattern matches FIELD: content (including newlines until next FIELD: or end)
        patterns = {
            'reasoning': r'REASONING:\s*(.*?)(?=\n(?:COMMAND|EXPECTED|LEARNING):|$)',
            'command': r'COMMAND:\s*(.*?)(?=\n(?:REASONING|EXPECTED|LEARNING):|$)',
            'expected': r'EXPECTED:\s*(.*?)(?=\n(?:REASONING|COMMAND|LEARNING):|$)',
            'learning': r'LEARNING:\s*(.*?)(?=\n(?:REASONING|COMMAND|EXPECTED):|$)',
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                # Clean up the value
                result[field] = value
        
        return result
    
    def _store_learning(self, learning: str, context: str):
        """Store a learning to long-term memory."""
        logger.log_learning(learning)
        self.memory.store_fact(
            fact=learning,
            source=f"Learned during: {context}"
        )
    
    def _execute_command(self, command: str) -> ExecutionResult:
        """Execute a command and return result."""
        logger.log_command_execution(command)
        
        result = self.executor.execute(command)
        
        logger.log_command_result(result)
        
        return result
    
    def _handle_failure(self, step, result: ExecutionResult):
        """Handle command failure with LLM-assisted retry or plan revision."""
        logger.log_info(f"Handling failure for step: {step.description}")
        
        step.retries += 1
        
        # Check for past solutions to similar errors
        error_solutions = self.memory.get_error_solutions(result.stderr)
        if error_solutions:
            logger.log_info(f"Found {len(error_solutions)} past solutions for similar errors")
        
        if step.retries < Config.MAX_RETRIES:
            logger.log_info(f"Retry {step.retries}/{Config.MAX_RETRIES}")
            
            # Ask LLM for help fixing the issue
            fixed_command = self._ask_llm_for_fix(step, result, error_solutions)
            
            if fixed_command:
                step.command = fixed_command
                logger.log_info(f"LLM suggested fix: {fixed_command}")
                
                # Execute the fixed command
                new_result = self._execute_command(fixed_command)
                
                if new_result.success:
                    # Store this as a successful error solution
                    self.memory.store_experience({
                        "error": result.stderr[:500],
                        "original_command": step.command,
                        "solution": fixed_command,
                        "success": "True",
                    }, category="error")
                    
                    self.planner.update_step_result(step.id, new_result, success=True)
                    return
        
        else:
            logger.log_info("Max retries exceeded, revising plan...")
            
            # Store the failure for future learning
            self.memory.store_experience({
                "error": result.stderr[:500],
                "command": step.command,
                "step": step.description,
                "success": "False",
            }, category="error")
            
            # Revise the entire plan
            failure_context = {
                "failed_step": step.description,
                "command": step.command,
                "error": result.stderr,
                "goal": self.goal,
                "past_solutions": [s.get('content', '')[:200] for s in error_solutions[:2]],
            }
            
            self.planner.revise_plan(failure_context)
    
    def _ask_llm_for_fix(
        self,
        step,
        result: ExecutionResult,
        past_solutions: list
    ) -> Optional[str]:
        """Ask LLM to suggest a fix for a failed command."""
        
        past_solutions_text = "\n".join([
            f"- {s.get('content', '')[:200]}"
            for s in past_solutions[:3]
        ]) if past_solutions else "No past solutions found"
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert troubleshooter. Suggest a fixed command to resolve the error."
            },
            {
                "role": "user",
                "content": f"""
The following command failed:
Command: {step.command}
Error: {result.stderr[:1000]}

Step description: {step.description}
Goal: {self.goal}

Past solutions to similar errors:
{past_solutions_text}

Provide ONLY the fixed command to run. No explanation, just the command.
If the error is unfixable, respond with: SKIP
"""
            }
        ]
        
        try:
            response = self.llm_client.send_message(messages, temperature=0.3)
            fixed = response['content'].strip()
            
            if fixed.upper() == "SKIP" or not fixed:
                return None
            
            # Remove any markdown code blocks
            fixed = re.sub(r'^```\w*\n?', '', fixed)
            fixed = re.sub(r'\n?```$', '', fixed)
            
            return fixed.strip()
            
        except Exception as e:
            logger.log_error(e, "Failed to get fix from LLM")
            return None
    
    def _generate_next_goal(self) -> Optional[str]:
        """Generate the next goal for continuous mode."""
        
        # Get memory statistics for context
        memory_stats = self.memory.get_statistics()
        
        # Get recent accomplishments
        recent_executions = self.context.get_recent_results(count=10)
        recent_successes = [e for e in recent_executions if e.get('success')]
        
        accomplishments = "\n".join([
            f"- {e.get('step_description', e.get('command', 'Unknown'))}"
            for e in recent_successes[-5:]
        ])
        
        messages = [
            {
                "role": "system",
                "content": """You are an autonomous AI agent planning your own evolution and work.
You have just completed a goal and need to decide what to work on next.
Be creative, ambitious, and self-improving. Consider:
- Building useful tools and capabilities for yourself
- Exploring and learning about your environment
- Automating tasks
- Improving your effectiveness
- Creating documentation
- Setting up monitoring or organization
"""
            },
            {
                "role": "user",
                "content": f"""
You just completed this goal: {self.goal}

Recent accomplishments:
{accomplishments if accomplishments else "Just getting started"}

Current capabilities:
- Stored memories: {memory_stats['total']}
- Procedures learned: {memory_stats['procedures']}
- Goals completed this session: {self.goals_completed}

Based on this context, what should your next goal be?
Provide a clear, specific, achievable goal.

Format your response EXACTLY as:
NEXT_GOAL: <your next goal here>
REASONING: <brief explanation of why this is a good next goal>
"""
            }
        ]
        
        try:
            response = self.llm_client.send_message(messages, temperature=0.8)
            content = response['content']
            
            # Extract the goal
            goal_match = re.search(r'NEXT_GOAL:\s*(.*?)(?=\nREASONING:|$)', content, re.DOTALL)
            if goal_match:
                new_goal = goal_match.group(1).strip()
                return new_goal
            
            # Fallback: use the whole response if it's short
            if len(content) < 200:
                return content.strip()
            
            return None
            
        except Exception as e:
            logger.log_error(e, "Failed to generate next goal")
            return None
    
    def _save_state(self):
        """Save current agent state."""
        state_data = {
            "goal": self.goal,
            "iteration_count": self.iteration_count,
            "goals_completed": self.goals_completed,
            "plan_id": self.planner.current_plan.id if self.planner.current_plan else None,
            "llm_stats": self.llm_client.get_statistics(),
        }
        
        self.context.save_state(state_data)
    
    def _shutdown(self):
        """Graceful shutdown."""
        logger.log_info("Shutting down agent...")
        
        # Save final state
        self._save_state()
        
        # Create session summary
        session_data = {
            "goal": self.goal,
            "iterations": self.iteration_count,
            "goals_completed": self.goals_completed,
            "llm_stats": self.llm_client.get_statistics(),
            "memory_stats": self.memory.get_statistics(),
            "ended_at": datetime.now().isoformat(),
        }
        
        self.memory.summarize_session(session_data)
        
        logger.log_agent_stop("Normal shutdown")
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals."""
        logger.log_info("\nReceived interrupt signal, stopping...")
        self.running = False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Autonomous Agent with OpenRouter")
    parser.add_argument('--goal', type=str, help='Initial goal for the agent')
    parser.add_argument('--resume', action='store_true', help='Resume from previous state')
    parser.add_argument('--memory-stats', action='store_true', help='Show memory statistics')
    parser.add_argument('--fresh', action='store_true', help='Start fresh (ignore previous state)')
    parser.add_argument('--no-continuous', action='store_true', help='Disable continuous mode')
    
    args = parser.parse_args()
    
    # Show memory stats and exit (doesn't need full config validation)
    if args.memory_stats:
        Config.validate(require_api_key=False)
        Config.ensure_directories()
        try:
            memory = LongTermMemory()
            stats = memory.get_statistics()
            print("\n=== Memory Statistics ===")
            for category, count in stats.items():
                print(f"{category}: {count}")
            print()
        except Exception as e:
            print(f"Could not load memory: {e}")
        return
    
    # Validate config before starting agent
    Config.validate(require_api_key=True)
    
    # Override continuous mode if requested
    if args.no_continuous:
        Config.CONTINUOUS_MODE = False
    
    # Create and start agent
    goal = args.goal or Config.INITIAL_GOAL
    agent = AutonomousAgent(goal=goal)
    agent.start(resume=args.resume and not args.fresh)


if __name__ == "__main__":
    main()
