"""Base platform interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class PlatformHandler(ABC):
    """Abstract base class for platform handlers."""
    
    @abstractmethod
    def parse_incoming(self, request_body: Dict[str, Any]) -> tuple[Optional[str], Optional[str], Dict[str, Any]]:
        """
        Parse incoming webhook request.
        
        Returns:
            (user_id, message_text, metadata)
        """
        pass
    
    @abstractmethod
    def send_outgoing(self, user_id: str, text: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Send outgoing message.
        
        Args:
            user_id: User ID
            text: Message text
            metadata: Optional metadata
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def verify_signature(self, request_body: bytes, signature: str) -> bool:
        """
        Verify webhook signature.
        
        Args:
            request_body: Raw request body
            signature: Signature header value
            
        Returns:
            True if signature is valid
        """
        pass

