"""
AWS authentication and request signing for SP-API.
"""

import hashlib
import hmac
import urllib.parse
from datetime import datetime
from typing import Dict, Any, Optional
import logging

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials
from botocore.session import Session

from ..config import SPAPIConfig

logger = logging.getLogger(__name__)

class AWSAuthManager:
    """Manages AWS authentication and request signing for SP-API."""
    
    def __init__(self, config: SPAPIConfig):
        self.config = config
        self._credentials: Optional[Credentials] = None
        self._session: Optional[Session] = None
        
    def get_credentials(self) -> Credentials:
        """Get AWS credentials, assuming role if configured."""
        if self._credentials:
            return self._credentials
            
        try:
            if self.config.aws_role_arn:
                # Assume role for SP-API access
                sts_client = boto3.client(
                    'sts',
                    aws_access_key_id=self.config.aws_access_key_id,
                    aws_secret_access_key=self.config.aws_secret_access_key,
                    aws_session_token=self.config.aws_session_token,
                    region_name=self.config.aws_region
                )
                
                response = sts_client.assume_role(
                    RoleArn=self.config.aws_role_arn,
                    RoleSessionName='sp-api-mcp-session'
                )
                
                credentials = response['Credentials']
                self._credentials = Credentials(
                    access_key=credentials['AccessKeyId'],
                    secret_key=credentials['SecretAccessKey'],
                    token=credentials['SessionToken']
                )
                
                logger.info("Successfully assumed SP-API role")
                
            else:
                # Use direct credentials
                self._credentials = Credentials(
                    access_key=self.config.aws_access_key_id,
                    secret_key=self.config.aws_secret_access_key,
                    token=self.config.aws_session_token
                )
                
                logger.info("Using direct AWS credentials")
                
            return self._credentials
            
        except Exception as e:
            logger.error(f"Failed to get AWS credentials: {e}")
            raise Exception(f"AWS credentials error: {e}")
    
    def sign_request(self, request: AWSRequest) -> None:
        """Sign an AWS request using SigV4."""
        credentials = self.get_credentials()
        
        # Create SigV4 signer
        signer = SigV4Auth(
            credentials,
            'execute-api',  # SP-API service name
            self.config.aws_region
        )
        
        # Sign the request
        signer.add_auth(request)
        logger.debug(f"Signed request to {request.url}")
    
    def create_signed_request(
        self, 
        method: str, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        data: Optional[bytes] = None
    ) -> AWSRequest:
        """Create and sign an AWS request."""
        if headers is None:
            headers = {}
            
        # Create AWS request
        request = AWSRequest(
            method=method,
            url=url,
            headers=headers,
            data=data
        )
        
        # Sign the request
        self.sign_request(request)
        
        return request
    
    def validate_credentials(self) -> Dict[str, Any]:
        """Validate AWS credentials by testing STS GetCallerIdentity."""
        try:
            sts_client = boto3.client(
                'sts',
                aws_access_key_id=self.config.aws_access_key_id,
                aws_secret_access_key=self.config.aws_secret_access_key,
                aws_session_token=self.config.aws_session_token,
                region_name=self.config.aws_region
            )
            
            # Test credentials
            response = sts_client.get_caller_identity()
            
            result = {
                "valid": True,
                "account_id": response.get('Account'),
                "user_id": response.get('UserId'),
                "arn": response.get('Arn'),
                "region": self.config.aws_region,
                "role_arn": self.config.aws_role_arn,
                "message": "AWS credentials are valid"
            }
            
            # Test role assumption if configured
            if self.config.aws_role_arn:
                try:
                    assume_response = sts_client.assume_role(
                        RoleArn=self.config.aws_role_arn,
                        RoleSessionName='sp-api-validation-test'
                    )
                    result["role_assumed"] = True
                    result["message"] += " and role assumption successful"
                except Exception as role_error:
                    result["role_assumed"] = False
                    result["role_error"] = str(role_error)
                    result["message"] += " but role assumption failed"
            
            return result
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "message": "AWS credentials validation failed"
            }
    
    def refresh_credentials(self) -> None:
        """Force refresh of AWS credentials."""
        self._credentials = None
        self._session = None
        logger.info("AWS credentials cache cleared")