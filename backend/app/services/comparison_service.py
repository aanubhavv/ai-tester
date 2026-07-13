import logging
import time
import json
from pathlib import Path
from typing import Any
import uuid
from datetime import datetime

import cv2
import numpy as np

from app.schemas.comparison import ComparisonRequest, ChangedRegion, DiffStatistics
from app.services.artifact_service import ArtifactService

logger = logging.getLogger(__name__)

class ComparisonError(Exception):
    """Custom exception for errors during the visual comparison process."""
    pass

class ComparisonService:
    """
    Visual Regression Engine.

    Responsible for comparing two scan artifacts (baseline and current),
    detecting visual differences, masking ignored regions, generating
    a composite diff image, and compiling structured statistics.
    """

    def __init__(self, artifact_service: ArtifactService):
        self._artifact_service = artifact_service

    def compare_scans(self, request: ComparisonRequest) -> dict[str, Any]:
        """
        Execute the full visual regression comparison.
        
        Args:
            request: The ComparisonRequest containing scan IDs and options.
            
        Returns:
            A dictionary matching RegressionReportSchema.
        """
        start_time = time.time()
        
        baseline_id = request.baseline_scan_id
        current_id = request.current_scan_id
        threshold = request.threshold if request.threshold is not None else 0.05
        ignored_selectors = request.ignored_selectors or []

        logger.info(f"Comparing {baseline_id} to {current_id}")

        # 1. Load screenshots
        baseline_path = self._artifact_service.get_screenshot_path(baseline_id)
        current_path = self._artifact_service.get_screenshot_path(current_id)

        if not baseline_path:
            raise ComparisonError(f"Baseline screenshot not found for scan {baseline_id}")
        if not current_path:
            raise ComparisonError(f"Current screenshot not found for scan {current_id}")

        # Load images via OpenCV (BGR format)
        img_baseline = cv2.imread(str(baseline_path))
        img_current = cv2.imread(str(current_path))

        if img_baseline is None or img_current is None:
            raise ComparisonError("Failed to decode screenshot images via OpenCV.")

        # 2. Mask ignored regions
        if ignored_selectors:
            self._mask_ignored_regions(baseline_id, img_baseline, ignored_selectors)
            self._mask_ignored_regions(current_id, img_current, ignored_selectors)

        # 3. Align dimensions (Pad the smaller image to match the larger one)
        h_b, w_b = img_baseline.shape[:2]
        h_c, w_c = img_current.shape[:2]
        
        max_h = max(h_b, h_c)
        max_w = max(w_b, w_c)
        
        img_baseline_aligned = self._pad_image(img_baseline, max_w, max_h)
        img_current_aligned = self._pad_image(img_current, max_w, max_h)

        # 4. Compute visual difference
        gray_baseline = cv2.cvtColor(img_baseline_aligned, cv2.COLOR_BGR2GRAY)
        gray_current = cv2.cvtColor(img_current_aligned, cv2.COLOR_BGR2GRAY)
        
        # Absolute pixel-by-pixel difference
        diff = cv2.absdiff(gray_baseline, gray_current)
        
        # Apply threshold to ignore tiny rendering differences
        # threshold is 0.0 to 1.0. We map it to 0-255 pixel intensity difference.
        pixel_threshold = int(threshold * 255)
        _, thresh = cv2.threshold(diff, pixel_threshold, 255, cv2.THRESH_BINARY)
        
        # Dilate the thresholded image slightly to connect fragmented diff pixels
        kernel = np.ones((5, 5), np.uint8)
        thresh = cv2.dilate(thresh, kernel, iterations=2)

        # 5. Find changed regions (bounding boxes)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        changed_regions: list[ChangedRegion] = []
        diff_image = img_current_aligned.copy()
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            
            # Ignore micro-regions (e.g. less than 16 pixels area)
            if area < 16:
                continue
                
            changed_regions.append(ChangedRegion(x=x, y=y, width=w, height=h, area=area))
            
            # Draw red bounding box on diff image (BGR format: 0, 0, 255 is red)
            cv2.rectangle(diff_image, (x, y), (x + w, y + h), (0, 0, 255), 2)
            
        # 6. Calculate statistics
        changed_pixels_count = cv2.countNonZero(thresh)
        total_pixels = max_w * max_h
        difference_percentage = (changed_pixels_count / total_pixels) if total_pixels > 0 else 0.0

        # We consider it 'passed' if there are no meaningful changed regions.
        passed = len(changed_regions) == 0

        # Encode diff image to PNG bytes
        success, encoded_img = cv2.imencode('.png', diff_image)
        if not success:
            raise ComparisonError("Failed to encode diff image to PNG format.")
        diff_bytes = encoded_img.tobytes()

        # Generate unique comparison ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_hex = uuid.uuid4().hex[:4]
        comparison_id = f"comp_{timestamp}_{short_hex}"

        # Compile report
        duration = round(time.time() - start_time, 3)
        report = {
            "info": {
                "comparison_id": comparison_id,
                "baseline_scan_id": baseline_id,
                "current_scan_id": current_id,
                "compared_at": datetime.now().isoformat(),
                "duration_seconds": duration,
                "threshold_used": threshold,
                "ignored_selectors": ignored_selectors,
            },
            "status": "passed" if passed else "failed",
            "statistics": {
                "difference_percentage": difference_percentage,
                "changed_pixels": int(changed_pixels_count),
                "image_width": max_w,
                "image_height": max_h,
            },
            "changed_regions": [r.model_dump() for r in changed_regions],
            "warnings": [],
        }

        # Save artifacts
        self._artifact_service.create_comparison_directory(comparison_id)
        self._artifact_service.save_diff_image(comparison_id, diff_bytes)
        self._artifact_service.save_comparison_report(comparison_id, report)
        
        logger.info(f"Comparison completed in {duration}s. Passed: {passed}")

        return report

    def _pad_image(self, img: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
        """Pad an image with black pixels to match the target dimensions."""
        h, w = img.shape[:2]
        if h == target_h and w == target_w:
            return img
            
        # Create a new black image (BGR) of target size
        padded = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        # Copy the original image into the top-left corner
        padded[0:h, 0:w] = img
        return padded

    def _mask_ignored_regions(self, scan_id: str, img: np.ndarray, selectors: list[str]) -> None:
        """
        Load layout.json for the scan and draw black rectangles over any
        elements matching the ignored selectors.
        """
        # Read layout.json
        scan_dir = self._artifact_service._scan_dir(scan_id)
        layout_path = scan_dir / "analysis" / "layout.json"
        
        if not layout_path.exists():
            logger.warning(f"layout.json not found for scan {scan_id}. Cannot mask dynamic regions.")
            return
            
        try:
            with open(layout_path, "r", encoding="utf-8") as f:
                layout_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load layout.json for scan {scan_id}: {e}")
            return
            
        elements = layout_data.get("elements", [])
        
        for selector in selectors:
            matched_elements = self._find_matching_elements(elements, selector)
            for el in matched_elements:
                x, y = el.get("x", 0), el.get("y", 0)
                w, h = el.get("width", 0), el.get("height", 0)
                # Draw a solid black rectangle over the element
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 0), -1)
                
    def _find_matching_elements(self, elements: list[dict], selector: str) -> list[dict]:
        """
        Basic CSS selector resolution against the LayoutSchema elements.
        Supports .class, #id, and tag name.
        """
        selector = selector.strip()
        matched = []
        
        for el in elements:
            if selector.startswith("."):
                class_name = selector[1:]
                if class_name in el.get("classes", []):
                    matched.append(el)
            elif selector.startswith("#"):
                id_name = selector[1:]
                if id_name == el.get("id"):
                    matched.append(el)
            else:
                # Assume tag name
                if selector.lower() == el.get("tag", ""):
                    matched.append(el)
                    
        return matched
