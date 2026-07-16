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
        if "/" in task_name:
            prompt_path = self.prompts_dir / f"{task_name}.md"
        else:
            prompt_path = self.prompts_dir / group / f"{task_name}.md"
        
        if not prompt_path.exists():
            # Fallback for when the file isn't created yet, mostly for resilience during development
            return f"SYSTEM INSTRUCTION: Proceed with task '{task_name}'."
            
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()
            
        # Safe replacement for both {var} and {{var}} syntaxes
        # This avoids KeyErrors when the template contains code blocks with { } like JS/TS.
        for key, value in kwargs.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
            template = template.replace(f"{{{key}}}", str(value))
            
        return template

prompt_manager = PromptManager()
