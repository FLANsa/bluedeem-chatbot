"""Rate limiting middleware."""
from typing import Dict
from datetime import datetime, timedelta
from collections import defaultdict
import config


class RateLimiter:
    """Rate limiter per user."""
    
    def __init__(self):
        """Initialize rate limiter."""
        self.requests: Dict[str, list] = defaultdict(list)
        self.max_requests = config.RATE_LIMIT_PER_MINUTE
        self.window_seconds = 60
    
    def is_allowed(self, user_id: str) -> bool:
        """
        Check if request is allowed.
        
        Args:
            user_id: User ID
            
        Returns:
            True if allowed, False if rate limited
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        # Clean old requests
        self.requests[user_id] = [
            ts for ts in self.requests[user_id]
            if ts > cutoff
        ]
        
        # Check limit
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[user_id].append(now)
        return True
    
    def reset(self, user_id: str):
        """Reset rate limit for user."""
        if user_id in self.requests:
            del self.requests[user_id]


# Global instance
rate_limiter = RateLimiter()

