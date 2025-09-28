"""
Rate limiting utilities for GitHub API and other external services
"""
import asyncio
import time
from typing import Dict, Optional
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class SimpleRateLimiter:
    """Simple rate limiter to prevent API abuse"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[str, list] = {}
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for the given key"""
        now = time.time()
        
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove old requests outside the time window
        self.requests[key] = [
            req_time for req_time in self.requests[key] 
            if now - req_time < self.time_window
        ]
        
        # Check if we're under the limit
        if len(self.requests[key]) < self.max_requests:
            self.requests[key].append(now)
            return True
        
        return False
    
    def get_reset_time(self, key: str) -> Optional[float]:
        """Get the time when the rate limit will reset"""
        if key not in self.requests or not self.requests[key]:
            return None
        
        oldest_request = min(self.requests[key])
        return oldest_request + self.time_window

# Global rate limiter for GitHub API
github_rate_limiter = SimpleRateLimiter(max_requests=30, time_window=60)  # 30 requests per minute

def rate_limit_github_api(func):
    """Decorator to rate limit GitHub API calls"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Use the token or a default key for rate limiting
        token = kwargs.get('token', 'default')
        rate_limit_key = f"github_api_{token}"
        
        if not github_rate_limiter.is_allowed(rate_limit_key):
            reset_time = github_rate_limiter.get_reset_time(rate_limit_key)
            wait_time = reset_time - time.time() if reset_time else 60
            
            logger.warning(f"Rate limit exceeded for GitHub API. Waiting {wait_time:.1f} seconds.")
            
            # Wait for rate limit to reset
            await asyncio.sleep(min(wait_time, 60))  # Cap at 1 minute
            
            # Try again after waiting
            if not github_rate_limiter.is_allowed(rate_limit_key):
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=429,
                    detail="GitHub API rate limit exceeded. Please try again later."
                )
        
        return await func(*args, **kwargs)
    
    return wrapper

def get_rate_limit_status(key: str) -> Dict[str, any]:
    """Get rate limit status for a key"""
    now = time.time()
    
    if key not in github_rate_limiter.requests:
        return {
            "requests_made": 0,
            "requests_remaining": github_rate_limiter.max_requests,
            "reset_time": None,
            "is_limited": False
        }
    
    # Clean old requests
    github_rate_limiter.requests[key] = [
        req_time for req_time in github_rate_limiter.requests[key] 
        if now - req_time < github_rate_limiter.time_window
    ]
    
    requests_made = len(github_rate_limiter.requests[key])
    requests_remaining = max(0, github_rate_limiter.max_requests - requests_made)
    reset_time = github_rate_limiter.get_reset_time(key)
    
    return {
        "requests_made": requests_made,
        "requests_remaining": requests_remaining,
        "reset_time": reset_time,
        "is_limited": requests_remaining == 0
    }