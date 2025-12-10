"""Context manager for conversation history."""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
from models.conversation import ConversationHistory
from data.db import get_database_session

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages conversation context and history."""
    
    def __init__(self):
        """Initialize context manager."""
        self.db = get_database_session()
    
    def get_recent_context(
        self,
        user_id: str,
        platform: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversation history for context.
        
        Args:
            user_id: User ID
            platform: Platform name
            limit: Number of recent messages to retrieve
            
        Returns:
            List of conversation history entries
        """
        try:
            history = self.db.query(ConversationHistory).filter(
                ConversationHistory.user_id == user_id,
                ConversationHistory.platform == platform
            ).order_by(
                ConversationHistory.timestamp.desc()
            ).limit(limit).all()
            
            # Reverse to get chronological order
            return [h.to_dict() for h in reversed(history)]
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return []
    
    def add_to_context(
        self,
        user_id: str,
        platform: str,
        message: str,
        response: str
    ):
        """
        Add conversation to history.
        
        Args:
            user_id: User ID
            platform: Platform name
            message: User message
            response: Bot response
        """
        try:
            history_entry = ConversationHistory(
                user_id=user_id,
                platform=platform,
                message=message,
                response=response,
                timestamp=datetime.utcnow()
            )
            self.db.add(history_entry)
            self.db.commit()
        except Exception as e:
            logger.error(f"Error adding to context: {e}")
            self.db.rollback()
    
    def build_context_string(
        self,
        conversation_history: List[Dict[str, Any]],
        max_length: int = 2000
    ) -> str:
        """
        Build context string from conversation history.
        
        Args:
            conversation_history: List of conversation entries
            max_length: Maximum length of context string
            
        Returns:
            Formatted context string
        """
        if not conversation_history:
            return ""
        
        context_parts = []
        current_length = 0
        
        # Build from most recent to oldest (reverse order)
        for entry in reversed(conversation_history):
            message = entry.get('message', '')
            response = entry.get('response', '')
            
            entry_text = f"المستخدم: {message}\nالبوت: {response}\n\n"
            entry_length = len(entry_text)
            
            if current_length + entry_length > max_length:
                break
            
            context_parts.insert(0, entry_text)
            current_length += entry_length
        
        return "".join(context_parts).strip()


# Global instance
context_manager = ContextManager()

