import logging
import cv2
import numpy as np
import json
import uuid
import os
from pathlib import Path

from app.services.browser_service import BrowserService
from app.schemas.scan import ScanOptions
from app.services.page_readiness import ReadinessConfig
from app.services.ai.ai_service import ai_service
from app.services.project_service import project_service, PROJECTS_ROOT
from app.schemas.test_cases.models import TestCase
from app.core.config import settings

logger = logging.getLogger(__name__)

class TestCaseMarkerService:
    def __init__(self):
        pass

    def mark_target_on_screenshot(self, project_id: str, tc: TestCase) -> str | None:
        """
        Runs a scan on the project's base URL, uses AI to find the target element
        for the given test case, draws a bounding box, and saves the screenshot.
        
        Returns the relative URL to the screenshot, or None if it fails.
        """
        project = project_service.get_project(project_id)
        if not project or not project.primary_url:
            logger.error(f"Cannot mark target for {tc.tc_id}: Project missing primary_url")
            return None

        # 1. Run a background scan to get the screenshot and layout
        options = ScanOptions(url=project.primary_url, headless=True)
        readiness_config = ReadinessConfig(
            max_wait_seconds=settings.readiness_max_wait_seconds,
            final_delay_seconds=settings.readiness_final_delay_seconds,
            wait_for_videos=settings.readiness_wait_for_videos,
            videos_timeout_ms=settings.readiness_videos_timeout_ms,
            navigation_wait_strategy=settings.readiness_navigation_wait_strategy,
            enable_scroll_discovery=settings.readiness_enable_scroll_discovery,
            scroll_step_pixels=settings.readiness_scroll_step_pixels,
            scroll_pause_ms=settings.readiness_scroll_pause_ms,
            max_scroll_iterations=settings.readiness_max_scroll_iterations,
        )

        try:
            service = BrowserService()
            result = service.scan_url(options, readiness_config=readiness_config)
            
            screenshot_bytes = result.get("screenshot_bytes")
            analysis = result.get("analysis")
            
            if not screenshot_bytes or not analysis:
                logger.warning(f"Scan failed to return screenshot or analysis for {tc.tc_id}")
                return None

            layout_json_str = analysis.model_dump_json()

            # 2. Use AI to identify the target bounding box
            raw_ai_response = ai_service.generate_text(
                task="execution/target_marker",
                context_kwargs={
                    "tc_id": tc.tc_id,
                    "title": tc.title,
                    "preconditions": tc.preconditions or "None",
                    "test_steps": tc.test_steps,
                    "expected_result": tc.expected_result,
                    "layout_json": layout_json_str
                },
                options=None,
                use_cache=False
            )
            
            # Clean AI response
            clean_response = raw_ai_response.replace("```json", "").replace("```", "").strip()
            
            try:
                ai_result = json.loads(clean_response)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse AI response for target marker: {clean_response}")
                ai_result = {"found": False}
                
            # 3. Draw bounding box if found
            if ai_result.get("found"):
                # Decode image
                nparr = np.frombuffer(screenshot_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if img is not None:
                    x = int(ai_result.get("x", 0))
                    y = int(ai_result.get("y", 0))
                    w = int(ai_result.get("width", 0))
                    h = int(ai_result.get("height", 0))
                    
                    # Draw a red rectangle (BGR: 0, 0, 255) with thickness 3
                    cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 3)
                    
                    # Encode image back to bytes
                    success, encoded_img = cv2.imencode('.png', img)
                    if success:
                        screenshot_bytes = encoded_img.tobytes()

            # 4. Save the screenshot to the test case directory
            test_cases_dir = PROJECTS_ROOT / project_id / "test_cases"
            test_cases_dir.mkdir(parents=True, exist_ok=True)
            
            # Use unique ID to prevent caching issues
            image_filename = f"{tc.id}_screenshot.png"
            image_path = test_cases_dir / image_filename
            
            with open(image_path, "wb") as f:
                f.write(screenshot_bytes)
                
            # Return the URL endpoint that will serve this screenshot
            return f"{settings.api_prefix}/projects/{project_id}/test-cases/{tc.id}/screenshot"

        except Exception as e:
            logger.error(f"Failed to mark target for {tc.tc_id}: {e}", exc_info=True)
            return None

test_case_marker_service = TestCaseMarkerService()
