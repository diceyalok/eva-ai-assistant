"""
ModelManager - Singleton for efficient model loading and caching
Solves the biggest performance bottleneck: model reloading
"""
import os
import logging
import asyncio
from typing import Optional, Dict, Any
from sentence_transformers import SentenceTransformer
import torch

logger = logging.getLogger(__name__)

class ModelManager:
    """Singleton model manager that loads models once and keeps them cached"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._models = {}
            self._loading_locks = {}
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"ModelManager initialized on device: {self._device}")
            ModelManager._initialized = True
    
    async def get_embedding_model(self, model_name: str = "all-mpnet-base-v2") -> SentenceTransformer:
        """Get cached embedding model (loads once, reuses forever)"""
        if model_name in self._models:
            logger.debug(f"Using cached embedding model: {model_name}")
            return self._models[model_name]
        
        # Prevent multiple simultaneous loads of the same model
        if model_name not in self._loading_locks:
            self._loading_locks[model_name] = asyncio.Lock()
        
        async with self._loading_locks[model_name]:
            # Double-check after acquiring lock
            if model_name in self._models:
                return self._models[model_name]
            
            logger.info(f"Loading embedding model: {model_name}")
            
            # Try local paths first, then download
            local_paths = [
                './data/models/embeddings',
                'data/models/embeddings', 
                '/app/models/embeddings'
            ]
            
            model = None
            for path in local_paths:
                try:
                    if os.path.exists(path):
                        model = SentenceTransformer(path)
                        logger.info(f"✅ Loaded embedding model from: {path}")
                        break
                except Exception as e:
                    logger.debug(f"Failed to load from {path}: {e}")
                    continue
            
            # Fallback to download if local not found
            if model is None:
                try:
                    model = SentenceTransformer(model_name)
                    logger.info(f"✅ Downloaded embedding model: {model_name}")
                except Exception as e:
                    logger.error(f"Failed to load embedding model: {e}")
                    raise
            
            # Cache the model
            self._models[model_name] = model
            logger.info(f"🎯 Embedding model cached successfully: {model_name}")
            
            return model
    
    async def get_whisper_model(self, model_size: str = "small"):
        """Get cached Whisper model for voice processing"""
        import whisper
        
        model_key = f"whisper_{model_size}"
        
        if model_key in self._models:
            logger.debug(f"Using cached Whisper model: {model_size}")
            return self._models[model_key]
        
        if model_key not in self._loading_locks:
            self._loading_locks[model_key] = asyncio.Lock()
        
        async with self._loading_locks[model_key]:
            if model_key in self._models:
                return self._models[model_key]
            
            logger.info(f"Loading Whisper model: {model_size}")
            
            try:
                model = whisper.load_model(model_size)
                self._models[model_key] = model
                logger.info(f"✅ Whisper model cached: {model_size}")
                return model
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}")
                raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models"""
        return {
            "loaded_models": list(self._models.keys()),
            "device": self._device,
            "gpu_available": torch.cuda.is_available(),
            "memory_usage": self._get_memory_usage()
        }
    
    def _get_memory_usage(self) -> Dict[str, str]:
        """Get current memory usage"""
        try:
            if torch.cuda.is_available():
                return {
                    "gpu_allocated": f"{torch.cuda.memory_allocated() / 1024**3:.2f} GB",
                    "gpu_cached": f"{torch.cuda.memory_reserved() / 1024**3:.2f} GB"
                }
            else:
                return {"cpu_only": "No GPU available"}
        except Exception:
            return {"error": "Could not retrieve memory info"}
    
    async def warm_up_models(self):
        """Pre-load frequently used models for faster startup"""
        logger.info("🔥 Warming up models...")
        
        try:
            # Load embedding model
            await self.get_embedding_model()
            
            # Load Whisper if voice is enabled
            whisper_size = os.getenv("WHISPER_MODEL_SIZE", "small")
            await self.get_whisper_model(whisper_size)
            
            logger.info("🎯 Model warm-up completed!")
        except Exception as e:
            logger.error(f"Model warm-up failed: {e}")
    
    def clear_cache(self):
        """Clear all cached models (for debugging/memory management)"""
        logger.info("Clearing model cache...")
        self._models.clear()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("Model cache cleared")

# Singleton instance
model_manager = ModelManager()