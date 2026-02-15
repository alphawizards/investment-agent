"""
S3 Cache Storage Adapter
========================
Replaces local file system storage for Parquet files.
Uses aioboto3 for async S3 operations.
"""

import os
from io import BytesIO
import pandas as pd
import aioboto3
from botocore.exceptions import ClientError
from typing import Optional, Any
from backend.config import settings
import logging

logger = logging.getLogger(__name__)

class S3CacheStorage:
    """Async S3 storage adapter for DataFrames."""
    
    def __init__(self, bucket: str = settings.S3_BUCKET_NAME, prefix: str = settings.S3_CACHE_PREFIX):
        self.bucket = bucket
        self.prefix = prefix
        self.session = aioboto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
            region_name=settings.AWS_REGION
        )
    
    async def read_parquet(self, key: str) -> pd.DataFrame:
        """
        Read Parquet file from S3.
        Returns empty DataFrame if file not found.
        """
        if not settings.USE_S3_CACHE:
            # Fallback to local file system (implied by usage context, or raise error)
            # For migration safety, we strictly follow the S3 path here.
            pass

        full_key = f"{self.prefix}{key}"
        
        async with self.session.client("s3") as s3:
            try:
                obj = await s3.get_object(Bucket=self.bucket, Key=full_key)
                body = await obj['Body'].read()
                return pd.read_parquet(BytesIO(body))
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    logger.info(f"Cache miss for {full_key}")
                    return pd.DataFrame()
                logger.error(f"S3 read error: {e}")
                raise
            except Exception as e:
                logger.error(f"Error reading parquet from S3: {e}")
                return pd.DataFrame()

    async def write_parquet(self, key: str, df: pd.DataFrame) -> None:
        """Write DataFrame to S3 as Parquet."""
        full_key = f"{self.prefix}{key}"
        
        try:
            buffer = BytesIO()
            df.to_parquet(buffer, engine='pyarrow', compression='snappy')
            buffer.seek(0)
            
            async with self.session.client("s3") as s3:
                await s3.put_object(
                    Bucket=self.bucket, 
                    Key=full_key, 
                    Body=buffer.getvalue(),
                    ContentType='application/octet-stream'
                )
                logger.info(f"Wrote to S3: {full_key}")
        except Exception as e:
            logger.error(f"Error writing to S3: {e}")
            raise

    async def exists(self, key: str) -> bool:
        """Check if key exists in S3."""
        full_key = f"{self.prefix}{key}"
        async with self.session.client("s3") as s3:
            try:
                await s3.head_object(Bucket=self.bucket, Key=full_key)
                return True
            except ClientError:
                return False

# Global instance
s3_cache = S3CacheStorage()
