"""
Multi-step planning system for autonomous agent.
Creates, manages, and revises plans based on execution results.
"""
import json
import time
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict, field
from pathlib import Path
from config import Config
from utils.logger import logger


@dataclass
class Step:
    """A single step in a plan."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    command: Optional[str] = None
    expected_outcome: str = ""
    actual_outcome: Optional[str] = None
    status: str = "pending"  # pending, executing, completed, failed
    retries: int = 0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class Plan:
    """A multi-step plan for achieving a goal."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    steps: List[Step] = field(default_factory=list)
    current_step: int = 0
    status: str = "in_progress"  # in_progress, completed, failed
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "goal": self.goal,
            "steps": [step.to_dict() for step in self.steps],
            "current_step": self.current_step,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Plan':
        """Create Plan from dictionary."""
        steps = [Step(**step_data) for step_data in data.get('steps', [])]
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            goal=data.get('goal', ''),
            steps=steps,
            current_step=data.get('current_step', 0),
            status=data.get('status', 'in_progress'),
            created_at=data.get('created_at', datetime.now().isoformat()),
            updated_at=data.get('updated_at', datetime.now().isoformat()),
        )


class Planner:
    """Multi-step planning system with LLM integration."""
    
    def __init__(self, llm_client):
        """
        Initialize the planner.
        
        Args:
            llm_client: OpenRouter client for LLM communication
        """
        self.llm_client = llm_client
        self.current_plan: Optional[Plan] = None
        self.plan_history: List[Plan] = []
    
    def create_plan(self, goal: str, context: str = "") -> Plan:
        """
        Create a multi-step plan for achieving a goal.
        
        Args:
            goal: The goal to achieve
            context: Additional context about the environment
            
        Returns:
            Created Plan object
        """
        logger.log_info(f"Creating plan for goal: {goal}")
        
        # Build prompt for LLM
        messages = [
            {
                "role": "system",
                "content": "You are an expert planner. Break down complex goals into concrete, executable steps."
            },
            {
                "role": "user",
                "content": f"""
Create a detailed plan to achieve this goal: {goal}

{f"Context: {context}" if context else ""}

Provide a step-by-step plan. For each step:
1. Give a clear description
2. Specify the exact command to run (if applicable)
3. Describe the expected outcome

Format your response as JSON:
{{
  "steps": [
    {{
      "description": "Step description",
      "command": "command to run or null",
      "expected_outcome": "what should happen"
    }}
  ]
}}
"""
            }
        ]
        
        try:
            start_time = time.time()
            logger.log_llm_request(messages, self.llm_client.model)
            response = self.llm_client.send_message(messages, temperature=0.3)
            duration = time.time() - start_time
            logger.log_info(f"Plan creation took {duration:.2f}s")
            logger.log_llm_response(response['content'], response.get('usage'))
            
            # Parse response
            plan_data = self._parse_plan_response(response['content'])
            
            # Create Plan object
            steps = [
                Step(
                    description=step_data['description'],
                    command=step_data.get('command'),
                    expected_outcome=step_data.get('expected_outcome', '')
                )
                for step_data in plan_data.get('steps', [])
            ]
            
            plan = Plan(goal=goal, steps=steps)
            self.current_plan = plan
            self.plan_history.append(plan)
            
            logger.log_plan_update(plan.to_dict())
            self._save_plan(plan)
            
            return plan
            
        except Exception as e:
            logger.log_error(e, "Failed to create plan")
            # Return a simple fallback plan
            fallback_step = Step(
                description=f"Work on: {goal}",
                command=None,
                expected_outcome="Progress toward goal"
            )
            plan = Plan(goal=goal, steps=[fallback_step])
            self.current_plan = plan
            return plan
    
    def get_next_step(self) -> Optional[Step]:
        """
        Get the next step to execute.
        
        Returns:
            Next Step or None if plan is complete
        """
        if not self.current_plan:
            return None
        
        if self.current_plan.current_step >= len(self.current_plan.steps):
            self.current_plan.status = "completed"
            self._save_plan(self.current_plan)
            return None
        
        step = self.current_plan.steps[self.current_plan.current_step]
        step.status = "executing"
        self._save_plan(self.current_plan)
        
        return step
    
    def update_step_result(self, step_id: str, result: Any, success: bool = True):
        """
        Update a step with execution result.
        
        Args:
            step_id: ID of the step
            result: Execution result
            success: Whether the step succeeded
        """
        if not self.current_plan:
            return
        
        for step in self.current_plan.steps:
            if step.id == step_id:
                step.status = "completed" if success else "failed"
                step.actual_outcome = self._format_result(result)
                
                if not success and hasattr(result, 'stderr'):
                    step.error_message = result.stderr
                
                # Move to next step if successful
                if success and step == self.current_plan.steps[self.current_plan.current_step]:
                    self.current_plan.current_step += 1
                
                self.current_plan.updated_at = datetime.now().isoformat()
                self._save_plan(self.current_plan)
                break
    
    def revise_plan(self, failure_context: Dict) -> Plan:
        """
        Revise the plan based on failure or unexpected results.
        
        Args:
            failure_context: Context about what failed and why
            
        Returns:
            Revised Plan
        """
        logger.log_info("Revising plan based on failure")
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert problem solver. Revise plans when things don't go as expected."
            },
            {
                "role": "user",
                "content": f"""
Original goal: {self.current_plan.goal if self.current_plan else "Unknown"}

The plan encountered an issue:
{json.dumps(failure_context, indent=2)}

Please create a revised plan that addresses this issue. Format as JSON with steps.
"""
            }
        ]
        
        try:
            response = self.llm_client.send_message(messages, temperature=0.5)
            plan_data = self._parse_plan_response(response['content'])
            
            # Update current plan
            if self.current_plan:
                steps = [
                    Step(
                        description=step_data['description'],
                        command=step_data.get('command'),
                        expected_outcome=step_data.get('expected_outcome', '')
                    )
                    for step_data in plan_data.get('steps', [])
                ]
                self.current_plan.steps = steps
                self.current_plan.current_step = 0
                self.current_plan.updated_at = datetime.now().isoformat()
                self._save_plan(self.current_plan)
                
            return self.current_plan
            
        except Exception as e:
            logger.log_error(e, "Failed to revise plan")
            return self.current_plan
    
    def is_goal_achieved(self) -> bool:
        """Check if the goal has been achieved."""
        if not self.current_plan:
            return False
        
        return self.current_plan.status == "completed"
    
    def load_plan(self, plan_id: str) -> Optional[Plan]:
        """Load a plan from disk."""
        plan_file = Config.PLANS_DIR / f"{plan_id}.json"
        if plan_file.exists():
            with open(plan_file, 'r') as f:
                data = json.load(f)
            plan = Plan.from_dict(data)
            self.current_plan = plan
            return plan
        return None
    
    def _save_plan(self, plan: Plan):
        """Save plan to disk."""
        plan_file = Config.PLANS_DIR / f"{plan.id}.json"
        with open(plan_file, 'w') as f:
            json.dump(plan.to_dict(), f, indent=2)
    
    def _parse_plan_response(self, response: str) -> Dict:
        """Parse LLM response to extract plan data."""
        # Try to extract JSON from the response
        try:
            # Look for JSON block
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except:
            pass
        
        # Fallback: return empty plan
        return {"steps": []}
    
    def _format_result(self, result: Any) -> str:
        """Format execution result as string."""
        if hasattr(result, 'stdout'):
            return f"Output: {result.stdout[:200]}"
        return str(result)[:200]
