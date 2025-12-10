"""User preferences models."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from models.booking import Base
import json


class UserPreferences(Base):
    """User preferences model for learning."""
    __tablename__ = "user_preferences"

    user_id = Column(String, primary_key=True)
    platform = Column(String, primary_key=True)
    preferred_doctors = Column(Text, default="[]")  # JSON array
    preferred_branches = Column(Text, default="[]")  # JSON array
    preferred_services = Column(Text, default="[]")  # JSON array
    last_interaction = Column(DateTime, default=datetime.utcnow)
    interaction_count = Column(Integer, default=0)
    metadata_json = Column(Text, default="{}")  # Additional preferences
    
    def get_preferred_doctors(self):
        """Get preferred doctors list."""
        try:
            return json.loads(self.preferred_doctors or "[]")
        except:
            return []
    
    def set_preferred_doctors(self, doctors):
        """Set preferred doctors list."""
        self.preferred_doctors = json.dumps(doctors, ensure_ascii=False)
    
    def get_preferred_branches(self):
        """Get preferred branches list."""
        try:
            return json.loads(self.preferred_branches or "[]")
        except:
            return []
    
    def set_preferred_branches(self, branches):
        """Set preferred branches list."""
        self.preferred_branches = json.dumps(branches, ensure_ascii=False)
    
    def get_preferred_services(self):
        """Get preferred services list."""
        try:
            return json.loads(self.preferred_services or "[]")
        except:
            return []
    
    def set_preferred_services(self, services):
        """Set preferred services list."""
        self.preferred_services = json.dumps(services, ensure_ascii=False)
    
    def get_metadata(self):
        """Get metadata."""
        try:
            return json.loads(self.metadata_json or "{}")
        except:
            return {}
    
    def set_metadata(self, metadata):
        """Set metadata."""
        self.metadata_json = json.dumps(metadata, ensure_ascii=False)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "platform": self.platform,
            "preferred_doctors": self.get_preferred_doctors(),
            "preferred_branches": self.get_preferred_branches(),
            "preferred_services": self.get_preferred_services(),
            "last_interaction": self.last_interaction.isoformat() if self.last_interaction else None,
            "interaction_count": self.interaction_count,
            "metadata": self.get_metadata()
        }

