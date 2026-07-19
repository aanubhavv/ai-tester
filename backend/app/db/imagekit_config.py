import logging
from imagekitio import ImageKit
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global ImageKit instance
imagekit_client = None

def setup_imagekit():
    global imagekit_client
    if settings.imagekit_public_key and settings.imagekit_private_key and settings.imagekit_url_endpoint:
        imagekit_client = ImageKit(
            public_key=settings.imagekit_public_key,
            private_key=settings.imagekit_private_key,
            url_endpoint=settings.imagekit_url_endpoint
        )
        logger.info("ImageKit configured successfully.")
    else:
        logger.warning("ImageKit credentials are not set. Image uploads will fail.")

def get_imagekit():
    return imagekit_client
