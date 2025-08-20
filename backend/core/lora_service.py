"""
LoRAService - LoRA adapter management for personality fine-tuning
Manages personality-specific LoRA adapters per PRD specifications
"""

import asyncio
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import httpx
from .config_manager import config

logger = logging.getLogger(__name__)

class LoRAService:
    """Manages LoRA adapters for personality-specific model fine-tuning"""
    
    def __init__(self):
        self._initialized = False
        self.vllm_url = "http://vllm:8000"
        self.adapters_path = "/app/adapters"
        
        # Personality-specific LoRA adapters as per PRD
        self.personality_adapters = {
            "friendly": {
                "name": "eva-friendly-lora",
                "path": f"{self.adapters_path}/eva-friendly",
                "description": "Warm, empathetic, conversational personality",
                "loaded": False
            },
            "formal": {
                "name": "eva-formal-lora", 
                "path": f"{self.adapters_path}/eva-formal",
                "description": "Professional, structured, authoritative personality",
                "loaded": False
            },
            "gen-z": {
                "name": "eva-genz-lora",
                "path": f"{self.adapters_path}/eva-genz", 
                "description": "Casual, trendy, internet-savvy personality",
                "loaded": False
            }
        }
        
        self.current_adapter = None
        
    async def initialize(self):
        """Initialize LoRA service and check adapter availability"""
        if self._initialized:
            return
            
        try:
            # Check vLLM server availability
            await self._check_vllm_server()
            
            # Verify adapter files exist
            await self._verify_adapters()
            
            # Load default adapter (friendly)
            await self.load_adapter("friendly")
            
            self._initialized = True
            logger.info("🔧 LoRAService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize LoRAService: {e}")
            logger.warning("⚠️ LoRA service disabled - vLLM server not available")
            # Don't raise - allow Eva to continue without LoRA
    
    async def load_adapter(self, personality: str) -> bool:
        """Load specific LoRA adapter for personality"""
        
        if not self._initialized:
            await self.initialize()
            
        if not self._initialized:
            logger.debug("LoRA operation skipped - service not available")
            return False
            
        if personality not in self.personality_adapters:
            logger.error(f"Unknown personality: {personality}")
            return False
            
        try:
            adapter_info = self.personality_adapters[personality]
            
            # Skip if already loaded
            if self.current_adapter == personality and adapter_info["loaded"]:
                logger.debug(f"✅ LoRA adapter {personality} already loaded")
                return True
            
            # Unload current adapter if different
            if self.current_adapter and self.current_adapter != personality:
                await self._unload_current_adapter()
            
            # Load new adapter via vLLM API
            success = await self._load_adapter_via_api(adapter_info)
            
            if success:
                # Update state
                adapter_info["loaded"] = True
                self.current_adapter = personality
                
                logger.info(f"✅ LoRA adapter '{personality}' loaded successfully")
                return True
            else:
                logger.error(f"Failed to load LoRA adapter '{personality}'")
                return False
                
        except Exception as e:
            logger.error(f"LoRA adapter loading failed: {e}")
            return False
    
    async def get_current_adapter(self) -> Optional[str]:
        """Get currently loaded adapter personality"""
        return self.current_adapter
    
    async def list_available_adapters(self) -> Dict[str, Any]:
        """List all available personality adapters"""
        
        adapters = {}
        for personality, info in self.personality_adapters.items():
            adapters[personality] = {
                "name": info["name"],
                "description": info["description"], 
                "loaded": info["loaded"],
                "available": await self._check_adapter_exists(info["path"])
            }
        
        return {
            "current_adapter": self.current_adapter,
            "adapters": adapters,
            "total_count": len(self.personality_adapters)
        }
    
    async def optimize_for_personality(self, personality: str, context: List[Dict]) -> Dict[str, Any]:
        """Optimize model parameters for specific personality"""
        
        if not self._initialized:
            await self.initialize()
            
        if not self._initialized:
            logger.debug("LoRA optimization skipped - service not available")
            return {"success": False, "error": "LoRA service not available", "adapter": None}
        
        try:
            # Load appropriate adapter
            adapter_loaded = await self.load_adapter(personality)
            if not adapter_loaded:
                return {"error": f"Failed to load adapter for {personality}"}
            
            # Get personality-specific parameters
            params = self._get_personality_parameters(personality, context)
            
            # Apply parameters to vLLM
            success = await self._apply_generation_parameters(params)
            
            return {
                "success": success,
                "personality": personality,
                "adapter": self.personality_adapters[personality]["name"],
                "parameters": params,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Personality optimization failed: {e}")
            return {"error": str(e)}
    
    async def _check_vllm_server(self):
        """Check if vLLM server is available"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.vllm_url}/health")
                if response.status_code != 200:
                    raise Exception(f"vLLM server unhealthy: {response.status_code}")
                    
        except Exception as e:
            raise Exception(f"vLLM server not available: {e}")
    
    async def _verify_adapters(self):
        """Verify LoRA adapter files exist"""
        missing_adapters = []
        
        for personality, info in self.personality_adapters.items():
            if not await self._check_adapter_exists(info["path"]):
                missing_adapters.append(personality)
        
        if missing_adapters:
            logger.warning(f"Missing LoRA adapters: {missing_adapters}")
            logger.info("Creating placeholder adapters for development...")
            await self._create_placeholder_adapters(missing_adapters)
    
    async def _check_adapter_exists(self, adapter_path: str) -> bool:
        """Check if adapter directory and files exist"""
        try:
            # Check for adapter_config.json and adapter_model.bin
            config_file = os.path.join(adapter_path, "adapter_config.json")
            model_file = os.path.join(adapter_path, "adapter_model.bin") 
            
            return os.path.exists(config_file) and os.path.exists(model_file)
            
        except Exception:
            return False
    
    async def _create_placeholder_adapters(self, missing_personalities: List[str]):
        """Create placeholder adapters for development"""
        
        for personality in missing_personalities:
            try:
                adapter_info = self.personality_adapters[personality]
                adapter_path = adapter_info["path"]
                
                # Create adapter directory
                os.makedirs(adapter_path, exist_ok=True)
                
                # Create minimal adapter config
                config_content = {
                    "peft_type": "LORA",
                    "task_type": "CAUSAL_LM",
                    "r": 16,
                    "lora_alpha": 32,
                    "lora_dropout": 0.1,
                    "target_modules": ["q_proj", "v_proj"],
                    "personality": personality,
                    "base_model_name_or_path": "meta-llama/Meta-Llama-3-8B-Instruct"
                }
                
                config_path = os.path.join(adapter_path, "adapter_config.json")
                import json
                with open(config_path, 'w') as f:
                    json.dump(config_content, f, indent=2)
                
                # Create empty adapter model file (placeholder)
                model_path = os.path.join(adapter_path, "adapter_model.bin")
                import torch
                torch.save({}, model_path)
                
                logger.info(f"📁 Created placeholder adapter: {personality}")
                
            except Exception as e:
                logger.error(f"Failed to create placeholder adapter {personality}: {e}")
    
    async def _load_adapter_via_api(self, adapter_info: Dict[str, Any]) -> bool:
        """Load adapter via vLLM API"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # vLLM LoRA loading API call
                response = await client.post(
                    f"{self.vllm_url}/v1/adapters",
                    json={
                        "adapter_name": adapter_info["name"],
                        "adapter_path": adapter_info["path"],
                        "adapter_type": "lora"
                    }
                )
                
                if response.status_code == 200:
                    logger.debug(f"✅ LoRA adapter loaded: {adapter_info['name']}")
                    return True
                else:
                    logger.error(f"vLLM adapter loading failed: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"LoRA adapter API call failed: {e}")
            return False
    
    async def _unload_current_adapter(self):
        """Unload currently loaded adapter"""
        if not self.current_adapter:
            return
            
        try:
            current_info = self.personality_adapters[self.current_adapter]
            
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.delete(
                    f"{self.vllm_url}/v1/adapters/{current_info['name']}"
                )
                
                if response.status_code == 200:
                    current_info["loaded"] = False
                    logger.debug(f"✅ LoRA adapter unloaded: {current_info['name']}")
                else:
                    logger.warning(f"Failed to unload adapter: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Adapter unloading failed: {e}")
    
    def _get_personality_parameters(self, personality: str, context: List[Dict]) -> Dict[str, Any]:
        """Get generation parameters optimized for personality"""
        
        base_params = {
            "max_tokens": config.ai.max_tokens,
            "temperature": config.ai.temperature,
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }
        
        # Personality-specific parameter adjustments
        personality_adjustments = {
            "friendly": {
                "temperature": 0.8,  # More creative and warm
                "top_p": 0.9,
                "frequency_penalty": 0.1,  # Reduce repetition
                "presence_penalty": 0.1
            },
            "formal": {
                "temperature": 0.4,  # More structured and consistent
                "top_p": 0.8,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0
            },
            "gen-z": {
                "temperature": 0.9,  # Most creative and expressive
                "top_p": 0.95,
                "frequency_penalty": 0.2,  # Encourage varied expressions
                "presence_penalty": 0.15
            }
        }
        
        # Apply personality adjustments
        if personality in personality_adjustments:
            base_params.update(personality_adjustments[personality])
        
        # Dynamic adjustments based on context
        if len(context) > 10:  # Long conversations need more consistency
            base_params["temperature"] *= 0.9
        
        return base_params
    
    async def _apply_generation_parameters(self, params: Dict[str, Any]) -> bool:
        """Apply generation parameters to vLLM server"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.vllm_url}/v1/config",
                    json={"generation_params": params}
                )
                
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Parameter application failed: {e}")
            return False
    
    async def get_adapter_stats(self) -> Dict[str, Any]:
        """Get detailed adapter usage statistics"""
        
        return {
            "service_initialized": self._initialized,
            "current_adapter": self.current_adapter,
            "vllm_url": self.vllm_url,
            "adapters_path": self.adapters_path,
            "personality_count": len(self.personality_adapters),
            "loaded_adapters": [
                p for p, info in self.personality_adapters.items() 
                if info["loaded"]
            ],
            "available_adapters": [
                p for p, info in self.personality_adapters.items()
                if await self._check_adapter_exists(info["path"])
            ]
        }

# Global instance
lora_service = LoRAService()