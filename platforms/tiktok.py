"""TikTok platform handler (stub)."""
from typing import Dict, Any, Optional, Tuple
from platforms.base import PlatformHandler


class TikTokHandler(PlatformHandler):
    """TikTok webhook handler (stub implementation)."""
    
    def parse_incoming(self, request_body: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
        """Parse TikTok webhook request."""
        # TODO: Implement TikTok webhook parsing
        # For now, return mock data
        user_id = request_body.get("user_id", "tiktok_user_123")
        message_text = request_body.get("message", "")
        metadata = {"platform": "tiktok"}
        return user_id, message_text, metadata
    
    def send_outgoing(self, user_id: str, text: str, metadata: Dict[str, Any] = None) -> bool:
        """Send TikTok message."""
        # TODO: Implement TikTok message sending
        import logging
        logging.info(f"[TikTok] Would send to {user_id}: {text}")
        return True
    
    def verify_signature(self, request_body: bytes, signature: str) -> bool:
        """Verify TikTok webhook signature."""
        # TODO: Implement signature verification
        return True

