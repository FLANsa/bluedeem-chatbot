"""Logging middleware."""
import uuid
import json
import logging
from typing import Dict, Any
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def log_request(
    request_id: str,
    user_id: str,
    platform: str,
    message: str,
    response: str = None,
    metadata: Dict[str, Any] = None
):
    """
    Log request with structured data.
    
    Args:
        request_id: Unique request ID
        user_id: User ID
        platform: Platform name
        message: User message
        response: Bot response (optional)
        metadata: Additional metadata
    """
    log_data = {
        "request_id": request_id,
        "user_id": user_id,
        "platform": platform,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    if response:
        log_data["response"] = response
    
    if metadata:
        log_data["metadata"] = metadata
    
    logger.info(json.dumps(log_data, ensure_ascii=False))


def generate_request_id() -> str:
    """Generate unique request ID."""
    return str(uuid.uuid4())

