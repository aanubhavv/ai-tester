import asyncio
import json
import logging
import time
import subprocess
import os
import re
from pathlib import Path

from app.services.project_service import PROJECTS_ROOT
from app.schemas.test_cases.models import TestCase
from app.core.config import settings
logger = logging.getLogger(__name__)

def clean_text_for_excel(text: str) -> str:
    if not text:
        return ""
    # Remove ANSI escape sequences
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    cleaned = ansi_escape.sub('', text)
    # Remove control characters except newline and tab
    control_chars = re.compile(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]')
    cleaned = control_chars.sub('', cleaned)
    return cleaned

class PlaywrightExecutionService:
    """
    Executes Playwright tests via subprocess.
    """
    active_processes = {}

    @classmethod
    def cancel_execution(cls, project_id: str, tc_id: str):
        job_id = f"{project_id}_{tc_id}"
        proc = cls.active_processes.get(job_id)
        if proc:
            try:
                # Force kill the process tree since we use shell=True on Windows
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], capture_output=True)
            except Exception as e:
                logger.warning(f"Failed to kill process {job_id}: {e}")
            finally:
                cls.active_processes.pop(job_id, None)

    async def execute_script(self, project_id: str, tc: TestCase) -> dict:
        """
        Executes a single test case script and returns the result dictionary.
        """
        scripts_dir = PROJECTS_ROOT / project_id / "scripts" / "generated"
        file_path = scripts_dir / f"{tc.id}.spec.ts"
        
        if not file_path.exists():
            return {
                "status": "Failed",
                "duration": 0,
                "error": "Script file not found.",
                "logs": ""
            }
            
        start_time = time.time()
        
        try:
            job_id = f"{project_id}_{tc.id}"
            
            # Ensure playwright.config.ts exists to capture screenshots on failure
            config_path = scripts_dir / "playwright.config.ts"
            if not config_path.exists():
                config_content = """
import { defineConfig } from '@playwright/test';
export default defineConfig({
  use: {
    screenshot: 'only-on-failure',
  },
  reporter: 'json',
});
"""
                with open(config_path, "w", encoding="utf-8") as f:
                    f.write(config_content.strip())
            
            exec_file_name = f"{tc.id}_exec.spec.ts"
            exec_file_path = scripts_dir / exec_file_name

            # We use a single string command to avoid Windows shell list-argument drops
            def _run_playwright():
                # Inject layout extraction into the script
                with open(file_path, "r", encoding="utf-8") as f:
                    original_script = f.read()
                    
                injection = """

// --- AI Tester Injected Layout Extraction ---
test.afterEach(async ({ page }) => {
  try {
    // 0. Initial network idle
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    
    await page.evaluate(async () => {
      const sleep = ms => new Promise(r => setTimeout(r, ms));
      
      // 1. Wait for fonts
      await document.fonts.ready.catch(() => {});
      
      // 2. Wait for images
      const imgTimeout = Date.now() + 10000;
      while(Date.now() < imgTimeout) {
        const images = Array.from(document.images);
        if (images.every(img => img.complete)) break;
        await sleep(300);
      }
      
      // 3. Wait for videos
      const vidTimeout = Date.now() + 8000;
      while(Date.now() < vidTimeout) {
        const videos = Array.from(document.querySelectorAll('video'));
        const relevant = videos.filter(v => v.preload !== 'none' || v.readyState >= 2);
        if (relevant.every(v => v.readyState >= 2)) break;
        await sleep(300);
      }
      
      // 4. DOM Stability
      let domStableCount = 0;
      let lastDomLength = -1;
      const domTimeout = Date.now() + 10000;
      while(Date.now() < domTimeout) {
        const currentLength = document.querySelectorAll('*').length;
        if (currentLength === lastDomLength) {
          domStableCount++;
          if (domStableCount >= 3) break;
        } else {
          domStableCount = 0;
          lastDomLength = currentLength;
        }
        await sleep(300);
      }

      // 5. Layout Stability
      let layoutStableCount = 0;
      let lastScrollHeight = -1;
      const layoutTimeout = Date.now() + 10000;
      while(Date.now() < layoutTimeout) {
        const currentHeight = document.documentElement.scrollHeight;
        if (currentHeight === lastScrollHeight) {
          layoutStableCount++;
          if (layoutStableCount >= 3) break;
        } else {
          layoutStableCount = 0;
          lastScrollHeight = currentHeight;
        }
        await sleep(300);
      }

      // 6. Scroll Discovery (trigger lazy-loads)
      const scrollStep = 800;
      const scrollPause = 400;
      const maxScrolls = 25;
      let scrollY = 0;
      let scrollStableCount = 0;
      for (let i = 0; i < maxScrolls; i++) {
        window.scrollBy(0, scrollStep);
        scrollY += scrollStep;
        await sleep(scrollPause);
        
        const newHeight = document.documentElement.scrollHeight;
        if (scrollY >= newHeight || (window.innerHeight + window.scrollY) >= newHeight) {
          scrollStableCount++;
          if (scrollStableCount >= 2) break;
        } else {
          scrollStableCount = 0;
        }
      }
      // Scroll back to top safely
      window.scrollTo(0, 0);
      await sleep(500);
    }).catch(() => {});
    
    // 7. Skeletons / Loaders
    const skeletonSelectors = ['.skeleton', '.shimmer', '.loading', '.loader', '.spinner', '[aria-busy="true"]', '.placeholder-glow', '.placeholder-wave', '.ant-skeleton', '.MuiSkeleton-root', '.v-skeleton-loader'];
    for (const sel of skeletonSelectors) {
      try {
        const count = await page.locator(sel).count();
        if (count > 0) {
          await page.waitForSelector(sel, { state: 'hidden', timeout: 5000 }).catch(() => {});
        }
      } catch(e) {}
    }
    
    // 8. Final delay
    await page.waitForTimeout(500);
"""

                if settings.enable_target_screenshot:
                    injection += """
    // Capture screenshot and layout
    await page.screenshot({ path: 'target_screenshot.png', fullPage: true });
    const layout = await page.evaluate(() => {
      const elements = document.querySelectorAll('*');
      const layoutArray = [];
      for (const el of elements) {
        if (!el.id && el.classList.length === 0) continue;
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) continue;
        layoutArray.push({
          tag: el.tagName.toLowerCase(),
          id: el.id || null,
          classes: Array.from(el.classList),
          x: Math.round(rect.x + window.scrollX),
          y: Math.round(rect.y + window.scrollY),
          width: Math.round(rect.width),
          height: Math.round(rect.height)
        });
      }
      return { elements: layoutArray };
    });
    const fs = require('fs');
    fs.writeFileSync('target_layout.json', JSON.stringify(layout));
"""

                injection += """
  } catch(e) {
    console.error("Failed to extract layout:", e);
  }
});
"""
                with open(exec_file_path, "w", encoding="utf-8") as f:
                    f.write(original_script + injection)

                cmd_str = f"npx --yes playwright test {exec_file_name} --reporter=json --headed"
                env = os.environ.copy()
                env["PLAYWRIGHT_JSON_OUTPUT_NAME"] = "report.json"
                
                proc = subprocess.Popen(
                    cmd_str,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=str(scripts_dir),
                    text=True,
                    shell=True,
                    env=env
                )
                PlaywrightExecutionService.active_processes[job_id] = proc
                stdout, stderr = proc.communicate()
                return proc, stdout, stderr
                
            proc, stdout_str, stderr_str = await asyncio.to_thread(_run_playwright)
            PlaywrightExecutionService.active_processes.pop(job_id, None)
            
            duration = time.time() - start_time
            
            result_data = {
                "status": "Passed" if proc.returncode == 0 else "Failed",
                "duration": duration,
                "error": clean_text_for_excel(stderr_str),
                "logs": clean_text_for_excel(stdout_str)
            }
            
            # Parse playwright JSON output from file to get detailed errors
            report_file = scripts_dir / "report.json"
            if report_file.exists():
                try:
                    with open(report_file, "r", encoding="utf-8") as f:
                        json_data = json.load(f)
                    # Extract error messages from JSON if available
                    for suite in json_data.get('suites', []):
                        for spec in suite.get('specs', []):
                            for test in spec.get('tests', []):
                                for result in test.get('results', []):
                                    if result.get('status') != 'passed':
                                        error_msg = result.get('error', {}).get('message', '')
                                        if error_msg:
                                            result_data["error"] = clean_text_for_excel(error_msg)
                                        # Extract screenshot if available
                                        for attachment in result.get('attachments', []):
                                            if attachment.get('contentType') == 'image/png' and attachment.get('path'):
                                                result_data["screenshot_path"] = attachment.get('path')
                except Exception as parse_e:
                    logger.warning(f"Failed to parse report.json: {parse_e}")
                finally:
                    report_file.unlink(missing_ok=True)
            elif proc.returncode != 0 and not result_data["error"]:
                result_data["error"] = "Execution failed but no report.json was generated. Check logs."
                
            # Clean up the injected script
            try:
                exec_file_path.unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to clean up {exec_file_path}: {e}")
                
            return result_data
            
        except Exception as e:
            logger.error(f"Execution failed for {tc.tc_id}: {e}", exc_info=True)
            return {
                "status": "Failed",
                "duration": time.time() - start_time,
                "error": str(e),
                "logs": ""
            }

execution_runner = PlaywrightExecutionService()
