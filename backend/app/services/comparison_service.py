import logging
import time
import json
from typing import Any
import uuid
from datetime import datetime
import httpx

import cv2
import numpy as np

from app.schemas.comparison import ComparisonRequest, ChangedRegion
from app.services.artifact_service import ArtifactService

logger = logging.getLogger(__name__)

class ComparisonError(Exception):
    pass

class ComparisonService:
    def __init__(self, artifact_service: ArtifactService):
        self._artifact_service = artifact_service

    async def _fetch_image(self, url: str) -> np.ndarray:
        if "ik.imagekit.io" in url:
            url = f"{url}&tr=orig-true" if "?" in url else f"{url}?tr=orig-true"
            
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            image_bytes = response.content
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img

    async def compare_scans(self, request: ComparisonRequest) -> dict[str, Any]:
        start_time = time.time()
        
        baseline_id = request.baseline_scan_id
        current_id = request.current_scan_id
        threshold = request.threshold if request.threshold is not None else 0.1
        ignored_selectors = request.ignored_selectors or []

        logger.info(f"Comparing {baseline_id} to {current_id}")

        baseline_service = ArtifactService.get_for_scan(baseline_id)
        current_service = ArtifactService.get_for_scan(current_id)

        baseline_url = await baseline_service.get_screenshot_path(baseline_id)
        current_url = await current_service.get_screenshot_path(current_id)

        if not baseline_url:
            raise ComparisonError(f"Baseline screenshot not found for scan {baseline_id}")
        if not current_url:
            raise ComparisonError(f"Current screenshot not found for scan {current_id}")

        try:
            img_baseline = await self._fetch_image(baseline_url)
            img_current = await self._fetch_image(current_url)
        except Exception as e:
            raise ComparisonError(f"Failed to fetch and decode screenshots: {e}")

        if img_baseline is None or img_current is None:
            raise ComparisonError("Failed to decode screenshot images via OpenCV.")

        if ignored_selectors:
            await self._mask_ignored_regions(baseline_id, img_baseline, ignored_selectors, baseline_service)
            await self._mask_ignored_regions(current_id, img_current, ignored_selectors, current_service)

        h_b, w_b = img_baseline.shape[:2]
        h_c, w_c = img_current.shape[:2]
        
        max_h = max(h_b, h_c)
        max_w = max(w_b, w_c)
        
        img_baseline_aligned = self._pad_image(img_baseline, max_w, max_h)
        img_current_aligned = self._pad_image(img_current, max_w, max_h)

        gray_baseline = cv2.cvtColor(img_baseline_aligned, cv2.COLOR_BGR2GRAY)
        gray_current = cv2.cvtColor(img_current_aligned, cv2.COLOR_BGR2GRAY)
        
        # Apply GaussianBlur to reduce high-frequency noise (e.g. anti-aliasing artifacts)
        gray_baseline = cv2.GaussianBlur(gray_baseline, (5, 5), 0)
        gray_current = cv2.GaussianBlur(gray_current, (5, 5), 0)
        
        diff = cv2.absdiff(gray_baseline, gray_current)
        
        pixel_threshold = int(threshold * 255)
        _, thresh = cv2.threshold(diff, pixel_threshold, 255, cv2.THRESH_BINARY)
        
        kernel = np.ones((5, 5), np.uint8)
        thresh = cv2.dilate(thresh, kernel, iterations=2)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        changed_regions: list[ChangedRegion] = []
        diff_image = img_current_aligned.copy()
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            if area < 100:  # Increased from 16 to ignore small artifacts
                continue
            changed_regions.append(ChangedRegion(x=x, y=y, width=w, height=h, area=area))
            cv2.rectangle(diff_image, (x, y), (x + w, y + h), (0, 0, 255), 2)
            
        changed_pixels_count = cv2.countNonZero(thresh)
        total_pixels = max_w * max_h
        difference_percentage = (changed_pixels_count / total_pixels) if total_pixels > 0 else 0.0

        passed = len(changed_regions) == 0

        success, encoded_img = cv2.imencode('.png', diff_image)
        if not success:
            raise ComparisonError("Failed to encode diff image to PNG format.")
        diff_bytes = encoded_img.tobytes()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_hex = uuid.uuid4().hex[:4]
        comparison_id = f"comp_{timestamp}_{short_hex}"

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

        await self._artifact_service.create_comparison_directory(comparison_id)
        await self._artifact_service.save_diff_image(comparison_id, diff_bytes)
        await self._artifact_service.save_comparison_report(comparison_id, report)
        
        logger.info(f"Comparison completed in {duration}s. Passed: {passed}")

        return report

    def _pad_image(self, img: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
        h, w = img.shape[:2]
        if h == target_h and w == target_w:
            return img
        padded = np.full((target_h, target_w, 3), 255, dtype=np.uint8)
        padded[0:h, 0:w] = img
        return padded

    async def _mask_ignored_regions(self, scan_id: str, img: np.ndarray, selectors: list[str], service: ArtifactService) -> None:
        report = await service.get_scan_report(scan_id)
        if not report or "analysis" not in report or "layout" not in report["analysis"]:
            logger.warning(f"layout.json not found for scan {scan_id}. Cannot mask dynamic regions.")
            return
            
        layout_data = report["analysis"]["layout"]
        elements = layout_data.get("elements", [])
        
        for selector in selectors:
            matched_elements = self._find_matching_elements(elements, selector)
            for el in matched_elements:
                x, y = el.get("x", 0), el.get("y", 0)
                w, h = el.get("width", 0), el.get("height", 0)
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 0), -1)
                
    def _find_matching_elements(self, elements: list[dict], selector: str) -> list[dict]:
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
                if selector.lower() == el.get("tag", ""):
                    matched.append(el)
        return matched
