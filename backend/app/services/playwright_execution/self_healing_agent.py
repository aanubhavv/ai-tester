import logging
import asyncio
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from google.genai import types

from app.schemas.test_cases.models import TestCase
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
        attempt_history = []
        
        for attempt in range(1, max_retries + 1):
            logger.info(f"Self-Healing Attempt {attempt}/{max_retries} for {tc_id}")
            
            tc_list = await generation_service.get_test_cases(project_id)
            current_tc = next((t for t in tc_list if t.id == tc_id), tc)
            
            if not current_tc.script:
                await self._fail_tc(project_id, tc_id, "Cannot self-heal: Script content is empty.", current_result.get("logs", ""))
                return
                
            current_script = current_tc.script
                
            dom_snapshot = current_result.get("dom_snapshot", "")
            if len(dom_snapshot) > 50000:
                dom_snapshot = dom_snapshot[:50000] + "\n...[TRUNCATED]"
            
            history_text = ""
            if attempt_history:
                history_text = "\n### Previous Failed Attempts:\n"
                for i, hist in enumerate(attempt_history):
                    history_text += f"\nAttempt {i+1} Script:\n```typescript\n{hist['script']}\n```\nAttempt {i+1} Error:\n{hist['error']}\n"
                history_text += "\nDo NOT repeat the exact same script from previous attempts. Try a different approach (e.g. use different locators, wait for states, etc.).\n"

            has_screenshot = "failure_screenshot_bytes" in current_result
            
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
{f'### DOM Snapshot at Failure (Truncated):\\n```html\\n{dom_snapshot}\\n```' if dom_snapshot else ''}
{history_text}
### Examples of good fixes:
Example 1 (Timeout / Missing Wait):
Error: TimeoutError: locator('.loading-spinner').waitFor()
Fix: The spinner might not appear instantly. Use `await expect(page.locator('.loading-spinner')).toBeVisible();` or `await page.waitForLoadState('networkidle');` instead of hard waiting for a strict locator.

Example 2 (Strict Mode Violation):
Error: strict mode violation: locator('button') resolved to 5 elements.
Fix: Use a more specific locator based on the visual text or context, such as `await page.getByRole('button', {{ name: 'Submit' }}).click();` or `await page.locator('button').first().click();`.

Analyze the failure.{' Look at the attached screenshot CAREFULLY.' if has_screenshot else ''}
1. If the script is broken (e.g. strict selector failing, missing wait, logic error, or the UI has changed), set `is_website_bug` to false and provide the `fixed_script`. **CRITICAL**: Use the visual context from the screenshot and the DOM Snapshot to figure out the correct selector.
2. If the script is perfectly fine and correctly verifying the Expected Result, but the website itself is broken or the feature is missing, set `is_website_bug` to true and explain the bug in `analysis`.

Return the JSON object according to the schema. 
If you provide a fixed_script, ensure it is the FULL, valid TypeScript script, ready to run.
"""
            
            if has_screenshot:
                image_part = types.Part.from_bytes(data=current_result["failure_screenshot_bytes"], mime_type="image/png")
                final_prompt = [prompt, image_part]
            else:
                final_prompt = prompt
            
            await self._update_logs(project_id, tc_id, f"\n\n--- Self-Healing Attempt {attempt}/{max_retries} ---\nAnalyzing failure...")
            
            try:
                def _call_ai():
                    return ai_service.generate_structured_raw(
                        task="self_healing",
                        prompt=final_prompt,
                        schema_class=SelfHealingDecision
                    )
                decision = await asyncio.to_thread(_call_ai)
                
                analysis_log = f"AI Analysis:\nIs Website Bug: {decision.is_website_bug}\nReasoning: {decision.analysis}"
                await self._update_logs(project_id, tc_id, analysis_log)
                logger.info(f"Self-Healing Decision for {tc_id}: is_bug={decision.is_website_bug}")
                
                if decision.is_website_bug:
                    await self._complete_tc(
                        project_id, tc_id, "Failed", 
                        f"[Website Bug Found]\n{decision.analysis}", 
                        "",
                        error_msg=current_result.get("error", "Failed")
                    )
                    return
                
                if not decision.fixed_script:
                    await self._fail_tc(project_id, tc_id, "AI determined it was a script issue but failed to provide a fixed script.", "")
                    return
                
                clean_script = decision.fixed_script.replace("```typescript", "").replace("```ts", "").replace("```", "").strip()
                
                await generation_service.update_test_case_in_db(project_id, tc_id, {"script": clean_script})
                current_tc.script = clean_script
                
                await self._update_logs(project_id, tc_id, "Script rewritten. Triggering re-execution...")
                
                new_result = await execution_runner.execute_script(project_id, current_tc)
                
                combined_logs = f"\n\n--- Re-Execution Results ---\nStatus: {new_result['status']}\nError: {new_result['error']}\nLogs:\n{new_result['logs']}"
                await self._update_logs(project_id, tc_id, combined_logs)
                
                if new_result["status"] == "Passed":
                    actual_res = f"Successfully verified: {current_tc.expected_result}" if hasattr(current_tc, 'expected_result') and current_tc.expected_result else "Script passed successfully."
                    fixed_error_msg = f"[Fixed via Self-Healing] The following error was observed and automatically resolved:\n\n{initial_result.get('error', 'None')}\n\n--- Fix Applied ---\n{decision.analysis}"
                    await self._complete_tc(project_id, tc_id, "Passed", actual_res, "", error_msg=fixed_error_msg)
                    return
                else:
                    attempt_history.append({"script": clean_script, "error": new_result.get("error", "")})
                    current_result = new_result
                    
            except Exception as e:
                logger.error(f"Error during self-healing loop for {tc_id}: {e}", exc_info=True)
                await self._fail_tc(project_id, tc_id, f"Self-Healing Agent crashed: {str(e)}", "")
                return

        await self._fail_tc(project_id, tc_id, "Max self-healing retries reached. Script still failing.", "", error_msg=current_result.get("error", ""))
        
    async def _fail_tc(self, project_id: str, tc_id: str, actual_result: str, additional_logs: str, error_msg: str = None):
        await self._complete_tc(project_id, tc_id, "Failed", actual_result, additional_logs, error_msg=error_msg)

    async def _update_logs(self, project_id: str, tc_id: str, logs: str):
        tc_list = await generation_service.get_test_cases(project_id)
        existing_logs = ""
        for item in tc_list:
            if item.id == tc_id:
                existing_logs = item.execution_logs or ""
                break
        await generation_service.update_test_case_in_db(project_id, tc_id, {"execution_logs": existing_logs + "\n" + logs})

    async def _complete_tc(self, project_id: str, tc_id: str, status: str, actual_result: str, additional_logs: str, error_msg: str = None):
        tc_list = await generation_service.get_test_cases(project_id)
        existing_logs = ""
        for item in tc_list:
            if item.id == tc_id:
                existing_logs = item.execution_logs or ""
                break

        updates = {
            "execution_status": status,
            "status": "Pass" if status == "Passed" else ("Fail" if status == "Failed" else status),
            "actual_result": actual_result,
            "last_execution_timestamp": datetime.utcnow().isoformat()
        }
        
        if error_msg is not None:
            updates["last_execution_error"] = error_msg
            
        if additional_logs:
            updates["execution_logs"] = existing_logs + "\n\n" + additional_logs

        await generation_service.update_test_case_in_db(project_id, tc_id, updates)

self_healing_agent = SelfHealingAgent()
