"""
Tests for HTTP client.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from amazon_sp_api_mcp.config import SPAPIConfig
from amazon_sp_api_mcp.client.http_client import SPAPIClient
from amazon_sp_api_mcp.client.rate_limiter import RateLimiter

@pytest.fixture
def test_config():
    """Create test configuration."""
    return SPAPIConfig(
        client_id="test_client_id",
        client_secret="test_client_secret",
        refresh_token="test_refresh_token",
        aws_access_key_id="test_access_key",
        aws_secret_access_key="test_secret_key",
        aws_region="eu-west-1",
        aws_role_arn="arn:aws:iam::123456789012:role/test-role"
    )

class TestRateLimiter:
    """Tests for Rate Limiter."""
    
    def test_init(self):
        """Test rate limiter initialization."""
        rate_limiter = RateLimiter(buffer=0.1)
        
        assert rate_limiter.buffer == 0.1
        assert len(rate_limiter.buckets) > 0
        assert 'orders' in rate_limiter.buckets
        assert 'inventory' in rate_limiter.buckets
    
    @pytest.mark.asyncio
    async def test_acquire_with_available_tokens(self):
        """Test acquiring rate limit with available tokens."""
        rate_limiter = RateLimiter()
        
        # Should acquire immediately with full bucket
        await rate_limiter.acquire('orders')
        
        # Check that tokens were consumed
        status = rate_limiter.get_status()
        assert status['orders']['current_tokens'] < status['orders']['max_tokens']
    
    def test_get_status(self):
        """Test getting rate limiter status."""
        rate_limiter = RateLimiter()
        status = rate_limiter.get_status()
        
        assert isinstance(status, dict)
        assert 'orders' in status
        assert 'current_tokens' in status['orders']
        assert 'max_tokens' in status['orders']
        assert 'refill_rate' in status['orders']

class TestSPAPIClient:
    """Tests for SP-API Client."""
    
    def test_init(self, test_config):
        """Test SP-API client initialization."""
        client = SPAPIClient(test_config)
        
        assert client.config == test_config
        assert client.lwa_manager is not None
        assert client.aws_manager is not None
        assert client.rate_limiter is not None
        assert client.error_handler is not None
        assert client.session is not None
    
    @patch('amazon_sp_api_mcp.client.http_client.requests.Session')
    @patch('amazon_sp_api_mcp.auth.lwa_auth.LWATokenManager.get_access_token')
    @patch('amazon_sp_api_mcp.auth.aws_auth.AWSAuthManager.create_signed_request')
    @pytest.mark.asyncio
    async def test_request_success(self, mock_create_request, mock_get_token, mock_session_class, test_config):
        """Test successful API request."""
        # Mock access token
        mock_get_token.return_value = "test_access_token"
        
        # Mock AWS request
        mock_aws_request = Mock()
        mock_aws_request.method = "GET"
        mock_aws_request.url = "https://test.com/api"
        mock_aws_request.headers = {"Authorization": "test"}
        mock_aws_request.body = None
        mock_create_request.return_value = mock_aws_request
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": "test"}
        
        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        # Create client and make request
        client = SPAPIClient(test_config)
        client.session = mock_session  # Replace with mock
        
        result = await client.request(
            method="GET",
            endpoint="test",
            path="/test/api"
        )
        
        assert result["success"] is True
        assert result["data"] == "test"
        
        # Verify token was requested
        mock_get_token.assert_called_once()
        
        # Verify AWS request was created
        mock_create_request.assert_called_once()
    
    def test_validate_connection(self, test_config):
        """Test connection validation."""
        with patch('amazon_sp_api_mcp.auth.lwa_auth.LWATokenManager.validate_credentials') as mock_lwa_validate, \
             patch('amazon_sp_api_mcp.auth.aws_auth.AWSAuthManager.validate_credentials') as mock_aws_validate:
            
            mock_lwa_validate.return_value = {'valid': True}
            mock_aws_validate.return_value = {'valid': True}
            
            client = SPAPIClient(test_config)
            result = client.validate_connection()
            
            assert result['overall_valid'] is True
            assert result['lwa_auth']['valid'] is True
            assert result['aws_auth']['valid'] is True
            assert 'rate_limiter' in result