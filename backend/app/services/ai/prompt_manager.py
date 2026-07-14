import os
from pathlib import Path

class PromptManager:
    """
    Loads AI prompts from disk and injects contextual variables.
    This keeps Python files clean and allows non-developers to edit AI instructions.
    """
    
    def __init__(self):
        # Base directory for all prompts: /backend/prompts/
        # Adjust based on where this script runs from. Assuming app/services/ai/prompt_manager.py
        current_file = Path(__file__).resolve()
        self.prompts_dir = current_file.parent.parent.parent.parent / "prompts"

    def get_prompt(self, task_name: str, group: str = "planning", **kwargs) -> str:
        """
        Loads a prompt template (e.g. prompts/planning/feature_extraction.md)
        and formats it with the provided kwargs.
        """
        prompt_path = self.prompts_dir / group / f"{task_name}.md"
        
        if not prompt_path.exists():
            # Fallback for when the file isn't created yet, mostly for resilience during development
            return f"SYSTEM INSTRUCTION: Proceed with task '{task_name}'."
            
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()
            
        # Format the template with injected variables
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required context variable {e} for prompt {task_name}")

prompt_manager = PromptManager()
