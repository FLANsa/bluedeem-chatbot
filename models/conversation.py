"""Conversation history models."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from models.booking import Base


class ConversationHistory(Base):
    """Conversation history model for context."""
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    platform = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Index for faster queries
    __table_args__ = (
        Index('idx_user_platform_timestamp', 'user_id', 'platform', 'timestamp'),
    )

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "platform": self.platform,
            "message": self.message,
            "response": self.response,
            "timestamp": self.timestamp.isoformat()
        }

