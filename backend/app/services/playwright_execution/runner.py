import asyncio
import functools
import glob
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from app.schemas.test_cases.models import TestCase
from app.core.config import settings

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def get_npx_path() -> str:
    """
    Resolve the absolute path to the `npx` executable.

    Uses shutil.which() to locate npx on the system PATH and caches the result.
    Raises RuntimeError with a descriptive message if npx cannot be found.
    """
    npx_path = shutil.which("npx")
    if npx_path is None:
        raise RuntimeError(
            "Playwright execution failed: 'npx' executable not found on PATH. "
            "Ensure Node.js is installed and the PATH environment variable includes "
            "the directory containing 'npx' (e.g. /usr/bin or /usr/local/bin). "
            "If running as a systemd service, update the Environment directive "
            "to include the correct path."
        )
    logger.info(f"Resolved npx executable at: {npx_path}")
    return npx_path

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
                if sys.platform == "win32":
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], capture_output=True)
                else:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
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
            # We need to maintain the temp directory across the async operations
            temp_dir_obj = tempfile.TemporaryDirectory()
            temp_dir = Path(temp_dir_obj.name)
            
            # 1. Write Custom Reporter
            reporter_path = temp_dir / "ai_reporter.ts"
            reporter_content = """
import type { Reporter, TestCase, TestResult, TestStep } from '@playwright/test/reporter';

class AIStreamReporter implements Reporter {
  onStepBegin(test: TestCase, result: TestResult, step: TestStep) {
    if (step.category === 'test.step' && step.title && step.title.trim() !== '') {
      console.log(`__AI_TESTER_STEP__: ${JSON.stringify({
        event: 'stepBegin',
        id: step.title + '_' + step.startTime.getTime(),
        title: step.title,
        category: step.category,
        startTime: step.startTime.getTime()
      })}`);
    }
  }

  onStepEnd(test: TestCase, result: TestResult, step: TestStep) {
    if (step.category === 'test.step' && step.title && step.title.trim() !== '') {
      console.log(`__AI_TESTER_STEP__: ${JSON.stringify({
        event: 'stepEnd',
        id: step.title + '_' + step.startTime.getTime(),
        error: step.error?.message
      })}`);
    }
  }
}
export default AIStreamReporter;
"""
            with open(reporter_path, "w", encoding="utf-8") as f:
                f.write(reporter_content.strip())

            # 2. Write Playwright Config
            config_path = temp_dir / "playwright.config.ts"
            
            from app.core.config import settings
            
            browser_options = """launchOptions: {
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
      slowMo: 100
    },"""
            
            config_content = f"""
import {{ defineConfig }} from '@playwright/test';
export default defineConfig({{
  timeout: 60000,
  use: {{
    screenshot: 'only-on-failure',
    navigationTimeout: 15000,
    actionTimeout: 10000,
    {browser_options}
  }},
  outputDir: './test-results',
  reporter: [['list'], ['./ai_reporter.ts'], ['json', {{ outputFile: 'report.json' }}]],
}});
"""
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(config_content.strip())
            
            # 3. Write Executable Script
            exec_file_name = f"{tc.id}_exec.spec.ts"
            exec_file_path = temp_dir / exec_file_name
            
            original_script = tc.script
            
            # --- AI Rewrite for Plain English Steps ---
            try:
                from app.services.ai.ai_service import ai_service
                prompt = f"""You are an expert QA engineer. Rewrite the following Playwright test script.
Your task is to wrap the actions inside `test(..., async ({{ page }}) => {{ ... }})` into `await test.step('Plain English description of action', async () => {{ ... }});` blocks.
Group logical actions together. The plain english descriptions should be human-readable and describe what the user is doing.
CRITICAL: You MUST use `await test.step(...)` to ensure the step promises resolve properly.
DO NOT change any functionality, locators, or assertions. ONLY add `test.step` wrappers.
Return ONLY the raw TypeScript code, with NO markdown formatting (no ```typescript).

Script:
{original_script}
"""
                rewritten_script = await asyncio.to_thread(
                    ai_service.generate_text_raw,
                    task="rewrite_playwright_steps",
                    prompt=prompt,
                    options=None
                )
                if rewritten_script.strip().startswith("```"):
                    lines = rewritten_script.strip().split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    rewritten_script = "\n".join(lines)
                original_script = rewritten_script
            except Exception as e:
                logger.error(f"Failed to rewrite script with AI for job {job_id}: {e}")
            # ------------------------------------------
                
            injection = f"""
// --- AI Tester Injected CDP Screencast ---
let activeScreencastFetches = 0;

test.beforeEach(async ({{ page }}) => {{
  try {{
    const client = await page.context().newCDPSession(page);
    await client.send('Page.startScreencast', {{ format: 'jpeg', quality: 50, everyNthFrame: 1 }});
    client.on('Page.screencastFrame', async (frame) => {{
      activeScreencastFetches++;
      const ack = async () => {{
        try {{
          await client.send('Page.screencastFrameAck', {{ sessionId: frame.sessionId }});
        }} catch(e) {{}}
        activeScreencastFetches = Math.max(0, activeScreencastFetches - 1);
      }};

      try {{
        const backendPort = process.env.BACKEND_PORT || "8000";
        const endpoint = '/api/v1/browser-stream/{job_id}/frame';
        const url = `http://127.0.0.1:${{backendPort}}${{endpoint}}`;
        const http = require('http');
        const req = http.request(url, {{
            method: 'POST',
            headers: {{
                'Content-Type': 'text/plain',
                'Content-Length': Buffer.byteLength(frame.data)
            }}
        }});
        req.on('error', () => {{ ack(); }});
        req.on('response', () => {{ ack(); }});
        req.write(frame.data);
        req.end();
      }} catch(e) {{
        ack();
      }}
    }});
  }} catch (e) {{
    console.error("Failed to start CDP screencast:", e);
  }}
}});

test.afterEach(async () => {{
  let waited = 0;
  while (activeScreencastFetches > 0 && waited < 2000) {{
    await new Promise(r => setTimeout(r, 50));
    waited += 50;
  }}
}});
// -----------------------------------------

// --- AI Tester Injected DOM Capture on Failure ---
test.afterEach(async ({{ page }}, testInfo) => {{
  if (testInfo.status !== 'passed' && testInfo.status !== 'skipped') {{
    try {{
      const html = await page.content();
      const fs = require('fs');
      fs.writeFileSync('failed_dom.html', html);
    }} catch(e) {{
      console.error("Failed to extract DOM on failure:", e);
    }}
  }}
}});
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

            npx_executable = get_npx_path()
            cmd = [npx_executable, "playwright", "test", exec_file_name]

            env = os.environ.copy()
            env["PLAYWRIGHT_JSON_OUTPUT_NAME"] = "report.json"
            env["NODE_OPTIONS"] = "--max-old-space-size=512"
            env["BACKEND_PORT"] = str(getattr(settings, "port", os.getenv("PORT", "8000")))
            
            backend_dir = Path(__file__).resolve().parent.parent.parent.parent
            node_modules_dir = backend_dir / "node_modules"
            
            if sys.platform == "win32":
                subprocess.run(["cmd", "/c", "mklink", "/J", str(temp_dir / "node_modules"), str(node_modules_dir)], capture_output=True)
            else:
                try:
                    os.symlink(str(node_modules_dir), str(temp_dir / "node_modules"), target_is_directory=True)
                except Exception as e:
                    logger.warning(f"Failed to symlink node_modules: {e}")
            
            logger.info(f"Executing Playwright command with threaded streams: {cmd}")
            
            kwargs = dict(
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(temp_dir),
                env=env,
                text=True,
                bufsize=1
            )
            if sys.platform != "win32":
                kwargs["preexec_fn"] = os.setsid
                
            proc = subprocess.Popen(cmd, **kwargs)
            PlaywrightExecutionService.active_processes[job_id] = proc
            
            from app.services.playwright_execution.browser_stream_manager import browser_stream_manager
            import threading
            
            stdout_lines = []
            stderr_lines = []
            loop = asyncio.get_running_loop()
            
            def read_stream(stream, is_stderr: bool):
                for line in iter(stream.readline, ''):
                    line = line.rstrip('\r\n')
                    if is_stderr:
                        stderr_lines.append(line)
                    else:
                        stdout_lines.append(line)
                        if line.startswith("__AI_TESTER_STEP__:"):
                            try:
                                step_json = json.loads(line.replace("__AI_TESTER_STEP__: ", "", 1))
                                asyncio.run_coroutine_threadsafe(
                                    browser_stream_manager.put_frame(job_id, {
                                        "type": "step",
                                        "data": step_json
                                    }),
                                    loop
                                )
                            except Exception as e:
                                logger.warning(f"Failed to parse step JSON: {e}")
                        else:
                            asyncio.run_coroutine_threadsafe(
                                browser_stream_manager.put_frame(job_id, {
                                    "type": "log",
                                    "text": line
                                }),
                                loop
                            )

            t1 = threading.Thread(target=read_stream, args=(proc.stdout, False))
            t2 = threading.Thread(target=read_stream, args=(proc.stderr, True))
            t1.start()
            t2.start()

            try:
                def wait_proc():
                    return proc.wait(timeout=90.0)
                await asyncio.to_thread(wait_proc)
            except subprocess.TimeoutExpired:
                if sys.platform == "win32":
                    try:
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], capture_output=True)
                    except:
                        pass
                else:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except:
                        pass
                
                t1.join(timeout=1.0)
                t2.join(timeout=1.0)
                stdout_str = "\n".join(stdout_lines)
                stderr_str = "\n".join(stderr_lines)
                logger.error(f"Playwright execution timed out! stdout: {stdout_str}\nstderr: {stderr_str}")
                
                temp_dir_obj.cleanup()
                return {
                    "status": "Failed",
                    "duration": time.time() - start_time,
                    "error": f"Execution timed out after 90 seconds. Stderr: {stderr_str}",
                    "logs": stdout_str
                }
            finally:
                PlaywrightExecutionService.active_processes.pop(job_id, None)
            
            t1.join()
            t2.join()
            
            stdout_str = "\n".join(stdout_lines)
            stderr_str = "\n".join(stderr_lines)
            
            result_data = {
                "status": "Passed" if proc.returncode == 0 else "Failed",
                "duration": time.time() - start_time,
                "error": clean_text_for_excel(stderr_str),
                "logs": clean_text_for_excel(stdout_str)
            }
            
            # Post-execution parsing (screenshots, layouts, etc.)
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
                                            if attachment.get('name') == 'screenshot' and attachment.get('path'):
                                                att_path = Path(attachment['path'])
                                                if not att_path.is_absolute():
                                                    att_path = temp_dir / att_path
                                                if att_path.exists():
                                                    try:
                                                        with open(att_path, 'rb') as af:
                                                            result_data['failure_screenshot_bytes'] = af.read()
                                                            logger.info(f"Captured failure screenshot from {att_path}")
                                                    except Exception as att_e:
                                                        logger.warning(f"Failed to read attachment screenshot: {att_e}")
                except Exception as parse_e:
                    logger.warning(f"Failed to parse report.json: {parse_e}")
            elif proc.returncode != 0 and not result_data["error"]:
                result_data["error"] = "Execution failed but no report.json was generated. Check logs."
            
            if 'failure_screenshot_bytes' not in result_data and proc.returncode != 0:
                test_results_dir = temp_dir / "test-results"
                if test_results_dir.exists():
                    png_files = list(test_results_dir.rglob("*.png"))
                    if png_files:
                        try:
                            with open(png_files[0], 'rb') as sf:
                                result_data['failure_screenshot_bytes'] = sf.read()
                                logger.info(f"Captured fallback failure screenshot from {png_files[0]}")
                        except Exception as fb_e:
                            logger.warning(f"Failed to read fallback screenshot: {fb_e}")
                
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
                    
            temp_dir_obj.cleanup()
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
