"""Database models for booking system."""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import json
import os

Base = declarative_base()


class BookingTicket(Base):
    """Booking ticket model."""
    __tablename__ = "booking_tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    platform = Column(String, nullable=False)
    payload_json = Column(Text, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "platform": self.platform,
            "payload": json.loads(self.payload_json),
            "status": self.status,
            "created_at": self.created_at.isoformat()
        }


class ConversationState(Base):
    """Conversation state model."""
    __tablename__ = "conversation_state"

    user_id = Column(String, primary_key=True)
    platform = Column(String, primary_key=True)
    state = Column(String, nullable=False)
    data_json = Column(Text, default="{}")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_data(self) -> Dict[str, Any]:
        """Get parsed data."""
        return json.loads(self.data_json or "{}")

    def set_data(self, data: Dict[str, Any]):
        """Set data."""
        self.data_json = json.dumps(data, ensure_ascii=False)


class ProcessedMessage(Base):
    """Processed message model for deduplication."""
    __tablename__ = "processed_messages"

    platform = Column(String, primary_key=True)
    message_id = Column(String, primary_key=True)
    processed_at = Column(DateTime, default=datetime.utcnow)


# Database setup
engine = create_engine(
    os.getenv('DATABASE_URL', 'sqlite:///bluedeem.db'),
    connect_args={"check_same_thread": False} if "sqlite" in os.getenv('DATABASE_URL', 'sqlite:///bluedeem.db') else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables."""
    # Import all models to ensure they're registered
    from models import conversation, user_preferences
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

