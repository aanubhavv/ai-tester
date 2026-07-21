import asyncio
import json
import logging
import time
import subprocess
import os
import re
import tempfile
from pathlib import Path

from app.schemas.test_cases.models import TestCase
from app.core.config import settings

logger = logging.getLogger(__name__)

def clean_text_for_excel(text: str) -> str:
    if not text:
        return ""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    cleaned = ansi_escape.sub('', text)
    control_chars = re.compile(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]')
    cleaned = control_chars.sub('', cleaned)
    return cleaned

class PlaywrightExecutionService:
    """
    Executes Playwright tests via subprocess using ephemeral temporary directories.
    """
    active_processes = {}

    @classmethod
    def cancel_execution(cls, project_id: str, tc_id: str):
        job_id = f"{project_id}_{tc_id}"
        proc = cls.active_processes.get(job_id)
        if proc:
            try:
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], capture_output=True)
            except Exception as e:
                logger.warning(f"Failed to kill process {job_id}: {e}")
            finally:
                cls.active_processes.pop(job_id, None)

    async def execute_script(self, project_id: str, tc: TestCase) -> dict:
        """
        Executes a single test case script from the TestCase model using a temporary directory,
        and returns the result dictionary including screenshot bytes if applicable.
        """
        if not tc.script:
            return {
                "status": "Failed",
                "duration": 0,
                "error": "Script content is empty.",
                "logs": ""
            }
            
        start_time = time.time()
        job_id = f"{project_id}_{tc.id}"
        
        try:
            def _run_playwright_in_temp():
                with tempfile.TemporaryDirectory() as temp_dir_str:
                    temp_dir = Path(temp_dir_str)
                    
                    config_path = temp_dir / "playwright.config.ts"
                    
                    connect_options = ""
                    from app.core.config import settings
                    if settings.browserless_ws_endpoint:
                        connect_options = f"connectOptions: {{ wsEndpoint: '{settings.browserless_ws_endpoint}' }},"
                    
                    config_content = f"""
import {{ defineConfig }} from '@playwright/test';
export default defineConfig({{
  use: {{
    screenshot: 'only-on-failure',
    {connect_options}
  }},
  reporter: 'json',
}});
"""
                    with open(config_path, "w", encoding="utf-8") as f:
                        f.write(config_content.strip())
                    
                    exec_file_name = f"{tc.id}_exec.spec.ts"
                    exec_file_path = temp_dir / exec_file_name
                    
                    original_script = tc.script
                        
                    injection = """
// --- AI Tester Injected DOM Capture on Failure ---
test.afterEach(async ({ page }, testInfo) => {
  if (testInfo.status !== 'passed' && testInfo.status !== 'skipped') {
    try {
      const html = await page.content();
      const fs = require('fs');
      fs.writeFileSync('failed_dom.html', html);
    } catch(e) {
      console.error("Failed to extract DOM on failure:", e);
    }
  }
});
"""
                    if settings.enable_target_screenshot:
                        injection += """

// --- AI Tester Injected Layout Extraction ---
test.afterEach(async ({ page }) => {
  try {
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    
    await page.evaluate(async () => {
      const sleep = ms => new Promise(r => setTimeout(r, ms));
      await document.fonts.ready.catch(() => {});
      
      const imgTimeout = Date.now() + 10000;
      while(Date.now() < imgTimeout) {
        const images = Array.from(document.images);
        if (images.every(img => img.complete)) break;
        await sleep(300);
      }
      
      const vidTimeout = Date.now() + 8000;
      while(Date.now() < vidTimeout) {
        const videos = Array.from(document.querySelectorAll('video'));
        const relevant = videos.filter(v => v.preload !== 'none' || v.readyState >= 2);
        if (relevant.every(v => v.readyState >= 2)) break;
        await sleep(300);
      }
      
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
      window.scrollTo(0, 0);
      await sleep(500);
    }).catch(() => {});
    
    const skeletonSelectors = ['.skeleton', '.shimmer', '.loading', '.loader', '.spinner', '[aria-busy="true"]', '.placeholder-glow', '.placeholder-wave', '.ant-skeleton', '.MuiSkeleton-root', '.v-skeleton-loader'];
    for (const sel of skeletonSelectors) {
      try {
        const count = await page.locator(sel).count();
        if (count > 0) {
          await page.waitForSelector(sel, { state: 'hidden', timeout: 5000 }).catch(() => {});
        }
      } catch(e) {}
    }
    
    await page.waitForTimeout(500);

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
  } catch(e) {
    console.error("Failed to extract layout:", e);
  }
});
"""
                    with open(exec_file_path, "w", encoding="utf-8") as f:
                        f.write(original_script + injection)
    
                    headed_flag = "--headed" if settings.app_env == "development" else ""
                    cmd_str = f"npx playwright test {exec_file_name} --reporter=json {headed_flag}"
                    env = os.environ.copy()
                    env["PLAYWRIGHT_JSON_OUTPUT_NAME"] = "report.json"
                    
                    backend_dir = Path(__file__).resolve().parent.parent.parent.parent
                    node_modules_dir = backend_dir / "node_modules"
                    
                    import sys
                    if sys.platform == "win32":
                        subprocess.run(
                            ["cmd", "/c", "mklink", "/J", str(temp_dir / "node_modules"), str(node_modules_dir)],
                            capture_output=True
                        )
                    else:
                        try:
                            os.symlink(str(node_modules_dir), str(temp_dir / "node_modules"), target_is_directory=True)
                        except Exception as e:
                            logger.warning(f"Failed to symlink node_modules: {e}")
                    
                    proc = subprocess.Popen(
                        cmd_str,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=str(temp_dir),
                        text=True,
                        shell=True,
                        env=env
                    )
                    PlaywrightExecutionService.active_processes[job_id] = proc
                    stdout_str, stderr_str = proc.communicate()
                    
                    result_data = {
                        "status": "Passed" if proc.returncode == 0 else "Failed",
                        "duration": time.time() - start_time,
                        "error": clean_text_for_excel(stderr_str),
                        "logs": clean_text_for_excel(stdout_str)
                    }
                    
                    report_file = temp_dir / "report.json"
                    if report_file.exists():
                        try:
                            with open(report_file, "r", encoding="utf-8") as f:
                                json_data = json.load(f)
                            for suite in json_data.get('suites', []):
                                for spec in suite.get('specs', []):
                                    for test in spec.get('tests', []):
                                        for result in test.get('results', []):
                                            if result.get('status') != 'passed':
                                                error_msg = result.get('error', {}).get('message', '')
                                                if error_msg:
                                                    result_data["error"] = clean_text_for_excel(error_msg)
                                                for attachment in result.get('attachments', []):
                                                    # For actual playwright failure screenshots, they are usually in test-results, 
                                                    # but since we didn't specify output dir, they might be discarded or we'll rely on the dom_snapshot.
                                                    pass
                        except Exception as parse_e:
                            logger.warning(f"Failed to parse report.json: {parse_e}")
                    elif proc.returncode != 0 and not result_data["error"]:
                        result_data["error"] = "Execution failed but no report.json was generated. Check logs."
                        
                    dom_file = temp_dir / "failed_dom.html"
                    if dom_file.exists():
                        try:
                            with open(dom_file, "r", encoding="utf-8") as f:
                                result_data["dom_snapshot"] = f.read()
                        except Exception as dom_e:
                            logger.warning(f"Failed to read failed_dom.html: {dom_e}")
                            
                    screenshot_file = temp_dir / "target_screenshot.png"
                    layout_file = temp_dir / "target_layout.json"
                    
                    if screenshot_file.exists() and layout_file.exists():
                        try:
                            with open(screenshot_file, "rb") as f:
                                result_data["screenshot_bytes"] = f.read()
                            with open(layout_file, "r", encoding="utf-8") as f:
                                result_data["layout_json"] = f.read()
                        except Exception as e:
                            logger.warning(f"Failed to read target assets: {e}")
                            
                    return result_data
                    
            result_data = await asyncio.to_thread(_run_playwright_in_temp)
            PlaywrightExecutionService.active_processes.pop(job_id, None)
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
