"""
Comprehensive storage encryption and security manager for GameForge.
Handles KMS-managed encryption, storage tiers, and access controls.
"""
import os
import boto3
import hashlib
import json
import aiofiles
import asyncio
from typing import Dict, Any, Optional, Union, List, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from gameforge.core.config import get_settings
from gameforge.core.logging_config import get_structured_logger

logger = get_structured_logger(__name__)


class StorageTier(Enum):
    """Storage tier definitions."""
    HOT = "hot"          # Fast access, short-lived (in-progress assets)
    WARM = "warm"        # Standard access, medium-term (completed assets)
    COLD = "cold"        # Infrequent access, long-term (archived assets)
    FROZEN = "frozen"    # Backup and compliance (rarely accessed)


class EncryptionProvider(Enum):
    """Supported encryption providers."""
    AWS_KMS = "aws_kms"
    AZURE_KEY_VAULT = "azure_key_vault"
    GCP_KMS = "gcp_kms"
    VAULT_TRANSIT = "vault_transit"
    LOCAL_FERNET = "local_fernet"  # Fallback for development


@dataclass
class StorageConfig:
    """Storage configuration with encryption settings."""
    tier: StorageTier
    bucket_name: str
    encryption_provider: EncryptionProvider
    encryption_key_id: Optional[str] = None
    ttl_days: Optional[int] = None
    lifecycle_rules: Optional[Dict[str, Any]] = None
    access_policies: Optional[List[str]] = None


@dataclass
class EncryptedAsset:
    """Encrypted asset metadata."""
    asset_id: str
    original_path: str
    encrypted_path: str
    encryption_key_id: str
    checksum_sha256: str
    size_bytes: int
    created_at: datetime
    tier: StorageTier
    metadata: Dict[str, Any]


class StorageSecurityManager:
    """Comprehensive storage security and encryption manager."""
    
    def __init__(self):
        self.settings = get_settings()
        self._encryption_clients = {}
        self._storage_clients = {}
        
        # Load storage tier configurations
        self.storage_configs = self._load_storage_configs()
        
        # Initialize encryption providers
        self._init_encryption_providers()
        
        # Initialize storage clients
        self._init_storage_clients()
    
    def _load_storage_configs(self) -> Dict[StorageTier, StorageConfig]:
        """Load storage tier configurations."""
        return {
            StorageTier.HOT: StorageConfig(
                tier=StorageTier.HOT,
                bucket_name=os.getenv("STORAGE_BUCKET_HOT", "gameforge-hot"),
                encryption_provider=EncryptionProvider(
                    os.getenv("ENCRYPTION_PROVIDER", "aws_kms")
                ),
                encryption_key_id=os.getenv("HOT_STORAGE_KMS_KEY"),
                ttl_days=7,  # 7 days for in-progress assets
                lifecycle_rules={
                    "transition_to_warm": 2,  # Move to warm after 2 days
                    "delete_after": 7
                },
                access_policies=["gameforge:asset:read", "gameforge:asset:write"]
            ),
            StorageTier.WARM: StorageConfig(
                tier=StorageTier.WARM,
                bucket_name=os.getenv("STORAGE_BUCKET_WARM", "gameforge-warm"),
                encryption_provider=EncryptionProvider(
                    os.getenv("ENCRYPTION_PROVIDER", "aws_kms")
                ),
                encryption_key_id=os.getenv("WARM_STORAGE_KMS_KEY"),
                ttl_days=90,  # 90 days for completed assets
                lifecycle_rules={
                    "transition_to_cold": 30,  # Move to cold after 30 days
                    "delete_after": 90
                },
                access_policies=["gameforge:asset:read"]
            ),
            StorageTier.COLD: StorageConfig(
                tier=StorageTier.COLD,
                bucket_name=os.getenv("STORAGE_BUCKET_COLD", "gameforge-cold"),
                encryption_provider=EncryptionProvider(
                    os.getenv("ENCRYPTION_PROVIDER", "aws_kms")
                ),
                encryption_key_id=os.getenv("COLD_STORAGE_KMS_KEY"),
                ttl_days=365,  # 1 year for archived assets
                lifecycle_rules={
                    "transition_to_frozen": 180,  # Move to frozen after 6 months
                    "delete_after": 365
                },
                access_policies=["gameforge:asset:read"]
            ),
            StorageTier.FROZEN: StorageConfig(
                tier=StorageTier.FROZEN,
                bucket_name=os.getenv("STORAGE_BUCKET_FROZEN", "gameforge-frozen"),
                encryption_provider=EncryptionProvider(
                    os.getenv("ENCRYPTION_PROVIDER", "aws_kms")
                ),
                encryption_key_id=os.getenv("FROZEN_STORAGE_KMS_KEY"),
                ttl_days=2555,  # 7 years for compliance
                lifecycle_rules={
                    "delete_after": 2555
                },
                access_policies=["gameforge:asset:read", "gameforge:compliance:audit"]
            )
        }
    
    def _init_encryption_providers(self):
        """Initialize encryption provider clients."""
        try:
            # AWS KMS
            if os.getenv("AWS_ACCESS_KEY_ID"):
                self._encryption_clients[EncryptionProvider.AWS_KMS] = boto3.client(
                    'kms',
                    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                    region_name=os.getenv("AWS_REGION", "us-east-1")
                )
                logger.info("AWS KMS client initialized")
            
            # Azure Key Vault
            if os.getenv("AZURE_CLIENT_ID"):
                from azure.keyvault.keys import KeyClient
                from azure.identity import DefaultAzureCredential
                
                credential = DefaultAzureCredential()
                self._encryption_clients[EncryptionProvider.AZURE_KEY_VAULT] = KeyClient(
                    vault_url=os.getenv("AZURE_KEY_VAULT_URL"),
                    credential=credential
                )
                logger.info("Azure Key Vault client initialized")
            
            # GCP KMS
            if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                from google.cloud import kms
                
                self._encryption_clients[EncryptionProvider.GCP_KMS] = kms.KeyManagementServiceClient()
                logger.info("GCP KMS client initialized")
            
            # Vault Transit
            if self.settings.vault_client:
                self._encryption_clients[EncryptionProvider.VAULT_TRANSIT] = self.settings.vault_client
                logger.info("Vault Transit client initialized")
            
            # Local Fernet (fallback)
            self._init_local_encryption()
            
        except Exception as e:
            logger.error(f"Failed to initialize encryption providers: {e}")
            # Ensure at least local encryption is available
            self._init_local_encryption()
    
    def _init_local_encryption(self):
        """Initialize local Fernet encryption as fallback."""
        try:
            # Generate or load encryption key
            key_path = Path(os.getenv("LOCAL_ENCRYPTION_KEY_PATH", "/app/config/encryption.key"))
            
            if key_path.exists():
                with open(key_path, 'rb') as f:
                    key = f.read()
            else:
                # Generate new key
                password = os.getenv("ENCRYPTION_PASSWORD", "gameforge-default-key").encode()
                salt = os.getenv("ENCRYPTION_SALT", "gameforge-salt").encode()
                
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(password))
                
                # Save key securely
                key_path.parent.mkdir(parents=True, exist_ok=True)
                with open(key_path, 'wb') as f:
                    f.write(key)
                os.chmod(key_path, 0o600)  # Restrict permissions
            
            self._encryption_clients[EncryptionProvider.LOCAL_FERNET] = Fernet(key)
            logger.info("Local Fernet encryption initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize local encryption: {e}")
            raise
    
    def _init_storage_clients(self):
        """Initialize storage clients for different providers."""
        try:
            # AWS S3
            if os.getenv("AWS_ACCESS_KEY_ID"):
                self._storage_clients["aws_s3"] = boto3.client(
                    's3',
                    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                    region_name=os.getenv("AWS_REGION", "us-east-1")
                )
                logger.info("AWS S3 client initialized")
            
            # MinIO (S3-compatible)
            if os.getenv("MINIO_ACCESS_KEY"):
                from minio import Minio
                
                self._storage_clients["minio"] = Minio(
                    os.getenv("MINIO_ENDPOINT", "localhost:9000"),
                    access_key=os.getenv("MINIO_ACCESS_KEY"),
                    secret_key=os.getenv("MINIO_SECRET_KEY"),
                    secure=os.getenv("MINIO_SECURE", "false").lower() == "true"
                )
                logger.info("MinIO client initialized")
            
            # Azure Blob Storage
            if os.getenv("AZURE_STORAGE_CONNECTION_STRING"):
                from azure.storage.blob import BlobServiceClient
                
                self._storage_clients["azure_blob"] = BlobServiceClient.from_connection_string(
                    os.getenv("AZURE_STORAGE_CONNECTION_STRING")
                )
                logger.info("Azure Blob Storage client initialized")
            
            # Google Cloud Storage
            if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                from google.cloud import storage
                
                self._storage_clients["gcs"] = storage.Client()
                logger.info("Google Cloud Storage client initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize storage clients: {e}")
    
    async def encrypt_data(
        self, 
        data: bytes, 
        provider: EncryptionProvider, 
        key_id: Optional[str] = None
    ) -> Tuple[bytes, str]:
        """
        Encrypt data using specified provider.
        
        Returns:
            Tuple of (encrypted_data, encryption_metadata)
        """
        try:
            if provider == EncryptionProvider.AWS_KMS:
                return await self._encrypt_aws_kms(data, key_id)
            elif provider == EncryptionProvider.AZURE_KEY_VAULT:
                return await self._encrypt_azure_kv(data, key_id)
            elif provider == EncryptionProvider.GCP_KMS:
                return await self._encrypt_gcp_kms(data, key_id)
            elif provider == EncryptionProvider.VAULT_TRANSIT:
                return await self._encrypt_vault_transit(data, key_id)
            elif provider == EncryptionProvider.LOCAL_FERNET:
                return await self._encrypt_local_fernet(data)
            else:
                raise ValueError(f"Unsupported encryption provider: {provider}")
                
        except Exception as e:
            logger.error(f"Encryption failed with {provider}: {e}")
            # Fallback to local encryption
            if provider != EncryptionProvider.LOCAL_FERNET:
                logger.warning("Falling back to local encryption")
                return await self._encrypt_local_fernet(data)
            raise
    
    async def decrypt_data(
        self, 
        encrypted_data: bytes, 
        provider: EncryptionProvider, 
        encryption_metadata: str
    ) -> bytes:
        """Decrypt data using specified provider."""
        try:
            if provider == EncryptionProvider.AWS_KMS:
                return await self._decrypt_aws_kms(encrypted_data, encryption_metadata)
            elif provider == EncryptionProvider.AZURE_KEY_VAULT:
                return await self._decrypt_azure_kv(encrypted_data, encryption_metadata)
            elif provider == EncryptionProvider.GCP_KMS:
                return await self._decrypt_gcp_kms(encrypted_data, encryption_metadata)
            elif provider == EncryptionProvider.VAULT_TRANSIT:
                return await self._decrypt_vault_transit(encrypted_data, encryption_metadata)
            elif provider == EncryptionProvider.LOCAL_FERNET:
                return await self._decrypt_local_fernet(encrypted_data)
            else:
                raise ValueError(f"Unsupported encryption provider: {provider}")
                
        except Exception as e:
            logger.error(f"Decryption failed with {provider}: {e}")
            raise
    
    async def _encrypt_aws_kms(self, data: bytes, key_id: str) -> Tuple[bytes, str]:
        """Encrypt data using AWS KMS."""
        client = self._encryption_clients.get(EncryptionProvider.AWS_KMS)
        if not client:
            raise ValueError("AWS KMS client not initialized")
        
        response = client.encrypt(
            KeyId=key_id,
            Plaintext=data,
            EncryptionAlgorithm='SYMMETRIC_DEFAULT'
        )
        
        metadata = {
            "key_id": key_id,
            "encryption_algorithm": "SYMMETRIC_DEFAULT",
            "encrypted_at": datetime.utcnow().isoformat()
        }
        
        return response['CiphertextBlob'], json.dumps(metadata)
    
    async def _decrypt_aws_kms(self, encrypted_data: bytes, metadata: str) -> bytes:
        """Decrypt data using AWS KMS."""
        client = self._encryption_clients.get(EncryptionProvider.AWS_KMS)
        if not client:
            raise ValueError("AWS KMS client not initialized")
        
        response = client.decrypt(
            CiphertextBlob=encrypted_data,
            EncryptionAlgorithm='SYMMETRIC_DEFAULT'
        )
        
        return response['Plaintext']
    
    async def _encrypt_vault_transit(self, data: bytes, key_name: str) -> Tuple[bytes, str]:
        """Encrypt data using Vault Transit engine."""
        vault_client = self._encryption_clients.get(EncryptionProvider.VAULT_TRANSIT)
        if not vault_client:
            raise ValueError("Vault Transit client not initialized")
        
        # Encode data as base64 for Vault
        encoded_data = base64.b64encode(data).decode('utf-8')
        
        response = vault_client.encrypt_data(key_name, encoded_data)
        
        metadata = {
            "key_name": key_name,
            "encrypted_at": datetime.utcnow().isoformat(),
            "vault_version": response.get("version", 1)
        }
        
        return response['ciphertext'].encode(), json.dumps(metadata)
    
    async def _decrypt_vault_transit(self, encrypted_data: bytes, metadata: str) -> bytes:
        """Decrypt data using Vault Transit engine."""
        vault_client = self._encryption_clients.get(EncryptionProvider.VAULT_TRANSIT)
        if not vault_client:
            raise ValueError("Vault Transit client not initialized")
        
        ciphertext = encrypted_data.decode()
        response = vault_client.decrypt_data(ciphertext)
        
        # Decode from base64
        return base64.b64decode(response['plaintext'])
    
    async def _encrypt_local_fernet(self, data: bytes) -> Tuple[bytes, str]:
        """Encrypt data using local Fernet encryption."""
        fernet = self._encryption_clients.get(EncryptionProvider.LOCAL_FERNET)
        if not fernet:
            raise ValueError("Local Fernet encryption not initialized")
        
        encrypted_data = fernet.encrypt(data)
        
        metadata = {
            "encryption_type": "fernet",
            "encrypted_at": datetime.utcnow().isoformat()
        }
        
        return encrypted_data, json.dumps(metadata)
    
    async def _decrypt_local_fernet(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using local Fernet encryption."""
        fernet = self._encryption_clients.get(EncryptionProvider.LOCAL_FERNET)
        if not fernet:
            raise ValueError("Local Fernet encryption not initialized")
        
        return fernet.decrypt(encrypted_data)
    
    def calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA256 checksum of data."""
        return hashlib.sha256(data).hexdigest()
    
    async def store_encrypted_asset(
        self,
        asset_id: str,
        data: bytes,
        tier: StorageTier,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EncryptedAsset:
        """
        Store an asset with encryption in the specified storage tier.
        
        Args:
            asset_id: Unique identifier for the asset
            data: Raw asset data to encrypt and store
            tier: Storage tier to use
            metadata: Additional metadata for the asset
            
        Returns:
            EncryptedAsset object with storage details
        """
        config = self.storage_configs[tier]
        
        # Calculate checksum of original data
        checksum = self.calculate_checksum(data)
        
        # Encrypt the data
        encrypted_data, encryption_metadata = await self.encrypt_data(
            data, config.encryption_provider, config.encryption_key_id
        )
        
        # Generate storage path
        storage_path = f"{tier.value}/{asset_id[:2]}/{asset_id[2:4]}/{asset_id}.enc"
        
        # Store encrypted data
        await self._store_to_bucket(
            config.bucket_name,
            storage_path,
            encrypted_data,
            tier
        )
        
        # Create asset record
        encrypted_asset = EncryptedAsset(
            asset_id=asset_id,
            original_path=f"/{asset_id}",
            encrypted_path=f"s3://{config.bucket_name}/{storage_path}",
            encryption_key_id=config.encryption_key_id or "local",
            checksum_sha256=checksum,
            size_bytes=len(data),
            created_at=datetime.utcnow(),
            tier=tier,
            metadata={
                "encryption_metadata": encryption_metadata,
                "encryption_provider": config.encryption_provider.value,
                **(metadata or {})
            }
        )
        
        logger.info(
            f"Stored encrypted asset {asset_id} in {tier.value} tier",
            extra={
                "asset_id": asset_id,
                "tier": tier.value,
                "size_bytes": len(data),
                "encrypted_size_bytes": len(encrypted_data),
                "checksum": checksum
            }
        )
        
        return encrypted_asset
    
    async def retrieve_encrypted_asset(
        self,
        encrypted_asset: EncryptedAsset
    ) -> bytes:
        """
        Retrieve and decrypt an asset.
        
        Args:
            encrypted_asset: EncryptedAsset metadata
            
        Returns:
            Decrypted asset data
        """
        config = self.storage_configs[encrypted_asset.tier]
        
        # Extract storage path from encrypted_path
        storage_path = encrypted_asset.encrypted_path.split('/', 3)[-1]
        
        # Retrieve encrypted data
        encrypted_data = await self._retrieve_from_bucket(
            config.bucket_name,
            storage_path
        )
        
        # Decrypt the data
        encryption_metadata = encrypted_asset.metadata.get("encryption_metadata", "{}")
        provider = EncryptionProvider(
            encrypted_asset.metadata.get("encryption_provider", "local_fernet")
        )
        
        decrypted_data = await self.decrypt_data(
            encrypted_data,
            provider,
            encryption_metadata
        )
        
        # Verify checksum
        calculated_checksum = self.calculate_checksum(decrypted_data)
        if calculated_checksum != encrypted_asset.checksum_sha256:
            raise ValueError(
                f"Checksum mismatch for asset {encrypted_asset.asset_id}. "
                f"Expected: {encrypted_asset.checksum_sha256}, "
                f"Got: {calculated_checksum}"
            )
        
        logger.info(
            f"Retrieved and decrypted asset {encrypted_asset.asset_id}",
            extra={
                "asset_id": encrypted_asset.asset_id,
                "tier": encrypted_asset.tier.value,
                "size_bytes": len(decrypted_data)
            }
        )
        
        return decrypted_data
    
    async def _store_to_bucket(
        self,
        bucket_name: str,
        object_key: str,
        data: bytes,
        tier: StorageTier
    ):
        """Store data to the appropriate storage backend."""
        try:
            # Try AWS S3 first
            if "aws_s3" in self._storage_clients:
                storage_class = self._get_s3_storage_class(tier)
                
                self._storage_clients["aws_s3"].put_object(
                    Bucket=bucket_name,
                    Key=object_key,
                    Body=data,
                    StorageClass=storage_class,
                    ServerSideEncryption='aws:kms' if tier != StorageTier.HOT else 'AES256'
                )
                logger.info(f"Stored to AWS S3: s3://{bucket_name}/{object_key}")
                return
            
            # Fallback to MinIO
            if "minio" in self._storage_clients:
                self._storage_clients["minio"].put_object(
                    bucket_name,
                    object_key,
                    data=io.BytesIO(data),
                    length=len(data)
                )
                logger.info(f"Stored to MinIO: {bucket_name}/{object_key}")
                return
            
            # Local filesystem fallback
            local_path = Path(f"/app/storage/{bucket_name}/{object_key}")
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(local_path, 'wb') as f:
                await f.write(data)
            
            logger.info(f"Stored locally: {local_path}")
            
        except Exception as e:
            logger.error(f"Failed to store to bucket {bucket_name}: {e}")
            raise
    
    async def _retrieve_from_bucket(
        self,
        bucket_name: str,
        object_key: str
    ) -> bytes:
        """Retrieve data from the appropriate storage backend."""
        try:
            # Try AWS S3 first
            if "aws_s3" in self._storage_clients:
                response = self._storage_clients["aws_s3"].get_object(
                    Bucket=bucket_name,
                    Key=object_key
                )
                return response['Body'].read()
            
            # Fallback to MinIO
            if "minio" in self._storage_clients:
                response = self._storage_clients["minio"].get_object(
                    bucket_name,
                    object_key
                )
                return response.read()
            
            # Local filesystem fallback
            local_path = Path(f"/app/storage/{bucket_name}/{object_key}")
            
            async with aiofiles.open(local_path, 'rb') as f:
                return await f.read()
            
        except Exception as e:
            logger.error(f"Failed to retrieve from bucket {bucket_name}: {e}")
            raise
    
    def _get_s3_storage_class(self, tier: StorageTier) -> str:
        """Get appropriate S3 storage class for tier."""
        storage_class_map = {
            StorageTier.HOT: "STANDARD",
            StorageTier.WARM: "STANDARD_IA",
            StorageTier.COLD: "GLACIER",
            StorageTier.FROZEN: "DEEP_ARCHIVE"
        }
        return storage_class_map[tier]
    
    async def setup_bucket_policies(self):
        """Setup bucket policies and lifecycle rules for all storage tiers."""
        for tier, config in self.storage_configs.items():
            try:
                await self._setup_bucket_lifecycle(config)
                await self._setup_bucket_encryption(config)
                await self._setup_bucket_access_policy(config)
                
                logger.info(f"Setup complete for {tier.value} tier bucket: {config.bucket_name}")
                
            except Exception as e:
                logger.error(f"Failed to setup bucket for {tier.value} tier: {e}")
    
    async def _setup_bucket_lifecycle(self, config: StorageConfig):
        """Setup lifecycle rules for a storage bucket."""
        if not config.lifecycle_rules or "aws_s3" not in self._storage_clients:
            return
        
        lifecycle_config = {
            'Rules': [{
                'ID': f'{config.tier.value}-lifecycle',
                'Status': 'Enabled',
                'Filter': {'Prefix': f'{config.tier.value}/'},
                'Transitions': [],
                'Expiration': {}
            }]
        }
        
        rule = lifecycle_config['Rules'][0]
        
        # Add transitions based on tier
        if config.tier == StorageTier.HOT and 'transition_to_warm' in config.lifecycle_rules:
            rule['Transitions'].append({
                'Days': config.lifecycle_rules['transition_to_warm'],
                'StorageClass': 'STANDARD_IA'
            })
        
        if 'transition_to_cold' in config.lifecycle_rules:
            rule['Transitions'].append({
                'Days': config.lifecycle_rules['transition_to_cold'],
                'StorageClass': 'GLACIER'
            })
        
        if 'delete_after' in config.lifecycle_rules:
            rule['Expiration']['Days'] = config.lifecycle_rules['delete_after']
        
        try:
            self._storage_clients["aws_s3"].put_bucket_lifecycle_configuration(
                Bucket=config.bucket_name,
                LifecycleConfiguration=lifecycle_config
            )
            logger.info(f"Lifecycle policy applied to {config.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to apply lifecycle policy to {config.bucket_name}: {e}")
    
    async def _setup_bucket_encryption(self, config: StorageConfig):
        """Setup server-side encryption for a storage bucket."""
        if "aws_s3" not in self._storage_clients:
            return
        
        try:
            encryption_config = {
                'Rules': [{
                    'ApplyServerSideEncryptionByDefault': {
                        'SSEAlgorithm': 'aws:kms' if config.encryption_key_id else 'AES256'
                    },
                    'BucketKeyEnabled': True
                }]
            }
            
            if config.encryption_key_id:
                encryption_config['Rules'][0]['ApplyServerSideEncryptionByDefault']['KMSMasterKeyID'] = config.encryption_key_id
            
            self._storage_clients["aws_s3"].put_bucket_encryption(
                Bucket=config.bucket_name,
                ServerSideEncryptionConfiguration=encryption_config
            )
            logger.info(f"Encryption policy applied to {config.bucket_name}")
            
        except Exception as e:
            logger.error(f"Failed to apply encryption policy to {config.bucket_name}: {e}")
    
    async def _setup_bucket_access_policy(self, config: StorageConfig):
        """Setup IAM access policy for a storage bucket."""
        if "aws_s3" not in self._storage_clients or not config.access_policies:
            return
        
        # Generate bucket policy based on access policies
        policy_document = {
            "Version": "2012-10-17",
            "Statement": []
        }
        
        # Add statements based on access policies
        for policy in config.access_policies:
            if policy == "gameforge:asset:read":
                policy_document["Statement"].append({
                    "Sid": "AllowAssetRead",
                    "Effect": "Allow",
                    "Principal": {"AWS": f"arn:aws:iam::{os.getenv('AWS_ACCOUNT_ID')}:role/GameForgeAssetReader"},
                    "Action": ["s3:GetObject"],
                    "Resource": f"arn:aws:s3:::{config.bucket_name}/*"
                })
            
            elif policy == "gameforge:asset:write":
                policy_document["Statement"].append({
                    "Sid": "AllowAssetWrite",
                    "Effect": "Allow",
                    "Principal": {"AWS": f"arn:aws:iam::{os.getenv('AWS_ACCOUNT_ID')}:role/GameForgeAssetWriter"},
                    "Action": ["s3:PutObject", "s3:DeleteObject"],
                    "Resource": f"arn:aws:s3:::{config.bucket_name}/*"
                })
        
        try:
            self._storage_clients["aws_s3"].put_bucket_policy(
                Bucket=config.bucket_name,
                Policy=json.dumps(policy_document)
            )
            logger.info(f"Access policy applied to {config.bucket_name}")
            
        except Exception as e:
            logger.error(f"Failed to apply access policy to {config.bucket_name}: {e}")


# Global storage security manager instance
storage_security_manager = StorageSecurityManager()