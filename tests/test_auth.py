"""
Tests for authentication modules.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from amazon_sp_api_mcp.config import SPAPIConfig
from amazon_sp_api_mcp.auth.lwa_auth import LWATokenManager
from amazon_sp_api_mcp.auth.aws_auth import AWSAuthManager

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

class TestLWATokenManager:
    """Tests for LWA Token Manager."""
    
    def test_init(self, test_config):
        """Test LWA Token Manager initialization."""
        token_manager = LWATokenManager(test_config)
        
        assert token_manager.config == test_config
        assert token_manager.access_token is None
        assert token_manager.token_expires_at is None
    
    @patch('amazon_sp_api_mcp.auth.lwa_auth.requests.post')
    def test_refresh_access_token_success(self, mock_post, test_config):
        """Test successful token refresh."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "expires_in": 3600
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        token_manager = LWATokenManager(test_config)
        token_manager._refresh_access_token()
        
        assert token_manager.access_token == "test_access_token"
        assert token_manager.token_expires_at is not None
        
        # Verify request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "refresh_token" in call_args[1]['data']
        assert test_config.refresh_token == call_args[1]['data']['refresh_token']
    
    @patch('amazon_sp_api_mcp.auth.lwa_auth.requests.post')
    def test_refresh_access_token_failure(self, mock_post, test_config):
        """Test token refresh failure."""
        # Mock failed response
        mock_post.side_effect = Exception("Network error")
        
        token_manager = LWATokenManager(test_config)
        
        with pytest.raises(Exception, match="LWA token refresh failed"):
            token_manager._refresh_access_token()
    
    def test_is_token_expired(self, test_config):
        """Test token expiration check."""
        token_manager = LWATokenManager(test_config)
        
        # No token should be considered expired
        assert token_manager._is_token_expired() is True
        
        # Set a token that expires soon
        from datetime import datetime, timedelta
        token_manager.access_token = "test_token"
        token_manager.token_expires_at = datetime.utcnow() + timedelta(minutes=2)
        
        # Should be considered expired (within 5 minute buffer)
        assert token_manager._is_token_expired() is True
        
        # Set a token that expires later
        token_manager.token_expires_at = datetime.utcnow() + timedelta(minutes=10)
        
        # Should not be considered expired
        assert token_manager._is_token_expired() is False

class TestAWSAuthManager:
    """Tests for AWS Auth Manager."""
    
    def test_init(self, test_config):
        """Test AWS Auth Manager initialization."""
        auth_manager = AWSAuthManager(test_config)
        
        assert auth_manager.config == test_config
        assert auth_manager._credentials is None
        assert auth_manager._session is None
    
    @patch('amazon_sp_api_mcp.auth.aws_auth.boto3.client')
    def test_get_credentials_with_role(self, mock_boto_client, test_config):
        """Test getting credentials with role assumption."""
        # Mock STS client and assume role response
        mock_sts_client = Mock()
        mock_sts_client.assume_role.return_value = {
            'Credentials': {
                'AccessKeyId': 'assumed_access_key',
                'SecretAccessKey': 'assumed_secret_key',
                'SessionToken': 'assumed_session_token'
            }
        }
        mock_boto_client.return_value = mock_sts_client
        
        auth_manager = AWSAuthManager(test_config)
        credentials = auth_manager.get_credentials()
        
        assert credentials.access_key == 'assumed_access_key'
        assert credentials.secret_key == 'assumed_secret_key'
        assert credentials.token == 'assumed_session_token'
        
        # Verify assume role was called
        mock_sts_client.assume_role.assert_called_once_with(
            RoleArn=test_config.aws_role_arn,
            RoleSessionName='sp-api-mcp-session'
        )