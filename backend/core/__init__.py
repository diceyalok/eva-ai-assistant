"""
Eva Core - Clean Architecture Components
High-performance, well-structured services
"""
from .model_manager import model_manager
from .config_manager import config
from .ai_service import ai_service
from .memory_service import memory_service
from .voice_service import voice_service
from .telegram_gateway import telegram_gateway

__all__ = [
    'model_manager', 
    'config', 
    'ai_service', 
    'memory_service', 
    'voice_service',
    'telegram_gateway'
]