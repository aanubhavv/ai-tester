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
            
            # We use a single string command to avoid Windows shell list-argument drops
            def _run_playwright():
                cmd_str = f"npx --yes playwright test {file_path.name} --reporter=json --headed"
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
