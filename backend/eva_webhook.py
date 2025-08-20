#!/usr/bin/env python3
"""
Eva Lite FastAPI Server - PRD Compliant Production Backend
Webhook mode with vLLM integration, XTTS v2, and comprehensive monitoring
"""

import asyncio
import logging
import os
from typing import Dict, Any
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import json

# Eva components
from core.config_manager import config
from core.model_manager import model_manager
from core.ai_service import ai_service
from core.memory_service import memory_service
from core.voice_service import voice_service
from core.telegram_gateway import telegram_gateway
from core.lora_service import lora_service
from core.reasoning_service import reasoning_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app with comprehensive API documentation
app = FastAPI(
    title="Eva Lite - AI Assistant Backend",
    description="Production-ready Telegram AI assistant with vLLM, LoRA personalities, and advanced reasoning",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Global state
services_initialized = False
telegram_app = None

async def initialize_services():
    """Initialize all Eva services"""
    global services_initialized
    
    if services_initialized:
        return
    
    logger.info("🚀 Initializing Eva services for webhook mode...")
    
    try:
        # Validate configuration
        if not config.telegram.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not configured")
        
        # Initialize model manager first
        logger.info("🔥 Warming up models...")
        await model_manager.warm_up_models()
        
        # Initialize services
        logger.info("🤖 Initializing AI service...")
        await ai_service.initialize()
        
        logger.info("🧠 Initializing memory service...")
        await memory_service.initialize()
        
        logger.info("🎵 Initializing voice service...")
        await voice_service.initialize()
        
        logger.info("📡 Initializing Telegram gateway...")
        await telegram_gateway.initialize()
        
        # Initialize LoRA service for personality management
        logger.info("🔧 Initializing LoRA service...")
        await lora_service.initialize()
        
        # Initialize reasoning service
        logger.info("🧠 Initializing reasoning service...")
        await reasoning_service.initialize()
        
        services_initialized = True
        logger.info("✅ All Eva Lite services initialized successfully!")
        
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    """FastAPI startup event"""
    await initialize_services()

@app.on_event("shutdown")
async def shutdown_event():
    """FastAPI shutdown event"""
    logger.info("🛑 Shutting down Eva services...")
    
    try:
        await ai_service.cleanup()
        await memory_service.cleanup()
        await voice_service.cleanup()
        await telegram_gateway.stop()
        logger.info("✅ Eva Lite services shut down successfully")
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint for RunPod"""
    if not services_initialized:
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    # Check service health
    ai_status = await ai_service.get_service_status()
    memory_stats = await memory_service.get_memory_stats()
    
    # Check all services
    voice_health = await voice_service.health_check()
    lora_stats = await lora_service.get_adapter_stats()
    
    return {
        "status": "healthy",
        "services": {
            "ai": ai_status.get("initialized", False),
            "memory": memory_stats.get("initialized", False),
            "voice": voice_health.get("service", False),
            "telegram": services_initialized,
            "lora": lora_stats.get("service_initialized", False),
            "reasoning": True  # Reasoning service always available
        },
        "performance": {
            "gpu_available": os.getenv("CUDA_VISIBLE_DEVICES") is not None,
            "vllm_connected": await check_vllm_connection(),
            "response_target": "≤2.5s text, ≤1.2s voice"
        },
        "version": "1.0.0",
        "architecture": "Eva Lite PRD Compliant"
    }

@app.get("/metrics")
async def metrics():
    """Metrics endpoint for monitoring"""
    if not services_initialized:
        return {"error": "Services not initialized"}
    
    try:
        memory_stats = await memory_service.get_memory_stats()
        ai_status = await ai_service.get_service_status()
        
        lora_stats = await lora_service.get_adapter_stats()
        
        return {
            "memory": memory_stats,
            "ai": ai_status,
            "lora": lora_stats,
            "uptime": "webhook_mode",
            "gpu_memory": get_gpu_memory_usage(),
            "vllm_status": await get_vllm_status()
        }
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        return {"error": str(e)}

async def check_vllm_connection() -> bool:
    """Check if vLLM server is accessible"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://vllm:8000/health")
            return response.status_code == 200
    except Exception:
        return False

async def get_vllm_status() -> dict:
    """Get vLLM server status and model information"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get model info
            models_response = await client.get("http://vllm:8000/v1/models")
            if models_response.status_code == 200:
                models_data = models_response.json()
                return {
                    "connected": True,
                    "models": models_data.get("data", []),
                    "base_model": "meta-llama/Meta-Llama-3-8B-Instruct"
                }
    except Exception as e:
        logger.debug(f"vLLM status check failed: {e}")
    
    return {"connected": False, "error": "vLLM server not accessible"}

def get_gpu_memory_usage():
    """Get GPU memory usage if available"""
    try:
        import torch
        if torch.cuda.is_available():
            memory_allocated = torch.cuda.memory_allocated(0)
            memory_reserved = torch.cuda.memory_reserved(0)
            return {
                "allocated_mb": memory_allocated / 1024 / 1024,
                "reserved_mb": memory_reserved / 1024 / 1024,
                "device_count": torch.cuda.device_count(),
                "gpu_name": torch.cuda.get_device_name(0)
            }
    except Exception:
        pass
    return {"gpu_available": False}

@app.post("/webhook")
async def webhook_handler(request: Request):
    """Main webhook handler for Telegram"""
    if not services_initialized:
        raise HTTPException(status_code=503, detail="Services not ready")
    
    try:
        # Get request body
        body = await request.body()
        update_dict = json.loads(body.decode('utf-8'))
        
        # Process update through Telegram gateway
        await telegram_gateway.process_webhook_update(update_dict)
        
        return JSONResponse({"status": "ok"})
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/set-webhook")
async def set_webhook():
    """Set Telegram webhook URL"""
    try:
        webhook_url = os.getenv("WEBHOOK_URL")
        if not webhook_url:
            raise ValueError("WEBHOOK_URL environment variable not set")
        
        result = await telegram_gateway.set_webhook(f"{webhook_url}/webhook")
        return {"status": "success", "result": result}
        
    except Exception as e:
        logger.error(f"Set webhook error: {e}")
        return {"status": "error", "error": str(e)}

@app.get("/status")
async def detailed_status():
    """Comprehensive status endpoint for monitoring"""
    if not services_initialized:
        return {"status": "initializing", "services_ready": False}
    
    try:
        # Get status from all services
        ai_status = await ai_service.get_service_status()
        memory_stats = await memory_service.get_memory_stats()
        voice_health = await voice_service.health_check()
        lora_stats = await lora_service.get_adapter_stats()
        gateway_stats = await telegram_gateway.get_gateway_stats()
        vllm_status = await get_vllm_status()
        
        return {
            "status": "operational",
            "timestamp": asyncio.get_event_loop().time(),
            "services": {
                "ai_service": ai_status,
                "memory_service": memory_stats,
                "voice_service": voice_health,
                "lora_service": lora_stats,
                "telegram_gateway": gateway_stats,
                "vllm_server": vllm_status
            },
            "performance": {
                "gpu_memory": get_gpu_memory_usage(),
                "targets": {
                    "text_response": "≤2.5s",
                    "voice_response": "≤1.2s",
                    "cost_target": "≤₹20k/month"
                }
            },
            "architecture": {
                "mode": "webhook",
                "backend": "FastAPI + vLLM",
                "model": "Llama-3 8B + LoRA",
                "voice": "XTTS v2",
                "memory": "ChromaDB + Redis"
            }
        }
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return {"status": "error", "error": str(e)}

@app.post("/lora/switch")
async def switch_personality(personality: str):
    """Switch LoRA personality adapter"""
    if not services_initialized:
        raise HTTPException(status_code=503, detail="Services not ready")
    
    try:
        success = await lora_service.load_adapter(personality)
        if success:
            return {"status": "success", "personality": personality}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to load personality: {personality}")
    except Exception as e:
        logger.error(f"Personality switch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/lora/adapters")
async def list_adapters():
    """List available LoRA adapters"""
    if not services_initialized:
        raise HTTPException(status_code=503, detail="Services not ready")
    
    try:
        adapters = await lora_service.list_available_adapters()
        return adapters
    except Exception as e:
        logger.error(f"Adapter listing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    logger.info(f"🚀 Starting Eva webhook server on {host}:{port}")
    
    # Run with production-optimized settings
    uvicorn.run(
        "eva_webhook:app",
        host=host,
        port=port,
        workers=1,  # Single worker for GPU memory efficiency
        access_log=True,
        log_level="info",
        loop="asyncio",
        reload=False,  # Disable reload in production
        timeout_keep_alive=30,
        timeout_graceful_shutdown=30
    )