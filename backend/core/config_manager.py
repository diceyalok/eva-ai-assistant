"""
ConfigurationManager - Centralized configuration management
No more scattered settings across multiple files
"""
import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

@dataclass
class TelegramConfig:
    """Telegram bot configuration"""
    bot_token: str
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    
    @property
    def is_webhook_mode(self) -> bool:
        return bool(self.webhook_url)

@dataclass 
class AIConfig:
    """AI model configuration"""
    openai_api_key: Optional[str]
    vllm_base_url: str
    local_model_name: str
    embedding_model: str
    max_tokens: int = 800
    temperature: float = 0.7
    
    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

@dataclass
class VoiceConfig:
    """Voice processing configuration"""
    whisper_model_size: str
    tts_enabled: bool = True
    audio_cache_ttl: int = 3600

@dataclass
class DatabaseConfig:
    """Database configuration"""
    redis_url: str
    chroma_host: str
    chroma_port: int
    postgres_url: Optional[str] = None

@dataclass
class PerformanceConfig:
    """Performance and resource configuration"""
    max_monthly_cost: float
    rate_limit_per_user: int
    rate_limit_global: int
    memory_decay_lambda: float
    max_memory_items: int
    gpu_memory_utilization: float = 0.6

class ConfigurationManager:
    """Centralized configuration manager"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            # Load environment variables
            load_dotenv()
            
            # Initialize configurations
            self.telegram = self._load_telegram_config()
            self.ai = self._load_ai_config()
            self.voice = self._load_voice_config()
            self.database = self._load_database_config()
            self.performance = self._load_performance_config()
            
            # Environment info
            self.environment = os.getenv("ENVIRONMENT", "development")
            self.log_level = os.getenv("LOG_LEVEL", "INFO")
            
            ConfigurationManager._initialized = True
            logger.info(f"✅ Configuration loaded for {self.environment} environment")
    
    def _load_telegram_config(self) -> TelegramConfig:
        """Load Telegram configuration"""
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required!")
        
        return TelegramConfig(
            bot_token=bot_token,
            webhook_url=os.getenv("TELEGRAM_WEBHOOK_URL"),
            webhook_secret=os.getenv("TELEGRAM_WEBHOOK_SECRET")
        )
    
    def _load_ai_config(self) -> AIConfig:
        """Load AI configuration"""
        return AIConfig(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            vllm_base_url=os.getenv("VLLM_BASE_URL", "http://localhost:8002/v1"),
            local_model_name=os.getenv("LOCAL_MODEL_NAME", "eva-local"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "all-mpnet-base-v2"),
            max_tokens=int(os.getenv("MAX_TOKENS", "800")),
            temperature=float(os.getenv("TEMPERATURE", "0.7"))
        )
    
    def _load_voice_config(self) -> VoiceConfig:
        """Load voice configuration"""
        return VoiceConfig(
            whisper_model_size=os.getenv("WHISPER_MODEL_SIZE", "small"),
            tts_enabled=os.getenv("TTS_ENABLED", "true").lower() == "true",
            audio_cache_ttl=int(os.getenv("AUDIO_CACHE_TTL", "3600"))
        )
    
    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration"""
        return DatabaseConfig(
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            chroma_host=os.getenv("CHROMA_HOST", "localhost"),
            chroma_port=int(os.getenv("CHROMA_PORT", "8001")),
            postgres_url=os.getenv("POSTGRES_URL")
        )
    
    def _load_performance_config(self) -> PerformanceConfig:
        """Load performance configuration"""
        return PerformanceConfig(
            max_monthly_cost=float(os.getenv("MAX_MONTHLY_COST_INR", "5000")),
            rate_limit_per_user=int(os.getenv("RATE_LIMIT_PER_USER", "10")),
            rate_limit_global=int(os.getenv("RATE_LIMIT_GLOBAL", "60")),
            memory_decay_lambda=float(os.getenv("MEMORY_DECAY_LAMBDA", "0.1")),
            max_memory_items=int(os.getenv("MAX_MEMORY_ITEMS", "1000")),
            gpu_memory_utilization=float(os.getenv("GPU_MEMORY_UTILIZATION", "0.6"))
        )
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for debugging"""
        return {
            "environment": self.environment,
            "telegram": {
                "webhook_mode": self.telegram.is_webhook_mode,
                "has_token": bool(self.telegram.bot_token)
            },
            "ai": {
                "has_openai": self.ai.has_openai,
                "vllm_url": self.ai.vllm_base_url,
                "local_model": self.ai.local_model_name
            },
            "voice": {
                "whisper_size": self.voice.whisper_model_size,
                "tts_enabled": self.voice.tts_enabled
            },
            "database": {
                "redis_url": self.database.redis_url,
                "chroma_host": self.database.chroma_host
            }
        }
    
    def validate_config(self) -> bool:
        """Validate critical configuration"""
        try:
            # Check required fields
            assert self.telegram.bot_token, "Telegram bot token missing"
            
            if not self.ai.has_openai:
                logger.warning("⚠️ No OpenAI API key - only local AI will be used")
            
            logger.info("✅ Configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Configuration validation failed: {e}")
            return False

# Singleton instance
config = ConfigurationManager()