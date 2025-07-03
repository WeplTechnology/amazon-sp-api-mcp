"""
Configuration management for Amazon SP-API MCP.
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

# Setup logging
logging.basicConfig(
    level=getattr(logging, os.getenv("AMAZON_SP_LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@dataclass
class SPAPIConfig:
    """Configuration for Amazon SP-API."""
    
    # LWA Credentials
    client_id: str
    client_secret: str 
    refresh_token: str
    
    # AWS Credentials
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str
    aws_role_arn: str
    aws_session_token: Optional[str] = None
    
    # SP-API Configuration
    region: str = "EU"
    base_url: str = "https://sellingpartnerapi-eu.amazon.com"
    marketplace_ids: List[str] = None
    
    # Optional Configuration
    sandbox: bool = False
    rate_limit_buffer: float = 0.1
    retry_attempts: int = 3
    timeout: int = 30
    debug: bool = False
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.marketplace_ids is None:
            self.marketplace_ids = ["A1RKKUPIHCS9HS"]  # Default to Spain
            
        if self.sandbox:
            self.base_url = f"https://sandbox.sellingpartnerapi-{self.region.lower()}.amazon.com"
            
        # Validate required fields
        required_fields = [
            "client_id", "client_secret", "refresh_token",
            "aws_access_key_id", "aws_secret_access_key", 
            "aws_region", "aws_role_arn"
        ]
        
        for field in required_fields:
            if not getattr(self, field):
                raise ValueError(f"Missing required configuration: {field}")
                
        logger.info(f"SP-API Config initialized for region {self.region}")

def load_config() -> SPAPIConfig:
    """Load configuration from environment variables."""
    
    # Parse marketplace IDs
    marketplace_ids_str = os.getenv("AMAZON_SP_MARKETPLACE_IDS", "A1RKKUPIHCS9HS")
    marketplace_ids = [mid.strip() for mid in marketplace_ids_str.split(",") if mid.strip()]
    
    config = SPAPIConfig(
        # LWA Credentials
        client_id=os.getenv("AMAZON_SP_CLIENT_ID", ""),
        client_secret=os.getenv("AMAZON_SP_CLIENT_SECRET", ""),
        refresh_token=os.getenv("AMAZON_SP_REFRESH_TOKEN", ""),
        
        # AWS Credentials
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        aws_region=os.getenv("AWS_REGION", "eu-west-1"),
        aws_role_arn=os.getenv("AWS_ROLE_ARN", ""),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
        
        # SP-API Configuration
        region=os.getenv("AMAZON_SP_REGION", "EU").upper(),
        base_url=os.getenv("AMAZON_SP_BASE_URL", "https://sellingpartnerapi-eu.amazon.com"),
        marketplace_ids=marketplace_ids,
        
        # Optional Configuration
        sandbox=os.getenv("AMAZON_SP_SANDBOX", "false").lower() == "true",
        rate_limit_buffer=float(os.getenv("AMAZON_SP_RATE_LIMIT_BUFFER", "0.1")),
        retry_attempts=int(os.getenv("AMAZON_SP_RETRY_ATTEMPTS", "3")),
        timeout=int(os.getenv("AMAZON_SP_TIMEOUT", "30")),
        debug=os.getenv("AMAZON_SP_DEBUG", "false").lower() == "true"
    )
    
    return config

# European Marketplace IDs
EUROPE_MARKETPLACES = {
    "A1RKKUPIHCS9HS": "Amazon.es (Spain)",
    "A1F83G8C2ARO7P": "Amazon.co.uk (United Kingdom)", 
    "A13V1IB3VIYZZH": "Amazon.de (Germany)",
    "APJ6JRA9NG5V4": "Amazon.it (Italy)",
    "A13V1IB3VIYZZH": "Amazon.fr (France)",
    "A1805IZSGTT6HS": "Amazon.nl (Netherlands)",
    "A2NODRKZP88ZB9": "Amazon.se (Sweden)",
    "A1C3SOZRARQ6R3": "Amazon.pl (Poland)"
}

# Rate limits per endpoint (requests per second, burst capacity)
RATE_LIMITS = {
    "orders": {"rate": 0.0167, "burst": 20},
    "inventory": {"rate": 2.0, "burst": 30},
    "reports": {"rate": 0.0222, "burst": 10},
    "feeds": {"rate": 0.0222, "burst": 10},
    "catalog": {"rate": 5.0, "burst": 15},
    "listings": {"rate": 5.0, "burst": 10},
    "finances": {"rate": 0.5, "burst": 30},
    "tokens": {"rate": 0.0167, "burst": 15}
}