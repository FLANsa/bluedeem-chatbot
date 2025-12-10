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
        Build context string from conversation history with smart summarization.
        
        Args:
            conversation_history: List of conversation entries
            max_length: Maximum length of context string
            
        Returns:
            Formatted context string with summary
        """
        if not conversation_history:
            return ""
        
        # Extract important information from conversation
        topics_mentioned = []
        doctors_mentioned = []
        services_mentioned = []
        branches_mentioned = []
        intents_detected = []
        
        # Analyze conversation to extract key information
        for entry in conversation_history:
            message = entry.get('message', '').lower()
            response = entry.get('response', '').lower()
            
            # Detect topics
            if any(word in message or word in response for word in ['طبيب', 'دكتور', 'د.']):
                # Try to extract doctor names
                for word in message.split() + response.split():
                    if len(word) > 3 and word not in ['طبيب', 'دكتور', 'د.']:
                        if word not in doctors_mentioned:
                            doctors_mentioned.append(word)
            
            if any(word in message or word in response for word in ['خدمة', 'خدمات']):
                topics_mentioned.append('خدمات')
            
            if any(word in message or word in response for word in ['فرع', 'فروع', 'فرعنا']):
                topics_mentioned.append('فروع')
            
            if any(word in message or word in response for word in ['حجز', 'موعد', 'احجز']):
                topics_mentioned.append('حجز')
            
            if any(word in message or word in response for word in ['دوام', 'ساعات', 'وقت']):
                topics_mentioned.append('أوقات الدوام')
        
        # Build summary
        summary_parts = []
        if topics_mentioned:
            unique_topics = list(set(topics_mentioned))
            summary_parts.append(f"المواضيع المطروحة: {', '.join(unique_topics)}")
        
        if doctors_mentioned:
            summary_parts.append(f"أطباء تم ذكرهم: {', '.join(doctors_mentioned[:5])}")  # Limit to 5
        
        summary = "\n".join(summary_parts)
        
        # Build conversation history
        context_parts = []
        if summary:
            context_parts.append(f"ملخص المحادثة السابقة:\n{summary}\n")
        
        current_length = len(summary) if summary else 0
        
        # Build from most recent to oldest (reverse order)
        # Prioritize recent messages
        for entry in reversed(conversation_history):
            message = entry.get('message', '')
            response = entry.get('response', '')
            
            entry_text = f"المستخدم: {message}\nالبوت: {response}\n\n"
            entry_length = len(entry_text)
            
            if current_length + entry_length > max_length:
                break
            
            context_parts.append(entry_text)
            current_length += entry_length
        
        result = "\n".join(context_parts).strip()
        
        # Add instruction at the end
        if result:
            result += "\n\n**مهم:** استخدم هذه المعلومات لفهم السياق وربط الأسئلة الحالية بالمحادثة السابقة."
        
        return result


# Global instance
context_manager = ContextManager()

