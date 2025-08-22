"""
Redis client configuration for caching and session management.
"""
import redis
import json
import logging
from typing import Optional, Any, Dict, List
from functools import wraps
import pickle

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create Redis client
redis_client = redis.Redis.from_url(
    settings.redis_url,
    db=settings.redis_db,
    decode_responses=False,  # Keep as bytes for pickle compatibility
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True
)


def check_redis_connection() -> bool:
    """Check if Redis connection is working."""
    try:
        redis_client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis connection check failed: {e}")
        return False


class CacheManager:
    """Manages caching operations with Redis."""
    
    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self.client = redis_client
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in cache with optional TTL."""
        try:
            serialized_value = pickle.dumps(value)
            ttl = ttl or self.default_ttl
            return self.client.setex(key, ttl, serialized_value)
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        try:
            value = self.client.get(key)
            if value is not None:
                return pickle.loads(value)
            return None
        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Failed to check cache key {key}: {e}")
            return False
    
    def set_hash(self, key: str, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set a hash in cache."""
        try:
            serialized_mapping = {k: pickle.dumps(v) for k, v in mapping.items()}
            result = self.client.hset(key, mapping=serialized_mapping)
            if ttl:
                self.client.expire(key, ttl)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to set hash {key}: {e}")
            return False
    
    def get_hash(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a hash from cache."""
        try:
            hash_data = self.client.hgetall(key)
            if hash_data:
                return {k.decode(): pickle.loads(v) for k, v in hash_data.items()}
            return None
        except Exception as e:
            logger.error(f"Failed to get hash {key}: {e}")
            return None
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter in cache."""
        try:
            return self.client.incr(key, amount)
        except Exception as e:
            logger.error(f"Failed to increment {key}: {e}")
            return None


# Global cache manager instance
cache_manager = CacheManager()


def cache_result(ttl: int = 3600, key_prefix: str = ""):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache first
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator


class SessionManager:
    """Manages user sessions with Redis."""
    
    def __init__(self, session_ttl: int = 86400):  # 24 hours
        self.session_ttl = session_ttl
        self.client = redis_client
    
    def create_session(self, user_id: str, session_data: Dict[str, Any]) -> str:
        """Create a new session for a user."""
        import uuid
        session_id = str(uuid.uuid4())
        session_key = f"session:{session_id}"
        
        session_data['user_id'] = user_id
        session_data['created_at'] = str(uuid.uuid1().time)
        
        self.client.setex(session_key, self.session_ttl, json.dumps(session_data))
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data by session ID."""
        session_key = f"session:{session_id}"
        try:
            session_data = self.client.get(session_key)
            if session_data:
                return json.loads(session_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        session_key = f"session:{session_id}"
        try:
            return bool(self.client.delete(session_key))
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    def extend_session(self, session_id: str) -> bool:
        """Extend session TTL."""
        session_key = f"session:{session_id}"
        try:
            return bool(self.client.expire(session_key, self.session_ttl))
        except Exception as e:
            logger.error(f"Failed to extend session {session_id}: {e}")
            return False


# Global session manager instance
session_manager = SessionManager() 