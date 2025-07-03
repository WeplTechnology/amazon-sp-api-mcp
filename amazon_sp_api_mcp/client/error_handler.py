"""
Error handling and retry logic for Amazon SP-API.
"""

import asyncio
import random
from typing import Callable, Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class SPAPIErrorHandler:
    """Handles errors and implements retry logic for SP-API requests."""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        
    async def execute_with_retry(
        self, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """Execute function with exponential backoff retry logic."""
        
        for attempt in range(self.max_retries + 1):
            try:
                return await self._call_function(func, *args, **kwargs)
                
            except Exception as e:
                # Check if we should retry
                if attempt == self.max_retries or not self._should_retry(e):
                    raise
                
                # Calculate backoff time
                backoff_time = self._calculate_backoff(attempt)
                
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.max_retries + 1}), "
                    f"retrying in {backoff_time:.2f}s: {e}"
                )
                
                await asyncio.sleep(backoff_time)
    
    async def _call_function(self, func: Callable, *args, **kwargs) -> Any:
        """Call function, handling both sync and async."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    
    def _should_retry(self, error: Exception) -> bool:
        """Determine if an error should trigger a retry."""
        # Import here to avoid circular imports
        from .http_client import SPAPIError
        
        if isinstance(error, SPAPIError):
            if hasattr(error, 'details') and error.details:
                status_code = error.details.get('status_code')
                
                # Retry on server errors (5xx) and rate limiting (429)
                if status_code in [429, 500, 502, 503, 504]:
                    return True
                
                # Retry on authentication errors (token might have expired)
                if status_code == 401:
                    return True
                
                # Don't retry on client errors (4xx except 401, 429)
                if 400 <= status_code < 500:
                    return False
        
        # Retry on network/connection errors
        if isinstance(error, (ConnectionError, TimeoutError)):
            return True
        
        # Don't retry by default
        return False
    
    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter."""
        # Exponential backoff: 2^attempt seconds
        base_delay = 2 ** attempt
        
        # Add jitter (random factor between 0.5 and 1.5)
        jitter = random.uniform(0.5, 1.5)
        
        # Cap at 60 seconds
        return min(60, base_delay * jitter)
    
    def format_error(self, error: Exception) -> Dict[str, Any]:
        """Format error for user-friendly display."""
        from .http_client import SPAPIError
        
        if isinstance(error, SPAPIError):
            result = {
                'type': 'SPAPIError',
                'message': str(error),
                'details': error.details
            }
            
            # Add specific error guidance
            if error.details:
                status_code = error.details.get('status_code')
                if status_code == 401:
                    result['guidance'] = 'Authentication failed. Check your LWA credentials and refresh token.'
                elif status_code == 403:
                    result['guidance'] = 'Access forbidden. Check your application permissions and roles.'
                elif status_code == 429:
                    result['guidance'] = 'Rate limit exceeded. The request will be retried automatically.'
                elif status_code >= 500:
                    result['guidance'] = 'Amazon server error. The request will be retried automatically.'
                elif status_code == 400:
                    result['guidance'] = 'Bad request. Check your request parameters.'
            
            return result
        
        else:
            return {
                'type': type(error).__name__,
                'message': str(error),
                'guidance': 'An unexpected error occurred.'
            }