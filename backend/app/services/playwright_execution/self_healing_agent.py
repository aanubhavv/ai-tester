import logging
import asyncio
from typing import Optional
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field
from google.genai import types

from app.schemas.test_cases.models import TestCase
from app.services.project_service import project_service, PROJECTS_ROOT
from app.services.ai.ai_service import ai_service
from app.services.test_generation.generation_service import generation_service
from app.services.playwright_execution.runner import execution_runner

logger = logging.getLogger(__name__)

class SelfHealingDecision(BaseModel):
    is_website_bug: bool = Field(description="True if the test script is correct but the website failed to behave as expected (a genuine bug or missing feature). False if the script itself is broken (e.g. bad selector, timing issue, missing step) and needs fixing.")
    analysis: str = Field(description="Detailed explanation of the error and reasoning for your decision.")
    fixed_script: Optional[str] = Field(description="If is_website_bug is False, provide the fully rewritten and fixed Playwright script here. It must be valid TypeScript. If is_website_bug is True, this can be null.")

class SelfHealingAgent:
    """
    Acts as a senior QA Automation Engineer to analyze failed executions,
    fix Playwright scripts automatically, and rerun them.
    """
    
    async def run_healing_loop(self, project_id: str, tc_id: str, tc: TestCase, initial_result: dict) -> None:
        """
        Runs the self-healing loop up to a maximum number of retries.
        Does not block the main event loop because we will run it via an asyncio Task, 
        but the loop itself is fully async.
        """
        logger.info(f"Triggering Self-Healing Pipeline for {tc_id}")
        
        max_retries = 3
        current_result = initial_result
        
        scripts_dir = PROJECTS_ROOT / project_id / "scripts" / "generated"
        script_path = scripts_dir / f"{tc_id}.spec.ts"
        
        for attempt in range(1, max_retries + 1):
            logger.info(f"Self-Healing Attempt {attempt}/{max_retries} for {tc_id}")
            
            # Read current script
            if not script_path.exists():
                self._fail_tc(project_id, tc_id, "Cannot self-heal: Script file not found.", current_result["logs"])
                return
                
            with open(script_path, "r", encoding="utf-8") as f:
                current_script = f.read()
                
            prompt = f"""
You are a Senior QA Automation Engineer. A Playwright script has failed during execution.

Test Case ID: {tc_id}
Preconditions: {tc.preconditions or 'None'}
Test Steps: {tc.test_steps or 'None'}
Expected Result: {tc.expected_result or 'None'}

### Original Playwright Script:
```typescript
{current_script}
```

### Execution Error:
{current_result.get("error", "None")}

### Execution Logs:
{current_result.get("logs", "None")}

Analyze the failure. You are provided with a screenshot of the failure state from Playwright. This screenshot is the most critical piece of evidence. Look at the attached screenshot CAREFULLY.
1. If the script is broken (e.g. strict selector failing, missing wait, logic error, or the UI has changed), set `is_website_bug` to false and provide the `fixed_script`. **CRITICAL**: Use the visual context from the screenshot to figure out the correct selector. For example, if a button's text changed, read the new text from the screenshot and update your locator in the new script.
   *Important Note on Whitespace/Line Breaks*: Playwright sometimes squashes text around `<br>` or inline tags (e.g., extracting "affordableGLP-1" instead of "affordable GLP-1"). If a failure is due to missing spaces where a line break naturally occurs, this is a SCRIPTing/assertion issue, NOT a website bug. You should fix the script (e.g. by using regex `.toHaveText(/affordable\\s*GLP-1/)` or splitting the assertion) instead of blaming the website.
2. If the script is perfectly fine and correctly verifying the Expected Result, but the website itself is broken or the feature is missing, set `is_website_bug` to true and explain the bug in `analysis`. Look at the attached screenshot to confirm the visual state of the website before deciding it is a website bug.

Return the JSON object according to the schema. 
If you provide a fixed_script, ensure it is the FULL, valid TypeScript script, ready to run.
"""
            
            # Check for screenshot
            final_prompt = prompt
            screenshot_path = current_result.get("screenshot_path")
            if screenshot_path:
                try:
                    with open(screenshot_path, "rb") as img_file:
                        image_bytes = img_file.read()
                    image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
                    final_prompt = [prompt, image_part]
                except Exception as e:
                    logger.warning(f"Failed to load screenshot for self-healing: {e}")
                    final_prompt = prompt
            
            # Log the attempt start in the UI
            self._update_logs(project_id, tc_id, f"\n\n--- Self-Healing Attempt {attempt}/{max_retries} ---\nAnalyzing failure...")
            
            try:
                def _call_ai():
                    return ai_service.generate_structured_raw(
                        task="self_healing",
                        prompt=final_prompt,
                        schema_class=SelfHealingDecision
                    )
                decision = await asyncio.to_thread(_call_ai)
                
                analysis_log = f"AI Analysis:\nIs Website Bug: {decision.is_website_bug}\nReasoning: {decision.analysis}"
                self._update_logs(project_id, tc_id, analysis_log)
                logger.info(f"Self-Healing Decision for {tc_id}: is_bug={decision.is_website_bug}")
                
                if decision.is_website_bug:
                    # It's a genuine bug. Fail the test case and stop the loop.
                    self._complete_tc(
                        project_id, tc_id, "Failed", 
                        f"[Website Bug Found]\n{decision.analysis}", 
                        "",
                        error_msg=current_result["error"]
                    )
                    return
                
                if not decision.fixed_script:
                    self._fail_tc(project_id, tc_id, "AI determined it was a script issue but failed to provide a fixed script.", "")
                    return
                
                # Clean the script if AI added markdown blocks
                clean_script = decision.fixed_script.replace("```typescript", "").replace("```ts", "").replace("```", "").strip()
                
                # Overwrite the script
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(clean_script)
                
                # Update script content in test cases metadata so frontend gets the new version
                tc_list = generation_service.get_test_cases(project_id)
                for i, item in enumerate(tc_list):
                    if item.id == tc_id:
                        item.script = clean_script
                        tc_list[i] = item
                        break
                generation_service.save_test_cases(project_id, tc_list)
                
                self._update_logs(project_id, tc_id, "Script rewritten. Triggering re-execution...")
                
                # Re-run the script
                new_result = await execution_runner.execute_script(project_id, tc)
                
                # Append the new execution logs to our running history
                combined_logs = f"\n\n--- Re-Execution Results ---\nStatus: {new_result['status']}\nError: {new_result['error']}\nLogs:\n{new_result['logs']}"
                self._update_logs(project_id, tc_id, combined_logs)
                
                if new_result["status"] == "Passed":
                    # Self-healing succeeded!
                    actual_res = f"Successfully verified: {tc.expected_result}" if hasattr(tc, 'expected_result') and tc.expected_result else "Script passed successfully."
                    fixed_error_msg = f"[Fixed via Self-Healing] The following error was observed and automatically resolved:\n\n{initial_result['error']}\n\n--- Fix Applied ---\n{decision.analysis}"
                    self._complete_tc(project_id, tc_id, "Passed", actual_res, "", error_msg=fixed_error_msg)
                    return
                else:
                    # Failed again, feed the new result into the next iteration
                    current_result = new_result
                    
            except Exception as e:
                logger.error(f"Error during self-healing loop for {tc_id}: {e}", exc_info=True)
                self._fail_tc(project_id, tc_id, f"Self-Healing Agent crashed: {str(e)}", "")
                return

        # If we exhausted max retries
        self._fail_tc(project_id, tc_id, "Max self-healing retries reached. Script still failing.", "", error_msg=current_result["error"])
        
    def _fail_tc(self, project_id: str, tc_id: str, actual_result: str, additional_logs: str, error_msg: str = None):
        self._complete_tc(project_id, tc_id, "Failed", actual_result, additional_logs, error_msg=error_msg)

    def _update_logs(self, project_id: str, tc_id: str, logs: str):
        tc_list = generation_service.get_test_cases(project_id)
        for i, item in enumerate(tc_list):
            if item.id == tc_id:
                existing_logs = item.execution_logs or ""
                item.execution_logs = existing_logs + "\n" + logs
                tc_list[i] = item
                break
        generation_service.save_test_cases(project_id, tc_list)

    def _complete_tc(self, project_id: str, tc_id: str, status: str, actual_result: str, additional_logs: str, error_msg: str = None):
        tc_list = generation_service.get_test_cases(project_id)
        for i, item in enumerate(tc_list):
            if item.id == tc_id:
                item.execution_status = status
                
                # Map execution status to global metadata status
                if status == "Passed":
                    item.status = "Pass"
                elif status == "Failed":
                    item.status = "Fail"
                else:
                    item.status = status
                item.actual_result = actual_result
                
                if error_msg is not None:
                    item.last_execution_error = error_msg
                
                if additional_logs:
                    existing_logs = item.execution_logs or ""
                    item.execution_logs = existing_logs + "\n\n" + additional_logs
                    
                item.last_execution_timestamp = datetime.utcnow().isoformat()
                
                tc_list[i] = item
                break
        generation_service.save_test_cases(project_id, tc_list)

self_healing_agent = SelfHealingAgent()
