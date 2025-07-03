"""
Login with Amazon (LWA) authentication for SP-API.
"""

import time
import requests
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from ..config import SPAPIConfig

logger = logging.getLogger(__name__)

class LWATokenManager:
    """Manages LWA access tokens for SP-API authentication."""
    
    def __init__(self, config: SPAPIConfig):
        self.config = config
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.lwa_endpoint = "https://api.amazon.com/auth/o2/token"
        
    def get_access_token(self, force_refresh: bool = False) -> str:
        """Get a valid access token, refreshing if necessary."""
        if self._is_token_expired() or force_refresh:
            self._refresh_access_token()
            
        if not self.access_token:
            raise Exception("Failed to obtain access token")
            
        return self.access_token
    
    def _is_token_expired(self) -> bool:
        """Check if current token is expired or will expire soon."""
        if not self.access_token or not self.token_expires_at:
            return True
            
        # Refresh 5 minutes before expiry
        buffer_time = timedelta(minutes=5)
        return datetime.utcnow() + buffer_time >= self.token_expires_at
    
    def _refresh_access_token(self) -> None:
        """Refresh the LWA access token using refresh token."""
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
        }
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.config.refresh_token,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret
        }
        
        try:
            logger.debug("Refreshing LWA access token")
            response = requests.post(
                self.lwa_endpoint,
                headers=headers,
                data=data,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            logger.info(f"LWA token refreshed, expires at {self.token_expires_at}")
            
        except requests.RequestException as e:
            logger.error(f"Failed to refresh LWA token: {e}")
            raise Exception(f"LWA token refresh failed: {e}")
        except KeyError as e:
            logger.error(f"Invalid token response format: {e}")
            raise Exception(f"Invalid LWA token response: {e}")
    
    def get_client_credentials_token(self, scope: str) -> str:
        """Get client credentials token for grantless operations."""
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
        }
        
        data = {
            "grant_type": "client_credentials",
            "scope": scope,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret
        }
        
        try:
            logger.debug(f"Getting client credentials token for scope: {scope}")
            response = requests.post(
                self.lwa_endpoint,
                headers=headers,
                data=data,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            token_data = response.json()
            return token_data["access_token"]
            
        except requests.RequestException as e:
            logger.error(f"Failed to get client credentials token: {e}")
            raise Exception(f"Client credentials token failed: {e}")
    
    def validate_credentials(self) -> Dict[str, Any]:
        """Validate LWA credentials by attempting token refresh."""
        try:
            # Test refresh token
            old_token = self.access_token
            self._refresh_access_token()
            
            result = {
                "valid": True,
                "client_id": self.config.client_id,
                "token_expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
                "message": "LWA credentials are valid"
            }
            
            # Restore old token if validation was called
            if old_token and not self._is_token_expired():
                self.access_token = old_token
                
            return result
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "message": "LWA credentials validation failed"
            }