import logging
import asyncio
from typing import Optional
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

from app.services.ai.ai_service import ai_service
from app.services.project_service import project_service, PROJECTS_ROOT
from google.genai import types
from app.services.ai.prompt_manager import prompt_manager
from app.schemas.test_cases.models import TestCase

logger = logging.getLogger(__name__)

class ScriptGenerationService:
    """
    Service responsible for generating Playwright scripts using AI
    by inspecting the target application's DOM and visual layout.
    """
    
    async def generate_script(self, project_id: str, tc: TestCase) -> Optional[str]:
        """
        Runs the full pipeline for a single test case:
        1. Launches headless browser.
        2. Visits project primary URL.
        3. Extracts DOM and takes a full-page screenshot.
        4. Calls AI (with vision) to generate Playwright script.
        5. Saves script.
        """
        project = project_service.get_project(project_id)
        if not project or not project.primary_url:
            logger.error(f"Cannot generate script for {tc.tc_id}: Project missing primary_url")
            return None
            
        base_url = project.primary_url
        dom_context = ""
        screenshot_bytes = None
        
        try:
            # 1. Collect Context via Playwright (Sync in thread to avoid Windows ProactorEventLoop issues)
            def _extract_and_generate():
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=False)
                    page = browser.new_page()
                    try:
                        page.goto(base_url, timeout=15000, wait_until="domcontentloaded")
                        page.wait_for_timeout(2000)
                        dom_context = page.evaluate("() => document.body.outerHTML")
                        if len(dom_context) > 50000:
                            dom_context = dom_context[:50000] + "\n...[TRUNCATED]"
                        screenshot_bytes = page.screenshot(full_page=True)
                        
                        # Prepare prompt manually
                        prompt_str = prompt_manager.get_prompt(
                            task_name="script_generation/playwright",
                            tc_id=tc.tc_id,
                            title=tc.title,
                            preconditions=tc.preconditions or "None",
                            test_steps=tc.test_steps,
                            expected_result=tc.expected_result,
                            base_url=base_url,
                            dom_context=dom_context
                        )
                        
                        image_part = types.Part.from_bytes(data=screenshot_bytes, mime_type="image/png")
                        
                        # Call AI with multimodal prompt
                        raw_script = ai_service.generate_text_raw(
                            task="script_generation",
                            prompt=[prompt_str, image_part],
                            options=None
                        )
                        return raw_script
                    except Exception as e:
                        logger.warning(f"Failed to generate script for {base_url}: {e}")
                        return ""
                    finally:
                        browser.close()
            
            raw_script = await asyncio.to_thread(_extract_and_generate)
            if not raw_script:
                return None
            
            # 2. Clean and Save Script
            # Remove markdown backticks if AI accidentally included them
            clean_script = raw_script.replace("```typescript", "").replace("```ts", "").replace("```", "").strip()
            
            self._save_script(project_id, tc.id, clean_script)
            
            return clean_script
            
        except Exception as e:
            logger.error(f"Error generating script for {tc.tc_id}: {e}", exc_info=True)
            return None

    async def improve_script(self, project_id: str, tc: TestCase, user_context: str, old_script: str) -> Optional[str]:
        """
        Runs the pipeline to improve a single test case script based on user context.
        """
        project = project_service.get_project(project_id)
        if not project or not project.primary_url:
            logger.error(f"Cannot improve script for {tc.tc_id}: Project missing primary_url")
            return None
            
        base_url = project.primary_url
        dom_context = ""
        
        try:
            def _extract_and_improve():
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=False)
                    page = browser.new_page()
                    try:
                        page.goto(base_url, timeout=15000, wait_until="domcontentloaded")
                        page.wait_for_timeout(2000)
                        dom_context = page.evaluate("() => document.body.outerHTML")
                        if len(dom_context) > 50000:
                            dom_context = dom_context[:50000] + "\n...[TRUNCATED]"
                        
                        raw_script = ai_service.generate_text(
                            task="script_generation/playwright_improvement",
                            context_kwargs={
                                "tc_id": tc.tc_id,
                                "title": tc.title,
                                "preconditions": tc.preconditions or "None",
                                "test_steps": tc.test_steps,
                                "expected_result": tc.expected_result,
                                "base_url": base_url,
                                "dom_context": dom_context,
                                "user_context": user_context,
                                "old_script": old_script
                            },
                            options=None,
                            use_cache=False
                        )
                        return raw_script
                    except Exception as e:
                        logger.warning(f"Failed to improve script for {base_url}: {e}")
                        return ""
                    finally:
                        browser.close()
            
            raw_script = await asyncio.to_thread(_extract_and_improve)
            if not raw_script:
                return None
            
            clean_script = raw_script.replace("```typescript", "").replace("```ts", "").replace("```", "").strip()
            
            self._save_script(project_id, tc.id, clean_script)
            
            return clean_script
            
        except Exception as e:
            logger.error(f"Error improving script for {tc.tc_id}: {e}", exc_info=True)
            return None

    def _save_script(self, project_id: str, tc_id: str, content: str):
        scripts_dir = PROJECTS_ROOT / project_id / "scripts" / "generated"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        file_path = scripts_dir / f"{tc_id}.spec.ts"
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

script_generator = ScriptGenerationService()
