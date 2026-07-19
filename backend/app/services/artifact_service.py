import logging
from app.db.imagekit_config import get_imagekit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
import base64
from typing import Any, Optional
from datetime import datetime

from app.db.mongodb import get_database

logger = logging.getLogger(__name__)

class ArtifactService:
    """
    Manages creation, storage, and retrieval of scan artifacts using MongoDB
    for structured data and Cloudinary for media.
    """

    def __init__(self, artifacts_dir: str = "artifacts"):
        # We no longer use local filesystem but keep the parameter for compatibility
        self._artifacts_dir = artifacts_dir

    @property
    def scans_collection(self):
        return get_database()["scans"]

    @property
    def comparisons_collection(self):
        return get_database()["comparisons"]

    @classmethod
    def get_for_scan(cls, scan_id: str) -> "ArtifactService":
        return cls()

    async def create_scan_directory(self, scan_id: str) -> None:
        """No-op for MongoDB."""
        pass

    async def create_comparison_directory(self, comparison_id: str) -> None:
        """No-op for MongoDB."""
        pass

    async def save_screenshot(self, scan_id: str, screenshot_bytes: bytes) -> str:
        """Upload to ImageKit and return the URL."""
        if not screenshot_bytes:
            return ""
        
        imagekit = get_imagekit()
        if not imagekit:
            logger.warning("ImageKit is not configured, skipping screenshot upload")
            return ""

        b64_file = base64.b64encode(screenshot_bytes).decode('utf-8')
        result = imagekit.upload(
            file=b64_file,
            file_name=f"scan_{scan_id}_screenshot.png",
            options=UploadFileRequestOptions(
                folder=f"/scans/{scan_id}/", 
                use_unique_file_name=False
            )
        )
        url = result.url
        
        # Save URL in scan document
        await self.scans_collection.update_one(
            {"scan_id": scan_id},
            {"$set": {"screenshot_url": url}},
            upsert=True
        )
        logger.info(f"Saved screenshot to ImageKit: {url}")
        return url

    async def save_analysis_artifacts(
        self,
        scan_id: str,
        analysis_data: dict[str, Any],
        readiness_data: dict[str, Any] | None = None,
    ) -> None:
        """Save analysis and readiness to MongoDB."""
        update_doc = {"analysis": analysis_data}
        if readiness_data:
            update_doc["readiness"] = readiness_data
            
        await self.scans_collection.update_one(
            {"scan_id": scan_id},
            {"$set": update_doc},
            upsert=True
        )
        logger.info(f"Saved analysis artifacts for {scan_id}")

    async def save_report(self, scan_id: str, report: dict[str, Any]) -> None:
        """Save master report to MongoDB."""
        await self.scans_collection.update_one(
            {"scan_id": scan_id},
            {"$set": {"report": report}},
            upsert=True
        )
        logger.info(f"Saved master report for {scan_id}")

    async def save_scan_log(self, scan_id: str, log_entries: list[dict[str, str]]) -> None:
        """Save scan lifecycle log to MongoDB."""
        await self.scans_collection.update_one(
            {"scan_id": scan_id},
            {"$set": {"logs": log_entries}},
            upsert=True
        )
        logger.info(f"Saved scan log for {scan_id}")

    async def save_diff_image(self, comparison_id: str, diff_bytes: bytes) -> str:
        """Upload diff image to ImageKit."""
        if not diff_bytes:
            return ""
            
        imagekit = get_imagekit()
        if not imagekit:
            logger.warning("ImageKit is not configured, skipping diff upload")
            return ""

        b64_file = base64.b64encode(diff_bytes).decode('utf-8')
        result = imagekit.upload(
            file=b64_file,
            file_name=f"comparison_{comparison_id}_diff.png",
            options=UploadFileRequestOptions(
                folder=f"/comparisons/{comparison_id}/", 
                use_unique_file_name=False
            )
        )
        url = result.url
        
        await self.comparisons_collection.update_one(
            {"comparison_id": comparison_id},
            {"$set": {"diff_image_url": url}},
            upsert=True
        )
        logger.info(f"Saved diff image to ImageKit: {url}")
        return url

    async def save_comparison_report(self, comparison_id: str, report: dict[str, Any]) -> None:
        """Save comparison report to MongoDB."""
        await self.comparisons_collection.update_one(
            {"comparison_id": comparison_id},
            {"$set": {"report": report}},
            upsert=True
        )
        logger.info(f"Saved comparison report for {comparison_id}")

    async def get_scan_report(self, scan_id: str) -> dict[str, Any] | None:
        """Load and return the master report for a scan."""
        doc = await self.scans_collection.find_one({"scan_id": scan_id}, {"report": 1})
        if doc and "report" in doc:
            return doc["report"]
        return None

    async def get_screenshot_path(self, scan_id: str) -> Optional[str]:
        """Return the screenshot Cloudinary URL."""
        doc = await self.scans_collection.find_one({"scan_id": scan_id}, {"screenshot_url": 1})
        if doc and "screenshot_url" in doc:
            return doc["screenshot_url"]
        return None

    async def get_diff_image_path(self, comparison_id: str) -> Optional[str]:
        """Return the diff image Cloudinary URL."""
        doc = await self.comparisons_collection.find_one({"comparison_id": comparison_id}, {"diff_image_url": 1})
        if doc and "diff_image_url" in doc:
            return doc["diff_image_url"]
        return None

    async def scan_exists(self, scan_id: str) -> bool:
        """Check whether a scan exists."""
        count = await self.scans_collection.count_documents({"scan_id": scan_id}, limit=1)
        return count > 0

    async def list_scans(self) -> list[dict[str, Any]]:
        """List all available scans with summary information."""
        cursor = self.scans_collection.find({}, {"report": 1, "scan_id": 1}).sort("_id", -1)
        scans = []
        async for doc in cursor:
            scan_id = doc.get("scan_id")
            report = doc.get("report", {})
            scan_info = report.get("scan_info", {})
            
            scans.append({
                "scan_id": scan_info.get("scan_id", scan_id),
                "url": scan_info.get("url", "unknown"),
                "status": scan_info.get("status", "unknown"),
                "created_at": scan_info.get("started_at"),
                "duration_seconds": scan_info.get("duration_seconds"),
            })
        return scans
