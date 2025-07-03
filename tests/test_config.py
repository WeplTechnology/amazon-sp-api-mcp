"""
Tests for configuration module.
"""

import os
import pytest
from amazon_sp_api_mcp.config import SPAPIConfig, load_config

def test_spapi_config_validation():
    """Test SPAPIConfig validation."""
    # Valid config
    config = SPAPIConfig(
        client_id="test_client_id",
        client_secret="test_client_secret",
        refresh_token="test_refresh_token",
        aws_access_key_id="test_access_key",
        aws_secret_access_key="test_secret_key",
        aws_region="eu-west-1",
        aws_role_arn="arn:aws:iam::123456789012:role/test-role"
    )
    
    assert config.region == "EU"
    assert config.base_url == "https://sellingpartnerapi-eu.amazon.com"
    assert len(config.marketplace_ids) > 0

def test_spapi_config_missing_required_field():
    """Test SPAPIConfig with missing required field."""
    with pytest.raises(ValueError, match="Missing required configuration"):
        SPAPIConfig(
            client_id="",  # Missing required field
            client_secret="test_client_secret",
            refresh_token="test_refresh_token",
            aws_access_key_id="test_access_key",
            aws_secret_access_key="test_secret_key",
            aws_region="eu-west-1",
            aws_role_arn="arn:aws:iam::123456789012:role/test-role"
        )

def test_sandbox_configuration():
    """Test sandbox configuration."""
    config = SPAPIConfig(
        client_id="test_client_id",
        client_secret="test_client_secret",
        refresh_token="test_refresh_token",
        aws_access_key_id="test_access_key",
        aws_secret_access_key="test_secret_key",
        aws_region="eu-west-1",
        aws_role_arn="arn:aws:iam::123456789012:role/test-role",
        sandbox=True
    )
    
    assert "sandbox" in config.base_url

def test_load_config_from_env(monkeypatch):
    """Test loading configuration from environment variables."""
    # Set environment variables
    env_vars = {
        "AMAZON_SP_CLIENT_ID": "test_client_id",
        "AMAZON_SP_CLIENT_SECRET": "test_client_secret",
        "AMAZON_SP_REFRESH_TOKEN": "test_refresh_token",
        "AWS_ACCESS_KEY_ID": "test_access_key",
        "AWS_SECRET_ACCESS_KEY": "test_secret_key",
        "AWS_REGION": "eu-west-1",
        "AWS_ROLE_ARN": "arn:aws:iam::123456789012:role/test-role",
        "AMAZON_SP_MARKETPLACE_IDS": "A1RKKUPIHCS9HS,A13V1IB3VIYZZH"
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    config = load_config()
    
    assert config.client_id == "test_client_id"
    assert config.aws_region == "eu-west-1"
    assert len(config.marketplace_ids) == 2
    assert "A1RKKUPIHCS9HS" in config.marketplace_ids