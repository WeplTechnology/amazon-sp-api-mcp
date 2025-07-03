"""
Authentication tools for Amazon SP-API MCP.
"""

from typing import Dict, Any
import logging

from ..client.http_client import SPAPIClient
from ..config import SPAPIConfig, EUROPE_MARKETPLACES

logger = logging.getLogger(__name__)

class AuthTools:
    """Authentication and validation tools for SP-API."""
    
    def __init__(self, client: SPAPIClient, config: SPAPIConfig):
        self.client = client
        self.config = config
    
    async def validate_credentials(self) -> Dict[str, Any]:
        """Validate all SP-API credentials and configuration."""
        try:
            # Validate connection
            validation_result = self.client.validate_connection()
            
            # Add configuration details
            result = {
                'success': True,
                'validation': validation_result,
                'configuration': {
                    'region': self.config.region,
                    'base_url': self.config.base_url,
                    'marketplace_ids': self.config.marketplace_ids,
                    'sandbox': self.config.sandbox
                },
                'marketplaces': {
                    mid: EUROPE_MARKETPLACES.get(mid, f'Unknown marketplace {mid}')
                    for mid in self.config.marketplace_ids
                }
            }
            
            if not validation_result['overall_valid']:
                result['success'] = False
                result['error'] = 'Credential validation failed'
            
            return result
            
        except Exception as e:
            logger.error(f"Credential validation error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to validate credentials'
            }
    
    async def refresh_access_token(self) -> Dict[str, Any]:
        """Manually refresh the LWA access token."""
        try:
            # Force refresh
            access_token = self.client.lwa_manager.get_access_token(force_refresh=True)
            
            return {
                'success': True,
                'message': 'Access token refreshed successfully',
                'expires_at': self.client.lwa_manager.token_expires_at.isoformat() if self.client.lwa_manager.token_expires_at else None,
                'token_preview': f"{access_token[:10]}..." if access_token else None
            }
            
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to refresh access token'
            }
    
    async def get_marketplace_participation(self) -> Dict[str, Any]:
        """Get marketplace participation information."""
        try:
            # Call SP-API to get marketplace participation
            response = await self.client.get(
                endpoint='sellers',
                path='/sellers/v1/marketplaceParticipations'
            )
            
            # Process response
            participations = response.get('payload', [])
            
            result = {
                'success': True,
                'participations': [],
                'summary': {
                    'total_marketplaces': len(participations),
                    'configured_marketplaces': len(self.config.marketplace_ids)
                }
            }
            
            for participation in participations:
                marketplace = participation.get('marketplace', {})
                marketplace_id = marketplace.get('id')
                
                participation_info = {
                    'marketplace_id': marketplace_id,
                    'marketplace_name': EUROPE_MARKETPLACES.get(marketplace_id, marketplace.get('name', 'Unknown')),
                    'country_code': marketplace.get('countryCode'),
                    'default_currency': marketplace.get('defaultCurrencyCode'),
                    'default_language': marketplace.get('defaultLanguageCode'),
                    'is_participating': participation.get('isParticipating', False),
                    'has_suspended_listings': participation.get('hasSuspendedListings', False),
                    'configured': marketplace_id in self.config.marketplace_ids
                }
                
                result['participations'].append(participation_info)
            
            return result
            
        except Exception as e:
            logger.error(f"Marketplace participation error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to get marketplace participation'
            }