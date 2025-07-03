"""
HTTP client for Amazon SP-API with authentication and rate limiting.
"""

import asyncio
import json
from typing import Dict, Any, Optional, Union
from urllib.parse import urljoin
import logging

import requests
from botocore.awsrequest import AWSRequest

from ..config import SPAPIConfig
from ..auth.lwa_auth import LWATokenManager
from ..auth.aws_auth import AWSAuthManager
from .rate_limiter import RateLimiter
from .error_handler import SPAPIErrorHandler

logger = logging.getLogger(__name__)

class SPAPIClient:
    """HTTP client for Amazon SP-API with full authentication and rate limiting."""
    
    def __init__(self, config: SPAPIConfig):
        self.config = config
        self.lwa_manager = LWATokenManager(config)
        self.aws_manager = AWSAuthManager(config)
        self.rate_limiter = RateLimiter(config.rate_limit_buffer)
        self.error_handler = SPAPIErrorHandler(config.retry_attempts)
        self.session = requests.Session()
        
        # Configure session
        self.session.timeout = config.timeout
        
    async def request(
        self,
        method: str,
        endpoint: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict, str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_rdt: bool = False,
        rdt_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make an authenticated request to SP-API."""
        
        # Apply rate limiting
        await self.rate_limiter.acquire(endpoint)
        
        # Prepare URL
        url = urljoin(self.config.base_url, path)
        
        # Prepare headers
        request_headers = {
            'User-Agent': 'amazon-sp-api-mcp/1.0.0',
            'Content-Type': 'application/json'
        }
        
        if headers:
            request_headers.update(headers)
        
        # Add authentication
        if use_rdt and rdt_token:
            # Use Restricted Data Token for PII operations
            request_headers['x-amz-access-token'] = rdt_token
        else:
            # Use LWA access token
            access_token = self.lwa_manager.get_access_token()
            request_headers['x-amz-access-token'] = access_token
        
        # Prepare request data
        request_data = None
        if data:
            if isinstance(data, (dict, list)):
                request_data = json.dumps(data).encode('utf-8')
            elif isinstance(data, str):
                request_data = data.encode('utf-8')
            elif isinstance(data, bytes):
                request_data = data
        
        # Create and sign AWS request
        aws_request = self.aws_manager.create_signed_request(
            method=method.upper(),
            url=url,
            headers=request_headers,
            data=request_data
        )
        
        # Add query parameters
        if params:
            aws_request.url += '?' + '&'.join(
                f"{k}={v}" for k, v in params.items() if v is not None
            )
        
        # Execute request with retry logic
        return await self.error_handler.execute_with_retry(
            self._execute_request, aws_request
        )
    
    async def _execute_request(self, aws_request: AWSRequest) -> Dict[str, Any]:
        """Execute the actual HTTP request."""
        try:
            # Convert AWS request to requests format
            response = self.session.request(
                method=aws_request.method,
                url=aws_request.url,
                headers=dict(aws_request.headers),
                data=aws_request.body,
                timeout=self.config.timeout
            )
            
            # Log request details in debug mode
            if self.config.debug:
                logger.debug(f"Request: {aws_request.method} {aws_request.url}")
                logger.debug(f"Response: {response.status_code} {response.text[:200]}...")
            
            # Handle response
            if response.status_code == 204:  # No Content
                return {'success': True}
            
            # Parse JSON response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {'raw_content': response.text}
            
            # Check for API errors
            if response.status_code >= 400:
                error_info = {
                    'status_code': response.status_code,
                    'response': response_data,
                    'url': aws_request.url,
                    'method': aws_request.method
                }
                raise SPAPIError(f"API error {response.status_code}", error_info)
            
            return response_data
            
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise SPAPIError(f"Request failed: {e}", {'original_error': str(e)})
    
    async def get(self, endpoint: str, path: str, params: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Make a GET request."""
        return await self.request('GET', endpoint, path, params=params, **kwargs)
    
    async def post(self, endpoint: str, path: str, data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Make a POST request."""
        return await self.request('POST', endpoint, path, data=data, **kwargs)
    
    async def put(self, endpoint: str, path: str, data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Make a PUT request."""
        return await self.request('PUT', endpoint, path, data=data, **kwargs)
    
    async def patch(self, endpoint: str, path: str, data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Make a PATCH request."""
        return await self.request('PATCH', endpoint, path, data=data, **kwargs)
    
    async def delete(self, endpoint: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make a DELETE request."""
        return await self.request('DELETE', endpoint, path, **kwargs)
    
    def validate_connection(self) -> Dict[str, Any]:
        """Validate SP-API connection by testing authentication."""
        result = {
            'lwa_auth': self.lwa_manager.validate_credentials(),
            'aws_auth': self.aws_manager.validate_credentials(),
            'rate_limiter': self.rate_limiter.get_status()
        }
        
        result['overall_valid'] = (
            result['lwa_auth']['valid'] and 
            result['aws_auth']['valid']
        )
        
        return result
    
    def close(self):
        """Close the HTTP session."""
        self.session.close()

class SPAPIError(Exception):
    """Custom exception for SP-API errors."""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.details = details or {}