"""WhatsApp platform handler."""
import hmac
import hashlib
import json
from typing import Dict, Any, Optional, Tuple
import httpx
from platforms.base import PlatformHandler
import config


class WhatsAppHandler(PlatformHandler):
    """WhatsApp webhook handler."""
    
    def __init__(self):
        """Initialize WhatsApp handler."""
        self.webhook_secret = config.WHATSAPP_WEBHOOK_SECRET
        self.verify_token = config.WHATSAPP_VERIFY_TOKEN
        # TODO: Add WhatsApp API credentials
        self.api_url = ""  # Meta WhatsApp API URL
        self.access_token = ""  # Meta access token
    
    def parse_incoming(self, request_body: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
        """
        Parse WhatsApp webhook request.
        
        WhatsApp webhook format (Meta):
        {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "user_id",
                            "text": {"body": "message"}
                        }]
                    }
                }]
            }]
        }
        """
        try:
            # Extract message from webhook
            entry = request_body.get("entry", [])
            if not entry:
                return None, None, {}
            
            changes = entry[0].get("changes", [])
            if not changes:
                return None, None, {}
            
            value = changes[0].get("value", {})
            messages = value.get("messages", [])
            
            if not messages:
                return None, None, {}
            
            message = messages[0]
            user_id = message.get("from", "")
            message_text = message.get("text", {}).get("body", "")
            
            metadata = {
                "message_id": message.get("id", ""),
                "timestamp": message.get("timestamp", ""),
                "type": message.get("type", "")
            }
            
            return user_id, message_text, metadata
            
        except Exception as e:
            import logging
            logging.error(f"Error parsing WhatsApp webhook: {e}")
            return None, None, {}
    
    def send_outgoing(self, user_id: str, text: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Send WhatsApp message.
        
        Args:
            user_id: WhatsApp user ID
            text: Message text
            metadata: Optional metadata
            
        Returns:
            True if successful
        """
        # Format text for WhatsApp (Bold, etc.)
        from utils.whatsapp_formatter import format_whatsapp_text
        formatted_text = format_whatsapp_text(text)
        
        if not self.api_url or not self.access_token:
            # In development, just log
            import logging
            logging.info(f"[WhatsApp] Would send to {user_id}: {formatted_text}")
            return True
        
        try:
            payload = {
                "messaging_product": "whatsapp",
                "to": user_id,
                "type": "text",
                "text": {"body": formatted_text}
            }
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Retry logic with backoff
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    with httpx.Client(timeout=10.0) as client:
                        response = client.post(
                            f"{self.api_url}/messages",
                            json=payload,
                            headers=headers
                        )
                        response.raise_for_status()
                        return True
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    # Exponential backoff
                    import time
                    time.sleep(2 ** attempt)
            
            return False
            
        except Exception as e:
            import logging
            logging.error(f"Error sending WhatsApp message: {e}")
            return False
    
    def verify_signature(self, request_body: bytes, signature: str) -> bool:
        """
        Verify WhatsApp webhook signature.
        
        Args:
            request_body: Raw request body
            signature: X-Hub-Signature-256 header value
            
        Returns:
            True if signature is valid
        """
        if not self.webhook_secret:
            return True  # Skip verification if no secret configured
        
        try:
            # Meta uses HMAC SHA256
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                request_body,
                hashlib.sha256
            ).hexdigest()
            
            # Signature format: sha256=<hash>
            if signature.startswith("sha256="):
                received_signature = signature[7:]
            else:
                received_signature = signature
            
            return hmac.compare_digest(expected_signature, received_signature)
            
        except Exception as e:
            import logging
            logging.error(f"Error verifying signature: {e}")
            return False
    
    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Verify webhook during setup (GET request).
        
        Args:
            mode: 'subscribe' mode
            token: Verify token
            challenge: Challenge string
            
        Returns:
            Challenge if verified, None otherwise
        """
        if mode == "subscribe" and token == self.verify_token:
            return challenge
        return None

