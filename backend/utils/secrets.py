"""
AWS Secrets Manager Integration
================================
Securely retrieve secrets from AWS Secrets Manager for production deployments.

Features:
- Async retrieval using aioboto3
- In-memory caching to reduce API calls
- Fallback to environment variables for local development
- Type-safe secret parsing

Usage:
    from backend.utils.secrets import get_secret, get_database_credentials

    # Get entire secret as dict
    secret_dict = await get_secret("potential-parakeet/prod")

    # Get database credentials
    db_creds = await get_database_credentials()
"""

import json
import os
from typing import Dict, Any, Optional
from functools import lru_cache

import aioboto3
from aws_lambda_powertools import Logger

logger = Logger(service="secrets-manager")

# In-memory cache for secrets (Lambda container reuse optimization)
_secrets_cache: Dict[str, Any] = {}


async def get_secret(secret_name: str, region_name: str = "us-east-1") -> Dict[str, Any]:
    """
    Retrieve a secret from AWS Secrets Manager.

    Args:
        secret_name: Name or ARN of the secret
        region_name: AWS region (default: us-east-1)

    Returns:
        Dictionary containing the secret key-value pairs

    Raises:
        Exception: If secret retrieval fails
    """
    # Return cached secret if available
    if secret_name in _secrets_cache:
        logger.debug(f"Using cached secret: {secret_name}")
        return _secrets_cache[secret_name]

    logger.info(f"Retrieving secret from AWS Secrets Manager: {secret_name}")

    try:
        # Create Secrets Manager client
        session = aioboto3.Session()
        async with session.client(
            service_name="secretsmanager",
            region_name=region_name
        ) as client:
            response = await client.get_secret_value(SecretId=secret_name)

        # Parse secret string as JSON
        if "SecretString" in response:
            secret_dict = json.loads(response["SecretString"])
        else:
            # Binary secrets (rare)
            secret_dict = {"SecretBinary": response["SecretBinary"]}

        # Cache the secret
        _secrets_cache[secret_name] = secret_dict
        logger.info(f"Successfully retrieved and cached secret: {secret_name}")
        return secret_dict

    except Exception as e:
        logger.error(f"Failed to retrieve secret {secret_name}: {str(e)}")
        raise


async def get_database_credentials() -> Dict[str, str]:
    """
    Retrieve database credentials from Secrets Manager.

    Expected secret format:
    {
        "NEON_DATABASE_URL": "postgresql://user:pass@host/db?sslmode=require",
        "DB_USERNAME": "username",
        "DB_PASSWORD": "password",
        "DB_HOST": "hostname",
        "DB_NAME": "database_name"
    }

    Returns:
        Dictionary with database credentials

    Fallback:
        If AWS_LAMBDA_FUNCTION_NAME is not set (local dev),
        returns credentials from environment variables.
    """
    # Local development: use environment variables
    if not os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        logger.info("Local development detected - using environment variables")
        return {
            "NEON_DATABASE_URL": os.getenv("NEON_DATABASE_URL", ""),
            "DB_USERNAME": os.getenv("DB_USERNAME", ""),
            "DB_PASSWORD": os.getenv("DB_PASSWORD", ""),
            "DB_HOST": os.getenv("DB_HOST", ""),
            "DB_NAME": os.getenv("DB_NAME", ""),
        }

    # Production: retrieve from Secrets Manager
    secret_name = os.getenv("AWS_SECRETS_MANAGER_NAME", "potential-parakeet/prod")
    region = os.getenv("AWS_REGION", "us-east-1")

    return await get_secret(secret_name, region)


async def get_api_keys() -> Dict[str, str]:
    """
    Retrieve API keys from Secrets Manager.

    Expected secret format:
    {
        "TIINGO_API_KEY": "your_tiingo_key",
        "POLYGON_API_KEY": "your_polygon_key",
        "ALPHA_VANTAGE_API_KEY": "your_alpha_vantage_key"
    }

    Returns:
        Dictionary with API keys
    """
    # Local development: use environment variables
    if not os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        logger.info("Local development detected - using environment variables for API keys")
        return {
            "TIINGO_API_KEY": os.getenv("TIINGO_API_KEY", ""),
            "POLYGON_API_KEY": os.getenv("POLYGON_API_KEY", ""),
            "ALPHA_VANTAGE_API_KEY": os.getenv("ALPHA_VANTAGE_API_KEY", ""),
        }

    # Production: retrieve from Secrets Manager
    secret_name = f"{os.getenv('AWS_SECRETS_MANAGER_NAME', 'potential-parakeet/prod')}/api-keys"
    region = os.getenv("AWS_REGION", "us-east-1")

    return await get_secret(secret_name, region)


def clear_secrets_cache() -> None:
    """
    Clear the in-memory secrets cache.

    Useful for testing or forcing a refresh.
    """
    global _secrets_cache
    _secrets_cache.clear()
    logger.info("Secrets cache cleared")


# Sync version for legacy code (to be deprecated)
def get_secret_sync(secret_name: str, region_name: str = "us-east-1") -> Dict[str, Any]:
    """
    LEGACY: Synchronous version of get_secret.

    ⚠️ This will be deprecated. Use async version instead.
    Only for code that hasn't been migrated to async yet.
    """
    import boto3
    from botocore.exceptions import ClientError

    # Return cached secret if available
    if secret_name in _secrets_cache:
        return _secrets_cache[secret_name]

    try:
        client = boto3.client(service_name="secretsmanager", region_name=region_name)
        response = client.get_secret_value(SecretId=secret_name)

        if "SecretString" in response:
            secret_dict = json.loads(response["SecretString"])
        else:
            secret_dict = {"SecretBinary": response["SecretBinary"]}

        _secrets_cache[secret_name] = secret_dict
        return secret_dict

    except ClientError as e:
        logger.error(f"Failed to retrieve secret {secret_name}: {str(e)}")
        raise
