"""Instagram platform handler (stub)."""
from typing import Dict, Any, Optional, Tuple
from platforms.base import PlatformHandler


class InstagramHandler(PlatformHandler):
    """Instagram webhook handler (stub implementation)."""
    
    def parse_incoming(self, request_body: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
        """Parse Instagram webhook request."""
        # TODO: Implement Instagram webhook parsing
        # For now, return mock data
        user_id = request_body.get("user_id", "instagram_user_123")
        message_text = request_body.get("message", "")
        metadata = {"platform": "instagram"}
        return user_id, message_text, metadata
    
    def send_outgoing(self, user_id: str, text: str, metadata: Dict[str, Any] = None) -> bool:
        """Send Instagram message."""
        # TODO: Implement Instagram message sending
        import logging
        logging.info(f"[Instagram] Would send to {user_id}: {text}")
        return True
    
    def verify_signature(self, request_body: bytes, signature: str) -> bool:
        """Verify Instagram webhook signature."""
        # TODO: Implement signature verification
        return True

