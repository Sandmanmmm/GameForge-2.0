"""
Application configuration management with Vault integration.
"""
import os
from functools import lru_cache
from typing import List, Optional
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load .env file from the project root
    env_path = Path(__file__).parent.parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass  # dotenv not installed, skip loading .env file


class Settings:
    """Application settings with environment variable and Vault support."""
    
    def __init__(self):
        # Environment
        self.environment = os.getenv("GAMEFORGE_ENV", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # Vault configuration
        self.use_vault = os.getenv("USE_VAULT", "true").lower() == "true"
        self.vault_url = os.getenv("VAULT_ADDR", "http://localhost:8200")
        self.vault_token = os.getenv("VAULT_TOKEN")
        
        # Initialize Vault client lazily
        self._vault_client = None
        self._vault_initialized = False
        
        # Initialize secrets cache for lazy loading
        self._secrets_cache = {}
        
        # Redis
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        
        # CORS
        cors_origins_str = os.getenv("CORS_ORIGINS", "*")
        self.cors_origins = (
            cors_origins_str.split(",") if cors_origins_str != "*"
            else ["*"]
        )
        
        # Trusted hosts
        allowed_hosts_str = os.getenv("ALLOWED_HOSTS", "*")
        self.allowed_hosts = (
            allowed_hosts_str.split(",") if allowed_hosts_str != "*"
            else ["*"]
        )
        
        # Domain configuration for production
        self.domain = os.getenv("DOMAIN", "localhost")
        self.frontend_domain = os.getenv("FRONTEND_DOMAIN", "")
        
        # Initialize lazy secret cache
        self._secrets_cache = {}
    
    @property
    def vault_client(self):
        """Lazily initialize and return Vault client."""
        if not self._vault_initialized:
            self._vault_initialized = True
            if self.use_vault:
                try:
                    from gameforge.core.auth_validation import get_vault_client
                    self._vault_client = get_vault_client()
                except Exception as e:
                    print(f"Warning: Failed to initialize Vault client: {e}")
                    print("Falling back to environment variables")
                    self._vault_client = None
        return self._vault_client
    
    @property
    def secret_key(self):
        """Lazily load secret key from Vault or environment."""
        if 'secret_key' not in self._secrets_cache:
            self._secrets_cache['secret_key'] = self._get_secret_or_env(
                "secrets/app",
                "secret_key",
                "SECRET_KEY",
                "dev-secret-key-change-in-production"
            )
        return self._secrets_cache['secret_key']
    
    @property
    def jwt_secret_key(self):
        """Lazily load JWT secret key from Vault or environment."""
        if 'jwt_secret_key' not in self._secrets_cache:
            self._secrets_cache['jwt_secret_key'] = self._get_secret_or_env(
                "secrets/jwt",
                "secret",
                "JWT_SECRET_KEY",
                "dev-jwt-secret-key-change-in-production"
            )
        return self._secrets_cache['jwt_secret_key']
    
    @property
    def database_url(self):
        """Lazily load database URL from Vault or environment."""
        if 'database_url' not in self._secrets_cache:
            # Check for development database environment variables first
            dev_host = os.getenv("DEV_DB_HOST")
            dev_port = os.getenv("DEV_DB_PORT", "5432")
            dev_name = os.getenv("DEV_DB_NAME")
            dev_user = os.getenv("DEV_DB_USER")
            dev_password = os.getenv("DEV_DB_PASSWORD")
            
            if all([dev_host, dev_name, dev_user, dev_password]):
                # Use development database configuration
                dev_database_url = (
                    f"postgresql+asyncpg://{dev_user}:{dev_password}@"
                    f"{dev_host}:{dev_port}/{dev_name}"
                )
                self._secrets_cache['database_url'] = dev_database_url
            else:
                # Fall back to Vault or default configuration
                gf_database_url = (
                    "postgresql+asyncpg://gameforge_user:your_password@"
                    "localhost:5432/gameforge_dev"
                )
                self._secrets_cache['database_url'] = self._get_secret_or_env(
                    "secrets/database",
                    "connection_string",
                    "DATABASE_URL",
                    gf_database_url
                )
        return self._secrets_cache['database_url']
    
    @property
    def openai_api_key(self):
        """Lazily load OpenAI API key from Vault or environment."""
        if 'openai_api_key' not in self._secrets_cache:
            self._secrets_cache['openai_api_key'] = self._get_model_token(
                "openai"
            )
        return self._secrets_cache['openai_api_key']
    
    @property
    def huggingface_token(self):
        """Lazily load Hugging Face token from Vault or environment."""
        if 'huggingface_token' not in self._secrets_cache:
            self._secrets_cache['huggingface_token'] = self._get_model_token(
                "huggingface"
            )
        return self._secrets_cache['huggingface_token']
    
    @property
    def stability_api_key(self):
        """Lazily load Stability AI API key from Vault or environment."""
        if 'stability_api_key' not in self._secrets_cache:
            self._secrets_cache['stability_api_key'] = self._get_model_token(
                "stability"
            )
        return self._secrets_cache['stability_api_key']
    
    @property
    def github_client_id(self):
        """Lazily load GitHub OAuth client ID from Vault or environment."""
        if 'github_client_id' not in self._secrets_cache:
            self._secrets_cache['github_client_id'] = self._get_secret_or_env(
                "secrets/oauth/github",
                "client_id",
                "GITHUB_CLIENT_ID",
                ""
            )
        return self._secrets_cache['github_client_id']
    
    @property
    def github_client_secret(self):
        """Lazily load GitHub OAuth client secret from Vault or environment."""
        if 'github_client_secret' not in self._secrets_cache:
            self._secrets_cache['github_client_secret'] = (
                self._get_secret_or_env(
                    "secrets/oauth/github",
                    "client_secret",
                    "GITHUB_CLIENT_SECRET",
                    ""
                )
            )
        return self._secrets_cache['github_client_secret']
    
    def _get_secret_or_env(
        self,
        vault_path: str,
        vault_key: str,
        env_var: str,
        default: str
    ) -> str:
        """
        Get secret from Vault or fall back to environment variable.
        
        Args:
            vault_path: Path in Vault
            vault_key: Key within the Vault secret
            env_var: Environment variable name
            default: Default value
            
        Returns:
            Secret value from Vault, environment, or default
        """
        if self.vault_client:
            try:
                value = self.vault_client.get_secret(vault_path, vault_key)
                if value:
                    return value
            except Exception as e:
                print(
                    f"Warning: Failed to get secret {vault_path}/"
                    f"{vault_key} from Vault: {e}"
                )
        
        return os.getenv(env_var, default)
    
    def _get_model_token(self, provider: str) -> Optional[str]:
        """
        Get AI model API token from Vault or environment.
        
        Args:
            provider: Model provider name
            
        Returns:
            API token or None
        """
        if self.vault_client:
            try:
                return self.vault_client.get_model_token(provider)
            except Exception as e:
                print(
                    f"Warning: Failed to get {provider} token from Vault: {e}"
                )
        
        # Fallback to environment variables
        env_vars = {
            "openai": "OPENAI_API_KEY",
            "huggingface": "HUGGINGFACE_TOKEN",
            "stability": "STABILITY_API_KEY"
        }
        
        env_var = env_vars.get(provider)
        return os.getenv(env_var) if env_var else None
    
    def get_vault_client(self):
        """Get the Vault client instance."""
        return self.vault_client


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
