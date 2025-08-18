import asyncio
import time
from typing import Dict, Optional
import redis.asyncio as aioredis
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-based rate limiter with token bucket algorithm"""
    
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        
        # Rate limiting rules (requests per time window)
        self.limits = {
            "user": 10,     # 10 requests per 60 seconds per user
            "global": 100,  # 100 requests per minute globally
            "voice": 3,     # 3 voice requests per 60 seconds per user
            "gpt": 5        # 5 GPT requests per 60 seconds per user
        }
        
        # Time windows in seconds
        self.windows = {
            "user": 60,     # 1 minute window for user requests
            "global": 60,   # 1 minute window for global requests
            "voice": 60,    # 1 minute window for voice requests
            "gpt": 60       # 1 minute window for GPT requests
        }
    
    async def is_allowed(self, key: str, limit_type: str = "user") -> bool:
        """Check if request is allowed under rate limit"""
        try:
            limit = self.limits.get(limit_type, 1)
            window = self.windows.get(limit_type, 1)
            
            # Redis key for this rate limit
            redis_key = f"rate_limit:{limit_type}:{key}"
            
            # Current timestamp
            now = int(time.time())
            
            # Use Redis pipeline for atomic operations
            pipe = self.redis.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(redis_key, 0, now - window)
            
            # Count current requests in window
            pipe.zcard(redis_key)
            
            # Execute pipeline
            results = await pipe.execute()
            current_count = results[1]
            
            # Check if under limit
            if current_count < limit:
                # Add current request
                await self.redis.zadd(redis_key, {str(now): now})
                await self.redis.expire(redis_key, window + 1)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open - allow request if Redis is down
            return True
    
    async def get_remaining(self, key: str, limit_type: str = "user") -> int:
        """Get remaining requests for this key"""
        try:
            limit = self.limits.get(limit_type, 1)
            window = self.windows.get(limit_type, 1)
            redis_key = f"rate_limit:{limit_type}:{key}"
            
            now = int(time.time())
            
            # Clean old entries and count current
            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(redis_key, 0, now - window)
            pipe.zcard(redis_key)
            
            results = await pipe.execute()
            current_count = results[1]
            
            return max(0, limit - current_count)
            
        except Exception as e:
            logger.error(f"Failed to get remaining requests: {e}")
            return 0
    
    async def get_reset_time(self, key: str, limit_type: str = "user") -> int:
        """Get timestamp when rate limit resets"""
        try:
            window = self.windows.get(limit_type, 1)
            redis_key = f"rate_limit:{limit_type}:{key}"
            
            # Get oldest entry in current window
            oldest_entries = await self.redis.zrange(redis_key, 0, 0, withscores=True)
            
            if oldest_entries:
                oldest_timestamp = int(oldest_entries[0][1])
                return oldest_timestamp + window
            
            return int(time.time())
            
        except Exception as e:
            logger.error(f"Failed to get reset time: {e}")
            return int(time.time())
    
    async def clear_user_limits(self, user_id: str):
        """Clear all rate limits for a user (admin function)"""
        try:
            pattern = f"rate_limit:*:{user_id}"
            keys = await self.redis.keys(pattern)
            
            if keys:
                await self.redis.delete(*keys)
                logger.info(f"Cleared rate limits for user {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to clear user limits: {e}")


class AIORateLimiter:
    """Async context manager for rate limiting"""
    
    def __init__(self, rate_limiter: RateLimiter, key: str, limit_type: str = "user"):
        self.rate_limiter = rate_limiter
        self.key = key
        self.limit_type = limit_type
        self.allowed = False
    
    async def __aenter__(self):
        self.allowed = await self.rate_limiter.is_allowed(self.key, self.limit_type)
        return self.allowed
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# Decorator for rate limiting
def rate_limit(limit_type: str = "user"):
    """Decorator to rate limit function calls"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract user_id from function arguments or context
            user_id = kwargs.get('user_id') or getattr(args[0], 'user_id', 'unknown')
            
            # Get rate limiter from global context or dependency injection
            rate_limiter = kwargs.get('rate_limiter')
            if not rate_limiter:
                logger.warning("No rate limiter provided, skipping rate limit check")
                return await func(*args, **kwargs)
            
            # Check rate limit
            if await rate_limiter.is_allowed(str(user_id), limit_type):
                return await func(*args, **kwargs)
            else:
                logger.warning(f"Rate limit exceeded for user {user_id}, type {limit_type}")
                raise Exception(f"Rate limit exceeded. Please try again later.")
        
        return wrapper
    return decorator