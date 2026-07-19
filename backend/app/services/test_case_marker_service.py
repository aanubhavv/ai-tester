import logging
import cv2
import numpy as np
import json
import uuid
import base64

from app.db.imagekit_config import get_imagekit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions

from app.services.ai.ai_service import ai_service
from app.services.project_service import project_service
from app.schemas.test_cases.models import TestCase
from app.core.config import settings

logger = logging.getLogger(__name__)

class TestCaseMarkerService:
    def __init__(self):
        pass

    def mark_target_on_screenshot(self, project_id: str, tc: TestCase, screenshot_bytes: bytes, layout_json_str: str) -> str | None:
        """
        Uses AI to find the target element for the given test case, 
        draws a bounding box on the screenshot bytes, uploads it to ImageKit,
        and returns the ImageKit URL.
        """
        project = project_service.get_project(project_id)
        if not project:
            logger.error(f"Cannot mark target for {tc.tc_id}: Project not found")
            return None

        try:
            # 1. Use AI to identify the target bounding box
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
            
            clean_response = raw_ai_response.replace("```json", "").replace("```", "").strip()
            
            try:
                ai_result = json.loads(clean_response)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse AI response for target marker: {clean_response}")
                ai_result = {"found": False}
                
            # 2. Draw bounding box if found
            if ai_result.get("found"):
                nparr = np.frombuffer(screenshot_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if img is not None:
                    elements = ai_result.get("elements", [])
                    if not elements and "x" in ai_result:
                        elements = [ai_result]
                        
                    for elem in elements:
                        x = int(elem.get("x", 0))
                        y = int(elem.get("y", 0))
                        w = int(elem.get("width", 0))
                        h = int(elem.get("height", 0))
                        
                        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 3)
                    
                    success, encoded_img = cv2.imencode('.png', img)
                    if success:
                        screenshot_bytes = encoded_img.tobytes()

            # 3. Upload to ImageKit
            short_hex = uuid.uuid4().hex[:6]
            imagekit = get_imagekit()
            if not imagekit:
                logger.warning("ImageKit is not configured, skipping target marker upload")
                return None

            b64_file = base64.b64encode(screenshot_bytes).decode('utf-8')
            upload_result = imagekit.upload(
                file=b64_file,
                file_name=f"tc_{tc.id}_{short_hex}_target.png",
                options=UploadFileRequestOptions(
                    folder=f"/test_cases/{project_id}/", 
                    use_unique_file_name=False
                )
            )
            
            return upload_result.url

        except Exception as e:
            logger.error(f"Failed to mark target for {tc.tc_id}: {e}", exc_info=True)
            return None

test_case_marker_service = TestCaseMarkerService()
