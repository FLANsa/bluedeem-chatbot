"""Database initialization and utilities."""
from models.booking import init_db, SessionLocal, Base
from models.conversation import ConversationHistory
from models.user_preferences import UserPreferences
import os


def initialize_database():
    """Initialize database tables."""
    # Import all models to ensure they're registered
    from models import conversation, user_preferences
    init_db()


def get_database_session():
    """Get database session."""
    return SessionLocal()

