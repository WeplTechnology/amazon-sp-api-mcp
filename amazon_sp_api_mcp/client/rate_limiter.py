"""
Rate limiting for Amazon SP-API endpoints.
"""

import time
import asyncio
from typing import Dict, Optional
from collections import defaultdict, deque
import logging

from ..config import RATE_LIMITS

logger = logging.getLogger(__name__)

class RateLimiter:
    """Token bucket rate limiter for SP-API endpoints."""
    
    def __init__(self, buffer: float = 0.1):
        self.buffer = buffer
        self.buckets: Dict[str, Dict] = {}
        self.last_request_times: Dict[str, float] = defaultdict(float)
        
        # Initialize buckets for each endpoint
        for endpoint, limits in RATE_LIMITS.items():
            self.buckets[endpoint] = {
                'tokens': limits['burst'],
                'max_tokens': limits['burst'],
                'refill_rate': limits['rate'],
                'last_refill': time.time()
            }
    
    async def acquire(self, endpoint: str) -> None:
        """Acquire permission to make a request to the endpoint."""
        if endpoint not in self.buckets:
            # Default rate limiting for unknown endpoints
            logger.warning(f"Unknown endpoint {endpoint}, using default rate limit")
            endpoint = 'default'
            if endpoint not in self.buckets:
                self.buckets[endpoint] = {
                    'tokens': 10,
                    'max_tokens': 10,
                    'refill_rate': 1.0,
                    'last_refill': time.time()
                }
        
        bucket = self.buckets[endpoint]
        
        while True:
            # Refill tokens
            now = time.time()
            time_passed = now - bucket['last_refill']
            tokens_to_add = time_passed * bucket['refill_rate']
            
            bucket['tokens'] = min(
                bucket['max_tokens'],
                bucket['tokens'] + tokens_to_add
            )
            bucket['last_refill'] = now
            
            # Check if we can make the request
            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                self.last_request_times[endpoint] = now
                logger.debug(f"Rate limit acquired for {endpoint}, {bucket['tokens']:.2f} tokens remaining")
                break
            
            # Calculate wait time
            wait_time = (1 - bucket['tokens']) / bucket['refill_rate']
            wait_time += self.buffer  # Add buffer
            
            logger.debug(f"Rate limit hit for {endpoint}, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
    
    def get_status(self) -> Dict[str, Dict]:
        """Get current rate limiter status."""
        status = {}
        now = time.time()
        
        for endpoint, bucket in self.buckets.items():
            # Update tokens
            time_passed = now - bucket['last_refill']
            tokens_to_add = time_passed * bucket['refill_rate']
            current_tokens = min(
                bucket['max_tokens'],
                bucket['tokens'] + tokens_to_add
            )
            
            status[endpoint] = {
                'current_tokens': round(current_tokens, 2),
                'max_tokens': bucket['max_tokens'],
                'refill_rate': bucket['refill_rate'],
                'last_request': self.last_request_times.get(endpoint, 0)
            }
        
        return status