import logging
import cv2
import numpy as np
import json
import uuid
import os
from pathlib import Path


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

        try:
            # 1. Read the screenshot and layout generated during execution
            scripts_dir = PROJECTS_ROOT / project_id / "scripts" / "generated"
            screenshot_path = scripts_dir / "target_screenshot.png"
            layout_path = scripts_dir / "target_layout.json"
            
            if not screenshot_path.exists() or not layout_path.exists():
                logger.warning(f"Target marker assets not found for {tc.tc_id}. Did the execution finish?")
                return None
                
            with open(screenshot_path, "rb") as f:
                screenshot_bytes = f.read()
                
            with open(layout_path, "r", encoding="utf-8") as f:
                layout_json_str = f.read()
                
            # Clean up the assets
            try:
                screenshot_path.unlink(missing_ok=True)
                layout_path.unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to clean up target assets: {e}")

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
                    elements = ai_result.get("elements", [])
                    
                    # For backward compatibility with older AI responses or missing elements list
                    if not elements and "x" in ai_result:
                        elements = [ai_result]
                        
                    for elem in elements:
                        x = int(elem.get("x", 0))
                        y = int(elem.get("y", 0))
                        w = int(elem.get("width", 0))
                        h = int(elem.get("height", 0))
                        
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
